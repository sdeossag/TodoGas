import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import AssetNode, Hospital
from apps.users.models import User


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_user(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


@pytest.fixture
def hospital(db):
    return baker.make(Hospital, is_active=True)


@pytest.mark.django_db
class TestAssetNodeTree:
    def test_tree_returns_nested_structure(self, admin_user, hospital):
        root = AssetNode.objects.create(hospital=hospital, name="Piso 1", node_type="FLOOR")
        child = AssetNode.objects.create(hospital=hospital, parent=root, name="UCI", node_type="AREA")
        AssetNode.objects.create(hospital=hospital, parent=child, name="Sala A", node_type="ROOM")

        client = auth_client(admin_user)
        url = reverse("asset-nodes-tree") + f"?hospital_id={hospital.id}"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        root_data = response.data[0]
        assert root_data["name"] == "Piso 1"
        assert len(root_data["children"]) == 1
        child_data = root_data["children"][0]
        assert child_data["name"] == "UCI"
        assert len(child_data["children"]) == 1
        assert child_data["children"][0]["name"] == "Sala A"

    def test_path_generated_correctly_for_root_node(self, hospital):
        node = AssetNode.objects.create(hospital=hospital, name="Edificio Principal", node_type="BUILDING")
        assert node.path == "Edificio Principal"

    def test_child_inherits_parent_path(self, hospital):
        root = AssetNode.objects.create(hospital=hospital, name="Torre A", node_type="BUILDING")
        child = AssetNode.objects.create(hospital=hospital, parent=root, name="Piso 2", node_type="FLOOR")
        grandchild = AssetNode.objects.create(hospital=hospital, parent=child, name="UCI", node_type="AREA")

        assert child.path == "Torre A/Piso 2"
        assert grandchild.path == "Torre A/Piso 2/UCI"

    def test_tree_requires_hospital_id(self, admin_user):
        client = auth_client(admin_user)
        url = reverse("asset-nodes-tree")
        response = client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
