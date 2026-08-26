import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.reports.models import GeneratedReport, ReportSendLog


# ── Helpers ─────────────────────────────────────────────────────────────────

def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="A",
        last_name="B",
        role=role,
        hospital=hospital,
    )


def make_hospital(name="H"):
    return Hospital.objects.create(
        name=name,
        code=str(uuid.uuid4())[:8],
        contact_email=f"{uuid.uuid4()}@hospital.com",
        contact_name="Contacto",
    )


def make_asset(hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


def make_wo(asset, created_by, assigned_to=None, wo_status=WorkOrder.Status.COMPLETED):
    wo = WorkOrder(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="OT test",
        status=wo_status,
        priority=WorkOrder.Priority.MEDIUM,
        scheduled_date=date.today(),
        assigned_to=assigned_to,
        created_by=created_by,
    )
    wo.save()
    return wo


FAKE_KEY = "reports/test/OT-1.pdf"
FAKE_URL = "https://s3.amazonaws.com/todogas/reports/test/OT-1.pdf?X=y"
FAKE_PDF = b"%PDF-1.4 test"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def hospital_b(db):
    return make_hospital("Hospital B")


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def tec(db, hospital):
    return make_user(User.Role.TEC, hospital=hospital)


@pytest.fixture
def cli(db, hospital):
    return make_user(User.Role.CLI, hospital=hospital)


@pytest.fixture
def cli_b(db, hospital_b):
    return make_user(User.Role.CLI, hospital=hospital_b)


@pytest.fixture
def asset(db, hospital):
    return make_asset(hospital)


@pytest.fixture
def wo(db, asset, admin, tec):
    return make_wo(asset, admin, assigned_to=tec)


@pytest.fixture
def report(db, wo):
    return GeneratedReport.objects.create(
        work_order=wo,
        report_type=GeneratedReport.ReportType.WORK_ORDER,
        title=f"Acta OT-{wo.wo_number}",
        file_url=FAKE_KEY,
        file_hash="abc123",
    )


# ── Task tests ────────────────────────────────────────────────────────────────

@patch("apps.reports.tasks.send_report_email")
@patch("apps.reports.tasks.generate_service_report_pdf")
def test_generate_work_order_pdf_task_creates_report_and_queues_email(
    mock_gen, mock_send_email, db, wo
):
    from apps.reports.tasks import generate_work_order_pdf

    mock_gen.return_value = (FAKE_PDF, FAKE_KEY, "abc123hash")
    mock_send_email.delay = MagicMock()

    result = generate_work_order_pdf(str(wo.id))

    assert result["status"] == "ok"
    mock_send_email.delay.assert_called_once_with(str(wo.id))


@patch("apps.reports.tasks.generate_service_report_pdf")
def test_generate_work_order_pdf_creates_generated_report(mock_gen, db, wo):
    from apps.reports.tasks import generate_work_order_pdf

    def _side_effect(work_order):
        GeneratedReport.objects.create(
            work_order=work_order,
            report_type=GeneratedReport.ReportType.WORK_ORDER,
            title=f"Acta OT-{work_order.wo_number}",
            file_url=FAKE_KEY,
            file_hash="pdf_hash",
        )
        return (FAKE_PDF, FAKE_KEY, "report_hash")

    mock_gen.side_effect = _side_effect

    with patch("apps.reports.tasks.send_report_email") as mock_email:
        mock_email.delay = MagicMock()
        generate_work_order_pdf(str(wo.id))

    assert GeneratedReport.objects.filter(work_order=wo).exists()
    gr = GeneratedReport.objects.get(work_order=wo)
    assert gr.report_type == GeneratedReport.ReportType.WORK_ORDER
    assert gr.file_url == FAKE_KEY


@patch("apps.reports.tasks.EmailMessage")
def test_send_report_email_creates_send_log_on_success(mock_email_cls, db, wo, report):
    from apps.reports.tasks import send_report_email

    mock_msg = MagicMock()
    mock_email_cls.return_value = mock_msg

    result = send_report_email(str(wo.id))

    assert result["status"] == "sent"
    log = ReportSendLog.objects.get(report=report)
    assert log.was_successful is True
    assert log.recipient_email == wo.asset.hospital.contact_email


@patch("apps.reports.tasks.send_report_email.retry")
@patch("apps.reports.tasks.EmailMessage")
def test_send_report_email_logs_error_on_failure(mock_email_cls, mock_retry, db, wo, report):
    from apps.reports.tasks import send_report_email

    mock_email_cls.side_effect = Exception("SMTP down")
    # Simular que el reintento tambien falla para que la excepcion se propague
    mock_retry.side_effect = Exception("SMTP down")

    with pytest.raises(Exception):
        send_report_email(str(wo.id))

    log = ReportSendLog.objects.filter(report=report, was_successful=False).first()
    assert log is not None
    assert "SMTP down" in log.error_message


# ── API permission tests ───────────────────────────────────────────────────────

REPORTS_URL = "/api/reports/"


@patch("apps.reports.serializers.default_storage")
def test_cli_can_see_reports_of_own_hospital(mock_storage, db, cli, report):
    mock_storage.url.return_value = FAKE_URL
    resp = auth_client(cli).get(REPORTS_URL)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 1


@patch("apps.reports.serializers.default_storage")
def test_cli_cannot_see_reports_of_other_hospital(mock_storage, db, cli_b, report):
    mock_storage.url.return_value = FAKE_URL
    resp = auth_client(cli_b).get(REPORTS_URL)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 0


@patch("apps.reports.tasks.send_report_email")
@patch("apps.reports.serializers.default_storage")
def test_admin_can_resend_email(mock_storage, mock_send_email, db, admin, report):
    mock_storage.url.return_value = FAKE_URL
    mock_send_email.delay = MagicMock()

    resp = auth_client(admin).post(f"{REPORTS_URL}{report.id}/resend-email/")

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "queued"
    mock_send_email.delay.assert_called_once_with(str(report.work_order_id))
