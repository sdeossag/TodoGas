"""
Al devolver una OT a correccion el tecnico asignado recibe push y correo con el
motivo; no se avisa en otras transiciones ni a quien se devuelve a si mismo.
"""

from unittest import mock

import pytest
from django.core import mail
from django.urls import reverse

from apps.notifications.models import NotificationLog
from apps.users.models import User
from apps.work_orders.models import WorkOrder
from apps.work_orders.tests.test_admin_ejecuta_y_corrige import (  # noqa: F401  (fixtures y ayudas)
    client_for,
    crear_ot,
    d,
    ejecutar,
    en_revision,
    make_user,
)
from django.test import TestCase

pytestmark = pytest.mark.django_db


def mover(user, wo_id, estado, comment=""):
    with TestCase.captureOnCommitCallbacks(execute=True):
        return client_for(user).post(
            reverse("work-orders-transition", kwargs={"pk": wo_id}),
            {"new_status": estado, "comment": comment}, format="json",
        )


def test_rechazar_avisa_al_tecnico_con_el_motivo(en_revision):
    e = en_revision
    mail.outbox.clear()
    r = mover(e["admin"], e["wo_id"], WorkOrder.Status.IN_PROGRESS, "Falta la foto del manómetro")
    assert r.status_code == 200, r.data
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == [e["tec"].email]
    assert "Falta la foto del manómetro" in msg.body
    assert WorkOrder.objects.get(pk=e["wo_id"]).wo_code in msg.subject
    assert "Zz Admin" in msg.body
    push = NotificationLog.objects.filter(user=e["tec"], entity_id=e["wo_id"]).latest("created_at")
    assert "Falta la foto del manómetro" in push.body


def test_otras_transiciones_no_avisan(d):
    tec = make_user(User.Role.TEC)
    wo_id = crear_ot(d, tec)
    mail.outbox.clear()
    ejecutar(client_for(tec), wo_id, d["campo"])  # iniciar y enviar a revision
    r = mover(d["admin"], wo_id, WorkOrder.Status.CANCELLED, "Ya no aplica")
    assert r.status_code == 200, r.data
    assert mail.outbox == []


def test_no_avisa_si_quien_rechaza_es_el_asignado(d):
    admin = d["admin"]
    wo_id = crear_ot(d, admin)
    ejecutar(client_for(admin), wo_id, d["campo"])
    mail.outbox.clear()
    r = mover(admin, wo_id, WorkOrder.Status.IN_PROGRESS, "Me faltó algo")
    assert r.status_code == 200, r.data
    assert mail.outbox == []


def test_un_fallo_de_envio_no_rompe_la_devolucion(en_revision):
    e = en_revision
    with mock.patch("apps.notifications.service.send_push_notification", side_effect=RuntimeError("fcm")), \
         mock.patch("apps.work_orders.tasks.EmailMessage.send", side_effect=RuntimeError("smtp")):
        r = mover(e["admin"], e["wo_id"], WorkOrder.Status.IN_PROGRESS, "Corrige el checklist")
    assert r.status_code == 200, r.data
    assert WorkOrder.objects.get(pk=e["wo_id"]).status == WorkOrder.Status.IN_PROGRESS


def test_last_rejection_en_la_lista_y_el_detalle(en_revision):
    e = en_revision
    c = client_for(e["tec"])
    def lista():
        return next(o for o in c.get(reverse("work-orders-list")).data["results"] if o["id"] == e["wo_id"])

    assert lista()["last_rejection"] is None  # en revision: aun no
    mover(e["admin"], e["wo_id"], WorkOrder.Status.IN_PROGRESS, "Foto borrosa")
    rej = lista()["last_rejection"]
    assert rej["motivo"] == "Foto borrosa" and rej["por"] == "Zz Admin" and rej["fecha"]
    det = c.get(reverse("work-orders-detail", kwargs={"pk": e["wo_id"]})).data
    assert det["last_rejection"]["motivo"] == "Foto borrosa"
    # Vuelve a revision: ya no esta vigente.
    mover(e["tec"], e["wo_id"], WorkOrder.Status.IN_REVIEW)
    assert lista()["last_rejection"] is None
