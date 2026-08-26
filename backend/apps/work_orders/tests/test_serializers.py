import pytest
from datetime import date

from rest_framework.test import APIRequestFactory

from apps.assets.models import Asset, Hospital
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.work_orders.serializers import WorkOrderCreateSerializer


def make_user(role):
    import uuid
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="A",
        last_name="B",
        role=role,
    )


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def tec(db):
    return make_user(User.Role.TEC)


@pytest.fixture
def sup(db):
    return make_user(User.Role.SUP)


@pytest.fixture
def hospital(db):
    import uuid
    return Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])


@pytest.fixture
def active_asset(db, hospital):
    import uuid
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo A",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


@pytest.fixture
def inactive_asset(db, hospital):
    import uuid
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo Inactivo",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.OUT_OF_SERVICE,
    )


def make_create_context(user):
    factory = APIRequestFactory()
    request = factory.post("/")
    request.user = user
    return {"request": request}


@pytest.mark.django_db
class TestWorkOrderCreateSerializer:
    def _valid_data(self, asset, assigned_to):
        return {
            "asset": str(asset.id),
            "task_type": WorkOrder.TaskType.CORRECTIVE,
            "title": "Cambio de válvula",
            "scheduled_date": str(date.today()),
            "assigned_to": str(assigned_to.id),
        }

    def test_valid_payload_is_accepted(self, admin, tec, active_asset):
        data = self._valid_data(active_asset, tec)
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert s.is_valid(), s.errors

    def test_preventive_task_type_is_rejected(self, admin, tec, active_asset):
        data = self._valid_data(active_asset, tec)
        data["task_type"] = WorkOrder.TaskType.PREVENTIVE
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert not s.is_valid()
        assert "task_type" in s.errors

    def test_installation_task_type_is_rejected(self, admin, tec, active_asset):
        data = self._valid_data(active_asset, tec)
        data["task_type"] = WorkOrder.TaskType.INSTALLATION
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert not s.is_valid()
        assert "task_type" in s.errors

    def test_verification_task_type_is_accepted(self, admin, tec, active_asset):
        data = self._valid_data(active_asset, tec)
        data["task_type"] = WorkOrder.TaskType.VERIFICATION
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert s.is_valid(), s.errors

    def test_inactive_asset_is_rejected(self, admin, tec, inactive_asset):
        data = self._valid_data(inactive_asset, tec)
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert not s.is_valid()
        assert "asset" in s.errors

    def test_non_tec_assigned_to_is_rejected(self, admin, sup, active_asset):
        data = self._valid_data(active_asset, sup)
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert not s.is_valid()
        assert "assigned_to" in s.errors

    def test_create_auto_sets_created_by_and_pending_status(self, admin, tec, active_asset):
        data = self._valid_data(active_asset, tec)
        s = WorkOrderCreateSerializer(data=data, context=make_create_context(admin))
        assert s.is_valid(), s.errors
        wo = s.save()
        assert wo.created_by == admin
        assert wo.status == WorkOrder.Status.PENDING
        assert wo.wo_number is not None
