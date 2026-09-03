"""
Prueba de humo del camino critico: el flujo que se ensena en una demo.

Un ADMIN crea una OT, el tecnico la ejecuta en campo (checklist, foto con GPS
y firma), el ADMIN la aprueba, el sistema genera el acta en PDF y el cliente
la ve y la descarga desde su portal.

No sustituye a los tests de unidad de cada modulo: existe para que un fallo en
cualquier eslabon aparezca aqui, entero y en orden, antes de aparecer delante
de un cliente. Si este test pasa, el recorrido de la demo funciona.
"""

import base64
import uuid
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Photo, Signature
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders.models import WorkOrder

# PNG 1x1 valido: sirve como firma y como foto sin depender de ficheros.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
    "IQAAAABJRU5ErkJggg=="
)


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, **kwargs):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@todogas.test",
        password="demo",
        first_name="Demo",
        last_name=role.title(),
        role=role,
        **kwargs,
    )


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(
        name="Hospital San Vicente", code=f"HSV{uuid.uuid4().hex[:4]}", is_active=True
    )


@pytest.fixture
def otro_hospital(db):
    return Hospital.objects.create(
        name="Clinica Las Americas", code=f"CLA{uuid.uuid4().hex[:4]}", is_active=True
    )


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def tecnico(db):
    return make_user(User.Role.TEC)


@pytest.fixture
def cliente(db, hospital):
    return make_user(User.Role.CLI, hospital=hospital)


@pytest.fixture
def activo(db, hospital):
    return Asset.objects.create(
        hospital=hospital,
        name="Central de oxigeno medicinal",
        code=f"OX-{uuid.uuid4().hex[:6]}",
        manufacturer="Air Liquide",
        model="Manifold MX-40",
        serial_number=f"SN{uuid.uuid4().hex[:8]}",
        status=Asset.Status.ACTIVE,
    )


@pytest.fixture
def checklist(db, admin):
    template = ChecklistTemplate.objects.create(
        name=f"Preventivo central de oxigeno {uuid.uuid4().hex[:6]}"
    )
    version = ChecklistTemplateVersion.objects.create(
        template=template, version_number=1, published_by=admin, is_current=True
    )
    ChecklistField.objects.create(
        version=version,
        label="Presion de linea (bar)",
        field_type=ChecklistField.FieldType.NUMBER,
        is_required=True,
        sort_order=1,
    )
    return version


@pytest.mark.django_db
class TestFlujoCompletoDeLaDemo:
    """Un unico recorrido, en el orden en que se ensena."""

    def test_de_creacion_a_entrega_al_cliente(
        self, admin, tecnico, cliente, activo, checklist, hospital
    ):
        admin_c, tec_c, cli_c = client_for(admin), client_for(tecnico), client_for(cliente)

        # ── 1. El ADMIN crea la OT ──────────────────────────────────────────
        resp = admin_c.post(
            reverse("work-orders-list"),
            {
                "asset": str(activo.id),
                "task_type": WorkOrder.TaskType.CORRECTIVE,
                "title": "Fuga audible en el regulador principal",
                "description": "El personal de enfermeria reporta silbido constante.",
                "priority": WorkOrder.Priority.HIGH,
                "scheduled_date": str(date.today() + timedelta(days=1)),
                "assigned_to": str(tecnico.id),
                "checklist_version": str(checklist.id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        wo_id = resp.data["id"]
        assert resp.data["status"] == WorkOrder.Status.PENDING

        # Numero legible OT-2026-00001, no "OT-1" (RF-OT-02).
        import re
        assert re.fullmatch(r"OT-\d{4}-\d{5}", resp.data["wo_code"]), resp.data["wo_code"]

        # ── 2. El tecnico la ve en su lista y la inicia ──────────────────────
        lista = tec_c.get(reverse("work-orders-list")).data
        assert str(wo_id) in [str(w["id"]) for w in lista["results"]], (
            "la OT recien creada no aparece en la lista del tecnico asignado"
        )

        transicion = reverse("work-orders-transition", kwargs={"pk": wo_id})
        resp = tec_c.post(
            transicion, {"new_status": WorkOrder.Status.IN_PROGRESS}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        # ── 3. Responde el checklist ────────────────────────────────────────
        resp = tec_c.post(
            reverse("checklist-responses-list"),
            {"work_order": str(wo_id), "version": str(checklist.id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        # El serializer de creacion solo devuelve work_order y version, sin id.
        # La app lo resuelve releyendo el detalle de la OT, asi que el test
        # hace lo mismo en vez de ir a la base de datos por atras.
        detalle = tec_c.get(reverse("work-orders-detail", kwargs={"pk": wo_id})).data
        cr_id = detalle["checklist_response_id"]
        assert cr_id, "el detalle de la OT no expone checklist_response_id"

        resp = tec_c.post(
            reverse("checklist-responses-submit-field", kwargs={"pk": cr_id}),
            {"field": str(checklist.fields.first().id), "value": "4.5"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        resp = tec_c.post(
            reverse("checklist-responses-complete", kwargs={"pk": cr_id})
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        # ── 4. Sube una foto con geolocalizacion ────────────────────────────
        foto = SimpleUploadedFile("evidencia.png", PNG_1PX, content_type="image/png")
        resp = tec_c.post(
            reverse("evidence-photos-list"),
            {
                "work_order": str(wo_id),
                "file": foto,
                "taken_at": timezone.now().isoformat(),
                "latitude": "6.2442000",
                "longitude": "-75.5812000",
                "caption": "Regulador principal antes de la intervencion",
            },
            format="multipart",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        foto_db = Photo.objects.get(work_order_id=wo_id)
        assert foto_db.file_hash, "la foto se guardo sin hash de integridad"
        assert foto_db.latitude is not None, "RF-EV-01 exige geolocalizacion"

        # ── 5. Firma ────────────────────────────────────────────────────────
        resp = tec_c.post(
            reverse("evidence-signatures-list"),
            {
                "work_order": str(wo_id),
                "image_data": base64.b64encode(PNG_1PX).decode(),
                "signer_name": "Juan Esteban Marulanda",
                "signer_role": "Tecnico de gases medicinales",
                "signature_type": Signature.SignatureType.TECHNICIAN,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        # ── 6. Envia a revision ─────────────────────────────────────────────
        resp = tec_c.post(
            transicion, {"new_status": WorkOrder.Status.IN_REVIEW}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        # ── 7. El ADMIN aprueba y se genera el acta ─────────────────────────
        resp = admin_c.post(
            transicion, {"new_status": WorkOrder.Status.COMPLETED}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

        reporte = GeneratedReport.objects.filter(work_order_id=wo_id).first()
        assert reporte is not None, (
            "no se genero el acta al completar la OT. CELERY_TASK_EAGER_PROPAGATES "
            "esta en False, asi que un fallo dentro de la tarea se traga la "
            "excepcion y la OT queda sin PDF sin avisar."
        )
        assert reporte.file_hash, "el acta se guardo sin hash del PDF"
        assert reporte.content_hash, "el acta se guardo sin hash de contenido"

        # ── 8. La integridad verifica ───────────────────────────────────────
        resp = admin_c.get(reverse("work-order-integrity", kwargs={"pk": wo_id}))
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["verified"] is True, (
            "el acta recien generada no verifica su propia integridad"
        )

        # ── 9. El cliente ve su OT y puede descargar el acta ────────────────
        resp = cli_c.get("/api/client-portal/summary/")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        wo_numbers = [w["wo_number"] for w in resp.data["recent_work_orders"]]
        assert WorkOrder.objects.get(pk=wo_id).wo_number in wo_numbers, (
            "la OT completada no aparece en el portal del cliente"
        )
        assert resp.data["recent_reports"], "el portal del cliente no ofrece el acta"
        # El APK ya publicado lee la clave antigua: si desaparece, las tablets
        # en campo dejan de ver los reportes sin que nadie lo note.
        assert resp.data["pending_reports"] == resp.data["recent_reports"]

        lista_cli = cli_c.get(reverse("work-orders-list")).data
        assert str(wo_id) in [str(w["id"]) for w in lista_cli["results"]]

        # ── 10. Y cerrada, ya no se puede tocar (Fase 0) ────────────────────
        resp = admin_c.patch(
            reverse("work-orders-detail", kwargs={"pk": wo_id}),
            {"title": "Titulo cambiado despues del cierre"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAislamientoEntreClientes:
    """Lo que un cliente NO puede ver. Es la pregunta que hara en la reunion."""

    def test_un_cliente_no_ve_activos_de_otro_hospital(
        self, cliente, activo, otro_hospital
    ):
        ajeno = Asset.objects.create(
            hospital=otro_hospital,
            name="Central ajena",
            code=f"AJ-{uuid.uuid4().hex[:6]}",
            status=Asset.Status.ACTIVE,
        )
        data = client_for(cliente).get(reverse("assets-list")).data
        codigos = [a["code"] for a in data["results"]]
        assert activo.code in codigos
        assert ajeno.code not in codigos, "fuga de datos entre hospitales"

    def test_un_cliente_no_ve_ots_sin_completar(
        self, cliente, activo, admin, tecnico
    ):
        abierta = WorkOrder.objects.create(
            asset=activo,
            task_type=WorkOrder.TaskType.CORRECTIVE,
            title="Trabajo en curso",
            status=WorkOrder.Status.IN_PROGRESS,
            priority=WorkOrder.Priority.MEDIUM,
            scheduled_date=date.today(),
            assigned_to=tecnico,
            created_by=admin,
        )
        data = client_for(cliente).get(reverse("work-orders-list")).data
        assert str(abierta.id) not in [str(w["id"]) for w in data["results"]], (
            "el cliente ve una OT que todavia no esta terminada"
        )
