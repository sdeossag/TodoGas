"""Un acta que no se pudo generar tiene que dejar rastro y ser visible.

Regresion: en modo eager (CELERY_TASK_ALWAYS_EAGER, el de desarrollo) self.retry()
no reintenta —levanta Retry y apply() la traga porque EAGER_PROPAGATES esta en
False—, asi que `retries` nunca crecia y la rama que anotaba el fallo en auditoria
no se alcanzaba jamas. La OT quedaba cerrada sin acta y sin ningun rastro, y la
pestaña de reportes giraba dos minutos sin poder distinguir el fallo de una
generacion todavia en curso.
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.audit.models import AuditLog
from apps.reports.failures import (
    FAILURE_MARKER,
    REPORT_ENTITY_TYPE,
    has_report_failure,
    record_report_failure,
)
from apps.reports.models import GeneratedReport
from apps.reports.tasks import generate_work_order_pdf
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.maintenance.testing import make_work_order

GENERATOR = "apps.reports.tasks.generate_service_report_pdf"


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="A",
        last_name="B",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(
        name="H", code=str(uuid.uuid4())[:8], contact_name="Contacto"
    )


@pytest.fixture
def asset(db, hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Equipo",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


@pytest.fixture
def completed_wo(db, asset, admin_user):
    return make_work_order(asset, admin_user, status=WorkOrder.Status.COMPLETED)


def failure_entries(work_order):
    return AuditLog.objects.filter(
        entity_type=REPORT_ENTITY_TYPE,
        entity_id=work_order.id,
        changes__resultado=FAILURE_MARKER,
    )


# ── El fallo queda registrado ────────────────────────────────────────────────

def test_failed_generation_is_recorded_in_eager_mode(completed_wo):
    """El nucleo del bug: en eager no habia reintentos, luego no habia registro."""
    with patch(GENERATOR, side_effect=RuntimeError('WeasyPrint exploto')):
        generate_work_order_pdf.apply(args=[str(completed_wo.id)])

    assert failure_entries(completed_wo).count() == 1


def test_recorded_failure_keeps_the_error_message(completed_wo):
    with patch(GENERATOR, side_effect=RuntimeError('falta libgobject')):
        generate_work_order_pdf.apply(args=[str(completed_wo.id)])

    entry = failure_entries(completed_wo).first()
    assert 'libgobject' in entry.changes['error']


def test_has_report_failure_sees_the_record(completed_wo):
    assert has_report_failure(completed_wo.id) is False
    record_report_failure(str(completed_wo.id), RuntimeError('boom'))
    assert has_report_failure(completed_wo.id) is True


def test_successful_generation_records_no_failure(completed_wo):
    with patch(GENERATOR, return_value=(b'%PDF', 'reports/x.pdf', 'hash')), \
            patch('apps.reports.tasks.send_report_email.delay'):
        generate_work_order_pdf.apply(args=[str(completed_wo.id)])

    assert failure_entries(completed_wo).count() == 0


# ── report_status distingue fallo de "aun generando" ─────────────────────────

def report_status_of(client, wo):
    resp = client.get(f'/api/work-orders/{wo.id}/')
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()['report_status']


def test_report_status_is_failed_after_a_recorded_failure(completed_wo, admin_user):
    with patch(GENERATOR, side_effect=RuntimeError('boom')):
        generate_work_order_pdf.apply(args=[str(completed_wo.id)])

    assert report_status_of(auth_client(admin_user), completed_wo) == 'failed'


def test_report_status_is_missing_while_still_generating(completed_wo, admin_user):
    """Sin acta y sin fallo registrado: todavia se esta generando."""
    assert report_status_of(auth_client(admin_user), completed_wo) == 'missing'


def test_report_status_is_ok_once_the_acta_exists(completed_wo, admin_user):
    GeneratedReport.objects.create(
        work_order=completed_wo,
        report_type=GeneratedReport.ReportType.WORK_ORDER,
        title='Acta',
        file_url='reports/x.pdf',
        file_hash='h',
    )
    assert report_status_of(auth_client(admin_user), completed_wo) == 'ok'


def test_report_status_recovers_to_ok_after_a_successful_retry(completed_wo, admin_user):
    """Un fallo antiguo no debe dejar la OT marcada como fallida para siempre."""
    record_report_failure(str(completed_wo.id), RuntimeError('boom'))
    GeneratedReport.objects.create(
        work_order=completed_wo,
        report_type=GeneratedReport.ReportType.WORK_ORDER,
        title='Acta',
        file_url='reports/x.pdf',
        file_hash='h',
    )
    assert report_status_of(auth_client(admin_user), completed_wo) == 'ok'


def test_open_work_order_reports_not_applicable(asset, admin_user):
    wo = make_work_order(asset, admin_user, title='OT abierta')
    assert report_status_of(auth_client(admin_user), wo) == 'not_applicable'
