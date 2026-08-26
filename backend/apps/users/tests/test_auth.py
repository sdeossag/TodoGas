"""
Tests de autenticación: login, logout, refresh, cambio de contraseña, rate limiting.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status

User = get_user_model()

STRONG_PASSWORD = "TestPass1!"
LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"
CHANGE_PWD_URL = "/api/auth/change-password/"
ME_URL = "/api/auth/me/"
REFRESH_URL = "/api/auth/refresh/"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestLogin:
    def test_login_success(self, api_client, admin_user):
        resp = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data
        assert resp.data["user"]["email"] == "admin@todogas.com"

    def test_login_wrong_password(self, api_client, admin_user):
        resp = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": "wrong"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_unknown_email(self, api_client, db):
        resp = api_client.post(LOGIN_URL, {"email": "noexiste@todogas.com", "password": STRONG_PASSWORD})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client):
        resp = api_client.post(LOGIN_URL, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, admin_user):
        admin_user.is_active = False
        admin_user.save()
        resp = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_login_case_insensitive_email(self, api_client, admin_user):
        resp = api_client.post(LOGIN_URL, {"email": "ADMIN@TODOGAS.COM", "password": STRONG_PASSWORD})
        assert resp.status_code == status.HTTP_200_OK


class TestLoginRateLimit:
    def test_lockout_after_5_failures(self, api_client, admin_user):
        for _ in range(5):
            api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": "wrong"})
        resp = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_reset_on_success(self, api_client, admin_user):
        for _ in range(3):
            api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": "wrong"})
        # Login exitoso debe resetear el contador
        login = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        assert login.status_code == status.HTTP_200_OK
        # Tras el reset, el siguiente intento fallido devuelve 401 (no 429 = no bloqueado)
        resp = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": "wrong"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    def test_logout_success(self, api_client, admin_user):
        login = api_client.post(LOGIN_URL, {"email": "admin@todogas.com", "password": STRONG_PASSWORD})
        refresh = login.data["refresh"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        resp = api_client.post(LOGOUT_URL, {"refresh": refresh})
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_requires_auth(self, api_client):
        resp = api_client.post(LOGOUT_URL, {"refresh": "cualquier-token"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_invalid_token(self, admin_client):
        resp = admin_client.post(LOGOUT_URL, {"refresh": "token-invalido"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestChangePassword:
    def test_change_password_success(self, admin_client, admin_user):
        resp = admin_client.post(CHANGE_PWD_URL, {
            "current_password": STRONG_PASSWORD,
            "new_password": "NewPass2@",
            "new_password_confirm": "NewPass2@",
        })
        assert resp.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.check_password("NewPass2@")
        assert not admin_user.must_change_password

    def test_wrong_current_password(self, admin_client):
        resp = admin_client.post(CHANGE_PWD_URL, {
            "current_password": "wrong",
            "new_password": "NewPass2@",
            "new_password_confirm": "NewPass2@",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_passwords_dont_match(self, admin_client):
        resp = admin_client.post(CHANGE_PWD_URL, {
            "current_password": STRONG_PASSWORD,
            "new_password": "NewPass2@",
            "new_password_confirm": "Diferente1!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_weak_new_password(self, admin_client):
        resp = admin_client.post(CHANGE_PWD_URL, {
            "current_password": STRONG_PASSWORD,
            "new_password": "simple",
            "new_password_confirm": "simple",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_auth(self, api_client):
        resp = api_client.post(CHANGE_PWD_URL, {})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMeView:
    def test_me_authenticated(self, admin_client, admin_user):
        resp = admin_client.get(ME_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["email"] == "admin@todogas.com"
        assert "full_name" in resp.data

    def test_me_unauthenticated(self, api_client):
        resp = api_client.get(ME_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
