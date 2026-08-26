import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def sup_user(db):
    return baker.make(User, role=User.Role.SUP, is_active=True)


@pytest.fixture
def tec_user(db):
    return baker.make(User, role=User.Role.TEC, is_active=True)


@pytest.fixture
def cli_user(db):
    return baker.make(User, role=User.Role.CLI, is_active=True)


@pytest.mark.django_db
class TestHospitalPermissions:
    def test_admin_can_create_hospital(self, admin_user):
        client = auth_client(admin_user)
        url = reverse("hospitals-list")
        data = {"name": "Hospital Central", "code": "HC001"}
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["code"] == "HC001"

    def test_admin_can_edit_hospital(self, admin_user):
        from apps.assets.models import Hospital
        hospital = baker.make(Hospital)
        client = auth_client(admin_user)
        url = reverse("hospitals-detail", kwargs={"pk": str(hospital.id)})
        response = client.patch(url, {"name": "Updated Name"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"

    def test_tec_cannot_create_hospital(self, tec_user):
        client = auth_client(tec_user)
        url = reverse("hospitals-list")
        data = {"name": "Hospital X", "code": "HX001"}
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cli_cannot_list_hospitals(self, cli_user):
        client = auth_client(cli_user)
        url = reverse("hospitals-list")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_toggle_active_changes_state(self, admin_user):
        from apps.assets.models import Hospital
        hospital = baker.make(Hospital, is_active=True)
        client = auth_client(admin_user)
        url = reverse("hospitals-toggle-active", kwargs={"pk": str(hospital.id)})
        response = client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False
        # toggle back
        response = client.post(url)
        assert response.data["is_active"] is True

    def test_cannot_delete_hospital(self, admin_user):
        from apps.assets.models import Hospital
        hospital = baker.make(Hospital)
        client = auth_client(admin_user)
        url = reverse("hospitals-detail", kwargs={"pk": str(hospital.id)})
        response = client.delete(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
