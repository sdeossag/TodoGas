"""Broker de Celery (Redis o SQS) y caché de Django según el entorno.

`CELERY_BROKER` se decide con el cliente sin tocar código: "redis" (default) o
"sqs". Los ajustes se leen al importar, así que cada caso corre en un
subproceso con su propio entorno (helper `importar` de test_production).

Una variable en "" cuenta como ausente: es la forma de quitarla del entorno del
subproceso aunque el .env local la defina.
"""

import json
import re
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings

from apps.users.throttling import MAX_ATTEMPTS, LoginRateThrottle
from config.tests.test_production import PRODUCCION, importar

REDIS = "redis://cache.interno:6379/0"
COLA = "https://sqs.us-east-1.amazonaws.com/123456789012/todogas-prod-celery"
SQS = {
    "CELERY_BROKER": "sqs", "CELERY_SQS_QUEUE_URL": COLA, "AWS_REGION": "us-east-1",
    "REDIS_URL": "", "AWS_ACCESS_KEY_ID": "", "AWS_SECRET_ACCESS_KEY": "",
}
CON_REDIS = {"CELERY_BROKER": "redis", "REDIS_URL": REDIS, "CELERY_SQS_QUEUE_URL": ""}

LEER = (
    "import json\n"
    "from django.conf import settings as s\n"
    "print(json.dumps({\n"
    "    'broker_url': s.CELERY_BROKER_URL,\n"
    "    'resultados': getattr(s, 'CELERY_RESULT_BACKEND', None),\n"
    "    'ignorar': getattr(s, 'CELERY_TASK_IGNORE_RESULT', False),\n"
    "    'opciones': getattr(s, 'CELERY_BROKER_TRANSPORT_OPTIONS', {}),\n"
    "    'cola': getattr(s, 'CELERY_TASK_DEFAULT_QUEUE', None),\n"
    "    'cache': s.CACHES['default'],\n"
    "}))\n"
)


def sin_dotenv(tmp_path):
    """Entorno para que decouple no encuentre el .env de la raíz del proyecto.

    decouple sube por las carpetas desde settings/ hasta dar con un .env; un
    sitecustomize en PYTHONPATH le fija otra carpeta de búsqueda (sin .env)
    antes de que se importen los ajustes.
    """
    (tmp_path / "sitecustomize.py").write_text(
        f"import decouple\ndecouple.config.search_path = {str(tmp_path)!r}\n", encoding="utf-8"
    )
    return {"PYTHONPATH": str(tmp_path)}


def ajustes(modulo="config.settings.production", **entorno):
    salida = importar(modulo, LEER, **{**PRODUCCION, **entorno})
    assert salida.returncode == 0, salida.stderr[-2000:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


# ── Redis: todo como hoy ──────────────────────────────────────────────────────

def test_redis_es_el_broker_por_defecto():
    a = ajustes(CELERY_BROKER="", REDIS_URL=REDIS)

    assert a["broker_url"] == REDIS


def test_con_redis_no_hay_opciones_de_sqs_y_no_se_guardan_resultados():
    a = ajustes(**CON_REDIS)

    assert a["broker_url"] == REDIS
    assert not a["opciones"]
    assert a["ignorar"] is True
    assert not a["resultados"]


def test_con_redis_el_cache_es_redis():
    a = ajustes(**CON_REDIS)

    assert a["cache"]["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert a["cache"]["LOCATION"] == REDIS


def test_redis_sin_url_no_arranca_y_avisa_cual_falta():
    salida = importar("config.settings.production", LEER, **{**PRODUCCION, **CON_REDIS, "REDIS_URL": ""})

    assert salida.returncode != 0
    assert "REDIS_URL" in salida.stderr


def test_redis_con_la_variable_sin_definir_tampoco_arranca(tmp_path):
    salida = importar(
        "config.settings.production", LEER,
        **{**PRODUCCION, **CON_REDIS, "REDIS_URL": None, **sin_dotenv(tmp_path)},
    )

    assert salida.returncode != 0
    assert "REDIS_URL" in salida.stderr


def test_un_broker_desconocido_no_arranca():
    salida = importar("config.settings.production", LEER, **{**PRODUCCION, **SQS, "CELERY_BROKER": "rabbit"})

    assert salida.returncode != 0
    assert "CELERY_BROKER" in salida.stderr


# ── SQS ───────────────────────────────────────────────────────────────────────

def test_sqs_usa_el_transporte_sqs_sin_claves_en_la_url():
    """Sin usuario ni clave en la URL: las credenciales salen del rol de la tarea de ECS."""
    a = ajustes(**SQS)

    assert a["broker_url"] == "sqs://"


def test_sqs_arranca_sin_redis_url(tmp_path):
    """Antes, config('REDIS_URL') sin default reventaba al importar. Aquí la
    variable queda sin definir (no vacía) y sin .env que la defina."""
    salida = importar(
        "config.settings.production", LEER,
        **{**PRODUCCION, **SQS, "REDIS_URL": None, **sin_dotenv(tmp_path)},
    )

    assert salida.returncode == 0, salida.stderr[-2000:]


def test_sqs_apunta_a_la_cola_por_url_para_no_pedir_listqueues_ni_createqueue():
    opciones = ajustes(**SQS)["opciones"]

    assert opciones["region"] == "us-east-1"
    assert opciones["predefined_queues"] == {"todogas-prod-celery": {"url": COLA}}


def test_sqs_no_pone_claves_en_las_opciones():
    opciones = ajustes(**SQS)["opciones"]
    texto = json.dumps(opciones).lower()

    assert "access_key" not in texto and "secret" not in texto


def test_el_worker_usa_la_cola_de_sqs_por_defecto():
    a = ajustes(**SQS)

    assert a["cola"] == "todogas-prod-celery"


def test_el_visibility_timeout_supera_a_la_tarea_mas_larga():
    """El PDF del acta es la tarea más larga: si vence antes, SQS la entrega dos veces."""
    opciones = ajustes(**SQS)["opciones"]

    assert opciones["visibility_timeout"] >= 15 * 60


def test_sqs_usa_long_polling_para_no_gastar_pedidos():
    opciones = ajustes(**SQS)["opciones"]

    assert opciones["wait_time_seconds"] == 20
    assert opciones["polling_interval"] >= 1


def test_sqs_sin_url_de_cola_no_arranca_y_avisa():
    salida = importar("config.settings.production", LEER, **{**PRODUCCION, **SQS, "CELERY_SQS_QUEUE_URL": ""})

    assert salida.returncode != 0
    assert "CELERY_SQS_QUEUE_URL" in salida.stderr


def test_sqs_sin_region_no_arranca_y_avisa():
    salida = importar(
        "config.settings.production", LEER,
        **{**PRODUCCION, **SQS, "AWS_REGION": "", "AWS_S3_REGION_NAME": ""},
    )

    assert salida.returncode != 0
    assert "AWS_REGION" in salida.stderr


# ── Resultados de las tareas ──────────────────────────────────────────────────

def test_ninguna_parte_del_codigo_lee_resultados_de_tareas():
    """Hallazgo: solo se devuelve `result.id` (reports/views.py) con un 202; no hay
    AsyncResult, .ready() ni un endpoint que consulte el estado de una tarea."""
    raiz = Path(__file__).resolve().parents[2] / "apps"
    patron = re.compile(r"AsyncResult|\.ready\(\)|celery\.result|result\.(get|state|status|successful)\(")
    usos = [
        str(p.relative_to(raiz)) for p in raiz.rglob("*.py")
        if "tests" not in p.parts and patron.search(p.read_text(encoding="utf-8"))
    ]

    assert usos == []


@pytest.mark.parametrize("entorno", [SQS, CON_REDIS], ids=["sqs", "redis"])
def test_con_ningun_broker_las_tareas_ignoran_los_resultados(entorno):
    a = ajustes(**entorno)

    assert a["ignorar"] is True
    assert not a["resultados"]


# ── Caché de Django ───────────────────────────────────────────────────────────

def test_sin_redis_url_el_cache_es_la_base_de_datos():
    a = ajustes(**SQS)

    assert a["cache"]["BACKEND"] == "django.core.cache.backends.db.DatabaseCache"
    assert a["cache"]["LOCATION"] == "django_cache"


def test_con_sqs_y_redis_url_el_cache_sigue_siendo_redis():
    """El contrato: si REDIS_URL existe, el caché usa Redis aunque el broker sea SQS."""
    a = ajustes(**{**SQS, "REDIS_URL": REDIS})

    assert a["cache"]["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert a["cache"]["LOCATION"] == REDIS
    assert a["broker_url"] == "sqs://"


def test_desarrollo_arranca_sin_redis_url_ni_cola(tmp_path):
    """Desarrollo importa base.py, pero es eager y usa caché local: no exige nada."""
    salida = importar(
        "config.settings.development", LEER,
        REDIS_URL=None, CELERY_BROKER=None, CELERY_SQS_QUEUE_URL=None, **sin_dotenv(tmp_path),
    )

    assert salida.returncode == 0, salida.stderr[-2000:]


def test_desarrollo_sigue_con_cache_local_y_tareas_sincronas():
    a = ajustes("config.settings.development", **SQS)
    eager = importar(
        "config.settings.development",
        "from django.conf import settings as s\nprint(s.CELERY_TASK_ALWAYS_EAGER)\n",
    )

    assert a["cache"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"
    assert eager.stdout.strip().splitlines()[-1] == "True"


@pytest.fixture
def cache_en_base(db):
    """El caché de la base, con su tabla (en el despliegue la crea `createcachetable`)."""
    config = {"default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache",
    }}
    with override_settings(CACHES=config):
        call_command("createcachetable", verbosity=0)
        cache.clear()
        yield cache
        cache.clear()


def test_el_bloqueo_de_login_funciona_con_el_cache_en_base(cache_en_base):
    throttle = LoginRateThrottle()
    for _ in range(MAX_ATTEMPTS):
        assert not throttle.is_blocked("a@b.co")
        throttle.register_failed_attempt("a@b.co")

    assert throttle.is_blocked("A@b.co ")
    assert throttle.remaining_attempts("a@b.co") == 0
    throttle.reset_attempts("a@b.co")
    assert not throttle.is_blocked("a@b.co")


def test_el_tablero_cabe_en_el_cache_en_base(cache_en_base):
    """El tablero guarda un dict con listas y números; DatabaseCache lo serializa con pickle."""
    datos = {"compliance": 91.5, "ots_by_status": [{"status": "DONE", "n": 3}], "overdue": 0}

    cache_en_base.set("dashboard_None_30", datos, timeout=300)

    assert cache_en_base.get("dashboard_None_30") == datos


# ── Prueba de humo: la app de Celery ──────────────────────────────────────────

APP = (
    "import json\n"
    "from config.celery import app\n"
    "c = app.conf\n"
    "print(json.dumps({\n"
    "    'broker': c.broker_url, 'opciones': c.broker_transport_options,\n"
    "    'cola': c.task_default_queue, 'resultados': c.result_backend,\n"
    "    'ignorar': c.task_ignore_result, 'zona': c.timezone,\n"
    "    'programa': {k: [v['task'], str(v['schedule'])] for k, v in c.beat_schedule.items()},\n"
    "}))\n"
)


def app_de_celery(**entorno):
    salida = importar("config.settings.production", APP, **{**PRODUCCION, **entorno})
    assert salida.returncode == 0, salida.stderr[-2000:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_la_app_de_celery_con_sqs_lee_su_configuracion_sin_conectarse_a_aws():
    c = app_de_celery(**SQS)

    assert c["broker"] == "sqs://"
    assert c["opciones"]["predefined_queues"] == {"todogas-prod-celery": {"url": COLA}}
    assert c["opciones"]["region"] == "us-east-1"
    assert c["cola"] == "todogas-prod-celery"
    assert c["ignorar"] is True
    assert not c["resultados"]


def test_la_app_de_celery_con_redis_conserva_el_broker_y_no_guarda_resultados():
    c = app_de_celery(**CON_REDIS)

    assert c["broker"] == REDIS
    assert c["ignorar"] is True
    assert not c["resultados"]


def test_el_cliente_asincrono_de_sqs_se_crea():
    """El worker (pool prefork, con hub) lee SQS con AsyncSQSConnection, y kombu
    5.6.2 le da siempre un cliente HTTP de pycurl: no hay alternativa con
    urllib3. Se omite donde pycurl no está (Windows de desarrollo)."""
    pytest.importorskip("pycurl")
    salida = importar(
        "config.settings.production",
        "from kombu.asynchronous import Hub\n"
        "from kombu.asynchronous.http import get_client\n"
        "print(type(get_client(Hub())).__name__)\n",
        **{**PRODUCCION, **SQS},
    )

    assert salida.returncode == 0, salida.stderr[-2000:]
    assert salida.stdout.strip().splitlines()[-1] == "CurlClient"


def test_el_transporte_sqs_de_kombu_se_puede_importar():
    """Falla si falta algo del extra kombu[sqs] (boto3 y urllib3; pycurl solo fuera de Windows)."""
    salida = importar(
        "config.settings.production",
        "from kombu.transport import SQS\nprint(SQS.Transport.__name__)\n",
        **{**PRODUCCION, **SQS},
    )

    assert salida.returncode == 0, salida.stderr[-2000:]


@pytest.mark.parametrize("entorno", [SQS, CON_REDIS], ids=["sqs", "redis"])
def test_el_beat_no_cambia_con_ningun_broker(entorno):
    c = app_de_celery(**entorno)

    assert c["zona"] == "UTC"
    assert c["programa"] == {
        "generate-preventive-work-orders-daily": [
            "maintenance.generate_preventive_work_orders", "<crontab: 0 11 * * * (m/h/dM/MY/d)>"],
        "send-contract-expiry-notices-daily": [
            "assets.send_contract_expiry_notices", "<crontab: 30 11 * * * (m/h/dM/MY/d)>"],
    }
