"""Importacion de activos desde Excel de Fracttal. Los Excel son sinteticos."""

import datetime
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from model_bakery import baker
from openpyxl import Workbook
from rest_framework.test import APIClient

from apps.assets import importacion_fracttal as imp
from apps.assets.models import Asset, AssetNode, Hospital
from apps.audit.models import AuditLog
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.users.models import User

URL_UBIC = "https://app.fracttal.com/#inventories.facilities/"
URL_EQ = "https://app.fracttal.com/#inventories.equipments/"

COLS_UBIC = ["Habilitado", "Fuera de servicio", "Descripción", "Nombre (C)", "Dirección (C)",
             "Ciudad (C)", "Código", "Notas", "Ubicado en ó es Parte de", "Url Código QR"]
COLS_EQ = ["Habilitado", "Fuera de servicio", "Código", "Nombre (C)", "Fabricante (C)",
           "Modelo (C)", "Número de Serial (C)", "Prioridad", "Clasificación 1",
           "Fecha de Compra", "Ubicado en ó es Parte de", "Plan de Tareas", "Notas",
           "Url Código QR"]


def excel(encabezados, filas):
    wb = Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(encabezados)
    for f in filas:
        ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def ubic(nombre, ruta, fid=None, habilitado="Si", fuera="No", direccion=None, ciudad=None, codigo=None):
    return [habilitado, fuera, nombre, nombre, direccion, ciudad, codigo, None, ruta,
            f"{URL_UBIC}{fid}" if fid else None]


def equipo(nombre, ruta, fid=None, codigo=None, prioridad="Media", habilitado="Si", fuera="No",
           plan=None, fecha="---", notas=None, fabricante=None):
    return [habilitado, fuera, codigo, nombre, fabricante, None, None, prioridad, None, fecha,
            ruta, plan, notas, f"{URL_EQ}{fid}" if fid else None]


def planificar_con(ub=None, eq=None):
    u = imp.leer_ubicaciones(excel(COLS_UBIC, ub)) if ub is not None else []
    e = imp.leer_equipos(excel(COLS_EQ, eq)) if eq is not None else []
    return imp.planificar(u, e)


@pytest.fixture
def admin(db):
    return baker.make(User, role=User.Role.ADMIN, is_active=True)


# ---------------------------------------------------------------- lectura

def test_normaliza_textos_de_fracttal():
    assert imp.limpiar("/AMICO/") == "AMICO"
    assert imp.limpiar("/ 3 GASES /") == "3 GASES"
    assert imp.limpiar("  ALARMA   DE   AREA ") == "ALARMA DE AREA"
    assert imp.limpiar("---") == ""
    assert imp.limpiar(None) == ""
    assert imp.normalizar("  Imágenes   DIAGNOSTICAS ") == "imagenes diagnosticas"
    assert imp.partir_ruta("// CLINICA EJEMPLO NORTE/ IMÁGENES DIAGNOSTICAS/") == [
        "CLINICA EJEMPLO NORTE", "IMÁGENES DIAGNOSTICAS"]


def test_lee_columnas_por_nombre_aunque_cambie_el_orden():
    cols = ["Ubicado en ó es Parte de", "Url Código QR", "Nombre (C)", "Columna Rara", "Modelo (C)"]
    filas = imp.leer_equipos(excel(cols, [["// H1/", URL_EQ + "274", "/ALARMA/", "x", " /M-1/ "]]))
    assert len(filas) == 1
    assert filas[0].fila == 2
    assert filas[0].nombre == "ALARMA"
    assert filas[0].datos["modelo"] == "M-1"
    assert filas[0].datos["fracttal_id"] == "274"
    assert imp.partir_ruta(filas[0].datos["ruta"]) == ["H1"]


def test_tolera_columnas_ausentes_pero_exige_nombre_y_ubicado_en():
    filas = imp.leer_equipos(excel(["Nombre", "Ubicado en"], [["Bomba", "// H1/"]]))
    assert filas[0].datos.get("fabricante") is None
    with pytest.raises(imp.ImportacionError, match="columnas obligatorias"):
        imp.leer_equipos(excel(["Nombre (C)", "Código"], [["Bomba", "X"]]))


def test_archivo_que_no_es_excel():
    with pytest.raises(imp.ImportacionError, match="no es un Excel"):
        imp.leer_equipos(io.BytesIO(b"esto no es un xlsx"))


def test_numero_de_fila_de_excel_con_filas_vacias():
    filas = imp.leer_equipos(excel(COLS_EQ, [
        equipo("A", "// H/"), [None] * len(COLS_EQ), equipo("B", "// H/")]))
    assert [f.fila for f in filas] == [2, 4]


# ------------------------------------------------------------------- plan

@pytest.mark.django_db
def test_hospital_nuevo_con_codigo_unico_y_existente_sin_tildes_ni_mayusculas():
    baker.make(Hospital, name="Clínica del Norte", code="CLINICA-DEL-NORTE")
    baker.make(Hospital, name="Otro", code="HOSPITAL-NUEVO")
    plan = planificar_con(eq=[
        equipo("A", "// clinica  del NORTE/ Urgencias/"),
        equipo("B", "// Hospital Nuevo/"),
    ])
    r = plan.resumen()
    assert r["hospitals"]["existing"] == ["Clínica del Norte"]
    assert r["hospitals"]["create"] == ["Hospital Nuevo"]
    # el codigo generado choca con uno existente y se desambigua
    assert plan.hospitales["hospital nuevo"].codigo == "HOSPITAL-NUEVO-2"
    assert Hospital.objects.count() == 2  # solo planifica


@pytest.mark.django_db
def test_ubicaciones_anidadas_e_intermedias_con_aviso():
    plan = planificar_con(
        ub=[ubic("3° Piso", "// H1/ Bloque A/", fid=10, direccion="Calle 1 # 2", ciudad="CALI")],
        eq=[equipo("Bomba", "// H1/ Bloque A/ 3° Piso/ Cuarto/", fid=1, codigo="B-1")],
    )
    r = plan.resumen()
    # Bloque A (intermedia), 3° Piso (archivo) y Cuarto (intermedia)
    assert r["locations"] == {"create": 3, "update": 0}
    avisos = [w for f in r["rows"] for w in f["warnings"]]
    assert any("«Bloque A»" in w and "intermedia" in w for w in avisos)
    assert any("«Cuarto»" in w for w in avisos)
    assert not any("«3° Piso»" in w for w in avisos)
    assert r["rows"][1]["location"] == "H1 / Bloque A / 3° Piso / Cuarto"


@pytest.mark.django_db
def test_errores_de_fila():
    plan = planificar_con(
        ub=[ubic("", "// H1/"), ubic("Sala", "")],
        eq=[equipo("", "// H1/"), equipo("Sin hospital", ""), equipo("Bien", "// H1/", fid=5)],
    )
    r = plan.resumen()
    assert [f["action"] for f in r["rows"]] == ["error", "error", "error", "error", "create"]
    assert r["errors_count"] == 4
    assert "no tiene nombre" in r["rows"][0]["errors"][0]


@pytest.mark.django_db
def test_codigo_faltante_y_repetido_se_generan_unicos():
    baker.make(Asset, code="DUP-1", hospital=baker.make(Hospital))
    plan = planificar_con(eq=[
        equipo("Sin codigo", "// H/", fid=1),
        equipo("Choca con la base", "// H/", fid=2, codigo="DUP-1"),
        equipo("Primero", "// H/", fid=3, codigo="NUEVO"),
        equipo("Choca en archivo", "// H/", fid=4, codigo="nuevo"),
        equipo("Normal", "// H/", fid=5, codigo="/SCH/IMG/A/"),
    ])
    codigos = [a.campos["code"] for a in plan.activos]
    assert len(set(c.lower() for c in codigos)) == 5
    assert codigos[2] == "NUEVO" and codigos[4] == "SCH/IMG/A"
    assert codigos[0].startswith("FRC-") and codigos[1].startswith("FRC-") and codigos[3].startswith("FRC-")
    avisos = [f["warnings"] for f in plan.filas]
    assert "no trae código" in avisos[0][0]
    assert "ya lo usa otro activo" in avisos[1][0]


@pytest.mark.django_db
def test_prioridad_estados_y_fecha(admin):
    plan = planificar_con(eq=[
        equipo("A", "// H/", fid=1, prioridad="Alta"),
        equipo("B", "// H/", fid=2, prioridad="Baja", fuera="Si"),
        equipo("C", "// H/", fid=3, prioridad=None, habilitado="No", fuera="Si",
               fecha=datetime.datetime(2020, 5, 17)),
        equipo("D", "// H/", fid=4, fecha="no es fecha"),
        equipo("E", "// H/", fid=5, fecha="03/02/2021", notas="Una nota"),
    ])
    c = [a.campos for a in plan.activos]
    assert (c[0]["priority"], c[0]["status"]) == ("HIGH", "ACTIVE")
    assert (c[1]["priority"], c[1]["status"]) == ("LOW", "OUT_OF_SERVICE")
    assert (c[2]["priority"], c[2]["status"]) == ("MEDIUM", "DECOMMISSIONED")
    assert c[2]["purchase_date"] == datetime.date(2020, 5, 17)
    assert c[3]["purchase_date"] is None
    assert any("Fecha de compra" in w for w in plan.filas[3]["warnings"])
    assert c[4]["purchase_date"] == datetime.date(2021, 2, 3) and c[4]["notes"] == "Una nota"


# ----------------------------------------------------------------- aplicar

def _plan_con_tarea(nombre="PLAN DE SERVICIO ALARMA"):
    plan = MaintenancePlan.objects.create(name=nombre)
    PlanTask.objects.create(plan=plan, name="Revision", frequency_value=6, frequency_unit="MONTHS")
    return plan


@pytest.mark.django_db
def test_aplicar_crea_todo_y_asigna_protocolo_existente(admin):
    plan_pm = _plan_con_tarea()
    plan = planificar_con(
        ub=[ubic("Cuarto de gases", "// H1/ Bloque A/", fid=10, direccion="Av 6", ciudad="CALI",
                 codigo="204-1")],
        eq=[
            equipo("Alarma", "// H1/ Bloque A/ Cuarto de gases/", fid=274, codigo="AL-1",
                   plan="  plan de servicio   alarma "),
            equipo("Otra", "// H1/", fid=275, plan="PLAN FANTASMA"),
        ],
    )
    r = plan.resumen()
    assert r["plans"] == {"create": ["PLAN FANTASMA"], "existing": ["PLAN DE SERVICIO ALARMA"]}
    assert any("Se creará el protocolo «PLAN FANTASMA» vacío" in w
               for w in plan.filas[2]["warnings"])
    conteos = imp.aplicar(plan, admin)

    assert conteos["hospitals_created"] == 1 and conteos["locations_created"] == 2
    assert conteos["assets_created"] == 2 and conteos["plans_assigned"] == 2
    assert conteos["plans_created"] == 1
    hospital = Hospital.objects.get(name="H1")
    cuarto = AssetNode.objects.get(name="Cuarto de gases")
    assert cuarto.parent.name == "Bloque A" and cuarto.parent.parent is None
    assert cuarto.path == "Bloque A/Cuarto de gases"
    assert cuarto.address == "Av 6, CALI" and cuarto.code == "204-1" and cuarto.fracttal_id == "10"
    alarma = Asset.objects.get(fracttal_id="274")
    assert alarma.node == cuarto and alarma.hospital == hospital and alarma.plan == plan_pm
    assert Task.objects.filter(asset=alarma, status=Task.Status.PENDING).count() == 1
    otra = Asset.objects.get(fracttal_id="275")
    assert otra.node is None and otra.plan.name == "PLAN FANTASMA"
    assert otra.plan.tasks.count() == 0 and "Falta agregar tareas" in otra.plan.description


@pytest.mark.django_db
def test_reimportar_actualiza_sin_duplicar(admin):
    plan_pm = _plan_con_tarea()
    ub = [ubic("Sala", "// H1/", fid=10)]
    eq = [equipo("Bomba", "// H1/ Sala/", fid=1, codigo="B-1", plan=plan_pm.name, notas="v1")]
    imp.aplicar(planificar_con(ub, eq), admin)
    manual = Asset.objects.get(fracttal_id="1")
    manual.manufacturer = "Puesto a mano"
    manual.save()

    eq2 = [equipo("Bomba renombrada", "// H1/ Sala/", fid=1, codigo="OTRO", plan=plan_pm.name,
                  notas="v2", prioridad="Alta")]
    plan2 = planificar_con(ub, eq2)
    r = plan2.resumen()
    assert r["locations"] == {"create": 0, "update": 1}
    assert r["assets"] == {"create": 0, "update": 1}
    assert [f["action"] for f in r["rows"]] == ["update", "update"]
    conteos = imp.aplicar(plan2, admin)

    assert Asset.objects.count() == 1 and AssetNode.objects.count() == 1 and Hospital.objects.count() == 1
    a = Asset.objects.get()
    assert (a.name, a.notes, a.priority, a.code) == ("Bomba renombrada", "v2", "HIGH", "B-1")
    assert a.manufacturer == "Puesto a mano"  # un vacio de Fracttal no borra
    assert conteos["plans_assigned"] == 0  # ya tenia ese protocolo
    assert Task.objects.filter(asset=a).count() == 1


@pytest.mark.django_db
def test_protocolos_nuevos_se_deduplican_y_la_reimportacion_no_duplica(admin):
    eq = [
        equipo("A", "// H1/", fid=1, plan="PLAN  SERVICIO   TOMAS"),
        equipo("B", "// H1/", fid=2, plan="plan servicio tomas"),
        equipo("C", "// H1/", fid=3, plan="Plan Servicio Alarma"),
        equipo("D", "// H1/", fid=4),
    ]
    p1 = planificar_con(eq=eq)
    assert p1.resumen()["plans"] == {
        "create": ["PLAN SERVICIO TOMAS", "Plan Servicio Alarma"], "existing": []}
    assert MaintenancePlan.objects.count() == 0  # planificar no escribe
    c1 = imp.aplicar(p1, admin)
    assert c1["plans_created"] == 2 and c1["plans_assigned"] == 3
    assert MaintenancePlan.objects.count() == 2
    a, b = Asset.objects.get(fracttal_id="1"), Asset.objects.get(fracttal_id="2")
    assert a.plan_id == b.plan_id and Asset.objects.get(fracttal_id="4").plan is None

    p2 = planificar_con(eq=eq)
    assert p2.resumen()["plans"]["create"] == []
    assert len(p2.resumen()["plans"]["existing"]) == 2
    assert not any("Cambia de protocolo" in w for f in p2.filas for w in f["warnings"])
    c2 = imp.aplicar(p2, admin)
    assert c2["plans_created"] == 0 and c2["plans_assigned"] == 0
    assert MaintenancePlan.objects.count() == 2 and Asset.objects.count() == 4


@pytest.mark.django_db
def test_cambia_de_protocolo_y_fila_sin_plan_conserva_el_suyo(admin):
    viejo = _plan_con_tarea("PLAN VIEJO")
    nuevo = _plan_con_tarea("PLAN NUEVO")
    imp.aplicar(planificar_con(eq=[
        equipo("A", "// H1/", fid=1, plan=viejo.name),
        equipo("B", "// H1/", fid=2, plan=viejo.name),
        equipo("C", "// H1/", fid=3, plan=viejo.name),
    ]), admin)
    plan = planificar_con(eq=[
        equipo("A", "// H1/", fid=1, plan=nuevo.name),      # a uno existente
        equipo("B", "// H1/", fid=2),                       # sin plan: conserva
        equipo("C", "// H1/", fid=3, plan="PLAN CREADO"),   # a uno por crear
    ])
    avisos = [f["warnings"] for f in plan.filas]
    assert "Cambia de protocolo: «PLAN VIEJO» → «PLAN NUEVO»." in avisos[0]
    assert avisos[1] == []
    assert "Cambia de protocolo: «PLAN VIEJO» → «PLAN CREADO»." in avisos[2]
    imp.aplicar(plan, admin)
    assert Asset.objects.get(fracttal_id="1").plan == nuevo
    assert Asset.objects.get(fracttal_id="2").plan == viejo
    assert Asset.objects.get(fracttal_id="3").plan.name == "PLAN CREADO"
    # las pendientes del plan viejo se anularon al cambiar
    assert not Task.objects.filter(
        asset__fracttal_id__in=["1", "3"], plan_task__plan=viejo, status=Task.Status.PENDING).exists()


@pytest.mark.django_db
def test_protocolo_vacio_no_rompe_nada(admin):
    imp.aplicar(planificar_con(eq=[equipo("A", "// H1/", fid=1, plan="PLAN VACIO")]), admin)
    asset = Asset.objects.get()
    c = APIClient()
    c.force_authenticate(admin)
    lista = c.get("/api/maintenance/plans/")
    assert lista.status_code == 200
    fila = next(p for p in lista.data["results"] if p["name"] == "PLAN VACIO")
    assert fila["tasks"] == [] and fila["assets_count"] == 1
    assert c.get(f"/api/maintenance/plans/{fila['id']}/").status_code == 200
    assert c.get(f"/api/assets/{asset.id}/").status_code == 200


@pytest.mark.django_db
def test_ubicacion_existente_sin_id_se_encuentra_por_nombre(admin):
    h = baker.make(Hospital, name="H1", code="H1")
    nodo = AssetNode.objects.create(hospital=h, name="Sala", parent=None)
    plan = planificar_con(ub=[ubic("SALA", "// h1/", fid=99)])
    assert plan.resumen()["locations"] == {"create": 0, "update": 1}
    imp.aplicar(plan, admin)
    nodo.refresh_from_db()
    assert nodo.fracttal_id == "99" and AssetNode.objects.count() == 1


@pytest.mark.django_db
def test_errores_bloquean_y_no_aplican_nada(admin):
    plan = planificar_con(eq=[equipo("Bien", "// H1/", fid=1), equipo("", "// H1/")])
    assert plan.errores == 1
    with pytest.raises(imp.ImportacionError):
        imp.aplicar(plan, admin)
    assert Hospital.objects.count() == 0 and Asset.objects.count() == 0


@pytest.mark.django_db
def test_atomicidad_si_falla_a_mitad_no_queda_nada(admin, monkeypatch):
    plan_pm = _plan_con_tarea()
    plan = planificar_con(
        ub=[ubic("Sala", "// H1/", fid=10)],
        eq=[equipo("Uno", "// H1/ Sala/", fid=1, plan=plan_pm.name),
            equipo("Dos", "// H1/ Sala/", fid=2, plan=plan_pm.name)],
    )
    llamadas = []
    original = imp.set_asset_plan

    def falla_en_la_segunda(*args, **kwargs):
        llamadas.append(1)
        if len(llamadas) == 2:
            raise RuntimeError("falla a mitad")
        return original(*args, **kwargs)

    monkeypatch.setattr(imp, "set_asset_plan", falla_en_la_segunda)
    with pytest.raises(RuntimeError):
        imp.aplicar(plan, admin)
    assert len(llamadas) == 2
    assert Hospital.objects.count() == 0 and AssetNode.objects.count() == 0
    assert Asset.objects.count() == 0 and Task.objects.count() == 0


# --------------------------------------------------------------------- API

def _post(client, nombre, ubicaciones=None, equipos=None):
    datos = {}
    if ubicaciones is not None:
        datos["ubicaciones"] = SimpleUploadedFile("ubicaciones.xlsx", ubicaciones.getvalue())
    if equipos is not None:
        datos["equipos"] = SimpleUploadedFile("equipos.xlsx", equipos.getvalue())
    return client.post(reverse(nombre), datos, format="multipart")


@pytest.fixture
def cliente_admin(admin):
    c = APIClient()
    c.force_authenticate(admin)
    return c


@pytest.mark.django_db
def test_preview_responde_el_resumen_y_no_escribe(cliente_admin):
    r = _post(cliente_admin, "import-fracttal-preview",
              ubicaciones=excel(COLS_UBIC, [ubic("Sala", "// H1/", fid=10)]),
              equipos=excel(COLS_EQ, [equipo("Bomba", "// H1/ Sala/", fid=1, codigo="B1")]))
    assert r.status_code == 200
    assert set(r.data) == {"hospitals", "locations", "assets", "plans", "rows",
                           "errors_count", "warnings_count", "applied"}
    assert r.data["applied"] is False
    assert r.data["hospitals"] == {"create": ["H1"], "existing": []}
    assert r.data["rows"][1] == {"file": "equipos", "row": 2, "name": "Bomba",
                                 "location": "H1 / Sala", "action": "create",
                                 "errors": [], "warnings": []}
    assert Hospital.objects.count() == 0


@pytest.mark.django_db
def test_preview_con_un_solo_archivo_y_validaciones(cliente_admin):
    ok = _post(cliente_admin, "import-fracttal-preview",
               equipos=excel(COLS_EQ, [equipo("Bomba", "// H1/", fid=1)]))
    assert ok.status_code == 200
    assert _post(cliente_admin, "import-fracttal-preview").status_code == 400
    malo = cliente_admin.post(
        reverse("import-fracttal-preview"),
        {"equipos": SimpleUploadedFile("equipos.xlsx", b"no es excel")}, format="multipart")
    assert malo.status_code == 400 and "Excel" in malo.data["detail"]
    csv = cliente_admin.post(
        reverse("import-fracttal-preview"),
        {"equipos": SimpleUploadedFile("equipos.csv", b"a,b")}, format="multipart")
    assert csv.status_code == 400


@pytest.mark.django_db
def test_importar_aplica_y_audita(cliente_admin, admin):
    r = _post(cliente_admin, "import-fracttal",
              ubicaciones=excel(COLS_UBIC, [ubic("Sala", "// H1/", fid=10)]),
              equipos=excel(COLS_EQ, [equipo("Bomba", "// H1/ Sala/", fid=1, codigo="B1")]))
    assert r.status_code == 201
    assert r.data["applied"] is True
    assert r.data["applied_counts"]["assets_created"] == 1
    assert Asset.objects.filter(fracttal_id="1").exists()
    log = AuditLog.objects.get(entity_type="FracttalImport")
    assert log.user == admin
    assert log.changes["archivos"] == {"ubicaciones": "ubicaciones.xlsx", "equipos": "equipos.xlsx"}
    assert log.changes["equipos"]["create"] == 1


@pytest.mark.django_db
def test_importar_con_errores_responde_400_sin_aplicar(cliente_admin):
    r = _post(cliente_admin, "import-fracttal",
              equipos=excel(COLS_EQ, [equipo("Bien", "// H1/", fid=1), equipo("", "// H1/")]))
    assert r.status_code == 400
    assert r.data["errors_count"] == 1 and r.data["applied"] is False
    assert Asset.objects.count() == 0 and Hospital.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [User.Role.SUP, User.Role.TEC, User.Role.CLI])
def test_solo_admin(rol):
    user = baker.make(User, role=rol, is_active=True)
    c = APIClient()
    c.force_authenticate(user)
    for nombre in ("import-fracttal-preview", "import-fracttal"):
        r = _post(c, nombre, equipos=excel(COLS_EQ, [equipo("Bomba", "// H1/", fid=1)]))
        assert r.status_code == 403
    assert Asset.objects.count() == 0
    anon = APIClient()
    assert _post(anon, "import-fracttal", equipos=excel(COLS_EQ, [])).status_code == 401


# ----------------------------------------------------------------- comando

@pytest.mark.django_db
def test_comando_sin_aplicar_solo_muestra(tmp_path, capsys):
    ruta = tmp_path / "equipos.xlsx"
    ruta.write_bytes(excel(COLS_EQ, [equipo("Bomba", "// H1/", fid=1, codigo="B1")]).getvalue())
    call_command("importar_fracttal", equipos=str(ruta))
    assert "Equipos: 1 a crear" in capsys.readouterr().out
    assert Asset.objects.count() == 0


@pytest.mark.django_db
def test_comando_aplicar_usa_primer_admin(tmp_path, admin):
    ruta = tmp_path / "equipos.xlsx"
    ruta.write_bytes(excel(COLS_EQ, [equipo("Bomba", "// H1/", fid=1, codigo="B1")]).getvalue())
    call_command("importar_fracttal", equipos=str(ruta), aplicar=True)
    assert Asset.objects.filter(code="B1").exists()
    assert AuditLog.objects.get(entity_type="FracttalImport").user == admin
    with pytest.raises(CommandError):
        call_command("importar_fracttal")
