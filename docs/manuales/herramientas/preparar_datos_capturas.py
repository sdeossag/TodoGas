# Prepara los estados que la demo (seed_demo) no genera y que piden las capturas
# de los manuales. Solo corre sobre la base aislada `todogas_manual_demo`.
#
#   cd backend
#   DB_NAME=todogas_manual_demo PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe manage.py shell -c "exec(open('../docs/manuales/herramientas/preparar_datos_capturas.py', encoding='utf-8').read(), globals())"
#
# (No usar `shell < archivo`: Django abre una consola interactiva, rompe las sangrias y
# lee la entrada con la pagina de codigos de Windows, que daña los acentos.)
#
# Idempotente: cada bloque comprueba si ya existe y no duplica. Usa el ORM y los
# servicios del backend (apps.maintenance.services, apps.work_orders.transitions)
# para llegar a estados validos. Toda imagen o PDF es sintetico; ningun dato real.
import hashlib
import io
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

if settings.DATABASES["default"]["NAME"] != "todogas_manual_demo":
    raise SystemExit(
        "ABORTADO: este script solo corre sobre la base «todogas_manual_demo» "
        f"(hoy: {settings.DATABASES['default']['NAME']!r})."
    )

from PIL import Image, ImageDraw

from apps.assets.models import Asset, AssetNode, Hospital
from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Photo, Signature, UserSignature
from apps.inventory.models import InventoryItem, StockMovement
from apps.maintenance import services
from apps.maintenance.models import MaintenancePlan, Task
from apps.reports.models import ReportSettings
from apps.users.models import PrivacyConsent, User
from apps.work_orders.models import WorkOrder, WorkOrderStatusHistory
from apps.work_orders.transitions import apply_transition

DOMINIO = "demo.todogas.local"
rnd = random.Random(2026)
ahora = timezone.now()
hoy = timezone.localdate()
log = lambda m: print(f"[preparar] {m}")  # noqa: E731

admin = User.objects.get(email=f"admin@{DOMINIO}")
sup = User.objects.get(email=f"supervisor@{DOMINIO}")
tec = User.objects.get(email=f"tecnico@{DOMINIO}")
cli = User.objects.get(email=f"biomedica@{DOMINIO}")
norte = Hospital.objects.get(code="DEMO-NORTE")
activo = lambda codigo: Asset.objects.get(code=codigo)  # noqa: E731


def guardar(nombre, contenido):
    return default_storage.save(f"demo/{nombre}", ContentFile(contenido))


def png_firma(semilla):
    r = random.Random(semilla)
    img = Image.new("RGB", (500, 200), (255, 255, 255))
    ImageDraw.Draw(img).line([(20 + i * 22, 100 + r.randint(-60, 60)) for i in range(21)], fill=(20, 30, 90), width=3)
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def jpg_foto(texto, color):
    img = Image.new("RGB", (800, 600), color)
    d = ImageDraw.Draw(img)
    for y in range(0, 600, 40):
        d.line([(0, y), (800, y + 80)], fill=tuple(min(255, c + 25) for c in color), width=6)
    d.rectangle([40, 230, 760, 370], fill=(255, 255, 255))
    d.text((60, 285), texto, fill=(20, 40, 70))
    b = io.BytesIO()
    img.save(b, "JPEG", quality=80)
    return b.getvalue()


def foto(ot, tarea, etapa, texto, minutos, hidden=False, leyenda=""):
    contenido = jpg_foto(texto, {"BEFORE": (60, 110, 160), "AFTER": (60, 140, 100)}.get(etapa, (150, 120, 60)))
    clave = guardar(f"{ot.wo_code}/{etapa.lower() or 'extra'}-{tarea.asset.code}-{minutos}.jpg", contenido)
    return Photo.objects.create(
        work_order=ot, task=tarea, file_url=clave, taken_at=ahora - timedelta(minutes=minutos),
        latitude=norte.latitude, longitude=norte.longitude, caption=leyenda or texto,
        stage=etapa, file_hash=hashlib.sha256(contenido).hexdigest(), uploaded_by=tec,
        hidden=hidden, hidden_by=sup if hidden else None, hidden_at=ahora if hidden else None,
    )


def firmas(ot, minutos=20):
    for tipo, nombre, rol in (("TECHNICIAN", "Técnico Demo", "Técnico de mantenimiento"),
                              ("CLIENT", "Laura Ríos", "Ingeniera biomédica")):
        c = png_firma(f"{ot.wo_number}{tipo}")
        Signature.objects.create(
            work_order=ot, signature_type=tipo, file_url=guardar(f"{ot.wo_code}/firma-{tipo.lower()}.png", c),
            signer_name=nombre, signer_role=rol, file_hash=hashlib.sha256(c).hexdigest(),
            signed_at=ahora - timedelta(minutes=minutos), latitude=ot.hospital.latitude, longitude=ot.hospital.longitude,
        )


def responder(ot, valor_de, completar=True, usuario=tec):
    """Responde el checklist de cada tarea de la OT. valor_de(campo, rep, tarea) -> (valor, nota)."""
    from apps.assets.meters import record_from_checklist

    n = 0
    for tarea in ot.tasks.order_by("sort_order"):
        resp = tarea.checklist_response
        if resp.started_at is None:
            resp.started_at = ahora - timedelta(minutes=90)
            resp.save(update_fields=["started_at"])
        for campo, rep in resp.slots():
            valor, nota = valor_de(campo, rep, tarea)
            if valor == "" and not nota:
                continue
            n += 1
            fr = ChecklistFieldResponse.objects.create(
                response=resp, field=campo, repetition=rep, value=valor, notes=nota,
                answered_at=ahora - timedelta(minutes=80 - n),
            )
            if campo.field_type == "METER":
                record_from_checklist(fr, usuario)
        if completar:
            resp.completed_at = ahora - timedelta(minutes=30)
            resp.completed_by = usuario
            resp.save()


def hecho(titulo):
    return WorkOrder.objects.filter(title=titulo).first()


# ── 1. Usuarios extra para estados que los cuatro de la demo no pueden mostrar ──
def usuario(correo_local, nombre, apellido, rol, clave, **extra):
    u = User.objects.filter(email=f"{correo_local}@{DOMINIO}").first()
    if u is None:
        u = User.objects.create_user(
            email=f"{correo_local}@{DOMINIO}", password=clave, first_name=nombre, last_name=apellido,
            role=rol, employee_code=f"DEMO-{correo_local.upper()}", phone="3000000000", **extra,
        )
        log(f"usuario {u.email}")
    return u


revisor = usuario("revisor", "Revisor", "Demo", "SUP", "TgDemo-Revisor-2026")            # supervisor SIN firma (capturas 35, 71)
nuevo = usuario("nuevo", "Nuevo", "Demo", "TEC", "TgDemo-Nuevo-2026", must_change_password=True)  # captura 3
aviso = usuario("aviso", "Aviso", "Demo", "TEC", "TgDemo-Aviso-2026")                    # captura 4: nunca acepta el aviso
restablecer = usuario("restablecer", "Restablecer", "Demo", "TEC", "TgDemo-Restablecer-2026")  # captura 98 (enlace)
inactivo = usuario("inactivo", "Inactivo", "Demo", "TEC", "TgDemo-Inactivo-2026")        # captura 51
if inactivo.is_active:
    inactivo.is_active = False
    inactivo.deactivated_at = ahora - timedelta(days=800)
    inactivo.save(update_fields=["is_active", "deactivated_at", "updated_at"])
for u in (nuevo, restablecer):
    PrivacyConsent.objects.get_or_create(user=u, version=settings.PRIVACY_NOTICE_VERSION)
# El supervisor de la demo ya tiene firma; el revisor, no. Para los demas, se acepta el aviso al entrar.

# ── 2. Firmas guardadas (imagen sintetica) del administrador y del tecnico ──
for u in (admin, tec):
    if not UserSignature.objects.filter(user=u).exists():
        c = png_firma(f"guardada-{u.email}")
        UserSignature.objects.create(
            user=u, file_url=guardar(f"firmas-guardadas/{u.id}.png", c), file_hash=hashlib.sha256(c).hexdigest(),
        )
        log(f"firma guardada de {u.email}")

# ── 3. Razon social y NIT del acta ──
rs = ReportSettings.current()
if rs.company_name != "Gases Demo S.A." or rs.company_tax_id != "900.000.000-0":
    rs.company_name, rs.company_tax_id, rs.updated_by = "Gases Demo S.A.", "900.000.000-0", admin
    rs.save()
    log("razón social y NIT del acta")

# ── 4. Checklists: uno con «Aprobó / Alerta / Falló» y una segunda version ──
def publicar(nombre, descripcion, campos, grupos=()):
    plantilla = ChecklistTemplate.objects.filter(name=nombre).first()
    if plantilla:
        return plantilla, plantilla.versions.get(is_current=True)
    plantilla = ChecklistTemplate.objects.create(name=nombre, description=descripcion, is_active=True)
    version = ChecklistTemplateVersion.objects.create(
        template=plantilla, version_number=1, published_by=admin, is_current=True, repeatable_groups=list(grupos),
    )
    for orden, (et, tipo, grupo, oblig, ops, ayuda) in enumerate(campos):
        ChecklistField.objects.create(version=version, label=et, field_type=tipo, group=grupo,
                                      is_required=oblig, sort_order=orden, options_json=ops, help_text=ayuda)
    log(f"checklist «{nombre}»")
    return plantilla, version


tpl_paf, ver_paf = publicar(
    "Verificación del manifold de oxígeno", "Verificación con tres resultados: aprobó, alerta o falló.",
    [
        ("Estado del regulador", "PASS_ALERT_FAIL", "", True, {"allow_na": True}, "Aprobó, Alerta o Falló."),
        ("Estado de las mangueras de conexión", "PASS_ALERT_FAIL", "", True, {"allow_na": True}, ""),
        ("Válvulas de corte sin fuga", "PASS_ALERT_FAIL", "", True, {"allow_na": True}, ""),
        ("Observaciones", "TEXTAREA", "", False, [], ""),
    ],
)

tpl_corr = ChecklistTemplate.objects.get(name="Reporte de intervención correctiva")
if tpl_corr.versions.count() < 2:
    v1 = tpl_corr.versions.get(is_current=True)
    tpl_corr.versions.filter(is_current=True).update(is_current=False)
    v2 = ChecklistTemplateVersion.objects.create(
        template=tpl_corr, version_number=2, published_by=admin, is_current=True,
        repeatable_groups=list(v1.repeatable_groups),
    )
    n = 0
    for f in v1.fields.order_by("sort_order"):
        ChecklistField.objects.create(version=v2, label=f.label, field_type=f.field_type, group=f.group,
                                      is_required=f.is_required, sort_order=f.sort_order,
                                      options_json=f.options_json, help_text=f.help_text)
        n = f.sort_order + 1
    ChecklistField.objects.create(version=v2, label="Se probó la presión después de la intervención",
                                  field_type="BOOLEAN", is_required=False, sort_order=n,
                                  options_json={"allow_na": True}, help_text="Segunda versión de la plantilla.")
    log("segunda versión del checklist correctivo")
ver_corr_v1 = tpl_corr.versions.get(version_number=1)

# ── 5. OT «En revisión» (checklist completo, fotos, firmas; una foto oculta) ──
T_REV = "Revisión de alarma de presión - Hospitalización (Piso 3)"
if hecho(T_REV) is None:
    tareas = list(Task.objects.filter(asset__code="N-HOS-ALM-01", status=Task.Status.PENDING).select_related("asset"))
    ot, _ = services.create_work_order_for_tasks(
        tareas, sup, assigned_to=tec, scheduled_date=hoy, location=AssetNode.objects.get(hospital=norte, code="N-P3"),
        title=T_REV, description="Revisión semestral de la alarma de presión de Hospitalización.",
    )
    apply_transition(ot, WorkOrder.Status.IN_PROGRESS, tec)

    def vals_alarma(c, rep, t):
        return {"Alarma sonora funciona": ("true", ""), "Indicador luminoso funciona": ("true", ""),
                "Presión de la red": ("57.5", ""), "Umbral de alarma baja verificado (PSI)": ("50", ""),
                "Observaciones": ("Alarma probada con la válvula de prueba; sin novedades.", "")}.get(c.label, ("", ""))

    responder(ot, vals_alarma)
    t0 = ot.tasks.first()
    foto(ot, t0, "BEFORE", "ANTES - N-HOS-ALM-01", 70, leyenda="Antes del trabajo")
    foto(ot, t0, "AFTER", "DESPUÉS - N-HOS-ALM-01", 25, leyenda="Después del trabajo")
    foto(ot, t0, "AFTER", "FOTO BORROSA - N-HOS-ALM-01", 22, hidden=True, leyenda="Foto borrosa del manómetro")
    firmas(ot)
    apply_transition(ot, WorkOrder.Status.IN_REVIEW, tec)
    log(f"{ot.wo_code} en revisión")

# ── 6. OT devuelta con motivo (vuelve a «En proceso») + salida de inventario ──
T_DEV = "Caja de válvulas Urgencias: fuga en la válvula de corte"
if hecho(T_DEV) is None:
    ot = services.create_manual_work_order(
        [(activo("N-URG-CV-01"), ver_corr_v1)], sup, location=AssetNode.objects.get(hospital=norte, code="N-P1"),
        task_type="CORRECTIVE", title=T_DEV, description="Fuga leve en la válvula de corte de la línea de oxígeno.",
        status=WorkOrder.Status.PENDING, priority=WorkOrder.Priority.HIGH, scheduled_date=hoy, assigned_to=tec,
    )
    apply_transition(ot, WorkOrder.Status.IN_PROGRESS, tec)
    responder(ot, lambda c, r, t: {
        "Diagnóstico": ("Fuga en el sello de la válvula de corte.", ""),
        "Acción realizada": ("Se cambió el sello y se verificó con solución jabonosa.", ""),
        "Repuestos usados": ("Manómetro 0-100 PSI", ""), "Equipo quedó operativo": ("true", ""),
    }.get(c.label, ("", "")))
    t0 = ot.tasks.first()
    foto(ot, t0, "BEFORE", "ANTES - N-URG-CV-01", 60, leyenda="Antes del trabajo")
    firmas(ot)
    apply_transition(ot, WorkOrder.Status.IN_REVIEW, tec)
    apply_transition(ot, WorkOrder.Status.IN_PROGRESS, sup,
                     comment="Falta la foto del manómetro después del cambio. Súbela y vuelve a enviar.")
    log(f"{ot.wo_code} devuelta con motivo")

# ── 7. OT con un campo «Aprobó / Alerta / Falló» respondido (en proceso, del técnico) ──
T_PAF = "Verificación del manifold de oxígeno - Sótano"
if hecho(T_PAF) is None:
    ot = services.create_manual_work_order(
        [(activo("N-SOT-MAN-01"), ver_paf)], sup, location=AssetNode.objects.get(hospital=norte, code="N-SOT"),
        task_type="PREVENTIVE", title=T_PAF, description="Verificación trimestral del manifold.",
        status=WorkOrder.Status.PENDING, priority=WorkOrder.Priority.MEDIUM, scheduled_date=hoy, assigned_to=tec,
    )
    apply_transition(ot, WorkOrder.Status.IN_PROGRESS, tec)
    responder(ot, lambda c, r, t: {
        "Estado del regulador": ("APROBO", ""),
        "Estado de las mangueras de conexión": ("ALERTA", "Manguera con desgaste visible; cambiar en la próxima visita."),
    }.get(c.label, ("", "")), completar=False)
    log(f"{ot.wo_code} con Aprobó/Alerta/Falló")

# ── 8. OT historica de Fracttal (solo consulta), como la deja el importador ──
T_FRA = "[Fracttal 4521] Revisión de alarma de presión"
if hecho(T_FRA) is None:
    ot = services.create_manual_work_order(
        [(activo("N-URG-ALM-01"), ChecklistTemplate.objects.get(name="Revisión de alarma de presión").versions.get(is_current=True))],
        sup, location=AssetNode.objects.get(hospital=norte, code="N-P1"), task_type="PREVENTIVE",
        title=T_FRA, description="", status=WorkOrder.Status.PENDING, scheduled_date=hoy - timedelta(days=95),
    )
    hace = ahora - timedelta(days=95)
    responder(ot, lambda c, r, t: {
        "Alarma sonora funciona": ("true", ""), "Indicador luminoso funciona": ("true", ""),
        "Presión de la red": ("56.0", ""), "Observaciones": ("Sin novedades (histórico de Fracttal).", ""),
    }.get(c.label, ("", "")), usuario=admin)
    c = png_firma("fracttal-demo")
    Signature.objects.create(
        work_order=ot, signature_type="TECHNICIAN", file_url=guardar(f"{ot.wo_code}/firma-fracttal.png", c),
        signer_name="Técnico Ejemplo", signer_role="Técnico (Fracttal)", file_hash=hashlib.sha256(c).hexdigest(),
        signed_at=hace,
    )
    WorkOrder.objects.filter(pk=ot.pk).update(
        status=WorkOrder.Status.COMPLETED, progress=100, started_at=hace, completed_at=hace + timedelta(hours=1),
        actual_duration=timedelta(hours=1), origin="FRACTTAL", fracttal_id="DEMO-9001", fracttal_folio="4521",
        external_executor="Técnico Ejemplo", created_at=hace - timedelta(days=2),
        assigned_to=None,
        fracttal_data={"creada_por": "Planificador Ejemplo", "fotos_pendientes": 2, "tareas": []},
    )
    Task.objects.filter(work_order=ot).update(status=Task.Status.DONE, completed_at=hace + timedelta(hours=1))
    WorkOrderStatusHistory.objects.create(
        work_order=ot, from_status="", to_status="COMPLETED", changed_by=admin,
        comment="OT histórica importada de Fracttal.", changed_at=hace + timedelta(hours=1),
    )
    log(f"{ot.wo_code} histórica de Fracttal")

# ── 9. Inventario: articulos, uno con stock bajo, y una salida ligada a una OT ──
articulos = [
    ("DEMO-REP-001", "Manómetro 0-100 PSI", "und", 3, 4, 85000),
    ("DEMO-REP-002", "Acople DISS oxígeno", "und", 40, 10, 22000),
    ("DEMO-REP-003", "Cinta de teflón", "rollo", 25, 5, 3500),
    ("DEMO-REP-004", "Sello de válvula de corte", "und", 8, 4, 15000),
]
if not InventoryItem.objects.filter(code="DEMO-REP-001").exists():
    ot_dev = WorkOrder.objects.get(title=T_DEV)
    for codigo, nombre, unidad, stock, minimo, costo in articulos:
        item = InventoryItem.objects.create(code=codigo, name=nombre, unit_of_measure=unidad,
                                            current_stock=Decimal(0), min_stock=Decimal(minimo), unit_cost=Decimal(costo))
        entrada = stock + (3 if codigo == "DEMO-REP-001" else (1 if codigo == "DEMO-REP-004" else 0))
        StockMovement.objects.create(item=item, movement_type="IN", quantity=Decimal(entrada),
                                     reference="Compra inicial", performed_by=admin,
                                     performed_at=ahora - timedelta(days=20))
        item.current_stock = Decimal(entrada)
        item.save(update_fields=["current_stock", "updated_at"])
        if codigo in ("DEMO-REP-001", "DEMO-REP-004"):
            salida = 3 if codigo == "DEMO-REP-001" else 1
            StockMovement.objects.create(item=item, movement_type="OUT", quantity=Decimal(salida),
                                         work_order=ot_dev, notes="Usado en la intervención correctiva",
                                         performed_by=tec, performed_at=ahora - timedelta(hours=1))
            item.current_stock = Decimal(entrada - salida)
            item.save(update_fields=["current_stock", "updated_at"])
    log("inventario: 4 artículos, 1 con stock bajo, 2 salidas ligadas a una OT")

# ── 10. Protocolo asignado a una ubicacion (captura 22) ──
from apps.assets.activo_ubicacion import activo_de_ubicacion

plan_tomas = MaintenancePlan.objects.get(name="Mant. salidas de gases")
nodo_p1 = AssetNode.objects.get(hospital=norte, code="N-P1")
act_ub = activo_de_ubicacion(nodo_p1)
if act_ub.plan_id != plan_tomas.id:
    services.set_asset_plan(act_ub, plan_tomas, created_by=admin, start_date=hoy + timedelta(days=40))
    log("protocolo «Mant. salidas de gases» asignado a la ubicación Piso 1 - Urgencias")

log("listo")
