import pytest
from datetime import date

from rest_framework.exceptions import ValidationError

from apps.assets.models import Asset, Hospital
from apps.users.models import User
from apps.work_orders.models import WorkOrder, WorkOrderStatusHistory
from apps.work_orders.transitions import apply_transition, validate_transition


def make_user(role, **kwargs):
    import uuid
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="Test",
        last_name="User",
        role=role,
        **kwargs,
    )


def make_work_order(asset, created_by, assigned_to, status=WorkOrder.Status.PENDING):
    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="OT de prueba",
        status=status,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date=date.today(),
        assigned_to=assigned_to,
        created_by=created_by,
    )
    wo.save()
    return wo


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
def hospital(db):
    import uuid
    return Hospital.objects.create(name="H1", code=str(uuid.uuid4())[:8])


@pytest.fixture
def asset(db, hospital):
    import uuid
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo Test",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


@pytest.fixture
def wo_pending(db, asset, admin, tec):
    return make_work_order(asset, created_by=admin, assigned_to=tec)


@pytest.fixture
def wo_in_progress(db, asset, admin, tec):
    return make_work_order(asset, created_by=admin, assigned_to=tec,
                           status=WorkOrder.Status.IN_PROGRESS)


@pytest.fixture
def wo_in_review(db, asset, admin, tec):
    return make_work_order(asset, created_by=admin, assigned_to=tec,
                           status=WorkOrder.Status.IN_REVIEW)


@pytest.mark.django_db
class TestValidateTransition:
    def test_tec_can_start_own_pending_ot(self, wo_pending, tec):
        assert validate_transition(wo_pending, WorkOrder.Status.IN_PROGRESS, tec)

    def test_tec_cannot_start_other_techs_ot(self, wo_pending, tec2):
        with pytest.raises(ValidationError, match="técnico asignado"):
            validate_transition(wo_pending, WorkOrder.Status.IN_PROGRESS, tec2)

    def test_tec_can_move_to_in_review(self, wo_in_progress, tec):
        from apps.evidence.models import Signature
        Signature.objects.create(
            work_order=wo_in_progress,
            signature_type=Signature.SignatureType.TECHNICIAN,
            file_url="evidence/signatures/test.png",
            signer_name="Tecnico Test",
            file_hash="abc123",
        )
        assert validate_transition(wo_in_progress, WorkOrder.Status.IN_REVIEW, tec)

    def test_admin_can_complete_ot(self, wo_in_review, admin):
        assert validate_transition(wo_in_review, WorkOrder.Status.COMPLETED, admin)

    def test_sup_can_complete_ot(self, wo_in_review, sup):
        assert validate_transition(wo_in_review, WorkOrder.Status.COMPLETED, sup)

    def test_sup_can_reject_back_to_in_progress(self, wo_in_review, sup):
        assert validate_transition(wo_in_review, WorkOrder.Status.IN_PROGRESS, sup)

    def test_tec_cannot_complete_ot(self, wo_in_review, tec):
        with pytest.raises(ValidationError, match="rol"):
            validate_transition(wo_in_review, WorkOrder.Status.COMPLETED, tec)

    def test_invalid_transition_raises_error(self, wo_pending, admin):
        # PENDING → COMPLETED is not a valid path
        with pytest.raises(ValidationError, match="no está permitida"):
            validate_transition(wo_pending, WorkOrder.Status.COMPLETED, admin)

    def test_admin_can_cancel_with_comment(self, wo_pending, admin):
        assert validate_transition(wo_pending, WorkOrder.Status.CANCELLED, admin, comment="Motivo")

    def test_cancel_without_comment_raises_error(self, wo_pending, admin):
        with pytest.raises(ValidationError, match="comentario"):
            validate_transition(wo_pending, WorkOrder.Status.CANCELLED, admin, comment="")

    def test_non_admin_cannot_cancel(self, wo_pending, tec):
        with pytest.raises(ValidationError, match="ADMIN"):
            validate_transition(wo_pending, WorkOrder.Status.CANCELLED, tec, comment="Motivo")

    def test_cannot_cancel_completed_ot(self, wo_in_review, admin):
        wo_in_review.status = WorkOrder.Status.COMPLETED
        wo_in_review.save()
        with pytest.raises(ValidationError, match="cancelar"):
            validate_transition(wo_in_review, WorkOrder.Status.CANCELLED, admin, comment="X")


@pytest.mark.django_db
class TestApplyTransition:
    def test_apply_sets_started_at_on_first_in_progress(self, wo_pending, tec):
        assert wo_pending.started_at is None
        wo = apply_transition(wo_pending, WorkOrder.Status.IN_PROGRESS, tec)
        assert wo.status == WorkOrder.Status.IN_PROGRESS
        assert wo.started_at is not None

    def test_apply_does_not_overwrite_started_at(self, wo_in_review, tec, sup):
        # Reject back to IN_PROGRESS: started_at must not reset
        from django.utils import timezone as tz
        wo_in_review.started_at = tz.now()
        wo_in_review.save()
        original_started = wo_in_review.started_at
        wo = apply_transition(wo_in_review, WorkOrder.Status.IN_PROGRESS, sup)
        assert wo.started_at == original_started

    def test_apply_sets_completed_at_and_duration(self, wo_in_review, admin):
        from django.utils import timezone
        wo_in_review.started_at = timezone.now()
        wo_in_review.save()
        wo = apply_transition(wo_in_review, WorkOrder.Status.COMPLETED, admin)
        assert wo.completed_at is not None
        assert wo.actual_duration is not None

    def test_apply_creates_status_history_record(self, wo_pending, tec):
        assert WorkOrderStatusHistory.objects.filter(work_order=wo_pending).count() == 0
        apply_transition(wo_pending, WorkOrder.Status.IN_PROGRESS, tec)
        history = WorkOrderStatusHistory.objects.get(work_order=wo_pending)
        assert history.from_status == WorkOrder.Status.PENDING
        assert history.to_status == WorkOrder.Status.IN_PROGRESS
        assert history.changed_by == tec

    def test_apply_cancel_stores_comment(self, wo_pending, admin):
        wo = apply_transition(wo_pending, WorkOrder.Status.CANCELLED, admin, comment="Duplicada")
        history = WorkOrderStatusHistory.objects.get(work_order=wo)
        assert history.comment == "Duplicada"
