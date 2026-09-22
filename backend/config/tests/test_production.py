"""Ajustes de producción: CORS para la web y la app, y evidencia en S3.

Los ajustes se leen al importar el módulo, así que las pruebas que cargan
`config.settings.*` con otras variables de entorno corren en un proceso aparte.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.test import override_settings
from django.urls import reverse

from config.cors import ANDROID_APP_ORIGIN, allowed_origins, origin

BACKEND = Path(__file__).resolve().parents[2]
S3 = "storages.backends.s3boto3.S3Boto3Storage"


def cargar(modulo, **entorno):
    """Importa un módulo de ajustes con estas variables y devuelve lo que interesa."""
    codigo = (
        "import json, os, django\n"
        f"os.environ['DJANGO_SETTINGS_MODULE'] = {modulo!r}\n"
        "django.setup()\n"
        "from django.conf import settings\n"
        "from django.core.files.storage import default_storage\n"
        "default_storage._setup()\n"
        "print(json.dumps({\n"
        "    'cors': list(getattr(settings, 'CORS_ALLOWED_ORIGINS', [])),\n"
        "    'storage': settings.STORAGES['default']['BACKEND'],\n"
        "    'storage_real': type(default_storage._wrapped).__name__,\n"
        "}))\n"
    )
    env = {**os.environ, "DB_NAME": "x", "DB_USER": "x", "DB_PASSWORD": "x",
           "DB_HOST": "x", "DB_PORT": "5432", **entorno}
    salida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=BACKEND, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert salida.returncode == 0, salida.stderr[-2000:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


# ── CORS ──────────────────────────────────────────────────────────────────────

def test_el_origen_es_esquema_y_host():
    assert origin("https://app.todogas.com.co/ingresar?x=1") == "https://app.todogas.com.co"
    assert origin("http://localhost:5173") == "http://localhost:5173"
    assert origin("") is None
    assert origin("app.todogas.com.co") is None


def test_la_web_y_la_app_android_pueden_llamar_a_la_api():
    origenes = allowed_origins(
        "https://app.todogas.com.co/", " https://otra.todogas.com.co/x , ,capacitor://localhost"
    )

    assert origenes == [
        "capacitor://localhost",
        "https://app.todogas.com.co",
        ANDROID_APP_ORIGIN,
        "https://otra.todogas.com.co",
    ]


@pytest.mark.django_db
@override_settings(CORS_ALLOWED_ORIGINS=allowed_origins("https://app.todogas.com.co"))
def test_el_login_desde_la_app_pasa_el_preflight(client):
    """Sin esto la app publicada no inicia sesión: el WebView descarta la respuesta."""
    def preflight(origen):
        return client.options(
            reverse("auth-login"),
            HTTP_ORIGIN=origen,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

    app = preflight(ANDROID_APP_ORIGIN)
    web = preflight("https://app.todogas.com.co")
    ajeno = preflight("https://sitio-ajeno.com")

    assert app["access-control-allow-origin"] == ANDROID_APP_ORIGIN
    assert web["access-control-allow-origin"] == "https://app.todogas.com.co"
    assert "access-control-allow-origin" not in ajeno


def test_produccion_arma_el_cors_con_la_web_y_la_app():
    ajustes = cargar(
        "config.settings.production",
        FRONTEND_URL="https://app.todogas.com.co",
        BACKEND_URL="https://api.todogas.com.co",
        DJANGO_CORS_ALLOWED_ORIGINS="",
        AWS_ACCESS_KEY_ID="",
    )

    assert ajustes["cors"] == ["https://app.todogas.com.co", ANDROID_APP_ORIGIN]


# ── Evidencia en S3 ───────────────────────────────────────────────────────────

def test_con_claves_de_aws_la_evidencia_va_a_s3():
    """
    Django 5.1 dejó de leer DEFAULT_FILE_STORAGE: con claves de AWS las fotos,
    firmas y actas se guardaban en el disco local sin ningún aviso.
    """
    ajustes = cargar(
        "config.settings.development",
        AWS_ACCESS_KEY_ID="prueba", AWS_SECRET_ACCESS_KEY="prueba",
    )

    assert ajustes["storage"] == S3
    assert ajustes["storage_real"] == "S3Storage"


def test_sin_claves_desarrollo_guarda_en_disco():
    ajustes = cargar("config.settings.development", AWS_ACCESS_KEY_ID="", USE_S3="")

    assert ajustes["storage_real"] == "FileSystemStorage"


def test_produccion_usa_s3_aunque_no_haya_claves():
    """En ECS las credenciales las pone el rol de la tarea, no AWS_ACCESS_KEY_ID."""
    ajustes = cargar(
        "config.settings.production",
        FRONTEND_URL="https://app.todogas.com.co",
        BACKEND_URL="https://api.todogas.com.co",
        AWS_ACCESS_KEY_ID="",
    )

    assert ajustes["storage"] == S3
