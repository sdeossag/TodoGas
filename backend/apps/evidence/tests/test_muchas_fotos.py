"""
Una OT con muchas fotos: INVIMA pide foto de casi todo y hay reportes de hasta
95. No hay tope de fotos por OT, y subir, listar, abrir la OT y enviarla a
revision cuestan las mismas consultas con 1 foto que con 95 (nada por foto).
"""
import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.evidence.models import Photo, Signature
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.work_orders.tests.test_admin_ejecuta_y_corrige import (  # noqa: F401
    PNG_1PX, client_for, crear_ot, d, foto, make_user, transicion,
)

pytestmark = pytest.mark.django_db

INVIMA = 95


def _preparar(d, settings, tmp_path):
    """Una OT en proceso con el checklist cerrado y la firma: solo faltan las fotos."""
    settings.MEDIA_ROOT = str(tmp_path)
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    c = client_for(tec)
    assert transicion(c, wo_id, WorkOrder.Status.IN_PROGRESS).status_code == 200
    cr = c.get(reverse("work-orders-detail", kwargs={"pk": wo_id})).data["tasks"][0]["checklist_response_id"]
    r = c.post(reverse("checklist-responses-submit-field", kwargs={"pk": cr}),
               {"field": str(d["campo"].id), "value": "50"}, format="json")
    assert r.status_code == 200, r.data
    assert c.post(reverse("checklist-responses-complete", kwargs={"pk": cr})).status_code == 200
    r = c.post(reverse("evidence-signatures-list"), {
        "work_order": str(wo_id), "image_data": base64.b64encode(PNG_1PX).decode(),
        "signer_name": "Quien ejecuta", "signature_type": Signature.SignatureType.TECHNICIAN,
    }, format="json")
    assert r.status_code == 201, r.data
    return c, wo_id


def _consultas(fn):
    with CaptureQueriesContext(connection) as q:
        resp = fn()
    return resp, len(q)


def _subir(c, wo_id, n):
    """Sube n fotos; devuelve las consultas de la primera y de la ultima."""
    q = []
    for i in range(n):
        resp, nq = _consultas(lambda: c.post(reverse("evidence-photos-list"), {
            "work_order": str(wo_id),
            "file": SimpleUploadedFile(f"f{i}.png", PNG_1PX, content_type="image/png"),
            "taken_at": "2026-10-23T10:00:00Z",
            "caption": f"foto {i}",
            "stage": "BEFORE" if i % 2 else "AFTER",
        }, format="multipart"))
        assert resp.status_code == 201, resp.data
        q.append(nq)
    return q[0], q[-1]


def test_95_fotos_en_una_ot_suben_sin_tope_y_sin_consultas_extra(d, settings, tmp_path):
    c, wo_id = _preparar(d, settings, tmp_path)

    primera, ultima = _subir(c, wo_id, INVIMA)

    # La foto 95 cuesta lo mismo que la 1: ni un tope, ni una busqueda que crezca.
    assert Photo.objects.filter(work_order_id=wo_id).count() == INVIMA
    assert ultima == primera


def test_listar_y_abrir_la_ot_con_95_fotos_cuesta_lo_mismo_que_con_una(d, settings, tmp_path):
    c1, wo1 = _preparar(d, settings, tmp_path)
    _subir(c1, wo1, 1)
    c95, wo95 = _preparar(d, settings, tmp_path)
    _subir(c95, wo95, INVIMA)

    lista_url = reverse("evidence-photos-list")
    r1, lista_1 = _consultas(lambda: c1.get(lista_url, {"work_order": str(wo1)}))
    r95, lista_95 = _consultas(lambda: c95.get(lista_url, {"work_order": str(wo95)}))
    assert len(r1.data) == 1
    assert len(r95.data) == INVIMA, "la lista devuelve todas, sin paginar ni cortar"
    assert lista_95 == lista_1

    detalle = lambda cl, w: cl.get(reverse("work-orders-detail", kwargs={"pk": w}))  # noqa: E731
    dr1, det_1 = _consultas(lambda: detalle(c1, wo1))
    dr95, det_95 = _consultas(lambda: detalle(c95, wo95))
    assert dr95.data["photos_count"] == INVIMA
    assert det_95 == det_1


def test_enviar_a_revision_con_95_fotos_cuesta_lo_mismo_que_con_una(d, settings, tmp_path):
    c1, wo1 = _preparar(d, settings, tmp_path)
    _subir(c1, wo1, 1)
    c95, wo95 = _preparar(d, settings, tmp_path)
    _subir(c95, wo95, INVIMA)

    r1, tr_1 = _consultas(lambda: transicion(c1, wo1, WorkOrder.Status.IN_REVIEW))
    r95, tr_95 = _consultas(lambda: transicion(c95, wo95, WorkOrder.Status.IN_REVIEW))

    assert r1.status_code == 200, r1.data
    assert r95.status_code == 200, r95.data
    assert r95.data["status"] == WorkOrder.Status.IN_REVIEW
    assert r95.data["photos_count"] == INVIMA
    assert tr_95 == tr_1
