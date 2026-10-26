"""Servidor web en produccion: WhiteNoise, gunicorn, conexiones a la base y Sentry.

Los ajustes se leen al importar el modulo, asi que cada caso corre en un
proceso aparte con `importar()`.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from config.tests.test_production import PRODUCCION, importar

BACKEND = Path(__file__).resolve().parents[2]
MANIFEST = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MW = "whitenoise.middleware.WhiteNoiseMiddleware"
SECURITY_MW = "django.middleware.security.SecurityMiddleware"
# Host que no existe: si algo intentara enviar un evento, fallaria en vez de salir a internet.
DSN = "https://clavepublica@sentry.invalid/1"


def leer(modulo, codigo, **entorno):
    """Corre `codigo` (que imprime un JSON en su ultima linea) y lo devuelve."""
    salida = importar(modulo, codigo, **entorno)
    assert salida.returncode == 0, salida.stderr[-2000:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


# ── WhiteNoise ────────────────────────────────────────────────────────────────

ESTATICOS = (
    "import json\n"
    "from django.conf import settings as s\n"
    "print(json.dumps({'static': s.STORAGES['staticfiles']['BACKEND'], 'mw': list(s.MIDDLEWARE)}))\n"
)


def test_produccion_sirve_los_estaticos_con_whitenoise_y_manifest():
    a = leer("config.settings.production", ESTATICOS, **PRODUCCION)

    assert a["static"] == MANIFEST
    mw = a["mw"]
    # Justo despues de SecurityMiddleware, como pide la documentacion de WhiteNoise.
    assert mw.index(WHITENOISE_MW) == mw.index(SECURITY_MW) + 1


def test_el_health_va_antes_que_todo_en_produccion():
    mw = leer("config.settings.production", ESTATICOS, **PRODUCCION)["mw"]

    assert "health" in mw[0].lower()


def test_desarrollo_y_pruebas_no_exigen_collectstatic():
    """Con el manifest, cada plantilla del admin fallaria sin un collectstatic previo."""
    a = leer("config.settings.development", ESTATICOS)

    assert a["static"] != MANIFEST
    assert WHITENOISE_MW not in a["mw"]


# ── Base de datos ─────────────────────────────────────────────────────────────

BASE = (
    "import json\n"
    "from django.conf import settings as s\n"
    "d = s.DATABASES['default']\n"
    "print(json.dumps({'age': d['CONN_MAX_AGE'], 'checks': d.get('CONN_HEALTH_CHECKS'),\n"
    "                  'ssl': d.get('OPTIONS', {}).get('sslmode')}))\n"
)


def test_produccion_reutiliza_conexiones_y_exige_ssl_por_defecto():
    a = leer("config.settings.production", BASE, DB_CONN_MAX_AGE="", DB_SSLMODE="", **PRODUCCION)

    assert a == {"age": 60, "checks": True, "ssl": "require"}


def test_produccion_lee_conn_max_age_y_sslmode_del_entorno():
    a = leer("config.settings.production", BASE, DB_CONN_MAX_AGE="15", DB_SSLMODE="verify-full", **PRODUCCION)

    assert a == {"age": 15, "checks": True, "ssl": "verify-full"}


def test_desarrollo_no_cambia_la_conexion_a_la_base():
    """Postgres local sin SSL: el sslmode=require de produccion no debe filtrarse."""
    a = leer("config.settings.development", BASE)

    assert a["ssl"] != "require"
    assert a["age"] == 0


# ── Sentry ────────────────────────────────────────────────────────────────────

SENTRY = (
    "import json, sentry_sdk\n"
    "c = sentry_sdk.get_client()\n"
    "o = c.options\n"
    "print(json.dumps({\n"
    "    'activo': c.is_active(), 'dsn': o.get('dsn'), 'pii': o.get('send_default_pii'),\n"
    "    'entorno': o.get('environment'), 'trazas': o.get('traces_sample_rate'),\n"
    "    'integraciones': sorted(type(i).__name__ for i in o.get('integrations', [])),\n"
    "}))\n"
)


def test_sentry_apagado_si_no_hay_dsn():
    a = leer("config.settings.production", SENTRY, SENTRY_DSN="", **PRODUCCION)

    assert a["activo"] is False


def test_el_relleno_de_terraform_apaga_sentry_y_google_maps():
    """Parameter Store no admite valores vacios: Terraform deja "sin-configurar"
    hasta que alguien pegue el DSN y la clave reales."""
    codigo = SENTRY.replace(
        "'activo': c.is_active(),",
        "'activo': c.is_active(), 'maps': __import__('django.conf').conf.settings.GOOGLE_MAPS_API_KEY,",
    )
    a = leer("config.settings.production", codigo, SENTRY_DSN="sin-configurar",
             GOOGLE_MAPS_API_KEY="sin-configurar", **PRODUCCION)

    assert a["activo"] is False
    assert a["maps"] == ""


def test_produccion_arranca_aunque_las_variables_de_sentry_no_existan():
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("SENTRY_")}
    salida = subprocess.run(
        [sys.executable, "-c",
         "import os, django\n"
         "os.environ['DJANGO_SETTINGS_MODULE']='config.settings.production'\n"
         "django.setup()\n"],
        cwd=BACKEND, capture_output=True, text=True, timeout=120,
        env={**entorno, "DB_NAME": "x", "DB_USER": "x", "DB_PASSWORD": "x", "DB_HOST": "x",
             "SECRET_KEY": "clave-de-prueba-solo-para-tests", **PRODUCCION},
    )

    assert salida.returncode == 0, salida.stderr[-2000:]


def test_sentry_encendido_con_dsn_sin_datos_personales():
    a = leer(
        "config.settings.production", SENTRY, SENTRY_DSN=DSN,
        SENTRY_ENVIRONMENT="produccion", SENTRY_TRACES_SAMPLE_RATE="0.25", **PRODUCCION,
    )

    assert a["activo"] is True
    assert a["dsn"] == DSN
    assert a["pii"] is False  # hay datos de hospitales
    assert a["entorno"] == "produccion"
    assert a["trazas"] == 0.25
    assert "DjangoIntegration" in a["integraciones"]
    assert "CeleryIntegration" in a["integraciones"]


def test_sentry_trazas_apagadas_por_defecto():
    a = leer("config.settings.production", SENTRY, SENTRY_DSN=DSN,
             SENTRY_TRACES_SAMPLE_RATE="", SENTRY_ENVIRONMENT="", **PRODUCCION)

    assert a["trazas"] == 0


def test_desarrollo_nunca_inicia_sentry():
    a = leer("config.settings.development", SENTRY, SENTRY_DSN=DSN)

    assert a["activo"] is False


# ── gunicorn ──────────────────────────────────────────────────────────────────

def gunicorn(**entorno):
    """Carga gunicorn.conf.py como lo hace gunicorn (un script con variables sueltas)."""
    codigo = (
        "import json, runpy\n"
        "c = runpy.run_path('gunicorn.conf.py')\n"
        "print(json.dumps({k: v for k, v in c.items() if not k.startswith('_') and "
        "isinstance(v, (int, str, bool, type(None)))}))\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("GUNICORN_")}
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=BACKEND, env={**env, **entorno},
        capture_output=True, text=True, timeout=60,
    )
    assert salida.returncode == 0, salida.stderr[-2000:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_gunicorn_trae_valores_por_defecto():
    c = gunicorn()

    assert c["workers"] == 2
    assert c["threads"] == 4
    assert c["timeout"] == 60
    assert c["worker_class"] == "gthread"


def test_gunicorn_lee_workers_threads_y_timeout_del_entorno():
    c = gunicorn(GUNICORN_WORKERS="3", GUNICORN_THREADS="8", GUNICORN_TIMEOUT="120")

    assert (c["workers"], c["threads"], c["timeout"]) == (3, 8, 120)


def test_gunicorn_escucha_en_8000_y_confia_en_el_balanceador():
    c = gunicorn()

    assert c["bind"] == "0.0.0.0:8000"
    # Solo el ALB llega al contenedor; sin esto Django veria siempre http y la IP del ALB.
    assert c["forwarded_allow_ips"] == "*"


def test_gunicorn_registra_en_stdout_y_stderr():
    """Los contenedores no tienen disco util: CloudWatch lee la salida estandar."""
    c = gunicorn()

    assert c["accesslog"] == "-"
    assert c["errorlog"] == "-"


def test_gunicorn_recicla_workers_con_jitter():
    c = gunicorn()

    assert c["max_requests"] > 0
    assert 0 < c["max_requests_jitter"] < c["max_requests"]


def test_el_dockerfile_arranca_con_gunicorn_conf():
    docker = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    cmd = [linea for linea in docker.splitlines() if linea.startswith("CMD")][0]

    assert "gunicorn.conf.py" in cmd
    assert "--workers" not in cmd  # lo decide el archivo, no la linea de comandos


def test_el_dockerfile_documenta_los_procesos_del_contrato():
    docker = (BACKEND / "Dockerfile").read_text(encoding="utf-8")

    for comando in ("celery -A config worker", "celery -A config beat",
                    "migrate --noinput", "createcachetable"):
        assert comando in docker


def test_requirements_fija_whitenoise_y_sentry_con_version_exacta():
    lineas = (BACKEND / "requirements.txt").read_text(encoding="utf-8").splitlines()

    for paquete in ("whitenoise", "sentry-sdk"):
        fijadas = [linea for linea in lineas if linea.lower().startswith(paquete) and "==" in linea]
        assert fijadas, f"{paquete} debe estar fijado con =="
