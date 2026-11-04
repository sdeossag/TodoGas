"""
Una OT historica (origin = FRACTTAL) es solo consulta: ningun punto de escritura
la modifica. Las OTs normales siguen funcionando igual.
"""

import base64
import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.work_orders.historica import MENSAJE_HISTORICA, es_historica
from apps.work_orders.models import Finding, WorkOrder
from apps.work_orders.tests.test_admin_ejecuta_y_corrige import (  # noqa: F401  (fixtures y ayudas)
    PNG_1PX,
    client_for,
    crear_ot,
    d,
    ejecutar,
    foto,
    make_user,
)
from apps.users.models import User

pytestmark = pytest.mark.django_db


def historica(d, estado=None):
    """OT nuestra convertida en historica, con checklist, para probar los bloqueos."""
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    WorkOrder.objects.filter(pk=wo_id).update(
        origin="FRACTTAL", fracttal_folio="123", external_executor="Juan Perez",
        **({"status": estado} if estado else {}),
    )
    return wo_id, tec


def _rechazada(r):
    assert r.status_code == 409, getattr(r, "data", r)
    assert r.data["detail"] == MENSAJE_HISTORICA


def test_es_historica():
    assert es_historica(WorkOrder(origin="FRACTTAL"))
    assert not es_historica(WorkOrder(origin=""))
    assert not es_historica(None)


def test_el_detalle_expone_origen_folio_y_ejecutor(d):
    wo_id, _ = historica(d)
    r = client_for(d["admin"]).get(reverse("work-orders-detail", kwargs={"pk": wo_id}))
    assert r.data["origin"] == "FRACTTAL"
    assert r.data["fracttal_folio"] == "123"
    assert r.data["external_executor"] == "Juan Perez"


def test_no_se_edita_ni_se_reasigna(d):
    wo_id, tec = historica(d)
    c = client_for(d["admin"])
    url = reverse("work-orders-detail", kwargs={"pk": wo_id})
    _rechazada(c.patch(url, {"title": "Otro"}, format="json"))
    _rechazada(c.post(reverse("work-orders-assign", kwargs={"pk": wo_id}),
                      {"assigned_to": str(tec.id)}, format="json"))
    assert WorkOrder.objects.get(pk=wo_id).title != "Otro"


def test_no_hay_transiciones_ni_cancelacion(d):
    wo_id, _ = historica(d)
    c = client_for(d["admin"])
    _rechazada(c.post(reverse("work-orders-transition", kwargs={"pk": wo_id}),
                      {"new_status": "IN_PROGRESS"}, format="json"))
    _rechazada(c.post(reverse("work-orders-cancel", kwargs={"pk": wo_id}),
                      {"comment": "x"}, format="json"))


def test_no_se_corrige_intervencion_ni_se_regenera_acta(d):
    wo_id, _ = historica(d, estado=WorkOrder.Status.IN_REVIEW)
    c = client_for(d["admin"])
    _rechazada(c.post(reverse("work-orders-correct-intervention", kwargs={"pk": wo_id}),
                      {"start": None, "end": None}, format="json"))
    WorkOrder.objects.filter(pk=wo_id).update(status=WorkOrder.Status.COMPLETED)
    _rechazada(c.post(reverse("work-orders-regenerate-report", kwargs={"pk": wo_id})))


def test_no_se_tocan_tareas_de_la_ot(d):
    wo_id, _ = historica(d)
    c = client_for(d["admin"])
    _rechazada(c.post(reverse("work-orders-tasks", kwargs={"pk": wo_id}), {"task_ids": []}, format="json"))
    _rechazada(c.post(reverse("work-orders-remove-task", kwargs={"pk": wo_id}), {"task_id": None}, format="json"))
    _rechazada(c.post(reverse("work-orders-task-checklist", kwargs={"pk": wo_id}), {}, format="json"))


def test_no_se_sube_ni_oculta_evidencia_ni_firma(d):
    wo_id, tec = historica(d, estado=WorkOrder.Status.IN_PROGRESS)
    c = client_for(d["admin"])
    _rechazada(foto(c, wo_id))
    r = c.post(reverse("evidence-signatures-list"), {
        "work_order": str(wo_id), "image_data": base64.b64encode(PNG_1PX).decode(),
        "signer_name": "X", "signature_type": "TECHNICIAN",
    }, format="json")
    _rechazada(r)
    # Una foto previa (la OT aun era nuestra) no se puede ocultar
    from apps.evidence.models import Photo
    WorkOrder.objects.filter(pk=wo_id).update(origin="")
    assert foto(c, wo_id).status_code == 201
    WorkOrder.objects.filter(pk=wo_id).update(origin="FRACTTAL")
    p = Photo.objects.get(work_order_id=wo_id)
    _rechazada(c.patch(reverse("evidence-photos-detail", kwargs={"pk": p.id}), {"hidden": True}, format="json"))
    assert not Photo.objects.get(pk=p.id).hidden


def test_no_se_escribe_el_checklist(d):
    wo_id, tec = historica(d, estado=WorkOrder.Status.IN_PROGRESS)
    c = client_for(d["admin"])
    cr = c.get(reverse("work-orders-detail", kwargs={"pk": wo_id})).data["tasks"][0]["checklist_response_id"]
    _rechazada(c.post(reverse("checklist-responses-submit-field", kwargs={"pk": cr}),
                      {"field": str(d["campo"].id), "value": "5"}, format="json"))
    _rechazada(c.post(reverse("checklist-responses-complete", kwargs={"pk": cr})))
    _rechazada(c.post(reverse("checklist-responses-block-count", kwargs={"pk": cr}),
                      {"group": "x", "count": 2}, format="json"))
    _rechazada(c.post(reverse("checklist-responses-set-pending", kwargs={"pk": cr}),
                      {"pendientes": []}, format="json"))
    WorkOrder.objects.filter(pk=wo_id).update(status=WorkOrder.Status.IN_REVIEW)
    _rechazada(c.post(reverse("checklist-responses-correct-field", kwargs={"pk": cr}),
                      {"field": str(d["campo"].id), "value": "5"}, format="json"))


def test_no_se_registran_hallazgos(d):
    wo_id, tec = historica(d, estado=WorkOrder.Status.IN_PROGRESS)
    r = client_for(d["admin"]).post(reverse("findings-list"), {
        "id": str(uuid.uuid4()), "work_order": wo_id, "asset": str(d["activo"].id),
        "description": "Fuga", "severity": "HIGH", "reported_at": timezone.now().isoformat(),
    }, format="json")
    _rechazada(r)
    assert Finding.objects.count() == 0


def test_una_ot_normal_sigue_funcionando(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    c = client_for(tec)
    ejecutar(c, wo_id, d["campo"])
    a = client_for(d["admin"])
    assert a.patch(reverse("work-orders-detail", kwargs={"pk": wo_id}), {"title": "Nuevo"}, format="json").status_code == 200
    assert a.post(reverse("work-orders-assign", kwargs={"pk": wo_id}),
                  {"assigned_to": str(tec.id)}, format="json").status_code == 200
    assert foto(a, wo_id).status_code == 201


def test_el_detalle_cuenta_las_fotos_que_quedaron_en_fracttal(d):
    wo_id, _ = historica(d)
    WorkOrder.objects.filter(pk=wo_id).update(fracttal_data={"fotos_pendientes": 4, "rutas": ["x"]})
    r = client_for(d["admin"]).get(reverse("work-orders-detail", kwargs={"pk": wo_id}))
    assert r.data["fracttal_photos_pending"] == 4
    assert "fracttal_data" not in r.data
    normal = crear_ot(d, None)
    r = client_for(d["admin"]).get(reverse("work-orders-detail", kwargs={"pk": normal}))
    assert r.data["fracttal_photos_pending"] == 0
