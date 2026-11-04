"""Importacion del JSON del extractor de Fracttal. Todos los datos son inventados."""

import base64
import copy
import io
import json

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from apps.assets import importacion_fracttal_json as imp
from apps.assets.importacion_fracttal import ImportacionError
from apps.assets.models import Asset, AssetNode, Hospital
from apps.audit.models import AuditLog
from apps.checklists.models import ChecklistField, ChecklistFieldResponse
from apps.evidence.models import Photo, Signature
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.notifications.models import NotificationLog
from apps.reports.models import GeneratedReport
from apps.users.models import User
from apps.work_orders.models import WorkOrder

# PNG de 1x1 pixel.
PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6360f8ffff3f0005fe02fea7d6ca6f0000000049454e44ae426082"
    )
).decode()
FIRMA = "data:image/png;base64," + PNG


def sub(i, desc, tipo, grupo=None, requerida=False, unidad=None, opciones=None):
    return {"id": i, "descripcion": desc, "tipo": tipo, "grupo": grupo, "orden": i, "requerida": requerida,
            "unidad": unidad, "opciones": opciones or [], "iteraciones": {}, "adjuntos_requeridos": None}


def resp(i, desc, tipo, valor, grupo=None):
    return {"id_plan_subtarea": i, "descripcion": desc, "tipo": tipo, "grupo": grupo, "orden": i,
            "valor": valor, "unidad": None, "hecha": True}


def datos_base():
    """Una sede inventada: 1 piso, 1 sala, 2 equipos, 1 protocolo de 2 tareas, 2 OT."""
    return {
        "formato": "fracttal-json-v1",
        "extraido": "2026-11-04T00:00:00Z",
        "sede": "ZZ",
        "ubicaciones": [
            {"id": 100, "id_parent": None, "code": None, "nombre": "CLINICA ZETA", "descripcion": "x",
             "direccion": "Calle 1 # 2-3", "ciudad": "VILLA ZETA", "latitud": 6.25, "longitud": -75.5,
             "ruta": "// ", "path_node": "100", "habilitado": True, "reconstruida": True},
            {"id": 101, "id_parent": 100, "code": "/ZZ/P1/", "nombre": "PISO UNO", "descripcion": "x",
             "direccion": None, "ciudad": "VILLA ZETA", "latitud": None, "longitud": None,
             "ruta": "// CLINICA ZETA/ ", "path_node": "100.101", "habilitado": True},
            {"id": 102, "id_parent": 101, "code": None, "nombre": "SALA ALFA", "descripcion": "x",
             "direccion": None, "ciudad": None, "latitud": None, "longitud": None,
             "ruta": "// CLINICA ZETA/ PISO UNO/ ", "path_node": "100.101.102", "habilitado": True},
        ],
        "activos": [
            {"id": 200, "id_parent": 102, "code": "ZZ-001", "barcode": "B1", "descripcion": "d", "nombre": "BOMBA ALFA",
             "fabricante": "ACME", "modelo": "M-1", "serie": "S-1", "ubicacion_equipo": None, "otro": None,
             "path_node": "100.101.102.200", "habilitado": True, "disponible": True, "id_plan": 10,
             "plan": "PROTOCOLO ZETA", "prioridad": "HIGH", "centro_costo": "001", "clasificacion_1": "CONTRATO",
             "clasificacion_2": None, "notas": None},
            {"id": 201, "id_parent": 101, "code": None, "barcode": None, "descripcion": "d", "nombre": "VALVULA BETA",
             "fabricante": None, "modelo": None, "serie": None, "ubicacion_equipo": None, "otro": None,
             "path_node": "100.101.201", "habilitado": False, "disponible": True, "id_plan": None, "plan": None,
             "prioridad": None, "centro_costo": None, "clasificacion_1": None, "clasificacion_2": None,
             "notas": "vieja"},
        ],
        "planes": [
            {"id": 10, "nombre": "PROTOCOLO ZETA", "tareas": [
                {"id": 500, "descripcion": "REVISION  SEMESTRAL", "duracion_seg": 3600, "activa": True,
                 "tipo": None, "tipo_principal": "PREVENTIVO", "tipo_2": None, "prioridad": "HIGH",
                 "paro_activo": True, "paro_seg": 1800, "iteraciones": {"num": None, "nombre": {}, "ciclica": None},
                 "subtareas": [
                     sub(1, "UBICACION", "GEOREFERENCE"),
                     sub(2, "Observaciones", "TEXT", "GENERAL"),
                     sub(3, "Estado bomba", "BOOLEAN", "GENERAL", requerida=True),
                     sub(4, "Presion", "READING_METER", "LECTURAS", unidad="PSI"),
                     sub(5, "Cantidad", "NUMBER", "LECTURAS"),
                     sub(6, "Tipo de gas", "DROPDOWN", "LECTURAS", opciones=["Oxigeno", "Aire"]),
                     sub(7, "Fecha de cambio", "DATE_TIME"),
                     sub(8, "Valvula", "VERIFICATION", "VERIFICAR"),
                 ]},
                {"id": 501, "descripcion": "PRUEBA ESPECIAL", "duracion_seg": 600, "activa": True,
                 "tipo": "GARANTIA", "tipo_principal": "CORRECTIVO", "prioridad": None, "paro_activo": False,
                 "paro_seg": None, "iteraciones": {}, "subtareas": [sub(20, "Resultado", "TEXT")]},
            ]},
        ],
        "activadores": [
            {"id_activo": 200, "id_tarea": 500, "activador": "DATE$EVERY$6$MONTHS",
             "proxima": "2027-03-18T15:00:00+00:00", "ultima": "2026-09-18T15:00:00+00:00"},
            {"id_activo": 200, "id_tarea": 501, "activador": "METER$EVERY$100$HOURS", "proxima": None, "ultima": None},
        ],
        "ots": [
            {"id": 9001, "folio": "777", "estado": 3, "creada": "2026-10-01T10:00:00+00:00",
             "creada_por": "PERSONA UNO", "responsable": "TECNICO UNO", "nota": "nota de OT", "calificacion": 5,
             "clasificaciones": None, "tareas": [
                 {"id": 7001, "id_tarea": 500, "id_activo": 200, "descripcion": "REVISION  SEMESTRAL",
                  "activo": "BOMBA ALFA", "inicio": "2026-10-02T13:00:00+00:00", "fin": "2026-10-02T14:00:00+00:00",
                  "programada": "2026-10-01T10:00:00+00:00", "duracion_seg": 3600, "duracion_real_min": 60,
                  "paro_seg": 1200, "tecnico": "TECNICO UNO", "tipo": None, "tipo_principal": "PREVENTIVO",
                  "activador": "DATE$EVERY$6$MONTHS", "prioridad": "HIGH", "nota": None, "nota_tarea": "ok",
                  "calificacion": 5, "firma": FIRMA, "hecha": True,
                  "subtareas": [
                      resp(1, "UBICACION", "GEOREFERENCE",
                           json.dumps({"address": "Calle 9, Villa Zeta", "latitude": 6.1, "longitude": -75.2,
                                       "hour": "2/10/2026, 8:05:09"})),
                      resp(2, "Observaciones", "TEXT", "linea 1\nlinea 2", "GENERAL"),
                      resp(3, "Estado bomba", "BOOLEAN", "true", "GENERAL"),
                      resp(4, "Presion", "READING_METER", "58", "LECTURAS"),
                      resp(5, "Cantidad", "NUMBER", "3", "LECTURAS"),
                      resp(6, "Tipo de gas", "DROPDOWN", "Aire", "LECTURAS"),
                      resp(7, "Fecha de cambio", "DATE_TIME", None),
                      resp(8, "Valvula", "VERIFICATION", "2", "VERIFICAR"),
                  ],
                  "archivos": [{"ruta": ".ot/9001/a.jpeg", "nombre": "a.jpeg", "descripcion": None,
                                "fecha": "2026-10-02T13:10:00+00:00", "id_subtarea": None},
                               {"ruta": ".ot/9001/b.jpeg", "nombre": "b.jpeg", "descripcion": None,
                                "fecha": "2026-10-02T13:20:00+00:00", "id_subtarea": None}]},
             ]},
            {"id": 9002, "folio": "778", "estado": 4, "creada": "2026-10-05T10:00:00+00:00", "creada_por": None,
             "responsable": None, "nota": None, "calificacion": 0, "clasificaciones": None, "tareas": [
                 {"id": 7002, "id_tarea": 99999, "id_activo": 200, "descripcion": "TAREA SUELTA", "activo": "BOMBA ALFA",
                  "inicio": None, "fin": None, "programada": "2026-10-05T10:00:00+00:00", "duracion_seg": None,
                  "duracion_real_min": None, "paro_seg": None, "tecnico": None, "tipo": "ALGO RARO",
                  "tipo_principal": "CORRECTIVO", "activador": "NO_SCHEDULE_TASK", "prioridad": "LOW", "nota": None,
                  "nota_tarea": None, "calificacion": None, "firma": None, "hecha": False,
                  "subtareas": [resp(77, "Procedimiento", "TEXT", "algo")], "archivos": []},
             ]},
        ],
    }


def archivo(datos):
    return io.BytesIO(json.dumps(datos).encode("utf-8"))


def importar(datos, user):
    plan = imp.planificar(datos)
    assert plan.errores == 0, plan.errores_lista
    return plan, imp.aplicar(plan, user)


@pytest.fixture
def admin(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


# ---------------------------------------------------------------- lectura

def test_lee_solo_el_formato_del_extractor():
    assert imp.leer(archivo(datos_base()))["sede"] == "ZZ"
    with pytest.raises(ImportacionError, match="formato"):
        imp.leer(archivo({"formato": "otra-cosa"}))
    with pytest.raises(ImportacionError, match="JSON"):
        imp.leer(io.BytesIO(b"no es json"))
    d = datos_base()
    d["activos"] = "no es lista"
    with pytest.raises(ImportacionError, match="lista"):
        imp.leer(archivo(d))


# ------------------------------------------------------------ vista previa

@pytest.mark.django_db
def test_planificar_solo_lee_y_cuenta():
    plan = imp.planificar(datos_base())
    r = plan.resumen()
    assert r["hospitals"]["create"] == ["CLINICA ZETA"]
    assert r["locations"] == {"create": 2, "update": 0}
    assert r["assets"] == {"create": 2, "update": 0}
    assert r["plans"]["create"] == 1 and r["plan_tasks"]["create"] == 2
    assert r["checklist_fields"] == 9
    assert r["work_orders"] == {"create": 2, "existing": 0, "completed": 1, "cancelled": 1}
    assert r["photos_pending"] == 2
    assert r["signatures"] == 1
    assert r["errors_count"] == 0
    assert not Hospital.objects.exists() and not Asset.objects.exists() and not WorkOrder.objects.exists()
    assert not MaintenancePlan.objects.exists()


@pytest.mark.django_db
def test_avisos_de_activadores_no_reconocidos_y_otros():
    r = imp.planificar(datos_base()).resumen()
    textos = {w["mensaje"]: w for w in r["warnings"]}
    no_rec = [w for w in r["warnings"] if "no se reconocen" in w["mensaje"]]
    assert len(no_rec) == 1 and "METER$EVERY$100$HOURS" in no_rec[0]["ejemplos"][0]
    assert any("centro de costo" in m for m in textos)
    assert any("no están en ningún protocolo" in m for m in textos)
    assert r["triggers"] == {"DATE": 1, "no reconocido": 1}


# ------------------------------------------------------------------ aplicar

@pytest.mark.django_db
def test_crea_sede_ubicaciones_y_activos(admin):
    importar(datos_base(), admin)
    h = Hospital.objects.get()
    assert (h.name, h.fracttal_id, h.city, h.address) == ("CLINICA ZETA", "100", "VILLA ZETA", "Calle 1 # 2-3")
    assert str(h.latitude) == "6.2500000"
    piso = AssetNode.objects.get(fracttal_id="101")
    sala = AssetNode.objects.get(fracttal_id="102")
    assert piso.parent is None and sala.parent == piso
    assert piso.code == "/ZZ/P1/" and piso.address == "VILLA ZETA"
    bomba = Asset.objects.get(fracttal_id="200")
    assert (bomba.name, bomba.manufacturer, bomba.model, bomba.serial_number) == ("BOMBA ALFA", "ACME", "M-1", "S-1")
    assert (bomba.code, bomba.barcode, bomba.priority, bomba.classification_1) == ("ZZ-001", "B1", "HIGH", "CONTRATO")
    assert bomba.node == sala and bomba.hospital == h
    valvula = Asset.objects.get(fracttal_id="201")
    assert valvula.node == piso and valvula.status == Asset.Status.DECOMMISSIONED
    assert valvula.code == "FRC-201" and valvula.notes == "vieja"


@pytest.mark.django_db
def test_protocolo_tareas_y_campos_del_checklist(admin):
    importar(datos_base(), admin)
    plan = MaintenancePlan.objects.get(name="PROTOCOLO ZETA")
    assert plan.fracttal_plan_id == "10"
    t1 = PlanTask.objects.get(fracttal_task_id="500")
    assert t1.name == "REVISION SEMESTRAL"
    assert (t1.trigger, t1.frequency_value, t1.frequency_unit) == ("DATE", 6, "MONTHS")
    assert t1.task_type == "PREVENTIVE" and t1.priority == "HIGH"
    assert t1.estimated_duration.total_seconds() == 3600 and t1.downtime_duration.total_seconds() == 1800
    t2 = PlanTask.objects.get(fracttal_task_id="501")
    assert t2.trigger == "EVENT" and t2.task_type == "GARANTIA"
    campos = {f.label: f for f in t1.checklist_template.versions.get(is_current=True).fields.all()}
    tipos = {k: v.field_type for k, v in campos.items()}
    assert tipos == {
        "UBICACION": "GPS", "Observaciones": "TEXTAREA", "Estado bomba": "BOOLEAN", "Presion": "NUMBER",
        "Cantidad": "NUMBER", "Tipo de gas": "SELECT", "Fecha de cambio": "DATETIME", "Valvula": "PASS_ALERT_FAIL",
    }
    assert campos["Presion"].options_json == {"unit": "PSI"}
    assert campos["Tipo de gas"].options_json == ["Oxigeno", "Aire"]
    assert campos["Estado bomba"].is_required and campos["Estado bomba"].group == "GENERAL"
    assert campos["Estado bomba"].allows_na and campos["Valvula"].allows_na
    assert [f.sort_order for f in campos.values()] == list(range(1, 9))
    assert t2.checklist_template.versions.get().fields.get().field_type == "TEXT"


@pytest.mark.django_db
def test_conversion_de_valores_de_las_respuestas(admin):
    importar(datos_base(), admin)
    ot = WorkOrder.objects.get(fracttal_id="9001")
    valores = {r.field.label: r for r in ChecklistFieldResponse.objects.filter(response__task__work_order=ot)}
    assert valores["Valvula"].value == "ALERTA"
    assert valores["Estado bomba"].value == "true"
    assert valores["Presion"].value == "58" and valores["Cantidad"].value == "3"
    assert valores["Tipo de gas"].value == "Aire"
    assert valores["Observaciones"].value == "linea 1\nlinea 2"
    gps = valores["UBICACION"]
    assert gps.value == "6.1,-75.2" and gps.geo_address == "Calle 9, Villa Zeta"
    assert gps.answered_at.year == 2026 and gps.answered_at.month == 10
    assert "Fecha de cambio" not in valores  # sin valor, sin respuesta


def test_conversion_de_verificacion_y_booleanos():
    FT = ChecklistField.FieldType
    assert [imp._valor(FT.PASS_ALERT_FAIL, "VERIFICATION", v)[0] for v in ("1", "2", "3")] == [
        "APROBO", "ALERTA", "FALLO"]
    assert imp._valor(FT.PASS_ALERT_FAIL, "VERIFICATION", "N/A")[0] == "NA"
    assert imp._valor(FT.BOOLEAN, "BOOLEAN", "false")[0] == "false"
    assert imp._valor(FT.BOOLEAN, "BOOLEAN", "N/A")[0] == "na"
    assert imp._valor(FT.NUMBER, "NUMBER", "1,5")[0] == "1.5"
    assert imp._valor(FT.NUMBER, "NUMBER", "abc")[3] == "numero"
    assert imp._valor(FT.TEXT, "TEXT", None) is None


@pytest.mark.django_db
def test_ot_historica_sin_acta_correos_ni_notificaciones(admin):
    importar(datos_base(), admin)
    mail.outbox.clear()
    ot = WorkOrder.objects.get(fracttal_id="9001")
    assert ot.origin == "FRACTTAL" and ot.fracttal_folio == "777"
    assert ot.status == WorkOrder.Status.COMPLETED and ot.progress == 100
    assert ot.external_executor == "TECNICO UNO"
    assert ot.created_by == admin and ot.assigned_to is None
    assert ot.title == "[Fracttal 777] REVISION SEMESTRAL"
    assert ot.started_at.isoformat().startswith("2026-10-02T13:00") and ot.completed_at.hour == 14
    assert ot.actual_duration.total_seconds() == 3600 and ot.downtime.total_seconds() == 1200
    assert ot.rating == 5 and "nota de OT" in ot.notes and "ok" in ot.notes
    assert ot.created_at.date().isoformat() == "2026-10-01"
    assert ot.fracttal_data["creada_por"] == "PERSONA UNO"
    assert not GeneratedReport.objects.exists()
    assert not NotificationLog.objects.exists()
    assert len(mail.outbox) == 0
    hist = ot.status_history.get()
    assert (hist.from_status, hist.to_status) == ("", "COMPLETED")
    tarea = ot.tasks.get()
    assert tarea.status == Task.Status.DONE and tarea.plan_task.fracttal_task_id == "500"
    assert tarea.asset.fracttal_id == "200" and tarea.checklist_response.version is not None
    cancelada = WorkOrder.objects.get(fracttal_id="9002")
    assert cancelada.status == WorkOrder.Status.CANCELLED and cancelada.rating is None
    t = cancelada.tasks.get()
    assert t.status == Task.Status.CANCELLED and t.plan_task is None
    assert t.task_type == "CORRECTIVE"  # "ALGO RARO" no esta en el catalogo: manda el tipo principal
    assert t.checklist_response.field_responses.get().value == "algo"


@pytest.mark.django_db
def test_verificador_de_integridad_ignora_las_importadas(admin, capsys):
    importar(datos_base(), admin)
    call_command("verify_integrity")
    salida = capsys.readouterr().out
    assert "OT cerradas revisadas: 0" in salida
    assert "Sin acta generada: 0" in salida


@pytest.mark.django_db
def test_firma_del_tecnico_y_fotos_pendientes(admin):
    importar(datos_base(), admin)
    ot = WorkOrder.objects.get(fracttal_id="9001")
    firma = ot.signatures.get()
    assert firma.signature_type == Signature.SignatureType.TECHNICIAN
    assert firma.signer_name == "TECNICO UNO" and len(firma.file_hash) == 64
    assert firma.signed_at.hour == 14
    from django.core.files.storage import default_storage

    with default_storage.open(firma.file_url) as f:
        assert f.read(4) == b"\x89PNG"
    assert ot.fracttal_data["fotos_pendientes"] == 2
    rutas = [a["ruta"] for a in ot.fracttal_data["tareas"][0]["archivos"]]
    assert rutas == [".ot/9001/a.jpeg", ".ot/9001/b.jpeg"]
    assert not Photo.objects.exists()
    assert not WorkOrder.objects.get(fracttal_id="9002").signatures.exists()


@pytest.mark.django_db
def test_proxima_fecha_del_activo_sale_del_activador(admin):
    plan, conteos = importar(datos_base(), admin)
    pendiente = Task.objects.get(status=Task.Status.PENDING)
    assert pendiente.asset.fracttal_id == "200" and pendiente.plan_task.fracttal_task_id == "500"
    assert pendiente.scheduled_date.isoformat() == "2027-03-18"
    assert conteos["pending_tasks_created"] == 1
    # La tarea por evento no genera pendiente sola.
    assert not Task.objects.filter(plan_task__fracttal_task_id="501").exclude(status=Task.Status.DONE).exists()


@pytest.mark.django_db
def test_reimportar_no_duplica_y_actualiza(admin):
    importar(datos_base(), admin)
    antes = (Hospital.objects.count(), AssetNode.objects.count(), Asset.objects.count(),
             MaintenancePlan.objects.count(), PlanTask.objects.count(), WorkOrder.objects.count(),
             Task.objects.count(), ChecklistFieldResponse.objects.count(), Signature.objects.count())
    d2 = datos_base()
    d2["activos"][0]["nombre"] = "BOMBA ALFA RENOVADA"
    d2["activos"][0]["modelo"] = "M-2"
    plan = imp.planificar(d2)
    r = plan.resumen()
    assert r["assets"] == {"create": 0, "update": 2}
    assert r["work_orders"]["create"] == 0 and r["work_orders"]["existing"] == 2
    imp.aplicar(plan, admin)
    despues = (Hospital.objects.count(), AssetNode.objects.count(), Asset.objects.count(),
               MaintenancePlan.objects.count(), PlanTask.objects.count(), WorkOrder.objects.count(),
               Task.objects.count(), ChecklistFieldResponse.objects.count(), Signature.objects.count())
    assert antes == despues
    bomba = Asset.objects.get(fracttal_id="200")
    assert bomba.name == "BOMBA ALFA RENOVADA" and bomba.model == "M-2" and bomba.code == "ZZ-001"
    # Los checklists no cambiaron: no hay version nueva.
    assert PlanTask.objects.get(fracttal_task_id="500").checklist_template.versions.count() == 1


@pytest.mark.django_db
def test_reimportar_con_protocolo_cambiado_publica_version_nueva(admin):
    importar(datos_base(), admin)
    d2 = datos_base()
    d2["planes"][0]["tareas"][0]["subtareas"].append(sub(9, "Extra", "TEXT"))
    imp.aplicar(imp.planificar(d2), admin)
    tpl = PlanTask.objects.get(fracttal_task_id="500").checklist_template
    assert tpl.versions.count() == 2
    actual = tpl.versions.get(is_current=True)
    assert actual.version_number == 2 and actual.fields.count() == 9
    assert tpl.versions.get(version_number=1).fields.count() == 8  # la vieja queda intacta


@pytest.mark.django_db
def test_convive_con_lo_creado_por_el_excel(admin):
    h = baker.make(Hospital, name="Clinica  Zeta", code="CZ")
    nodo = baker.make(AssetNode, hospital=h, name="piso uno", parent=None, fracttal_id="")
    viejo = baker.make(Asset, hospital=h, node=nodo, name="otro", code="ZZ-001", fracttal_id="")
    por_id = baker.make(Asset, hospital=h, node=nodo, name="x", code="OTRO-9", fracttal_id="201")
    vacio = baker.make(MaintenancePlan, name="protocolo zeta")
    plan = imp.planificar(datos_base())
    r = plan.resumen()
    assert r["hospitals"] == {"create": [], "existing": ["Clinica  Zeta"]}
    assert r["locations"] == {"create": 1, "update": 1}
    assert r["assets"] == {"create": 0, "update": 2}
    assert r["plans"] == {"create": 0, "update": 1}
    imp.aplicar(plan, admin)
    viejo.refresh_from_db()
    por_id.refresh_from_db()
    nodo.refresh_from_db()
    h.refresh_from_db()
    assert viejo.fracttal_id == "200" and viejo.name == "BOMBA ALFA" and viejo.plan == vacio
    assert por_id.fracttal_id == "201" and por_id.code == "OTRO-9"
    assert nodo.fracttal_id == "101" and h.fracttal_id == "100"
    assert Hospital.objects.count() == 1 and Asset.objects.count() == 2
    vacio.refresh_from_db()
    assert vacio.fracttal_plan_id == "10" and vacio.tasks.count() == 2


@pytest.mark.django_db
def test_codigo_repetido_genera_otro(admin):
    baker.make(Asset, code="ZZ-001", fracttal_id="")  # de otro hospital: no se empareja
    plan = imp.planificar(datos_base())
    assert any("sin código usable" in w["mensaje"] for w in plan.resumen()["warnings"])
    imp.aplicar(plan, admin)
    assert Asset.objects.get(fracttal_id="200").code == "FRC-200"


@pytest.mark.django_db
def test_respuesta_de_tipo_distinto_al_protocolo_se_descarta(admin):
    d = datos_base()
    d["ots"][0]["tareas"][0]["subtareas"][4] = resp(5, "Cantidad", "BOOLEAN", "0", "LECTURAS")
    plan = imp.planificar(d)
    assert any("no coincide" in w["mensaje"] for w in plan.resumen()["warnings"])
    imp.aplicar(plan, admin)
    labels = set(ChecklistFieldResponse.objects.values_list("field__label", flat=True))
    assert "Cantidad" not in labels


@pytest.mark.django_db
def test_errores_de_estructura_no_se_aplican(admin):
    d = datos_base()
    d["ubicaciones"].append(dict(d["ubicaciones"][1]))
    plan = imp.planificar(d)
    assert plan.errores == 1 and "repetido" in plan.errores_lista[0]
    with pytest.raises(ImportacionError):
        imp.aplicar(plan, admin)
    d = datos_base()
    d["ubicaciones"] = []
    assert imp.planificar(d).errores == 1


@pytest.mark.django_db
def test_tipo_de_tarea_del_catalogo_por_nombre(admin):
    d = datos_base()
    d["planes"][0]["tareas"][0]["tipo"] = "Garantía"
    importar(d, admin)
    assert PlanTask.objects.get(fracttal_task_id="500").task_type == "GARANTIA"


@pytest.mark.django_db
def test_rendimiento_con_muchas_ot(admin, django_assert_max_num_queries):
    d = datos_base()
    base = d["ots"][0]
    d["ots"] = []
    for i in range(60):
        o = copy.deepcopy(base)
        o["id"], o["folio"] = 10000 + i, str(1000 + i)
        o["tareas"][0]["id"] = 20000 + i
        d["ots"].append(o)
    plan = imp.planificar(d)
    with django_assert_max_num_queries(400):
        imp.aplicar(plan, admin)
    assert WorkOrder.objects.filter(origin="FRACTTAL").count() == 60
    assert len(set(WorkOrder.objects.values_list("wo_number", flat=True))) == 60


# ------------------------------------------------------------------- comando

@pytest.mark.django_db
def test_comando_vista_previa_y_aplicar(admin, tmp_path, capsys):
    ruta = tmp_path / "x.json"
    ruta.write_text(json.dumps(datos_base()), encoding="utf-8")
    call_command("importar_fracttal_json", str(ruta))
    salida = capsys.readouterr().out
    assert "VISTA PREVIA" in salida and "OT históricas: 2 a crear" in salida
    assert not Hospital.objects.exists()
    call_command("importar_fracttal_json", str(ruta), "--aplicar", "--usuario", admin.email)
    assert "APLICADO" in capsys.readouterr().out
    assert WorkOrder.objects.filter(origin="FRACTTAL").count() == 2
    log = AuditLog.objects.get(entity_type="FracttalJsonImport")
    assert log.user == admin and log.changes["aplicado"]["work_orders_created"] == 2
    with pytest.raises(CommandError, match="formato"):
        ruta.write_text('{"formato": "x"}', encoding="utf-8")
        call_command("importar_fracttal_json", str(ruta))


# ------------------------------------------------------------------ endpoints

def _subir(client, nombre, contenido, url):
    return client.post(
        reverse(url), {"archivo": SimpleUploadedFile(nombre, contenido, content_type="application/json")},
        format="multipart",
    )


@pytest.mark.django_db
def test_endpoint_vista_previa_y_aplicar_solo_admin(admin):
    c = APIClient()
    c.force_authenticate(admin)
    contenido = json.dumps(datos_base()).encode()
    r = _subir(c, "x.json", contenido, "import-fracttal-json-preview")
    assert r.status_code == 200 and r.data["work_orders"]["create"] == 2 and r.data["applied"] is False
    assert not Hospital.objects.exists()
    r = _subir(c, "x.json", contenido, "import-fracttal-json-apply")
    assert r.status_code == 201 and r.data["applied"] is True
    assert r.data["applied_counts"]["work_orders_created"] == 2
    assert AuditLog.objects.filter(entity_type="FracttalJsonImport").count() == 1
    assert WorkOrder.objects.filter(origin="FRACTTAL").count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [User.Role.SUP, User.Role.TEC, User.Role.CLI])
def test_endpoint_prohibido_para_no_admin(rol):
    user = baker.make(User, role=rol, is_active=True)
    c = APIClient()
    c.force_authenticate(user)
    for url in ("import-fracttal-json-preview", "import-fracttal-json-apply"):
        assert _subir(c, "x.json", json.dumps(datos_base()).encode(), url).status_code == 403
    assert not Hospital.objects.exists()
    assert APIClient().post(reverse("import-fracttal-json-preview")).status_code in (401, 403)


@pytest.mark.django_db
def test_endpoint_valida_el_archivo(admin):
    c = APIClient()
    c.force_authenticate(admin)
    r = _subir(c, "x.txt", b"{}", "import-fracttal-json-preview")
    assert r.status_code == 400 and ".json" in r.data["detail"]
    r = _subir(c, "x.json", b'{"formato": "otro"}', "import-fracttal-json-preview")
    assert r.status_code == 400 and "formato" in r.data["detail"]
    r = _subir(c, "x.json", b"no es json", "import-fracttal-json-apply")
    assert r.status_code == 400
    r = c.post(reverse("import-fracttal-json-preview"), {}, format="multipart")
    assert r.status_code == 400
    d = datos_base()
    d["ubicaciones"] = []
    r = _subir(c, "x.json", json.dumps(d).encode(), "import-fracttal-json-apply")
    assert r.status_code == 400 and r.data["errors_count"] == 1
    assert not Hospital.objects.exists()


def test_el_limite_de_tamano_es_de_100_mb():
    from apps.assets.views_importacion import MAX_BYTES_JSON

    assert MAX_BYTES_JSON == 100 * 1024 * 1024
