"""
Tests de «¿Olvidaste tu contraseña?»: solicitud y confirmación con enlace por correo.
"""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status

from apps.users.throttling import MAX_ATTEMPTS

User = get_user_model()

STRONG_PASSWORD = "TestPass1!"
NEW_PASSWORD = "NuevaClave9#x"
REQUEST_URL = "/api/auth/password-reset/"
CONFIRM_URL = "/api/auth/password-reset/confirm/"
LOGIN_URL = "/api/auth/login/"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def locmem_mail(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.FRONTEND_URL = "https://cmms.example.com"


def _link_params():
    body = mail.outbox[-1].body
    match = re.search(r"restablecer-contrasena\?uid=([^&\s]+)&token=([^&\s]+)", body)
    assert match, body
    return match.group(1), match.group(2)


def _request_reset(api_client, email):
    return api_client.post(REQUEST_URL, {"email": email})


class TestRequest:
    def test_same_response_for_existing_and_unknown_email(self, api_client, admin_user):
        ok = _request_reset(api_client, "admin@todogas.com")
        unknown = _request_reset(api_client, "noexiste@todogas.com")
        assert ok.status_code == unknown.status_code == status.HTTP_200_OK
        assert ok.data == unknown.data

    def test_sends_one_email_with_link(self, api_client, admin_user):
        _request_reset(api_client, "Admin@Todogas.com")
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.to == ["admin@todogas.com"]
        assert msg.subject == "Restablecer tu contraseña – TodoGas"
        assert "https://cmms.example.com/restablecer-contrasena?uid=" in msg.body

    def test_unknown_email_sends_nothing(self, api_client, db):
        _request_reset(api_client, "noexiste@todogas.com")
        assert mail.outbox == []

    def test_invalid_email_format_same_generic_response(self, api_client, db):
        resp = _request_reset(api_client, "no-es-correo")
        assert resp.status_code == status.HTTP_200_OK
        assert mail.outbox == []

    def test_inactive_user_gets_nothing(self, api_client, admin_user):
        admin_user.is_active = False
        admin_user.deactivated_at = timezone.now()
        admin_user.save()
        resp = _request_reset(api_client, "admin@todogas.com")
        assert resp.status_code == status.HTTP_200_OK
        assert mail.outbox == []

    def test_user_with_deactivated_at_gets_nothing(self, api_client, admin_user):
        admin_user.deactivated_at = timezone.now()
        admin_user.save()
        _request_reset(api_client, "admin@todogas.com")
        assert mail.outbox == []

    def test_anonymized_user_gets_nothing(self, api_client, admin_user):
        admin_user.set_unusable_password()
        admin_user.save()
        _request_reset(api_client, "admin@todogas.com")
        assert mail.outbox == []

    def test_throttled_after_five_requests_per_hour(self, api_client, admin_user):
        for _ in range(5):
            assert _request_reset(api_client, "admin@todogas.com").status_code == 200
        assert _request_reset(api_client, "admin@todogas.com").status_code == 429

    def test_request_throttle_does_not_touch_login(self, api_client, admin_user):
        for _ in range(6):
            _request_reset(api_client, "admin@todogas.com")
        resp = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        assert resp.status_code == status.HTTP_200_OK


class TestConfirm:
    def _confirm(self, api_client, uid, token, password=NEW_PASSWORD):
        return api_client.post(CONFIRM_URL, {"uid": uid, "token": token, "new_password": password})

    def test_confirm_allows_login_with_new_password(self, api_client, admin_user):
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        resp = self._confirm(api_client, uid, token)
        assert resp.status_code == status.HTTP_200_OK

        old = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        assert old.status_code == status.HTTP_401_UNAUTHORIZED
        cache.clear()
        new = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": NEW_PASSWORD})
        assert new.status_code == status.HTTP_200_OK

    def test_confirm_clears_must_change_password(self, api_client, admin_user):
        admin_user.must_change_password = True
        admin_user.save()
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        self._confirm(api_client, uid, token)
        admin_user.refresh_from_db()
        assert admin_user.must_change_password is False

    def test_confirm_clears_login_lockout(self, api_client, admin_user):
        for _ in range(MAX_ATTEMPTS):
            api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": "mala"})
        blocked = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": NEW_PASSWORD})
        assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        assert self._confirm(api_client, uid, token).status_code == 200
        ok = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": NEW_PASSWORD})
        assert ok.status_code == status.HTTP_200_OK

    def test_reused_token_fails(self, api_client, admin_user):
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        assert self._confirm(api_client, uid, token).status_code == 200
        again = self._confirm(api_client, uid, token, "OtraClave7$yz")
        assert again.status_code == status.HTTP_400_BAD_REQUEST
        assert "enlace" in again.data["detail"]

    def test_tampered_token_fails(self, api_client, admin_user):
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        resp = self._confirm(api_client, uid, token[:-1] + ("a" if token[-1] != "a" else "b"))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        admin_user.refresh_from_db()
        assert admin_user.check_password(STRONG_PASSWORD)

    def test_tampered_uid_fails(self, api_client, admin_user):
        _request_reset(api_client, "admin@todogas.com")
        _, token = _link_params()
        resp = self._confirm(api_client, "basura", token)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_token_fails(self, api_client, admin_user, settings):
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        settings.PASSWORD_RESET_TIMEOUT = -1
        resp = self._confirm(api_client, uid, token)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "venció" in resp.data["detail"]

    def test_weak_password_fails_and_keeps_token_valid(self, api_client, admin_user):
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        resp = self._confirm(api_client, uid, token, "123")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in resp.data
        admin_user.refresh_from_db()
        assert admin_user.check_password(STRONG_PASSWORD)
        assert self._confirm(api_client, uid, token).status_code == 200

    def test_missing_fields_fail(self, api_client, db):
        resp = api_client.post(CONFIRM_URL, {"uid": "x"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_deactivated_after_request_cannot_confirm(self, api_client, admin_user):
        _request_reset(api_client, "admin@todogas.com")
        uid, token = _link_params()
        admin_user.is_active = False
        admin_user.deactivated_at = timezone.now()
        admin_user.save()
        resp = self._confirm(api_client, uid, token)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
