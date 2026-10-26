"""
Los campos Foto y Firma salen del checklist (audio3 05:10): la OT ya tiene fotos
de evidencia y firmas. El backend rechaza versiones NUEVAS con esos tipos; las
ya publicadas son inmutables y siguen funcionando como siempre.
"""

import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from apps.checklists.models import ChecklistField, ChecklistTemplate, ChecklistTemplateVersion
from apps.checklists.validators import validate_field_value
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return User.objects.create_user(email="admin@sfs.test", password="x", role="ADMIN", is_active=True)


@pytest.fixture
def cliente(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


@pytest.fixture
def plantilla():
    return baker.make(ChecklistTemplate, name="Gases", is_active=True)


def publicar(cliente, plantilla, campos):
    return cliente.post(
        f"/api/checklists/templates/{plantilla.id}/publish-version/",
        {"checklist_fields": campos}, format="json",
    )


def campo(label, tipo, orden=0):
    return {"label": label, "field_type": tipo, "is_required": False, "sort_order": orden}


@pytest.mark.parametrize("tipo", ["PHOTO", "SIGNATURE"])
def test_no_se_publica_una_version_con_foto_o_firma(cliente, plantilla, tipo):
    r = publicar(cliente, plantilla, [campo("Presión", "NUMBER"), campo("Evidencia", tipo, 1)])
    assert r.status_code == 400, r.data
    assert plantilla.versions.count() == 0, "no queda una version a medias"


def test_el_mensaje_explica_que_foto_y_firma_van_en_la_ot(cliente, plantilla):
    r = publicar(cliente, plantilla, [campo("Firma", "SIGNATURE")])
    assert r.status_code == 400
    texto = str(r.data).lower()
    assert "firma" in texto and "ot" in texto


def test_publicar_sin_foto_ni_firma_sigue_funcionando(cliente, plantilla):
    r = publicar(cliente, plantilla, [
        campo("Presión", "NUMBER"), campo("Observaciones", "TEXTAREA", 1), campo("Conforme", "BOOLEAN", 2),
    ])
    assert r.status_code == 201, r.data
    assert len(r.data["checklist_fields"]) == 3


def test_una_version_vieja_con_foto_y_firma_sigue_intacta_y_se_puede_leer(cliente, plantilla, admin):
    # Publicada antes de la decision: se crea directo, como estaba en la base.
    vieja = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1,
                       is_current=True, published_by=admin)
    f_foto = baker.make(ChecklistField, version=vieja, label="Foto", field_type="PHOTO", sort_order=0)
    baker.make(ChecklistField, version=vieja, label="Firma", field_type="SIGNATURE", sort_order=1)

    r = cliente.get(f"/api/checklists/templates/{plantilla.id}/")
    assert r.status_code == 200
    tipos = [f["field_type"] for f in r.data["versions"][0]["checklist_fields"]]
    assert tipos == ["PHOTO", "SIGNATURE"]
    # Y el validador de respuestas sigue aceptando sus valores.
    validate_field_value(f_foto, "foto:123")

    # Hacerla vigente de nuevo tampoco se bloquea: es una version ya publicada.
    nueva = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=2,
                       is_current=False, published_by=admin)
    r = cliente.post(f"/api/checklists/templates/{plantilla.id}/set-current/", {"version_id": str(nueva.id)})
    assert r.status_code == 200
    r = cliente.post(f"/api/checklists/templates/{plantilla.id}/set-current/", {"version_id": str(vieja.id)})
    assert r.status_code == 200


def test_duplicar_una_version_vieja_no_arrastra_foto_ni_firma(cliente, plantilla, admin):
    """
    Duplicar = publicar una version nueva con los campos de la anterior. El
    servidor no distingue "heredado" de "nuevo": rechaza el tipo siempre, y el
    editor es quien avisa y quita esos campos antes de publicar.
    """
    vieja = baker.make(ChecklistTemplateVersion, template=plantilla, version_number=1,
                       is_current=True, published_by=admin)
    baker.make(ChecklistField, version=vieja, label="Presión", field_type="NUMBER", sort_order=0)
    baker.make(ChecklistField, version=vieja, label="Foto", field_type="PHOTO", sort_order=1)

    heredados = [
        {"label": f.label, "field_type": f.field_type, "is_required": f.is_required, "sort_order": f.sort_order}
        for f in vieja.fields.order_by("sort_order")
    ]
    assert publicar(cliente, plantilla, heredados).status_code == 400
    sin_foto = [f for f in heredados if f["field_type"] != "PHOTO"]
    r = publicar(cliente, plantilla, sin_foto)
    assert r.status_code == 201, r.data
    assert r.data["version_number"] == 2
    # La anterior no se toco.
    assert vieja.fields.count() == 2
