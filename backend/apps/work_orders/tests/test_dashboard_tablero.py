"""
Tablero del administrador, segunda ronda ("mas parecido al de Fracttal").

Lo nuevo vive en apps.work_orders.dashboard:
  calculate_pending_by_month  tareas abiertas: vencidas + los proximos 6 meses
  calculate_ots_by_kind       OTs del periodo por lo que el catalogo dice que cuentan
  calculate_open_findings     hallazgos pendientes de decision, por severidad

y el estado de activos (/api/dashboard/assets-status/), que ya existia pero
sin pruebas y con fronteras distintas a las del listado de activos al que
lleva el clic.
"""

import uuid
from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import MaintenancePlan, PlanTask, Task
from apps.maintenance.testing import make_plan, make_work_order
from apps.users.models import User
from apps.work_orders import dashboard
from apps.work_orders.models import Finding, WorkOrder


# ---------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------

def make_user(role, hospital=None):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@test.com", password="pass",
        first_name="Test", last_name="User", role=role, hospital=hospital,
    )


def make_hospital():
    return Hospital.objects.create(name=f"H-{uuid.uuid4()}", code=str(uuid.uuid4())[:8])


def make_asset(hospital, status=Asset.Status.ACTIVE):
    return Asset.objects.create(
        hospital=hospital, name="Equipo", code=str(uuid.uuid4())[:10], status=status,
    )


def client_of(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def hoy():
    return timezone.localdate()


def en_dias(n):
    return hoy() + timedelta(days=n)


def tarea(asset, fecha, estado=Task.Status.PENDING, plan_task=None):
    """Tarea suelta (sin OT), como las que espera el planificador."""
    return Task.objects.create(
        asset=asset, plan_task=plan_task, title="Tarea", task_type="PREVENTIVE",
        status=estado, calculated_date=fecha, scheduled_date=fecha,
    )


def plan_para(asset, dias):
    """Plan activo cuya proxima fecha en `asset` cae a `dias` de hoy."""
    return make_plan(f"Plan {uuid.uuid4()}", next_due_date=en_dias(dias), assets=[asset])


def mes(n):
    """Dia 15 del mes que queda `n` meses despues del actual."""
    return (hoy().replace(day=1) + relativedelta(months=n)).replace(day=15)


def clave(n):
    return mes(n).strftime("%Y-%m")


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def hospital(db):
    return make_hospital()


@pytest.fixture
def hospital_b(db):
    return make_hospital()


@pytest.fixture
def admin(db):
    return make_user(User.Role.ADMIN)


@pytest.fixture
def asset(hospital):
    return make_asset(hospital)


@pytest.fixture
def asset_b(hospital_b):
    return make_asset(hospital_b)


# ---------------------------------------------------------------------------
# 1. Estado de activos (/api/dashboard/assets-status/)
# ---------------------------------------------------------------------------

URL_ESTADO = "/api/dashboard/assets-status/"


@pytest.fixture
def universo(hospital, admin):
    """Un activo por cada caso, con las fronteras de 0 y 30 dias."""
    casos = {}
    for codigo, dias in {
        "AL_DIA": 60, "FRONTERA_31": 31, "POR_VENCER": 10, "FRONTERA_30": 30,
        "HOY": 0, "VENCIDO": -1,
    }.items():
        a = make_asset(hospital)
        plan_para(a, dias)
        casos[codigo] = a
    casos["SIN_PLAN"] = make_asset(hospital)
    # No cuentan: dados de baja, aunque tengan tareas vencidas.
    baja = make_asset(hospital, status=Asset.Status.DECOMMISSIONED)
    plan_para(baja, -20)
    casos["BAJA"] = baja
    return casos


@pytest.mark.django_db
def test_estado_de_activos_cuenta_cada_categoria(universo, hospital, admin):
    r = client_of(admin).get(URL_ESTADO, {"hospital_id": str(hospital.id)})

    assert r.status_code == 200
    assert r.json() == {
        "on_time": 2,    # +60 y +31
        "due_soon": 3,   # +10, +30 y hoy (hoy no esta vencido)
        "overdue": 1,    # -1
        "no_plan": 1,
        "total": 7,      # los 7 activos en servicio; el dado de baja no entra
    }


@pytest.mark.django_db
def test_un_activo_con_una_tarea_vencida_es_vencido_aunque_tenga_otras_al_dia(
    hospital, admin
):
    a = make_asset(hospital)
    plan = plan_para(a, -5)
    otra = PlanTask.objects.create(
        plan=plan, name="Otra", task_type="PREVENTIVE", trigger=PlanTask.Trigger.DATE,
        frequency_value=6, frequency_unit=MaintenancePlan.FrequencyUnit.MONTHS,
    )
    tarea(a, en_dias(90), plan_task=otra)

    r = client_of(admin).get(URL_ESTADO, {"hospital_id": str(hospital.id)})

    assert (r.json()["overdue"], r.json()["on_time"], r.json()["due_soon"]) == (1, 0, 0)


@pytest.mark.django_db
def test_estado_de_activos_respeta_el_hospital(hospital, hospital_b, admin):
    plan_para(make_asset(hospital), -1)
    plan_para(make_asset(hospital_b), -1)
    plan_para(make_asset(hospital_b), -2)

    c = client_of(admin)

    assert c.get(URL_ESTADO, {"hospital_id": str(hospital.id)}).json()["overdue"] == 1
    assert c.get(URL_ESTADO, {"hospital_id": str(hospital_b.id)}).json()["overdue"] == 2
    assert c.get(URL_ESTADO).json()["overdue"] == 3


@pytest.mark.django_db
def test_un_supervisor_de_hospital_no_ve_el_estado_de_otro(hospital, hospital_b):
    plan_para(make_asset(hospital), -1)
    plan_para(make_asset(hospital_b), -1)
    plan_para(make_asset(hospital_b), -2)
    sup = make_user(User.Role.SUP, hospital=hospital)

    # Pedir el otro hospital a mano no sirve.
    r = client_of(sup).get(URL_ESTADO, {"hospital_id": str(hospital_b.id)})

    assert r.json()["overdue"] == 1


@pytest.mark.django_db
def test_el_clic_lleva_a_una_lista_con_el_mismo_numero(universo, hospital, admin):
    """
    La tarjeta dice N y el clic abre /activos?maintenance_status=X: la lista
    tiene que mostrar N filas. Hoy el tablero corta "por vencer" a 30 dias y el
    listado a 15, asi que +10 coincide pero +30 y +20 no.
    """
    c = client_of(admin)
    h = str(hospital.id)
    resumen = c.get(URL_ESTADO, {"hospital_id": h}).json()

    for categoria, clave_resumen in [
        ("on_time", "on_time"), ("due_soon", "due_soon"),
        ("overdue", "overdue"), ("no_plan", "no_plan"),
    ]:
        lista = c.get("/api/assets/", {
            "maintenance_status": categoria, "hospital_id": h, "status": "ACTIVE",
        })
        assert lista.data["count"] == resumen[clave_resumen], categoria


@pytest.mark.django_db
def test_estado_de_activos_tiene_pocas_consultas(universo, hospital, admin, django_assert_max_num_queries):
    c = client_of(admin)
    with django_assert_max_num_queries(6):
        c.get(URL_ESTADO, {"hospital_id": str(hospital.id)})


# ---------------------------------------------------------------------------
# 2. Tareas pendientes por mes
# ---------------------------------------------------------------------------

@pytest.fixture
def agenda(hospital, asset, hospital_b, asset_b, admin):
    """Tareas abiertas repartidas en el tiempo, y ruido que no debe contar."""
    tarea(asset, en_dias(-3))                                   # vencida
    make_work_order(asset, admin, scheduled_date=en_dias(-10))  # vencida, ya en una OT
    tarea(asset, hoy())                                         # este mes, hoy no esta vencida
    tarea(asset, mes(1))                                        # mes +1
    make_work_order(asset, admin, scheduled_date=mes(1))        # mes +1, programada
    tarea(asset, mes(5))                                        # ultimo mes de la ventana
    tarea(asset, mes(6))                                        # fuera de la ventana
    # No cuentan:
    make_work_order(asset, admin, scheduled_date=mes(2), status=WorkOrder.Status.COMPLETED)
    tarea(asset, mes(2), estado=Task.Status.CANCELLED)
    pausado = make_asset(hospital)
    plan = plan_para(pausado, 0)
    Task.objects.filter(asset=pausado).update(scheduled_date=mes(3))
    MaintenancePlan.objects.filter(pk=plan.pk).update(is_active=False)
    tarea(asset_b, en_dias(-1))                                 # otro hospital
    tarea(asset_b, mes(1))


@pytest.mark.django_db
def test_pendientes_por_mes_separa_vencidas_y_seis_meses(agenda, hospital):
    r = dashboard.calculate_pending_by_month(hospital_id=str(hospital.id))

    assert r["overdue"] == 2
    assert [m["month"] for m in r["months"]] == [clave(i) for i in range(6)]
    assert [m["count"] for m in r["months"]] == [1, 2, 0, 0, 0, 1]


@pytest.mark.django_db
def test_pendientes_por_mes_sin_hospital_suma_todos(agenda):
    r = dashboard.calculate_pending_by_month()

    assert r["overdue"] == 3
    assert [m["count"] for m in r["months"]] == [1, 3, 0, 0, 0, 1]


@pytest.mark.django_db
def test_pendientes_por_mes_sin_tareas_devuelve_los_seis_meses_en_cero(hospital):
    r = dashboard.calculate_pending_by_month(hospital_id=str(hospital.id))

    assert r["overdue"] == 0
    assert len(r["months"]) == 6
    assert all(m["count"] == 0 for m in r["months"])


@pytest.mark.django_db
def test_pendientes_por_mes_tiene_pocas_consultas(agenda, hospital, django_assert_max_num_queries):
    with django_assert_max_num_queries(3):
        dashboard.calculate_pending_by_month(hospital_id=str(hospital.id))


# ---------------------------------------------------------------------------
# 3. OTs del periodo por tipo (preventivo / correctivo / otro)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_ots_por_tipo_usa_lo_que_el_catalogo_dice(hospital, asset, hospital_b, asset_b, admin):
    for codigo in ["PREVENTIVE", "PREVENTIVE", "CAMBIO_DE_FILTROS"]:  # el 3o cuenta como preventivo
        make_work_order(asset, admin, task_type=codigo)
    make_work_order(asset, admin, task_type="CORRECTIVE")
    make_work_order(asset, admin, task_type="AJUSTE")                 # correctivo en el catalogo
    make_work_order(asset, admin, task_type="RETIRO")                 # ninguno
    make_work_order(asset, admin, task_type="CODIGO_QUE_YA_NO_EXISTE")  # fuera del catalogo: otro
    make_work_order(asset_b, admin, task_type="PREVENTIVE")           # otro hospital
    # Una cancelada no es trabajo hecho ni por hacer.
    make_work_order(asset, admin, task_type="PREVENTIVE", status=WorkOrder.Status.CANCELLED)

    r = dashboard.calculate_ots_by_kind(hospital_id=str(hospital.id), days=30)

    assert r == {"PREVENTIVE": 3, "CORRECTIVE": 2, "OTHER": 2}


@pytest.mark.django_db
def test_ots_por_tipo_solo_cuenta_el_periodo(hospital, asset, admin):
    vieja = make_work_order(asset, admin, task_type="PREVENTIVE")
    WorkOrder.objects.filter(pk=vieja.pk).update(created_at=timezone.now() - timedelta(days=45))
    make_work_order(asset, admin, task_type="PREVENTIVE")

    assert dashboard.calculate_ots_by_kind(str(hospital.id), days=30)["PREVENTIVE"] == 1
    assert dashboard.calculate_ots_by_kind(str(hospital.id), days=90)["PREVENTIVE"] == 2


@pytest.mark.django_db
def test_ots_por_tipo_sin_ots_devuelve_ceros(hospital):
    assert dashboard.calculate_ots_by_kind(str(hospital.id), days=30) == {
        "PREVENTIVE": 0, "CORRECTIVE": 0, "OTHER": 0,
    }


@pytest.mark.django_db
def test_ots_por_tipo_tiene_pocas_consultas(hospital, asset, admin, django_assert_max_num_queries):
    for codigo in ["PREVENTIVE", "CORRECTIVE", "RETIRO", "AJUSTE"]:
        make_work_order(asset, admin, task_type=codigo)
    with django_assert_max_num_queries(3):
        dashboard.calculate_ots_by_kind(str(hospital.id), days=30)


# ---------------------------------------------------------------------------
# 4. Hallazgos abiertos por severidad
# ---------------------------------------------------------------------------

def hallazgo(wo, asset, user, severity=Finding.Severity.MEDIUM,
             estado=Finding.Status.PENDING, fuera_de_servicio=False):
    return Finding.objects.create(
        work_order=wo, asset=asset, description="Fuga", severity=severity,
        status=estado, out_of_service=fuera_de_servicio, reported_by=user,
    )


@pytest.fixture
def hallazgos(hospital, asset, hospital_b, asset_b, admin):
    wo = make_work_order(asset, admin)
    wo_b = make_work_order(asset_b, admin)
    S = Finding.Severity
    hallazgo(wo, asset, admin, S.CRITICAL, fuera_de_servicio=True)
    hallazgo(wo, asset, admin, S.CRITICAL)
    hallazgo(wo, asset, admin, S.HIGH, fuera_de_servicio=True)
    hallazgo(wo, asset, admin, S.MEDIUM)
    hallazgo(wo, asset, admin, S.LOW)
    # Ya decididos o resueltos en sitio: no piden accion.
    for estado in (Finding.Status.RESOLVED, Finding.Status.CONVERTED, Finding.Status.DISMISSED):
        hallazgo(wo, asset, admin, S.CRITICAL, estado=estado)
    hallazgo(wo_b, asset_b, admin, S.CRITICAL)  # otro hospital


@pytest.mark.django_db
def test_hallazgos_abiertos_por_severidad(hallazgos, hospital):
    r = dashboard.calculate_open_findings(hospital_id=str(hospital.id))

    assert r == {
        "total": 5,
        "by_severity": {"CRITICAL": 2, "HIGH": 1, "MEDIUM": 1, "LOW": 1},
        "out_of_service": 2,
    }


@pytest.mark.django_db
def test_hallazgos_abiertos_sin_hospital_suma_todos(hallazgos):
    r = dashboard.calculate_open_findings()

    assert r["total"] == 6
    assert r["by_severity"]["CRITICAL"] == 3


@pytest.mark.django_db
def test_hallazgos_abiertos_sin_hallazgos_devuelve_ceros(hospital):
    assert dashboard.calculate_open_findings(hospital_id=str(hospital.id)) == {
        "total": 0,
        "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "out_of_service": 0,
    }


@pytest.mark.django_db
def test_hallazgos_abiertos_tiene_pocas_consultas(hallazgos, hospital, django_assert_max_num_queries):
    with django_assert_max_num_queries(2):
        dashboard.calculate_open_findings(hospital_id=str(hospital.id))


# ---------------------------------------------------------------------------
# El endpoint los entrega junto al resto, con el mismo alcance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_el_tablero_trae_los_bloques_nuevos(hallazgos, agenda, hospital, admin):
    r = client_of(admin).get("/api/dashboard/", {"hospital_id": str(hospital.id)})

    assert r.status_code == 200
    data = r.json()
    assert data["pending_by_month"]["overdue"] == 2
    assert data["ots_by_kind"].keys() == {"PREVENTIVE", "CORRECTIVE", "OTHER"}
    assert data["open_findings"]["total"] == 5
    # Lo que ya habia sigue ahi.
    for k in ("compliance", "mttr", "overdue", "ots_by_status", "ots_by_technician",
              "assets_without_maintenance"):
        assert k in data


@pytest.mark.django_db
def test_un_supervisor_de_hospital_solo_ve_los_hallazgos_de_su_hospital(
    hallazgos, agenda, hospital, hospital_b
):
    sup = make_user(User.Role.SUP, hospital=hospital)

    # Pide el otro hospital a mano: el tablero lo ignora y devuelve el suyo.
    data = client_of(sup).get("/api/dashboard/", {"hospital_id": str(hospital_b.id)}).json()

    assert data["open_findings"]["total"] == 5
    assert data["pending_by_month"]["overdue"] == 2


# ---------------------------------------------------------------------------
# OTs por tecnico: las consultas no dependen de cuantos tecnicos haya
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_ots_por_tecnico_cuenta_bien(hospital, asset, admin):
    tec = make_user(User.Role.TEC)
    make_work_order(asset, admin, assigned_to=tec, scheduled_date=en_dias(-2))
    make_work_order(asset, admin, assigned_to=tec, scheduled_date=en_dias(3))
    make_work_order(asset, admin, assigned_to=tec, scheduled_date=en_dias(-2),
                    status=WorkOrder.Status.COMPLETED)
    make_work_order(asset, admin, scheduled_date=en_dias(-2))  # de nadie

    (fila,) = dashboard.calculate_ots_by_technician(days=30)

    assert fila["technician_id"] == str(tec.id)
    assert (fila["assigned"], fila["overdue"]) == (3, 1)


@pytest.mark.django_db
def test_ots_por_tecnico_tiene_las_mismas_consultas_con_uno_o_con_diez(
    asset, admin, django_assert_max_num_queries
):
    for _ in range(10):
        tec = make_user(User.Role.TEC)
        make_work_order(asset, admin, assigned_to=tec, scheduled_date=en_dias(-1))

    with django_assert_max_num_queries(2):
        assert len(dashboard.calculate_ots_by_technician(days=30)) == 10
