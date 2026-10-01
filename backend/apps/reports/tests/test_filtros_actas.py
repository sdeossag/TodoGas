"""
Filtrar las actas por hospital en Reportes (audio3 07:12: "los puedo mirar...
por hospital"). Un valor mal formado no encuentra nada, en vez de un 500.
"""

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.testing import make_work_order
from apps.reports.models import GeneratedReport
from apps.users.models import User

pytestmark = pytest.mark.django_db
URL = "/api/reports/"


@pytest.fixture
def d():
    admin = User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=User.Role.ADMIN,
    )
    h1 = Hospital.objects.create(name="H1", code=uuid.uuid4().hex[:8])
    h2 = Hospital.objects.create(name="H2", code=uuid.uuid4().hex[:8])

    def acta(h, titulo):
        a = Asset.objects.create(hospital=h, name="Toma", code=uuid.uuid4().hex[:8])
        wo = make_work_order(a, admin, status="COMPLETED", title=titulo)
        GeneratedReport.objects.create(
            work_order=wo, title=titulo, file_url="x.pdf", file_hash="h", generated_at=timezone.now(),
        )
        return wo

    actas = {"a1": acta(h1, "a1"), "a2": acta(h1, "a2"), "b1": acta(h2, "b1")}
    c = APIClient()
    c.force_authenticate(user=admin)
    return {"c": c, "h1": h1, "h2": h2, "actas": actas}


def titulos(d, **params):
    r = d["c"].get(URL, params)
    assert r.status_code == 200, r.data
    datos = r.data["results"] if isinstance(r.data, dict) else r.data
    return sorted(x["title"] for x in datos)


def test_por_hospital(d):
    assert titulos(d) == ["a1", "a2", "b1"]
    assert titulos(d, hospital_id=d["h1"].id) == ["a1", "a2"]
    assert titulos(d, hospital_id=d["h2"].id) == ["b1"]


def test_por_numero_acepta_el_codigo_completo(d):
    wo = d["actas"]["a2"]
    assert titulos(d, wo_number=wo.wo_number) == ["a2"]
    assert titulos(d, wo_number=wo.wo_code) == ["a2"]


def test_valores_mal_formados_no_rompen(d):
    for params in ({"hospital_id": "x"}, {"work_order": "x"}, {"wo_number": "abc"},
                   {"date_from": "2026-13-45"}, {"date_to": "ayer"}):
        assert titulos(d, **params) == [], params
