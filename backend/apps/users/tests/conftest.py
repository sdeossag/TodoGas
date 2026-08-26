import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

STRONG_PASSWORD = "TestPass1!"


@pytest.fixture(autouse=True)
def use_locmem_cache(settings):
    """Reemplaza Redis por LocMemCache en todos los tests (Redis no necesario)."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@todogas.com",
        password=STRONG_PASSWORD,
        first_name="Admin",
        last_name="Test",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def tech_user(db):
    return User.objects.create_user(
        email="tec@todogas.com",
        password=STRONG_PASSWORD,
        first_name="Tecnico",
        last_name="Test",
        role=User.Role.TEC,
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def tech_client(api_client, tech_user):
    refresh = RefreshToken.for_user(tech_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
