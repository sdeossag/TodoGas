"""
Contrato de paginacion de la API.

Sin un DEFAULT_PAGINATION_CLASS global, /api/assets/ devolvia los ~3.940
activos en una sola respuesta, contra RF-AC-05 (50 por pagina, configurable a
100) y RNF-REN-01 (500 ms). Estos tests fijan el contrato para que no se pueda
desactivar por descuido, y para que un endpoint de lista nuevo lo herede.
"""

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.users.models import User


@pytest.fixture
def admin_client(db):
    client = APIClient()
    client.force_authenticate(user=baker.make(User, role=User.Role.ADMIN, is_active=True))
    return client


@pytest.fixture
def many_assets(db):
    hospital = baker.make(Hospital, is_active=True)
    Asset.objects.bulk_create(
        Asset(
            hospital=hospital,
            name=f"Equipo {i:03d}",
            code=f"EQ-{i:04d}",
            status=Asset.Status.ACTIVE,
        )
        for i in range(120)
    )
    return hospital


@pytest.mark.django_db
class TestPaginationContract:
    def test_respuesta_trae_la_envoltura_paginada(self, admin_client, many_assets):
        resp = admin_client.get(reverse("assets-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data) >= {"count", "next", "previous", "results"}
        assert resp.data["count"] == 120

    def test_pagina_por_defecto_son_50(self, admin_client, many_assets):
        resp = admin_client.get(reverse("assets-list"))
        assert len(resp.data["results"]) == 50, "RF-AC-05 fija 50 por defecto"
        assert resp.data["next"] is not None

    def test_page_size_es_configurable(self, admin_client, many_assets):
        resp = admin_client.get(reverse("assets-list"), {"page_size": 100})
        assert len(resp.data["results"]) == 100, "RF-AC-05 pide poder subir a 100"

    def test_page_size_tiene_tope(self, admin_client, many_assets):
        """Sin tope, ?page_size=100000 reabre el agujero que esto cierra."""
        resp = admin_client.get(reverse("assets-list"), {"page_size": 100000})
        assert len(resp.data["results"]) == 120  # topado a 200, hay 120
        resp = admin_client.get(reverse("assets-list"), {"page_size": 100000, "page": 2})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_segunda_pagina_devuelve_el_resto(self, admin_client, many_assets):
        first = admin_client.get(reverse("assets-list")).data
        second = admin_client.get(reverse("assets-list"), {"page": 2}).data
        assert len(second["results"]) == 50
        assert second["previous"] is not None
        ids_first = {a["id"] for a in first["results"]}
        ids_second = {a["id"] for a in second["results"]}
        assert not (ids_first & ids_second), "las paginas no pueden solaparse"

    def test_recorrer_todas_las_paginas_devuelve_el_total(self, admin_client, many_assets):
        """Es lo que hace fetchAllPages() en el frontend."""
        seen, page = set(), 1
        while True:
            data = admin_client.get(
                reverse("assets-list"), {"page": page, "page_size": 200}
            ).data
            seen.update(a["id"] for a in data["results"])
            if not data["next"]:
                break
            page += 1
        assert len(seen) == 120
