import pytest
from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.users.models import User
from apps.work_orders.models import WorkOrder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, hospital=None):
    import uuid
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="A",
        last_name="B",
        role=role,
        hospital=hospital,
    )


def make_hospital():
    import uuid
    return Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])


def make_asset(hospital, status=Asset.Status.ACTIVE):
    import uuid
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
        status=status,
    )


def make_wo(asset, created_by, assigned_to=None,
            wo_status=WorkOrder.Status.PENDING,
            scheduled_date=None,
            priority=WorkOrder.Priority.MEDIUM):
    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="OT test",
        status=wo_status,
        priority=priority,
        scheduled_date=scheduled_date or date.today(),
        assigned_to=assigned_to,
        created_by=created_by,
    )
    wo.save()
    return wo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def hospital_b(db):
    return make_hospital()


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def sup(db):
    return make_user(User.Role.SUP)


@pytest.fixture
def tec(db):
    return make_user(User.Role.TEC)


@pytest.fixture
def tec2(db):
    return make_user(User.Role.TEC)


@pytest.fixture
def cli_user(db, hospital):
    return make_user(User.Role.CLI, hospital=hospital)


@pytest.fixture
def asset(db, hospital):
    return make_asset(hospital)


@pytest.fixture
def asset_b(db, hospital_b):
    return make_asset(hospital_b)


@pytest.fixture
def wo(db, asset, admin, tec):
    return make_wo(asset, created_by=admin, assigned_to=tec)


# ---------------------------------------------------------------------------
# Tests: listado y filtrado por rol
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkOrderRoleFiltering:
    def test_admin_sees_all_work_orders(self, admin, asset, asset_b, tec, tec2):
        wo1 = make_wo(asset, admin, tec)
        wo2 = make_wo(asset_b, admin, tec2)
        resp = auth_client(admin).get(reverse("work-orders-list"))
        assert resp.status_code == status.HTTP_200_OK
        ids = [str(w["id"]) for w in resp.data]
        assert str(wo1.id) in ids
        assert str(wo2.id) in ids

    def test_tec_sees_only_assigned_work_orders(self, admin, asset, asset_b, tec, tec2):
        wo_mine = make_wo(asset, admin, tec)
        wo_other = make_wo(asset_b, admin, tec2)
        resp = auth_client(tec).get(reverse("work-orders-list"))
        assert resp.status_code == status.HTTP_200_OK
        ids = [str(w["id"]) for w in resp.data]
        assert str(wo_mine.id) in ids
        assert str(wo_other.id) not in ids

    def test_cli_sees_only_completed_ots_for_own_hospital(
        self, admin, asset, asset_b, tec, cli_user
    ):
        wo_completed = make_wo(asset, admin, tec, wo_status=WorkOrder.Status.COMPLETED)
        wo_pending = make_wo(asset, admin, tec, wo_status=WorkOrder.Status.PENDING)
        wo_other_hosp = make_wo(asset_b, admin, tec, wo_status=WorkOrder.Status.COMPLETED)
        resp = auth_client(cli_user).get(reverse("work-orders-list"))
        assert resp.status_code == status.HTTP_200_OK
        ids = [str(w["id"]) for w in resp.data]
        assert str(wo_completed.id) in ids
        assert str(wo_pending.id) not in ids
        assert str(wo_other_hosp.id) not in ids


# ---------------------------------------------------------------------------
# Tests: creación
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkOrderCreate:
    def _payload(self, asset, tec):
        return {
            "asset": str(asset.id),
            "task_type": "CORRECTIVE",
            "title": "Nueva OT",
            "scheduled_date": str(date.today()),
            "assigned_to": str(tec.id),
        }

    def test_admin_can_create_work_order(self, admin, asset, tec):
        resp = auth_client(admin).post(
            reverse("work-orders-list"), self._payload(asset, tec), format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == WorkOrder.Status.PENDING
        assert resp.data["wo_number"] is not None

    def test_tec_cannot_create_work_order(self, tec, asset):
        tec2 = make_user(User.Role.TEC)
        resp = auth_client(tec).post(
            reverse("work-orders-list"), self._payload(asset, tec2), format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_rejects_inactive_asset(self, admin, hospital, tec):
        inactive = make_asset(hospital, status=Asset.Status.OUT_OF_SERVICE)
        resp = auth_client(admin).post(
            reverse("work-orders-list"), self._payload(inactive, tec), format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_returns_405(self, admin, wo):
        url = reverse("work-orders-detail", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).delete(url)
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------------------------------------------------------------------------
# Tests: filtros
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkOrderFilters:
    def test_filter_by_status(self, admin, asset, tec):
        make_wo(asset, admin, tec, wo_status=WorkOrder.Status.PENDING)
        make_wo(asset, admin, tec, wo_status=WorkOrder.Status.COMPLETED)
        resp = auth_client(admin).get(reverse("work-orders-list") + "?status=PENDING")
        assert resp.status_code == status.HTTP_200_OK
        assert all(w["status"] == "PENDING" for w in resp.data)

    def test_filter_is_overdue(self, admin, asset, tec):
        past = date.today() - timedelta(days=5)
        overdue = make_wo(asset, admin, tec, scheduled_date=past)
        future = make_wo(asset, admin, tec, scheduled_date=date.today() + timedelta(days=5))
        resp = auth_client(admin).get(reverse("work-orders-list") + "?is_overdue=true")
        assert resp.status_code == status.HTTP_200_OK
        ids = [str(w["id"]) for w in resp.data]
        assert str(overdue.id) in ids
        assert str(future.id) not in ids

    def test_search_by_title(self, admin, asset, tec):
        wo_match = make_wo(asset, admin, tec)
        wo_match.title = "Válvula de oxígeno"
        wo_match.save()
        make_wo(asset, admin, tec)  # titulo genérico "OT test"
        resp = auth_client(admin).get(reverse("work-orders-list") + "?search=Válvula")
        assert resp.status_code == status.HTTP_200_OK
        ids = [str(w["id"]) for w in resp.data]
        assert str(wo_match.id) in ids

    def test_ordering_high_priority_first(self, admin, asset, tec):
        make_wo(asset, admin, tec, priority=WorkOrder.Priority.LOW)
        make_wo(asset, admin, tec, priority=WorkOrder.Priority.HIGH)
        make_wo(asset, admin, tec, priority=WorkOrder.Priority.MEDIUM)
        resp = auth_client(admin).get(reverse("work-orders-list"))
        assert resp.status_code == status.HTTP_200_OK
        priorities = [w["priority"] for w in resp.data]
        assert priorities[0] == WorkOrder.Priority.HIGH


# ---------------------------------------------------------------------------
# Tests: acciones de transición, asignación y cancelación
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkOrderActions:
    def test_tec_can_start_own_ot(self, tec, wo):
        url = reverse("work-orders-transition", kwargs={"pk": str(wo.id)})
        resp = auth_client(tec).post(url, {"new_status": "IN_PROGRESS"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == WorkOrder.Status.IN_PROGRESS
        assert resp.data["started_at"] is not None

    def test_transition_invalid_raises_400(self, admin, wo):
        url = reverse("work-orders-transition", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).post(url, {"new_status": "COMPLETED"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_transition_missing_new_status_returns_400(self, tec, wo):
        url = reverse("work-orders-transition", kwargs={"pk": str(wo.id)})
        resp = auth_client(tec).post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_assign_tec(self, admin, asset, tec, tec2):
        wo = make_wo(asset, admin, tec)
        url = reverse("work-orders-assign", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).post(url, {"assigned_to": str(tec2.id)}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        wo.refresh_from_db()
        assert wo.assigned_to == tec2

    def test_assign_non_tec_returns_400(self, admin, asset, tec, sup):
        wo = make_wo(asset, admin, tec)
        url = reverse("work-orders-assign", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).post(url, {"assigned_to": str(sup.id)}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_tec_cannot_assign(self, tec, wo):
        tec2 = make_user(User.Role.TEC)
        url = reverse("work-orders-assign", kwargs={"pk": str(wo.id)})
        resp = auth_client(tec).post(url, {"assigned_to": str(tec2.id)}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_cancel_with_comment(self, admin, wo):
        url = reverse("work-orders-cancel", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).post(url, {"comment": "Duplicada"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == WorkOrder.Status.CANCELLED

    def test_cancel_without_comment_returns_400(self, admin, wo):
        url = reverse("work-orders-cancel", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).post(url, {"comment": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Tests: partial_update
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkOrderPartialUpdate:
    def test_admin_can_patch_title(self, admin, wo):
        url = reverse("work-orders-detail", kwargs={"pk": str(wo.id)})
        resp = auth_client(admin).patch(url, {"title": "Nuevo título"}, format="json")
        assert resp.status_code == status.HTTP_200_OK

    def test_tec_can_patch_progress(self, tec, wo):
        url = reverse("work-orders-detail", kwargs={"pk": str(wo.id)})
        resp = auth_client(tec).patch(url, {"progress": 50}, format="json")
        assert resp.status_code == status.HTTP_200_OK

    def test_tec_cannot_patch_other_ots(self, tec2, wo):
        url = reverse("work-orders-detail", kwargs={"pk": str(wo.id)})
        resp = auth_client(tec2).patch(url, {"progress": 10}, format="json")
        # tec2 no tiene la OT en su queryset → 404
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_cli_cannot_patch(self, cli_user, asset, admin, tec):
        wo = make_wo(asset, admin, tec, wo_status=WorkOrder.Status.COMPLETED)
        url = reverse("work-orders-detail", kwargs={"pk": str(wo.id)})
        resp = auth_client(cli_user).patch(url, {"notes": "x"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Tests: historial de estados
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkOrderHistory:
    def test_admin_can_see_history_after_transition(self, admin, tec, wo):
        # Crear la transición primero
        transition_url = reverse("work-orders-transition", kwargs={"pk": str(wo.id)})
        auth_client(tec).post(transition_url, {"new_status": "IN_PROGRESS"}, format="json")

        history_url = reverse("work-order-history-list", kwargs={"work_order_pk": str(wo.id)})
        resp = auth_client(admin).get(history_url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["to_status"] == WorkOrder.Status.IN_PROGRESS

    def test_tec_cannot_see_history(self, tec, wo):
        history_url = reverse("work-order-history-list", kwargs={"work_order_pk": str(wo.id)})
        resp = auth_client(tec).get(history_url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN
