"""`/health/`: la consulta del balanceador (ALB) de AWS.

El ALB llama por HTTP y con la IP privada de la tarea como Host. Por eso la
respuesta no puede depender de ALLOWED_HOSTS, de la redirección a HTTPS, de la
sesión ni del throttling: solo de que la base conteste.
"""

import json
from unittest import mock

import pytest
from django.db.utils import OperationalError
from django.test import Client, override_settings

RESTRINGIDO = {"ALLOWED_HOSTS": ["api.cmms.todogas.com.co"]}
IP_PRIVADA = "10.0.12.34"
CURSOR = "django.db.backends.base.base.BaseDatabaseWrapper.cursor"


@pytest.mark.django_db
def test_health_responde_200_si_la_base_contesta(client):
    r = client.get("/health/")

    assert r.status_code == 200
    assert json.loads(r.content) == {"status": "ok"}
    assert r["Content-Type"].startswith("application/json")


@pytest.mark.django_db
def test_health_responde_503_si_la_base_no_contesta(client):
    with mock.patch(CURSOR, side_effect=OperationalError("sin conexion")):
        r = client.get("/health/")

    assert r.status_code == 503
    assert json.loads(r.content) == {"status": "error"}


@pytest.mark.django_db
def test_health_no_filtra_el_detalle_del_error(client):
    """El cuerpo lo ve quien llegue al ALB: nada de nombres de host ni de base."""
    with mock.patch(CURSOR, side_effect=OperationalError("password authentication failed for rds-interna")):
        r = client.get("/health/")

    assert b"rds-interna" not in r.content


@pytest.mark.django_db
@override_settings(**RESTRINGIDO)
def test_health_acepta_cualquier_host_aunque_allowed_hosts_este_restringido(client):
    """La IP privada no esta en ALLOWED_HOSTS: Django daria 400 si llamara a get_host()."""
    r = client.get("/health/", HTTP_HOST=IP_PRIVADA)

    assert r.status_code == 200


@pytest.mark.django_db
@override_settings(**RESTRINGIDO)
def test_el_resto_de_la_api_si_sigue_validando_el_host(client):
    """Control: la excepcion es solo de /health/, no un agujero para todo el sitio."""
    r = client.get("/api/auth/login/", HTTP_HOST=IP_PRIVADA)

    assert r.status_code == 400


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True, **RESTRINGIDO)
def test_health_no_redirige_a_https(client):
    r = client.get("/health/", HTTP_HOST=IP_PRIVADA)

    assert r.status_code == 200
    assert "Location" not in r


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True, **RESTRINGIDO)
def test_el_resto_del_sitio_si_redirige_a_https(client):
    """Control de la prueba anterior: la redireccion esta activa de verdad."""
    r = client.get("/admin/login/", HTTP_HOST="api.cmms.todogas.com.co")

    assert r.status_code == 301
    assert r["Location"].startswith("https://")


@pytest.mark.django_db
def test_health_no_pide_autenticacion(client):
    r = client.get("/health/")  # cliente anonimo, sin token ni sesion

    assert r.status_code == 200


@pytest.mark.django_db
def test_health_no_exige_csrf():
    cliente = Client(enforce_csrf_checks=True)

    r = cliente.get("/health/")

    assert r.status_code == 200


@pytest.mark.django_db
def test_health_no_tiene_throttling(client):
    """El ALB lo consulta cada pocos segundos desde varias zonas."""
    respuestas = {client.get("/health/").status_code for _ in range(60)}

    assert respuestas == {200}


@pytest.mark.django_db
def test_health_es_solo_la_ruta_exacta(client):
    """Nada de prefijos que se cuelen (p. ej. /health/x)."""
    r = client.get("/health/otra-cosa")

    assert r.status_code == 404


@pytest.mark.django_db
def test_health_no_deja_rastro_en_auditoria(client):
    """Miles de consultas del ALB no deben llenar la tabla de auditoria."""
    from apps.audit.models import AuditLog

    antes = AuditLog.objects.count()
    client.get("/health/")

    assert AuditLog.objects.count() == antes


def test_el_middleware_de_health_va_primero():
    """Antes de CORS, SecurityMiddleware (redireccion) y CommonMiddleware (get_host)."""
    from django.conf import settings

    assert "health" in settings.MIDDLEWARE[0].lower()
