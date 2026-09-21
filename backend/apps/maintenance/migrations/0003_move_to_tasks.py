"""Pasa los datos al modelo de tareas (diseno aprobado el 2026-09-21, fase 1).

Antes: el plan tenia la frecuencia, el checklist y la lista de activos; la OT
tenia un activo, su version de checklist y su plan; el checklist colgaba de la
OT.

Despues: cada plan tiene una tarea (PlanTask) con lo que antes tenia el plan;
cada activo apunta a su plan (Asset.plan); cada OT tiene una tarea (Task) con su
activo, su version y su origen; el checklist cuelga de la tarea; y cada activo
con plan y sin OT abierta tiene su tarea pendiente con la proxima fecha.

La migracion es estricta a proposito. Si un activo esta en mas de un plan, o un
mismo plan tiene dos OTs abiertas sobre el mismo activo, se detiene y los nombra
en vez de elegir por su cuenta: son datos que alguien tiene que decidir.

La inversa funciona mientras toda OT tenga exactamente una tarea. Con una OT
multiactivo ya creada se niega, porque el modelo anterior no puede expresarla.
"""

from datetime import date

from django.db import migrations

# Causas de reprogramacion que usa el cliente en su Fracttal (Configuracion ->
# Catalogos Auxiliares -> Causa de reprogramacion de la tarea).
CAUSAS_DEL_CLIENTE = [
    "3 VISITAS",
    "ADELANTADO",
    "ANUAL",
    "APLAZADO",
    "GARANTIA",
    "MANTENIMIENTO PUNTUAL",
    "NO DISPONIBLE",
    "PREVENTIVO",
    "PRIMERA VISITA",
    "SOLO 1 VISITA",
]

ESTADO_TAREA_SEGUN_OT = {
    "COMPLETED": "DONE",
    "CANCELLED": "CANCELLED",
    "PENDING": "SCHEDULED",
    "IN_PROGRESS": "SCHEDULED",
    "IN_REVIEW": "SCHEDULED",
}


def _sembrar_causas(apps):
    RescheduleCause = apps.get_model("maintenance", "RescheduleCause")
    for orden, nombre in enumerate(CAUSAS_DEL_CLIENTE):
        RescheduleCause.objects.get_or_create(
            name=nombre, defaults={"sort_order": orden}
        )


def _comprobar_conflictos(apps):
    MaintenancePlan = apps.get_model("maintenance", "MaintenancePlan")
    WorkOrder = apps.get_model("work_orders", "WorkOrder")

    planes_por_activo = {}
    for plan in MaintenancePlan.objects.prefetch_related("assets"):
        for asset in plan.assets.all():
            planes_por_activo.setdefault(asset.code, []).append(plan.name)
    en_varios = {c: p for c, p in planes_por_activo.items() if len(p) > 1}

    abiertas = {}
    for wo in WorkOrder.objects.filter(
        maintenance_plan__isnull=False,
        status__in=["PENDING", "IN_PROGRESS", "IN_REVIEW"],
    ).select_related("asset", "maintenance_plan"):
        clave = (wo.maintenance_plan.name, wo.asset.code)
        abiertas.setdefault(clave, []).append(wo.wo_number)
    duplicadas = {k: v for k, v in abiertas.items() if len(v) > 1}

    problemas = []
    for codigo, planes in sorted(en_varios.items()):
        problemas.append(
            f"- El activo {codigo} esta en varios planes ({', '.join(planes)}). "
            "Ahora cada activo tiene un solo plan: quitalo de los que sobran."
        )
    for (plan, codigo), numeros in sorted(duplicadas.items()):
        problemas.append(
            f"- El plan '{plan}' tiene varias OTs abiertas sobre {codigo} "
            f"({', '.join(map(str, numeros))}). Cierra o cancela las que sobran."
        )
    if problemas:
        raise RuntimeError(
            "No se puede pasar al modelo de tareas sin decidir esto a mano:\n"
            + "\n".join(problemas)
        )


def adelante(apps, schema_editor):
    MaintenancePlan = apps.get_model("maintenance", "MaintenancePlan")
    PlanTask = apps.get_model("maintenance", "PlanTask")
    Task = apps.get_model("maintenance", "Task")
    Asset = apps.get_model("assets", "Asset")
    WorkOrder = apps.get_model("work_orders", "WorkOrder")
    ChecklistResponse = apps.get_model("checklists", "ChecklistResponse")

    _sembrar_causas(apps)
    _comprobar_conflictos(apps)

    # 1. Una tarea por plan, con lo que hoy tiene el plan. Programacion no fija
    #    (decision D3): la siguiente fecha pasa a contarse desde la realizacion.
    tarea_del_plan = {}
    for plan in MaintenancePlan.objects.all():
        tarea_del_plan[plan.id] = PlanTask.objects.create(
            plan=plan,
            name=plan.name,
            description=plan.description,
            task_type=plan.task_type,
            priority=plan.priority,
            checklist_template_id=plan.checklist_template_id,
            trigger="DATE",
            frequency_value=plan.frequency_value,
            frequency_unit=plan.frequency_unit,
            fixed_schedule=False,
            estimated_duration=plan.estimated_duration,
            downtime_duration=plan.downtime_duration,
            is_active=plan.is_active,
            fracttal_task_id=plan.fracttal_task_id,
        )

    # 2. Cada activo apunta a su plan (decision D7).
    for plan in MaintenancePlan.objects.prefetch_related("assets"):
        ids = [a.id for a in plan.assets.all()]
        if ids:
            Asset.objects.filter(id__in=ids).update(plan=plan)

    # 3. Una tarea por OT, y el hospital directo en la OT.
    tarea_de_ot = {}
    for wo in WorkOrder.objects.select_related("asset").order_by("wo_number"):
        estado = ESTADO_TAREA_SEGUN_OT[wo.status]
        tarea_de_ot[wo.id] = Task.objects.create(
            asset_id=wo.asset_id,
            plan_task=tarea_del_plan.get(wo.maintenance_plan_id),
            work_order=wo,
            status=estado,
            title=wo.title,
            description=wo.description,
            task_type=wo.task_type,
            priority=wo.priority,
            checklist_version_id=wo.checklist_version_id,
            calculated_date=wo.scheduled_date,
            scheduled_date=wo.scheduled_date,
            estimated_duration=wo.estimated_duration,
            completed_at=wo.completed_at if estado == "DONE" else None,
            created_by_id=wo.created_by_id,
        )
        wo.hospital_id = wo.asset.hospital_id
        wo.save(update_fields=["hospital"])

    # 4. El checklist pasa a colgar de la tarea de su OT.
    for respuesta in ChecklistResponse.objects.all():
        respuesta.task = tarea_de_ot[respuesta.work_order_id]
        respuesta.save(update_fields=["task"])

    # 5. Cada activo con plan activo y sin tarea abierta recibe su pendiente con
    #    la proxima fecha del plan. Nadie pierde su proxima fecha.
    hoy = date.today()
    for plan in MaintenancePlan.objects.filter(is_active=True):
        tarea = tarea_del_plan[plan.id]
        fecha = plan.next_due_date or hoy
        activos = Asset.objects.filter(plan=plan, status="ACTIVE")
        for asset in activos:
            ya_abierta = Task.objects.filter(
                plan_task=tarea, asset=asset,
                status__in=["PENDING", "SCHEDULED"],
            ).exists()
            if ya_abierta:
                continue
            Task.objects.create(
                asset=asset,
                plan_task=tarea,
                status="PENDING",
                title=tarea.name,
                description=tarea.description,
                task_type=tarea.task_type,
                priority=tarea.priority,
                calculated_date=fecha,
                scheduled_date=fecha,
                estimated_duration=tarea.estimated_duration,
            )


def atras(apps, schema_editor):
    MaintenancePlan = apps.get_model("maintenance", "MaintenancePlan")
    Asset = apps.get_model("assets", "Asset")
    WorkOrder = apps.get_model("work_orders", "WorkOrder")
    ChecklistResponse = apps.get_model("checklists", "ChecklistResponse")
    Photo = apps.get_model("evidence", "Photo")
    Task = apps.get_model("maintenance", "Task")
    PlanTask = apps.get_model("maintenance", "PlanTask")
    TaskReschedule = apps.get_model("maintenance", "TaskReschedule")

    multiactivo = [
        wo.wo_number
        for wo in WorkOrder.objects.all()
        if Task.objects.filter(work_order=wo).count() != 1
    ]
    if multiactivo:
        raise RuntimeError(
            "No se puede volver al modelo anterior: estas OTs no tienen "
            "exactamente una tarea y el modelo anterior no puede expresarlas: "
            + ", ".join(map(str, sorted(multiactivo)))
        )

    for wo in WorkOrder.objects.all():
        tarea = Task.objects.select_related("plan_task").get(work_order=wo)
        wo.asset_id = tarea.asset_id
        wo.checklist_version_id = tarea.checklist_version_id
        wo.maintenance_plan_id = tarea.plan_task.plan_id if tarea.plan_task else None
        wo.save(update_fields=["asset", "checklist_version", "maintenance_plan"])

    for respuesta in ChecklistResponse.objects.select_related("task"):
        respuesta.work_order_id = respuesta.task.work_order_id
        respuesta.save(update_fields=["work_order"])

    for plan in MaintenancePlan.objects.all():
        primera = plan.tasks.order_by("sort_order", "name").first()
        if primera is not None:
            plan.task_type = primera.task_type
            plan.checklist_template_id = primera.checklist_template_id
            plan.frequency_value = primera.frequency_value or 6
            plan.frequency_unit = primera.frequency_unit or "MONTHS"
            plan.estimated_duration = primera.estimated_duration
            plan.downtime_duration = primera.downtime_duration
            plan.fracttal_task_id = primera.fracttal_task_id
            abierta = (
                Task.objects.filter(plan_task__plan=plan, status="PENDING")
                .order_by("scheduled_date")
                .first()
            )
            plan.next_due_date = abierta.scheduled_date if abierta else None
            plan.save()
        plan.assets.set(Asset.objects.filter(plan=plan))

    # Deja las tablas nuevas como estaban antes de la ida. Si quedaran llenas,
    # una segunda ida le pondria a cada OT otra tarea mas. Las causas de
    # reprogramacion se quedan: la ida las crea con get_or_create. El historial
    # de reprogramaciones se pierde; el modelo anterior no lo puede guardar.
    ChecklistResponse.objects.update(task=None)
    Photo.objects.update(task=None)
    TaskReschedule.objects.all().delete()
    Task.objects.all().delete()
    PlanTask.objects.all().delete()
    Asset.objects.update(plan=None)
    WorkOrder.objects.update(hospital=None, location=None)


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0002_plan_tasks_and_tasks"),
        ("assets", "0004_plan_tasks_and_tasks"),
        ("work_orders", "0004_plan_tasks_and_tasks"),
        ("checklists", "0005_plan_tasks_and_tasks"),
        ("evidence", "0004_photo_task"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
