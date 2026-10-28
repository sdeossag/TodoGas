"""
La IP que queda en la auditoria no se puede falsificar.

Regresion: cinco copias del mismo codigo (work_orders, checklists, evidence,
audit.services y el middleware) tomaban el PRIMER valor de X-Forwarded-For, que
es el que pone el cliente. Cualquiera podia dejar en la auditoria la IP que
quisiera. Ahora hay un solo helper, `apps.audit.ip.client_ip`, y solo confia en
lo que pusieron los proxies propios (TRUSTED_PROXY_COUNT, contando desde la
derecha).
"""

import uuid

import pytest
from django.core.cache import cache
from django.http import JsonResponse
from django.test import RequestFactory, override_settings
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.audit.middleware import AuditMiddleware
from apps.audit.models import AuditLog
from apps.maintenance.testing import make_work_order
from apps.users.models import User
from apps.work_orders.models import WorkOrder

REAL = "203.0.113.7"          # la IP con la que llega la conexion al servidor
FALSA = "6.6.6.6"             # lo que escribe el atacante en la cabecera
PROXY = "10.0.0.9"            # lo que anota el balanceador de carga


def client_ip(request):
    # Import perezoso: cada prueba falla por su cuenta mientras el modulo no
    # exista, en vez de romper la coleccion del archivo entero.
    from apps.audit.ip import client_ip as fn
    return fn(request)


def peticion(xff=None, remote=REAL):
    extra = {"REMOTE_ADDR": remote}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    return RequestFactory().get("/api/x/", **extra)


# ── El helper ────────────────────────────────────────────────────────────────

def test_sin_proxies_de_confianza_devuelve_la_ip_de_la_conexion():
    assert client_ip(peticion(xff=FALSA)) == REAL


@override_settings(TRUSTED_PROXY_COUNT=0)
def test_con_cero_proxies_ignora_la_cabecera_aunque_traiga_varias_ips():
    assert client_ip(peticion(xff=f"{FALSA}, 7.7.7.7, {PROXY}")) == REAL


def test_sin_el_setting_definido_se_comporta_como_cero(settings):
    if hasattr(settings, "TRUSTED_PROXY_COUNT"):
        del settings.TRUSTED_PROXY_COUNT
    assert client_ip(peticion(xff=FALSA)) == REAL


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_con_un_proxy_toma_la_ultima_ip_de_la_cabecera():
    """El ALB agrega la IP que ve al final: lo anterior lo escribio el cliente."""
    assert client_ip(peticion(xff=f"{FALSA}, {PROXY}")) == PROXY


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_con_un_proxy_y_una_sola_ip_la_toma():
    assert client_ip(peticion(xff=PROXY)) == PROXY


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_con_dos_proxies_toma_la_segunda_contando_desde_la_derecha():
    assert client_ip(peticion(xff=f"{FALSA}, 198.51.100.4, {PROXY}")) == "198.51.100.4"


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_si_la_cabecera_trae_menos_ips_que_proxies_devuelve_la_de_la_conexion():
    """Cabecera mas corta de lo que la infraestructura garantiza: no es de fiar."""
    assert client_ip(peticion(xff=PROXY)) == REAL


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_con_proxies_pero_sin_cabecera_devuelve_la_de_la_conexion():
    assert client_ip(peticion(xff=None)) == REAL


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_tolera_espacios_y_valores_vacios_en_la_cabecera():
    assert client_ip(peticion(xff=f" {FALSA} ,  {PROXY} ")) == PROXY


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_si_el_valor_de_confianza_esta_vacio_devuelve_la_de_la_conexion():
    assert client_ip(peticion(xff=f"{FALSA}, ")) == REAL


def test_sin_ninguna_ip_devuelve_none():
    request = RequestFactory().get("/api/x/")
    request.META.pop("REMOTE_ADDR", None)
    assert client_ip(request) is None


# ── Integracion: lo que queda en AuditLog ────────────────────────────────────

@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()
    yield
    cache.clear()


def make_user(role, **kw):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com", password="pass", first_name="T", last_name="U",
        role=role, **kw,
    )


@pytest.fixture
def ot_pendiente(db):
    hospital = Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])
    asset = Asset.objects.create(hospital=hospital, name="E", code=str(uuid.uuid4())[:10],
                                 status=Asset.Status.ACTIVE)
    admin = make_user(User.Role.ADMIN)
    tec = make_user(User.Role.TEC)
    wo = make_work_order(asset, admin, status=WorkOrder.Status.PENDING, assigned_to=tec)
    return wo, tec


def cambiar_estado(wo, tec, **cabeceras):
    c = APIClient()
    c.force_authenticate(user=tec)
    r = c.post(f"/api/work-orders/{wo.id}/transition/", {"new_status": "IN_PROGRESS"},
               format="json", **cabeceras)
    assert r.status_code == 200, r.data
    return AuditLog.objects.get(entity_type="WorkOrder", action=AuditLog.Action.STATUS_CHANGE,
                                entity_id=wo.id)


def test_la_transicion_de_una_ot_guarda_la_ip_real_y_no_la_falsificada(ot_pendiente):
    wo, tec = ot_pendiente
    log = cambiar_estado(wo, tec, REMOTE_ADDR=REAL, HTTP_X_FORWARDED_FOR=FALSA)
    assert log.ip_address == REAL


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_detras_de_un_proxy_la_transicion_guarda_lo_que_anoto_el_proxy(ot_pendiente):
    wo, tec = ot_pendiente
    log = cambiar_estado(wo, tec, REMOTE_ADDR="10.0.0.1",
                         HTTP_X_FORWARDED_FOR=f"{FALSA}, {PROXY}")
    assert log.ip_address == PROXY


def test_el_login_guarda_la_ip_real_y_no_la_falsificada(db):
    user = make_user(User.Role.ADMIN)
    r = APIClient().post("/api/auth/login/", {"email": user.email, "password": "mala"},
                         format="json", REMOTE_ADDR=REAL, HTTP_X_FORWARDED_FOR=FALSA)
    assert r.status_code in (400, 401)
    log = AuditLog.objects.get(action=AuditLog.Action.LOGIN)
    assert log.ip_address == REAL


def test_el_middleware_guarda_la_ip_real_y_no_la_falsificada(db):
    admin = make_user(User.Role.ADMIN)
    hospital = Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])
    asset = Asset.objects.create(hospital=hospital, name="E", code=str(uuid.uuid4())[:10],
                                 status=Asset.Status.ACTIVE)
    request = RequestFactory().post("/api/assets/", data={}, REMOTE_ADDR=REAL,
                                    HTTP_X_FORWARDED_FOR=FALSA)
    request.user = admin
    response = JsonResponse({"id": str(asset.id)}, status=201)
    AuditMiddleware(get_response=lambda r: response).process_response(request, response)

    log = AuditLog.objects.order_by("-timestamp").first()
    assert log.entity_type == "Asset"
    assert log.ip_address == REAL


def test_solo_el_helper_lee_x_forwarded_for():
    """
    Cubre las copias que no tienen prueba de integracion propia (evidence,
    checklists, work_orders): ninguna debe volver a leer la cabecera por su cuenta.
    """
    from pathlib import Path

    apps_dir = Path(__file__).resolve().parents[2]
    ofensores = sorted(
        str(p.relative_to(apps_dir))
        for p in apps_dir.rglob("*.py")
        if "tests" not in p.parts and "migrations" not in p.parts
        and p.name != "ip.py"
        and "X_FORWARDED_FOR" in p.read_text(encoding="utf-8")
    )
    assert ofensores == []


# ── CloudFront + ALB (TRUSTED_PROXY_COUNT=2, como en infra/terraform) ─────────

CLIENTE = "198.51.100.23"   # la IP real: la que CloudFront ve y anota
BORDE_CF = "130.176.10.5"   # la IP del servidor de borde de CloudFront, que anota el ALB


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_con_cloudfront_y_alb_la_ip_es_la_del_cliente():
    """CloudFront agrega la IP del cliente y el ALB la del borde: cliente = penultimo."""
    assert client_ip(peticion(xff=f"{CLIENTE}, {BORDE_CF}", remote="10.0.1.7")) == CLIENTE


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_con_cloudfront_y_alb_una_cabecera_falsificada_por_el_cliente_no_cuenta():
    """Lo que el cliente escriba va al principio; solo valen los dos ultimos valores."""
    xff = f"{FALSA}, 7.7.7.7, {CLIENTE}, {BORDE_CF}"
    assert client_ip(peticion(xff=xff, remote="10.0.1.7")) == CLIENTE


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_con_cloudfront_y_alb_la_transicion_guarda_la_ip_del_cliente(ot_pendiente):
    wo, tec = ot_pendiente
    log = cambiar_estado(wo, tec, REMOTE_ADDR="10.0.1.7",
                         HTTP_X_FORWARDED_FOR=f"{FALSA}, {CLIENTE}, {BORDE_CF}")
    assert log.ip_address == CLIENTE


def test_con_dos_proxies_el_throttling_de_drf_usa_la_ip_del_cliente(settings):
    """NUM_PROXIES sigue a TRUSTED_PROXY_COUNT en settings; aqui se fija en 2."""
    from rest_framework.request import Request
    from rest_framework.throttling import BaseThrottle

    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 2}
    request = Request(peticion(xff=f"{FALSA}, {CLIENTE}, {BORDE_CF}", remote="10.0.1.7"))
    assert BaseThrottle().get_ident(request) == CLIENTE


# ── Throttling de DRF ────────────────────────────────────────────────────────

def test_el_throttling_ignora_una_x_forwarded_for_falsificada_con_cero_proxies():
    """
    Con NUM_PROXIES sin definir DRF usa la cabecera completa como identidad, y
    rotandola se esquiva cualquier throttle por IP.
    """
    from rest_framework.request import Request
    from rest_framework.throttling import BaseThrottle

    request = Request(peticion(xff=FALSA))
    assert BaseThrottle().get_ident(request) == REAL


def test_num_proxies_de_drf_sigue_a_trusted_proxy_count():
    from django.conf import settings

    assert settings.REST_FRAMEWORK["NUM_PROXIES"] == settings.TRUSTED_PROXY_COUNT
