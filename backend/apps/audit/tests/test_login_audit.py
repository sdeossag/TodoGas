"""La auditoria debe decir quien inicio sesion y contra que cuenta se fallo.

Regresion: AuditMiddleware resuelve el autor con request.user, que en el login
todavia es anonimo. Resultado: todos los inicios de sesion quedaban registrados
como "Sistema", y los intentos fallidos no decian a que cuenta apuntaban, lo que
los dejaba sin valor forense. Ademas el tipo de entidad era la ruta cruda
('/api/auth/login/'), que no coincide con ninguna opcion del filtro.
"""

import uuid

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.audit.services import AUTH_ENTITY_TYPE, LoginOutcome
from apps.users.models import User

PASSWORD = "Nacional2369**"
LOGIN_URL = "/api/auth/login/"


@pytest.fixture(autouse=True)
def clear_throttle():
    """El bloqueo por intentos vive en cache y se comparte entre tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password=PASSWORD,
        first_name="Ana",
        last_name="Prueba",
        role=User.Role.ADMIN,
    )


def login_entries():
    return AuditLog.objects.filter(action=AuditLog.Action.LOGIN)


def only_login_entry():
    entries = list(login_entries())
    assert len(entries) == 1, f'se esperaba un unico registro, hay {len(entries)}'
    return entries[0]


# ── Login correcto ───────────────────────────────────────────────────────────

def test_successful_login_records_who_entered(user):
    resp = APIClient().post(
        LOGIN_URL, {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == status.HTTP_200_OK

    entry = only_login_entry()
    assert entry.user_id == user.id, 'el login debe quedar atribuido al usuario'
    assert entry.entity_type == AUTH_ENTITY_TYPE
    assert entry.changes["outcome"] == LoginOutcome.SUCCESS
    assert entry.changes["email"] == user.email


def test_successful_login_is_not_logged_twice(user):
    """El middleware ya no escribe esta ruta: la vista es la unica que la audita."""
    APIClient().post(
        LOGIN_URL, {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert AuditLog.objects.filter(entity_type__contains="auth").count() == 0
    only_login_entry()


# ── Intentos fallidos ────────────────────────────────────────────────────────

def test_failed_login_records_the_targeted_account(user):
    resp = APIClient().post(
        LOGIN_URL, {"email": user.email, "password": "claveIncorrecta"}, format="json"
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    entry = only_login_entry()
    # El autor es desconocido: atribuirselo al dueño daria a entender que fue el.
    assert entry.user_id is None
    # Pero la cuenta apuntada si queda registrada, que es lo que hace falta para
    # investigar un ataque de fuerza bruta.
    assert entry.entity_id == user.id
    assert entry.changes["email"] == user.email
    assert entry.changes["outcome"] == LoginOutcome.BAD_CREDENTIALS
    assert entry.changes["failed"] is True


def test_failed_login_with_unknown_email_still_records_it(db):
    resp = APIClient().post(
        LOGIN_URL, {"email": "nadie@test.com", "password": "loQueSea"}, format="json"
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    entry = only_login_entry()
    assert entry.user_id is None
    assert entry.changes["email"] == "nadie@test.com"
    assert entry.changes["outcome"] == LoginOutcome.UNKNOWN_EMAIL


def test_login_on_inactive_account_is_recorded(user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    resp = APIClient().post(
        LOGIN_URL, {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    entry = only_login_entry()
    assert entry.changes["outcome"] == LoginOutcome.INACTIVE
    assert entry.entity_id == user.id


def test_incomplete_login_is_recorded(db):
    resp = APIClient().post(LOGIN_URL, {"email": "", "password": ""}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    entry = only_login_entry()
    assert entry.changes["outcome"] == LoginOutcome.INCOMPLETE


def test_brute_force_leaves_one_entry_per_attempt(user):
    client = APIClient()
    for _ in range(3):
        client.post(
            LOGIN_URL, {"email": user.email, "password": "mala"}, format="json"
        )

    entries = login_entries()
    assert entries.count() == 3
    assert all(e.changes["email"] == user.email for e in entries)


# ── Otras rutas de autenticacion ─────────────────────────────────────────────

def test_logout_is_filed_under_authentication(user):
    client = APIClient()
    login = client.post(
        LOGIN_URL, {"email": user.email, "password": PASSWORD}, format="json"
    )
    refresh = login.json()["refresh"]
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.json()["access"]}')

    client.post("/api/auth/logout/", {"refresh": refresh}, format="json")

    logout_entry = (
        AuditLog.objects
        .filter(entity_type=AUTH_ENTITY_TYPE)
        .exclude(action=AuditLog.Action.LOGIN)
        .first()
    )
    assert logout_entry is not None, 'el logout debe quedar auditado'
    # Antes se guardaba '/api/auth/logout/' como tipo de entidad y no era filtrable.
    assert not logout_entry.entity_type.startswith('/api/')
