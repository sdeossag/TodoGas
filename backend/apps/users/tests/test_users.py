"""
Tests de gestión de usuarios: CRUD, deactivate, reset_password, permisos.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

USERS_URL = "/api/users/"
STRONG_PASSWORD = "TestPass1!"


def user_detail_url(pk):
    return f"/api/users/{pk}/"


def deactivate_url(pk):
    return f"/api/users/{pk}/deactivate/"


def reset_url(pk):
    return f"/api/users/{pk}/reset-password/"


class TestUserList:
    def test_admin_can_list(self, admin_client):
        resp = admin_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_sup_can_list(self, db, api_client):
        sup = User.objects.create_user(
            email="sup@todogas.com", password=STRONG_PASSWORD,
            first_name="Sup", last_name="Test", role=User.Role.SUP,
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(sup)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_tec_cannot_list(self, tech_client):
        resp = tech_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_list(self, api_client):
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserCreate:
    def test_admin_creates_user(self, admin_client):
        payload = {
            "email": "nuevo@todogas.com",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "role": User.Role.TEC,
            "password": STRONG_PASSWORD,
        }
        resp = admin_client.post(USERS_URL, payload)
        assert resp.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="nuevo@todogas.com")
        assert user.must_change_password is True

    def test_create_weak_password_rejected(self, admin_client):
        payload = {
            "email": "weak@todogas.com",
            "first_name": "Weak",
            "last_name": "Pass",
            "role": User.Role.TEC,
            "password": "1234",
        }
        resp = admin_client.post(USERS_URL, payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_tec_cannot_create(self, tech_client):
        resp = tech_client.post(USERS_URL, {})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_email_rejected(self, admin_client, admin_user):
        payload = {
            "email": "admin@todogas.com",
            "first_name": "Dup",
            "last_name": "User",
            "role": User.Role.TEC,
            "password": STRONG_PASSWORD,
        }
        resp = admin_client.post(USERS_URL, payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestUserUpdate:
    def test_admin_can_update(self, admin_client, tech_user):
        resp = admin_client.patch(user_detail_url(tech_user.id), {"first_name": "Modificado"})
        assert resp.status_code == status.HTTP_200_OK
        tech_user.refresh_from_db()
        assert tech_user.first_name == "Modificado"

    def test_tec_cannot_update_others(self, tech_client, admin_user):
        resp = tech_client.patch(user_detail_url(admin_user.id), {"first_name": "Hack"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestUserDeactivate:
    def test_admin_deactivates_user(self, admin_client, tech_user):
        resp = admin_client.post(deactivate_url(tech_user.id))
        assert resp.status_code == status.HTTP_200_OK
        tech_user.refresh_from_db()
        assert tech_user.is_active is False

    def test_admin_cannot_deactivate_self(self, admin_client, admin_user):
        resp = admin_client.post(deactivate_url(admin_user.id))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_tec_cannot_deactivate(self, tech_client, admin_user):
        resp = tech_client.post(deactivate_url(admin_user.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestUserResetPassword:
    def test_admin_resets_password(self, admin_client, tech_user):
        old_hash = tech_user.password
        resp = admin_client.post(reset_url(tech_user.id))
        assert resp.status_code == status.HTTP_200_OK
        tech_user.refresh_from_db()
        assert tech_user.password != old_hash
        assert tech_user.must_change_password is True

    def test_tec_cannot_reset(self, tech_client, admin_user):
        resp = tech_client.post(reset_url(admin_user.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestStrongPasswordValidator:
    """Tests directos del validador de contraseñas."""

    def test_valid_password(self):
        from apps.users.validators import StrongPasswordValidator
        validator = StrongPasswordValidator()
        validator.validate("ValidPass1!")  # No lanza excepción

    def test_no_uppercase(self):
        from django.core.exceptions import ValidationError
        from apps.users.validators import StrongPasswordValidator
        validator = StrongPasswordValidator()
        with pytest.raises(ValidationError):
            validator.validate("nouppercase1!")

    def test_no_digit(self):
        from django.core.exceptions import ValidationError
        from apps.users.validators import StrongPasswordValidator
        validator = StrongPasswordValidator()
        with pytest.raises(ValidationError):
            validator.validate("NoDigit!")

    def test_no_special(self):
        from django.core.exceptions import ValidationError
        from apps.users.validators import StrongPasswordValidator
        validator = StrongPasswordValidator()
        with pytest.raises(ValidationError):
            validator.validate("NoSpecial1")

    def test_too_short(self):
        from django.core.exceptions import ValidationError
        from apps.users.validators import StrongPasswordValidator
        validator = StrongPasswordValidator()
        with pytest.raises(ValidationError):
            validator.validate("Ab1!")
