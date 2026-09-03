"""
Filtro de estado de mantenimiento en el servidor (RF-AC-07).

maintenance_status es un campo calculado: antes solo existia en el serializer y
AssetsPage tenia que traer todos los activos para filtrar por color en el
cliente, lo que impedia paginar de verdad. Ahora el filtro vive en el servidor
y deriva del mismo `_next_due` que se muestra, asi que el color pintado y el
filtro no pueden divergir.
"""

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.models import MaintenancePlan
from apps.users.models import User


def admin_client(db):
    c = APIClient()
    c.force_authenticate(
        user=User.objects.create_user(
            email=f"{uuid.uuid4()}@t.co", password="x",
            first_name="A", last_name="D", role=User.Role.ADMIN,
        )
    )
    return c


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(name="H", code=str(uuid.uuid4())[:8])


def make_asset(hospital, code):
    return Asset.objects.create(
        hospital=hospital, name=f"Activo {code}", code=code,
        status=Asset.Status.ACTIVE,
    )


def plan_for(asset, days_from_today):
    """Plan activo cuya proxima fecha cae a N dias de hoy (N negativo = vencido)."""
    plan = MaintenancePlan.objects.create(
        name=f"Plan {uuid.uuid4()}",
        is_active=True,
        next_due_date=timezone.localdate() + timedelta(days=days_from_today),
    )
    plan.assets.add(asset)
    return plan


@pytest.fixture
def universo(db, hospital):
    """Un activo de cada categoria."""
    overdue = make_asset(hospital, "OVERDUE")
    plan_for(overdue, -3)
    due_soon = make_asset(hospital, "DUESOON")
    plan_for(due_soon, 10)
    on_time = make_asset(hospital, "ONTIME")
    plan_for(on_time, 90)
    no_plan = make_asset(hospital, "NOPLAN")  # sin plan
    return {
        "overdue": overdue, "due_soon": due_soon,
        "on_time": on_time, "no_plan": no_plan,
    }


@pytest.mark.django_db
class TestMaintenanceStatusFilter:
    def _codes(self, resp):
        return {a["code"] for a in resp.data["results"]}

    def test_sin_filtro_devuelve_los_cuatro(self, universo):
        resp = admin_client(None).get(reverse("assets-list"))
        assert self._codes(resp) == {"OVERDUE", "DUESOON", "ONTIME", "NOPLAN"}

    @pytest.mark.parametrize("categoria,esperado", [
        ("overdue", "OVERDUE"),
        ("due_soon", "DUESOON"),
        ("on_time", "ONTIME"),
        ("no_plan", "NOPLAN"),
    ])
    def test_cada_categoria_devuelve_su_activo(self, universo, categoria, esperado):
        resp = admin_client(None).get(
            reverse("assets-list"), {"maintenance_status": categoria}
        )
        assert self._codes(resp) == {esperado}

    def test_el_filtro_coincide_con_el_campo_calculado(self, universo):
        """Lo que devuelve el filtro es lo que el serializer pinta."""
        c = admin_client(None)
        for categoria in ("overdue", "due_soon", "on_time", "no_plan"):
            resp = c.get(reverse("assets-list"), {"maintenance_status": categoria})
            for row in resp.data["results"]:
                assert row["maintenance_status"] == categoria

    def test_hoy_cuenta_como_due_soon(self, hospital):
        """Frontera delta=0: mismo criterio que el serializer (delta <= 15)."""
        hoy = make_asset(hospital, "HOY")
        plan_for(hoy, 0)
        resp = admin_client(None).get(
            reverse("assets-list"), {"maintenance_status": "due_soon"}
        )
        assert "HOY" in self._codes(resp)

    def test_frontera_15_dias(self, hospital):
        make_asset_15 = make_asset(hospital, "DIA15")
        plan_for(make_asset_15, 15)
        make_asset_16 = make_asset(hospital, "DIA16")
        plan_for(make_asset_16, 16)
        c = admin_client(None)
        due = c.get(reverse("assets-list"), {"maintenance_status": "due_soon"})
        ontime = c.get(reverse("assets-list"), {"maintenance_status": "on_time"})
        assert "DIA15" in self._codes(due)
        assert "DIA16" in self._codes(ontime)

    def test_plan_inactivo_no_cuenta(self, hospital):
        """Un activo cuyo unico plan esta inactivo es no_plan, no on_time."""
        a = make_asset(hospital, "INACT")
        p = plan_for(a, 90)
        p.is_active = False
        p.save()
        resp = admin_client(None).get(
            reverse("assets-list"), {"maintenance_status": "no_plan"}
        )
        assert "INACT" in self._codes(resp)
