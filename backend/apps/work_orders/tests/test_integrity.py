"""
Regresiones de la Fase 0: inalterabilidad de una OT cerrada.

Antes de estos tests el endpoint de integridad no tenia ninguna cobertura, y
comparaba el hash del contenido contra el hash de los bytes del PDF, asi que
reportaba alteracion sobre todo reporte legitimo.

Lo que se verifica aqui, en orden:
  1. una OT intacta verifica,
  2. tocar la evidencia deja de verificar (checklist, foto, firma, tecnico),
  3. la API rechaza editar una OT en estado terminal,
  4. la base de datos rechaza alterar el log de auditoria y las firmas.
"""

import uuid
from datetime import date

import pytest
from django.db import connection, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.audit.models import AuditLog
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Photo, Signature
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders.integrity import (
    INTEGRITY_ALGORITHM_VERSION,
    compute_wo_content_hash,
)
from apps.work_orders.models import WorkOrder

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, **kwargs):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com",
        password="pass",
        first_name="Test",
        last_name="User",
        role=role,
        **kwargs,
    )


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def tec(db):
    return make_user(User.Role.TEC)


@pytest.fixture
def tec2(db):
    return make_user(User.Role.TEC)


@pytest.fixture
def asset(db):
    hospital = Hospital.objects.create(name="H1", code=str(uuid.uuid4())[:8])
    return Asset.objects.create(
        hospital=hospital,
        name="Central de oxigeno",
        code=str(uuid.uuid4())[:10],
        status=Asset.Status.ACTIVE,
    )


@pytest.fixture
def checklist_version(db, admin):
    template = ChecklistTemplate.objects.create(
        name=f"Mantenimiento preventivo {uuid.uuid4()}",
    )
    version = ChecklistTemplateVersion.objects.create(
        template=template,
        version_number=1,
        published_by=admin,
        is_current=True,
    )
    ChecklistField.objects.create(
        version=version,
        label="Presion de trabajo (bar)",
        field_type=ChecklistField.FieldType.NUMBER,
        is_required=True,
        sort_order=1,
    )
    return version


@pytest.fixture
def completed_wo(db, asset, admin, tec, checklist_version):
    """OT cerrada con checklist respondido, foto y firma del tecnico."""
    wo = WorkOrder.objects.create(
        asset=asset,
        task_type=WorkOrder.TaskType.CORRECTIVE,
        title="Fuga en regulador",
        description="Se detecta fuga audible en el regulador principal.",
        status=WorkOrder.Status.COMPLETED,
        priority=WorkOrder.Priority.HIGH,
        scheduled_date=date.today(),
        assigned_to=tec,
        created_by=admin,
        checklist_version=checklist_version,
        completed_at=timezone.now(),
    )
    response = ChecklistResponse.objects.create(
        work_order=wo,
        version=checklist_version,
        completed_by=tec,
        completed_at=timezone.now(),
    )
    ChecklistFieldResponse.objects.create(
        response=response,
        field=checklist_version.fields.first(),
        value="4.5",
        notes="Dentro de rango.",
    )
    Photo.objects.create(
        work_order=wo,
        file_url="evidence/photos/a.jpg",
        taken_at=timezone.now(),
        file_hash="a" * 64,
        uploaded_by=tec,
    )
    Signature.objects.create(
        work_order=wo,
        signature_type=Signature.SignatureType.TECHNICIAN,
        file_url="evidence/signatures/a.png",
        signer_name="Tecnico Test",
        file_hash="b" * 64,
    )
    return wo


def seal(wo):
    """Crea el GeneratedReport como lo haria el generador tras completar."""
    return GeneratedReport.objects.create(
        work_order=wo,
        report_type=GeneratedReport.ReportType.WORK_ORDER,
        title=f"Acta de Servicio OT-{wo.wo_number}",
        file_url=f"reports/{wo.id}/OT-{wo.wo_number}.pdf",
        file_hash="f" * 64,  # hash de los bytes del PDF, otro dominio
        content_hash=compute_wo_content_hash(wo),
        integrity_version=INTEGRITY_ALGORITHM_VERSION,
    )


def check_integrity(wo, admin):
    url = reverse("work-order-integrity", kwargs={"pk": str(wo.id)})
    return auth_client(admin).get(url)


# ---------------------------------------------------------------------------
# 1. El caso que antes fallaba siempre
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIntegrityVerifiesUntouchedRecord:
    def test_untouched_work_order_verifies(self, completed_wo, admin):
        seal(completed_wo)
        resp = check_integrity(completed_wo, admin)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["verified"] is True, (
            "una OT intacta debe verificar; si falla aqui el hash almacenado y "
            "el recalculado no son del mismo dominio"
        )

    def test_content_hash_is_not_the_pdf_hash(self, completed_wo):
        """El bug original era comparar estos dos valores entre si."""
        report = seal(completed_wo)
        assert report.content_hash != report.file_hash

    def test_hash_is_stable_across_recomputation(self, completed_wo):
        first = compute_wo_content_hash(completed_wo)
        second = compute_wo_content_hash(
            WorkOrder.objects.get(pk=completed_wo.pk)
        )
        assert first == second, "la serializacion canonica no es determinista"


# ---------------------------------------------------------------------------
# 2. Tocar la evidencia tiene que romper la verificacion
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIntegrityDetectsTampering:
    def test_detects_modified_checklist_answer(self, completed_wo, admin):
        seal(completed_wo)
        fr = ChecklistFieldResponse.objects.get(
            response__work_order=completed_wo
        )
        fr.value = "9.9"
        fr.save()
        resp = check_integrity(completed_wo, admin)
        assert resp.data["verified"] is False

    def test_detects_swapped_photo(self, completed_wo, admin):
        seal(completed_wo)
        photo = Photo.objects.get(work_order=completed_wo)
        photo.file_hash = "c" * 64
        photo.save()
        resp = check_integrity(completed_wo, admin)
        assert resp.data["verified"] is False

    def test_detects_added_photo(self, completed_wo, admin, tec):
        seal(completed_wo)
        Photo.objects.create(
            work_order=completed_wo,
            file_url="evidence/photos/b.jpg",
            taken_at=timezone.now(),
            file_hash="d" * 64,
            uploaded_by=tec,
        )
        resp = check_integrity(completed_wo, admin)
        assert resp.data["verified"] is False

    def test_detects_changed_technician(self, completed_wo, admin, tec2):
        """El dato que RNF-COM-01 exige inalterable bajo ISO 7396-1."""
        seal(completed_wo)
        WorkOrder.objects.filter(pk=completed_wo.pk).update(assigned_to=tec2)
        resp = check_integrity(
            WorkOrder.objects.get(pk=completed_wo.pk), admin
        )
        assert resp.data["verified"] is False

    def test_detects_rewritten_notes(self, completed_wo, admin):
        seal(completed_wo)
        WorkOrder.objects.filter(pk=completed_wo.pk).update(
            notes="Observacion anadida despues del cierre."
        )
        resp = check_integrity(
            WorkOrder.objects.get(pk=completed_wo.pk), admin
        )
        assert resp.data["verified"] is False

    def test_legacy_report_without_content_hash_is_inconclusive(
        self, completed_wo, admin
    ):
        """Nunca afirmar 'verificado' sobre un reporte que no se puede probar."""
        report = seal(completed_wo)
        GeneratedReport.objects.filter(pk=report.pk).update(
            content_hash="", integrity_version=""
        )
        resp = check_integrity(completed_wo, admin)
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["verified"] is None


# ---------------------------------------------------------------------------
# 3. La API no deja editar una OT en estado terminal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCompletedWorkOrderIsReadOnly:
    def _detail(self, wo):
        return reverse("work-orders-detail", kwargs={"pk": str(wo.id)})

    def test_admin_cannot_patch_completed_wo(self, completed_wo, admin):
        resp = auth_client(admin).patch(
            self._detail(completed_wo), {"title": "Otro titulo"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        completed_wo.refresh_from_db()
        assert completed_wo.title == "Fuga en regulador"

    def test_admin_cannot_reassign_technician_of_completed_wo(
        self, completed_wo, admin, tec, tec2
    ):
        """Segunda via: el endpoint assign no pasa por partial_update."""
        url = reverse("work-orders-assign", kwargs={"pk": str(completed_wo.id)})
        resp = auth_client(admin).post(
            url, {"assigned_to": str(tec2.id)}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        completed_wo.refresh_from_db()
        assert completed_wo.assigned_to_id == tec.id

    def test_tec_cannot_patch_own_completed_wo(self, completed_wo, tec):
        resp = auth_client(tec).patch(
            self._detail(completed_wo), {"notes": "nota tardia"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cancelled_wo_is_also_read_only(self, completed_wo, admin):
        WorkOrder.objects.filter(pk=completed_wo.pk).update(
            status=WorkOrder.Status.CANCELLED
        )
        resp = auth_client(admin).patch(
            self._detail(completed_wo), {"title": "x"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_open_wo_is_still_editable(self, completed_wo, admin):
        """El guard no puede bloquear el flujo normal de una OT abierta."""
        WorkOrder.objects.filter(pk=completed_wo.pk).update(
            status=WorkOrder.Status.IN_PROGRESS
        )
        resp = auth_client(admin).patch(
            self._detail(completed_wo), {"title": "Titulo corregido"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 4. La garantia vive en la base de datos, no solo en el ORM
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestDatabaseLevelImmutability:
    def _audit_row(self, admin):
        return AuditLog.objects.create(
            user=admin,
            action=AuditLog.Action.STATUS_CHANGE,
            entity_type="WorkOrder",
            entity_id=uuid.uuid4(),
            changes={"new_status": "COMPLETED"},
        )

    def test_queryset_update_on_auditlog_is_blocked_by_database(self, admin):
        """La via que el guard del ORM no cubria."""
        log = self._audit_row(admin)
        with pytest.raises(Exception) as exc, transaction.atomic():
            AuditLog.objects.filter(pk=log.pk).update(action="CREATE")
        assert "append-only" in str(exc.value)
        log.refresh_from_db()
        assert log.action == AuditLog.Action.STATUS_CHANGE

    def test_queryset_delete_on_auditlog_is_blocked_by_database(self, admin):
        log = self._audit_row(admin)
        with pytest.raises(Exception) as exc, transaction.atomic():
            AuditLog.objects.filter(pk=log.pk).delete()
        assert "append-only" in str(exc.value)
        assert AuditLog.objects.filter(pk=log.pk).exists()

    def test_raw_sql_update_on_auditlog_is_blocked(self, admin):
        """Ni siquiera saltandose Django por completo."""
        log = self._audit_row(admin)
        with (
            pytest.raises(Exception) as exc,
            transaction.atomic(),
            connection.cursor() as cur,
        ):
            cur.execute(
                "UPDATE audit_auditlog SET entity_type = %s WHERE id = %s",
                ["Alterado", str(log.pk)],
            )
        assert "append-only" in str(exc.value)

    def test_signature_update_is_blocked_by_database(self, completed_wo):
        sig = Signature.objects.get(work_order=completed_wo)
        with pytest.raises(Exception) as exc, transaction.atomic():
            Signature.objects.filter(pk=sig.pk).update(signer_name="Otro")
        assert "inmutable" in str(exc.value)
        sig.refresh_from_db()
        assert sig.signer_name == "Tecnico Test"

    def test_signature_delete_is_blocked_by_database(self, completed_wo):
        sig = Signature.objects.get(work_order=completed_wo)
        with pytest.raises(Exception) as exc, transaction.atomic():
            Signature.objects.filter(pk=sig.pk).delete()
        assert "inmutable" in str(exc.value)
        assert Signature.objects.filter(pk=sig.pk).exists()

    def test_auditlog_insert_still_works(self, admin):
        """Append-only significa append: los INSERT no se tocan."""
        before = AuditLog.objects.count()
        self._audit_row(admin)
        assert AuditLog.objects.count() == before + 1


# ---------------------------------------------------------------------------
# 5. Versiones de checklist inmutables
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChecklistVersionImmutability:
    def test_cannot_edit_published_version(self, checklist_version):
        checklist_version.version_number = 99
        with pytest.raises(ValueError, match="inmutable"):
            checklist_version.save()

    def test_can_still_flip_is_current(self, checklist_version):
        """Publicar una version nueva baja la bandera de la anterior."""
        checklist_version.is_current = False
        checklist_version.save(update_fields=["is_current"])
        checklist_version.refresh_from_db()
        assert checklist_version.is_current is False

    def test_cannot_edit_field_label(self, checklist_version):
        field = checklist_version.fields.first()
        field.label = "Otra pregunta"
        with pytest.raises(ValueError, match="inmutable"):
            field.save()

    def test_cannot_delete_field(self, checklist_version):
        field = checklist_version.fields.first()
        with pytest.raises(ValueError, match="no se elimina"):
            field.delete()
