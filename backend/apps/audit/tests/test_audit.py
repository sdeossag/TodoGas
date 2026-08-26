import uuid

import pytest
from django.test import RequestFactory
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.audit.middleware import AuditMiddleware
from apps.audit.models import AuditLog
from apps.users.models import User


# ── Helpers ──────────────────────────────────────────────────────────────────

def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="T",
        last_name="U",
        role=role,
        hospital=hospital,
    )


def make_hospital():
    return Hospital.objects.create(
        name="Hosp", code=str(uuid.uuid4())[:8]
    )


def make_asset(hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


# ── Middleware tests ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_middleware_records_create_on_post():
    """AuditMiddleware crea un AuditLog cuando hay un POST exitoso a /api/."""
    admin = make_user(User.Role.ADMIN)
    hospital = make_hospital()

    factory = RequestFactory()
    request = factory.post('/api/assets/', data={})
    request.user = admin
    request.META['REMOTE_ADDR'] = '127.0.0.1'

    # Simulate a 201 JSON response
    from django.http import JsonResponse
    asset = make_asset(hospital)
    response = JsonResponse({'id': str(asset.id)}, status=201)

    before = AuditLog.objects.count()
    middleware = AuditMiddleware(get_response=lambda r: response)
    middleware.process_response(request, response)
    after = AuditLog.objects.count()

    assert after == before + 1
    log = AuditLog.objects.order_by('-timestamp').first()
    assert log.action == AuditLog.Action.CREATE
    assert log.entity_type == 'Asset'
    assert log.user == admin


@pytest.mark.django_db
def test_middleware_does_not_record_get():
    """AuditMiddleware no registra peticiones GET."""
    factory = RequestFactory()
    request = factory.get('/api/assets/')
    request.user = make_user(User.Role.ADMIN)

    from django.http import JsonResponse
    response = JsonResponse({'results': []}, status=200)

    before = AuditLog.objects.count()
    middleware = AuditMiddleware(get_response=lambda r: response)
    middleware.process_response(request, response)

    assert AuditLog.objects.count() == before


@pytest.mark.django_db
def test_middleware_does_not_interrupt_on_log_failure():
    """Si falla la creación del log, la respuesta se retorna igual."""
    factory = RequestFactory()
    request = factory.post('/api/assets/', data={})

    # Unauthenticated user — AnonymousUser doesn't have is_authenticated=True
    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    request.META['REMOTE_ADDR'] = '127.0.0.1'

    from django.http import HttpResponse
    # Response with invalid content type — body parsing will fail gracefully
    response = HttpResponse(b'not-json', status=201, content_type='application/json')

    # Should NOT raise even if AuditLog creation fails
    middleware = AuditMiddleware(get_response=lambda r: response)
    result = middleware.process_response(request, response)
    assert result is response


@pytest.mark.django_db
def test_middleware_skips_non_api_paths():
    """AuditMiddleware ignora rutas que no empiezan con /api/."""
    factory = RequestFactory()
    request = factory.post('/admin/login/', data={})
    request.user = make_user(User.Role.ADMIN)

    from django.http import JsonResponse
    response = JsonResponse({}, status=200)

    before = AuditLog.objects.count()
    middleware = AuditMiddleware(get_response=lambda r: response)
    middleware.process_response(request, response)

    assert AuditLog.objects.count() == before


# ── API tests ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_only_admin_can_access_audit_list():
    admin = make_user(User.Role.ADMIN)
    sup = make_user(User.Role.SUP)
    tec = make_user(User.Role.TEC)

    # Create a real AuditLog entry
    hospital = make_hospital()
    asset = make_asset(hospital)
    AuditLog.objects.create(
        user=admin,
        action=AuditLog.Action.CREATE,
        entity_type='Asset',
        entity_id=asset.id,
    )

    assert auth_client(admin).get('/api/audit/').status_code == 200
    assert auth_client(sup).get('/api/audit/').status_code == 403
    assert auth_client(tec).get('/api/audit/').status_code == 403


@pytest.mark.django_db
def test_audit_list_filter_by_entity_type():
    admin = make_user(User.Role.ADMIN)
    hospital = make_hospital()
    asset = make_asset(hospital)

    AuditLog.objects.create(
        user=admin, action=AuditLog.Action.CREATE,
        entity_type='Asset', entity_id=asset.id,
    )
    AuditLog.objects.create(
        user=admin, action=AuditLog.Action.UPDATE,
        entity_type='Hospital', entity_id=hospital.id,
    )

    c = auth_client(admin)
    resp = c.get('/api/audit/?entity_type=Asset')
    assert resp.status_code == 200
    data = resp.json()
    results = data.get('results', data)
    assert all(r['entity_type'] == 'Asset' for r in results)


@pytest.mark.django_db
def test_audit_list_filter_by_action():
    admin = make_user(User.Role.ADMIN)
    hospital = make_hospital()
    asset = make_asset(hospital)

    AuditLog.objects.create(
        user=admin, action=AuditLog.Action.CREATE,
        entity_type='Asset', entity_id=asset.id,
    )
    AuditLog.objects.create(
        user=admin, action=AuditLog.Action.DELETE,
        entity_type='Asset', entity_id=asset.id,
    )

    c = auth_client(admin)
    resp = c.get('/api/audit/?action=CREATE')
    assert resp.status_code == 200
    data = resp.json()
    results = data.get('results', data)
    assert all(r['action'] == 'CREATE' for r in results)
