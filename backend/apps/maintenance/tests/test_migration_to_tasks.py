"""La migracion al modelo de tareas (maintenance 0003) sobre datos del modelo viejo.

Retrocede la base al estado anterior a la migracion, crea datos con la forma
vieja (plan con frecuencia y lista de activos, OT con un activo y su checklist),
calcula el hash de integridad v1 con una copia congelada del algoritmo
original, migra hacia adelante y comprueba dos cosas:

- que cada dato quedo donde el diseno dice;
- que el hash v1 de la OT cerrada sigue siendo EXACTAMENTE el mismo. Es la
  garantia de que las actas ya firmadas se siguen verificando.

Tambien la migracion inversa y el conflicto de un activo en dos planes.
"""

import hashlib
import json
from datetime import date, timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

ANTES = [
    ("maintenance", "0002_plan_tasks_and_tasks"),
    ("assets", "0004_plan_tasks_and_tasks"),
    ("work_orders", "0004_plan_tasks_and_tasks"),
    ("checklists", "0005_plan_tasks_and_tasks"),
    ("evidence", "0004_photo_task"),
]

pytestmark = pytest.mark.django_db(transaction=True)


# ── Copia congelada del algoritmo v1 original (commit 16c6079) ───────────────

def _dt(v):
    return v.isoformat() if v is not None else None


def _id(v):
    return str(v) if v is not None else None


def _num(v):
    return str(v) if v is not None else None


def hash_v1_original(apps, work_order):
    ChecklistResponse = apps.get_model("checklists", "ChecklistResponse")
    Photo = apps.get_model("evidence", "Photo")
    Signature = apps.get_model("evidence", "Signature")
    StockMovement = apps.get_model("inventory", "StockMovement")

    checklist = (
        ChecklistResponse.objects.filter(work_order=work_order)
        .prefetch_related("field_responses")
        .first()
    )
    checklist_payload = None if checklist is None else {
        "id": _id(checklist.id),
        "version": _id(checklist.version_id),
        "completed_at": _dt(checklist.completed_at),
        "completed_by": _id(checklist.completed_by_id),
        "fields": sorted(
            (
                {
                    "field": _id(fr.field_id),
                    "value": fr.value,
                    "notes": fr.notes,
                    "answered_at": _dt(fr.answered_at),
                }
                for fr in checklist.field_responses.all()
            ),
            key=lambda row: row["field"],
        ),
    }
    photos = sorted(
        (
            {
                "id": _id(p.id), "file_hash": p.file_hash, "taken_at": _dt(p.taken_at),
                "latitude": _num(p.latitude), "longitude": _num(p.longitude),
                "uploaded_by": _id(p.uploaded_by_id),
            }
            for p in Photo.objects.filter(work_order=work_order)
        ),
        key=lambda row: row["id"],
    )
    signatures = sorted(
        (
            {
                "id": _id(s.id), "signature_type": s.signature_type,
                "file_hash": s.file_hash, "signer_name": s.signer_name,
                "signer_role": s.signer_role, "signed_at": _dt(s.signed_at),
            }
            for s in Signature.objects.filter(work_order=work_order)
        ),
        key=lambda row: row["id"],
    )
    stock = sorted(
        (
            {
                "id": _id(m.id), "item": _id(m.item_id),
                "movement_type": m.movement_type, "quantity": _num(m.quantity),
            }
            for m in StockMovement.objects.filter(work_order=work_order)
        ),
        key=lambda row: row["id"],
    )
    payload = {
        "algorithm_version": "1",
        "work_order": {
            "id": _id(work_order.id), "wo_number": work_order.wo_number,
            "task_type": work_order.task_type, "status": work_order.status,
            "title": work_order.title, "description": work_order.description,
            "notes": work_order.notes, "asset": _id(work_order.asset_id),
            "assigned_to": _id(work_order.assigned_to_id),
            "checklist_version": _id(work_order.checklist_version_id),
            "scheduled_date": _dt(work_order.scheduled_date),
            "started_at": _dt(work_order.started_at),
            "completed_at": _dt(work_order.completed_at),
        },
        "checklist_response": checklist_payload,
        "photos": photos,
        "signatures": signatures,
        "stock_movements": stock,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Utilidades de migracion ──────────────────────────────────────────────────

def _executor():
    return MigrationExecutor(connection)


def ir_a(objetivos):
    executor = _executor()
    executor.migrate(objetivos)
    # El estado historico solo incluye los antecesores de los objetivos; se
    # anade la ultima migracion de las demas apps para que modelos como User
    # lleguen con todos sus campos.
    loader = _executor().loader
    tocadas = {app for app, _ in objetivos}
    resto = [n for n in loader.graph.leaf_nodes() if n[0] not in tocadas]
    return loader.project_state(list(objetivos) + resto).apps


def ir_al_final():
    executor = _executor()
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.fixture
def base_antigua():
    """Deja la base justo antes de la migracion de datos y la devuelve al final."""
    apps = ir_a(ANTES)
    try:
        yield apps
    finally:
        ir_al_final()


def datos_viejos(apps):
    Hospital = apps.get_model("assets", "Hospital")
    Asset = apps.get_model("assets", "Asset")
    User = apps.get_model("users", "User")
    MaintenancePlan = apps.get_model("maintenance", "MaintenancePlan")
    WorkOrder = apps.get_model("work_orders", "WorkOrder")
    ChecklistTemplate = apps.get_model("checklists", "ChecklistTemplate")
    Version = apps.get_model("checklists", "ChecklistTemplateVersion")
    Field = apps.get_model("checklists", "ChecklistField")
    Response = apps.get_model("checklists", "ChecklistResponse")
    FieldResponse = apps.get_model("checklists", "ChecklistFieldResponse")
    Photo = apps.get_model("evidence", "Photo")
    Signature = apps.get_model("evidence", "Signature")

    hospital = Hospital.objects.create(name="H", code="H-MIG")
    admin = User.objects.create(email="admin@mig.test", role="ADMIN", password="x")
    tec = User.objects.create(email="tec@mig.test", role="TEC", password="x")
    alarma = Asset.objects.create(hospital=hospital, name="Alarma", code="MIG-1", status="ACTIVE")
    caja = Asset.objects.create(hospital=hospital, name="Caja", code="MIG-2", status="ACTIVE")
    plantilla = ChecklistTemplate.objects.create(name="Preventivo MIG")
    version = Version.objects.create(template=plantilla, version_number=1, is_current=True)
    campo = Field.objects.create(version=version, label="PSI", field_type="NUMBER", sort_order=0)

    proxima = date.today() + timedelta(days=45)
    plan = MaintenancePlan.objects.create(
        name="Plan alarmas", task_type="PREVENTIVE", frequency_value=6,
        frequency_unit="MONTHS", checklist_template=plantilla,
        next_due_date=proxima, estimated_duration=timedelta(minutes=70),
    )
    plan.assets.set([alarma, caja])

    cerrada = WorkOrder.objects.create(
        wo_number=1, wo_year=2026, asset=alarma, task_type="PREVENTIVE",
        title="[PM] Plan alarmas — Alarma", status="COMPLETED", priority="MEDIUM",
        scheduled_date=date.today() - timedelta(days=5), created_by=admin,
        assigned_to=tec, maintenance_plan=plan, checklist_version=version,
        started_at=timezone.now() - timedelta(hours=2), completed_at=timezone.now(),
    )
    respuesta = Response.objects.create(
        work_order=cerrada, version=version, completed_by=tec,
        started_at=timezone.now(), completed_at=timezone.now(),
    )
    FieldResponse.objects.create(response=respuesta, field=campo, value="55")
    Photo.objects.create(
        work_order=cerrada, file_url="p.jpg", taken_at=timezone.now(),
        file_hash="a" * 64, uploaded_by=tec,
    )
    Signature.objects.create(
        work_order=cerrada, signature_type="TECHNICIAN", file_url="s.png",
        signer_name="Tec", file_hash="b" * 64,
    )
    abierta = WorkOrder.objects.create(
        wo_number=2, wo_year=2026, asset=caja, task_type="PREVENTIVE",
        title="[PM] Plan alarmas — Caja", status="IN_PROGRESS", priority="MEDIUM",
        scheduled_date=date.today(), created_by=admin, assigned_to=tec,
        maintenance_plan=plan, checklist_version=version,
    )
    return {
        "hospital": hospital, "alarma": alarma, "caja": caja, "plan": plan,
        "cerrada": cerrada, "abierta": abierta, "respuesta": respuesta,
        "version": version, "proxima": proxima,
        "hash_v1": hash_v1_original(apps, cerrada),
    }


# ── Pruebas ──────────────────────────────────────────────────────────────────

def test_el_hash_v1_no_cambia_al_migrar(base_antigua):
    viejo = datos_viejos(base_antigua)

    ir_al_final()

    from apps.work_orders.integrity import compute_wo_content_hash
    from apps.work_orders.models import WorkOrder

    cerrada = WorkOrder.objects.get(pk=viejo["cerrada"].pk)
    assert compute_wo_content_hash(cerrada, "1") == viejo["hash_v1"], (
        "el hash v1 de una OT cerrada cambio al migrar: sus actas dejarian de verificar"
    )


def test_los_datos_quedan_donde_dice_el_diseno(base_antigua):
    viejo = datos_viejos(base_antigua)

    ir_al_final()

    from apps.assets.models import Asset
    from apps.checklists.models import ChecklistResponse
    from apps.maintenance.models import MaintenancePlan, RescheduleCause, Task
    from apps.work_orders.models import WorkOrder

    plan = MaintenancePlan.objects.get(pk=viejo["plan"].pk)
    tarea_plan = plan.tasks.get()
    assert (tarea_plan.frequency_value, tarea_plan.frequency_unit) == (6, "MONTHS")
    assert tarea_plan.checklist_template_id == viejo["version"].template_id
    assert tarea_plan.fixed_schedule is False, "D3: no fija por defecto"
    assert tarea_plan.estimated_duration == timedelta(minutes=70)

    assert set(Asset.objects.filter(plan=plan).values_list("code", flat=True)) == {"MIG-1", "MIG-2"}

    cerrada = WorkOrder.objects.get(pk=viejo["cerrada"].pk)
    assert cerrada.hospital_id == viejo["hospital"].pk
    t_cerrada = cerrada.tasks.get()
    assert t_cerrada.status == Task.Status.DONE
    assert t_cerrada.plan_task == tarea_plan
    assert t_cerrada.checklist_version_id == viejo["version"].pk
    assert t_cerrada.completed_at == cerrada.completed_at
    assert ChecklistResponse.objects.get(pk=viejo["respuesta"].pk).task == t_cerrada

    abierta = WorkOrder.objects.get(pk=viejo["abierta"].pk)
    assert abierta.tasks.get().status == Task.Status.SCHEDULED

    # La alarma no tiene OT abierta: recibe su pendiente con la proxima fecha.
    pendiente = Task.objects.get(asset_id=viejo["alarma"].pk, status=Task.Status.PENDING)
    assert pendiente.scheduled_date == viejo["proxima"]
    assert pendiente.plan_task == tarea_plan
    # La caja ya tiene su tarea abierta dentro de la OT: no se duplica.
    assert not Task.objects.filter(asset_id=viejo["caja"].pk, status=Task.Status.PENDING).exists()

    assert RescheduleCause.objects.filter(name="SOLO 1 VISITA").exists()


def test_un_activo_en_dos_planes_detiene_la_migracion(base_antigua):
    viejo = datos_viejos(base_antigua)
    MaintenancePlan = base_antigua.get_model("maintenance", "MaintenancePlan")
    otro = MaintenancePlan.objects.create(name="Otro plan", frequency_value=3, frequency_unit="MONTHS")
    otro.assets.add(viejo["alarma"])

    with pytest.raises(RuntimeError, match="MIG-1"):
        _executor().migrate([("maintenance", "0003_move_to_tasks")])

    # Se deshace el conflicto para que el fixture pueda volver al final.
    otro.assets.clear()


def test_la_migracion_inversa_restaura_el_modelo_viejo(base_antigua):
    viejo = datos_viejos(base_antigua)
    ir_a([("maintenance", "0004_drop_legacy_fields"), ("work_orders", "0005_drop_legacy_fields"),
          ("checklists", "0006_drop_legacy_fields"), ("assets", "0005_drop_legacy_fields")])

    apps = ir_a(ANTES)

    WorkOrder = apps.get_model("work_orders", "WorkOrder")
    MaintenancePlan = apps.get_model("maintenance", "MaintenancePlan")
    ChecklistResponse = apps.get_model("checklists", "ChecklistResponse")
    cerrada = WorkOrder.objects.get(pk=viejo["cerrada"].pk)
    assert cerrada.asset_id == viejo["alarma"].pk
    assert cerrada.checklist_version_id == viejo["version"].pk
    assert cerrada.maintenance_plan_id == viejo["plan"].pk
    assert ChecklistResponse.objects.get(pk=viejo["respuesta"].pk).work_order_id == cerrada.pk
    plan = MaintenancePlan.objects.get(pk=viejo["plan"].pk)
    assert set(plan.assets.values_list("code", flat=True)) == {"MIG-1", "MIG-2"}
    assert hash_v1_original(apps, cerrada) == viejo["hash_v1"]


def test_ida_vuelta_e_ida_no_duplica_tareas(base_antigua):
    """
    Si se revierte en produccion y se vuelve a migrar, la segunda ida tiene que
    dar lo mismo que la primera. Antes la vuelta dejaba las tareas creadas y la
    segunda ida le ponia a cada OT otra tarea mas: la respuesta del checklist
    quedaba en la nueva y la OT mostraba la vieja, sin checklist.
    """
    viejo = datos_viejos(base_antigua)
    ir_al_final()
    ir_a(ANTES)

    ir_al_final()

    from apps.checklists.models import ChecklistResponse
    from apps.maintenance.models import MaintenancePlan, Task
    from apps.work_orders.integrity import compute_wo_content_hash
    from apps.work_orders.models import WorkOrder

    cerrada = WorkOrder.objects.get(pk=viejo["cerrada"].pk)
    assert cerrada.tasks.count() == 1
    assert WorkOrder.objects.get(pk=viejo["abierta"].pk).tasks.count() == 1
    assert MaintenancePlan.objects.get(pk=viejo["plan"].pk).tasks.count() == 1
    assert ChecklistResponse.objects.get(pk=viejo["respuesta"].pk).task == cerrada.primary_task
    assert Task.objects.filter(status=Task.Status.PENDING).count() == 1
    assert compute_wo_content_hash(cerrada, "1") == viejo["hash_v1"]
