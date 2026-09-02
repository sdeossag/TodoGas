import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, AssetNode, Hospital
from apps.users.models import User


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def tec_user(db):
    return baker.make(User, role=User.Role.TEC, is_active=True)


@pytest.fixture
def hospital_a(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def hospital_b(db):
    return baker.make(Hospital, is_active=True)


@pytest.fixture
def cli_user(db, hospital_a):
    return baker.make(User, role=User.Role.CLI, is_active=True, hospital=hospital_a)


@pytest.mark.django_db
class TestAssetCRUD:
    def test_admin_can_create_asset_with_unique_code(self, admin_user, hospital_a):
        client = auth_client(admin_user)
        url = reverse("assets-list")
        data = {
            "hospital": str(hospital_a.id),
            "name": "Ventilador A",
            "code": "VEN-001",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["code"] == "VEN-001"

    def test_duplicate_code_fails(self, admin_user, hospital_a):
        baker.make(Asset, code="VEN-DUP", hospital=hospital_a)
        client = auth_client(admin_user)
        url = reverse("assets-list")
        data = {
            "hospital": str(hospital_a.id),
            "name": "Otro equipo",
            "code": "VEN-DUP",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_node_from_other_hospital_fails(self, admin_user, hospital_a, hospital_b):
        node_b = baker.make(AssetNode, hospital=hospital_b)
        client = auth_client(admin_user)
        url = reverse("assets-list")
        data = {
            "hospital": str(hospital_a.id),
            "node": str(node_b.id),
            "name": "Equipo X",
            "code": "EQX-001",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_decommission_asset(self, admin_user, hospital_a):
        asset = baker.make(Asset, hospital=hospital_a, status=Asset.Status.ACTIVE)
        client = auth_client(admin_user)
        url = reverse("assets-decommission", kwargs={"pk": str(asset.id)})
        response = client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Asset.Status.DECOMMISSIONED

    def test_cli_sees_only_own_hospital_assets(self, cli_user, hospital_a, hospital_b):
        baker.make(Asset, hospital=hospital_a, code="A001")
        baker.make(Asset, hospital=hospital_b, code="B001")
        client = auth_client(cli_user)
        url = reverse("assets-list")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        codes = [a["code"] for a in response.data["results"]]
        assert "A001" in codes
        assert "B001" not in codes

    def test_tec_sees_all_assets(self, tec_user, hospital_a, hospital_b):
        baker.make(Asset, hospital=hospital_a, code="T001")
        baker.make(Asset, hospital=hospital_b, code="T002")
        client = auth_client(tec_user)
        url = reverse("assets-list")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        codes = [a["code"] for a in response.data["results"]]
        assert "T001" in codes
        assert "T002" in codes

    def test_search_returns_correct_results(self, admin_user, hospital_a):
        baker.make(Asset, hospital=hospital_a, code="SRCH-01", name="Ventilador Mecánico", serial_number="SN-XYZ")
        baker.make(Asset, hospital=hospital_a, code="SRCH-02", name="Monitor Cardíaco", model="CardioMon")
        client = auth_client(admin_user)
        url = reverse("assets-list") + "?search=Ventilador"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        codes = [a["code"] for a in response.data["results"]]
        assert "SRCH-01" in codes
        assert "SRCH-02" not in codes

    def test_cannot_delete_asset(self, admin_user, hospital_a):
        asset = baker.make(Asset, hospital=hospital_a)
        client = auth_client(admin_user)
        url = reverse("assets-detail", kwargs={"pk": str(asset.id)})
        response = client.delete(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
