"""
Reenviar varias actas por correo con un clic: POST /api/reports/resend-email/.
Los PDF van adjuntos y se reparten en varios correos si pesan mas que
settings.REPORTS_EMAIL_MAX_BYTES; un PDF que solo ya lo supera va como enlace.
"""

import uuid
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assets.models import Asset, Hospital
from apps.maintenance.testing import make_work_order
from apps.reports.models import GeneratedReport, ReportSendLog
from apps.reports.tasks import send_reports_bundle
from apps.users.models import User

pytestmark = pytest.mark.django_db
URL = "/api/reports/resend-email/"


def _usuario(rol):
    return User.objects.create_user(
        email=f"{uuid.uuid4()}@t.co", password="x", first_name="A", last_name="B", role=rol,
    )


@pytest.fixture
def d():
    admin = _usuario(User.Role.ADMIN)
    h1 = Hospital.objects.create(name="H1", code=uuid.uuid4().hex[:8], contact_email="h1@hosp.co", contact_name="Ana")
    h2 = Hospital.objects.create(name="H2", code=uuid.uuid4().hex[:8], contact_email="h2@hosp.co")
    h3 = Hospital.objects.create(name="H3 sin correo", code=uuid.uuid4().hex[:8])

    def acta(h, tam=100):
        a = Asset.objects.create(hospital=h, name="Toma", code=uuid.uuid4().hex[:8])
        wo = make_work_order(a, admin, status="COMPLETED")
        ruta = default_storage.save(f"reports/{uuid.uuid4().hex}.pdf", ContentFile(b"%PDF" + b"x" * (tam - 4)))
        return GeneratedReport.objects.create(
            work_order=wo, title="t", file_url=ruta, file_hash="h", generated_at=timezone.now(),
        )

    c = APIClient()
    c.force_authenticate(user=admin)
    return {"c": c, "h1": h1, "h2": h2, "h3": h3, "acta": acta, "admin": admin}


def _ids(*actas):
    return {"report_ids": [str(a.id) for a in actas]}


def test_agrupa_por_hospital_un_correo_con_adjuntos(d):
    a1, a2, b1 = d["acta"](d["h1"]), d["acta"](d["h1"]), d["acta"](d["h2"])
    r = d["c"].post(URL, _ids(a1, b1, a2), format="json")
    assert r.status_code == 202, r.data
    assert r.data["skipped"] == []
    assert {(q["hospital"], q["to"], q["count"]) for q in r.data["queued"]} == {
        ("H1", "h1@hosp.co", 2), ("H2", "h2@hosp.co", 1),
    }
    assert len(mail.outbox) == 2
    por_dest = {m.to[0]: m for m in mail.outbox}
    m1 = por_dest["h1@hosp.co"]
    assert m1.subject == "Actas de servicio - H1"
    assert sorted(a[0] for a in m1.attachments) == sorted(
        [f"{a1.work_order.wo_code}.pdf", f"{a2.work_order.wo_code}.pdf"]
    )
    assert a1.work_order.wo_code in m1.body
    assert len(por_dest["h2@hosp.co"].attachments) == 1


def test_logs_por_acta(d):
    a1, a2 = d["acta"](d["h1"]), d["acta"](d["h1"])
    d["c"].post(URL, _ids(a1, a2), format="json")
    logs = ReportSendLog.objects.all()
    assert logs.count() == 2
    assert all(lg.was_successful and lg.recipient_email == "h1@hosp.co" for lg in logs)
    assert {lg.report_id for lg in logs} == {a1.id, a2.id}


@override_settings(REPORTS_EMAIL_MAX_BYTES=250)
def test_reparte_en_varios_lotes(d):
    actas = [d["acta"](d["h1"], tam=100) for _ in range(5)]  # 2 por lote -> 3 correos
    r = d["c"].post(URL, _ids(*actas), format="json")
    assert r.status_code == 202
    assert len(mail.outbox) == 3
    assert [m.subject for m in mail.outbox] == [
        "Actas de servicio - H1 (1 de 3)", "Actas de servicio - H1 (2 de 3)", "Actas de servicio - H1 (3 de 3)",
    ]
    assert [len(m.attachments) for m in mail.outbox] == [2, 2, 1]
    for m in mail.outbox:
        assert sum(len(a[1]) for a in m.attachments) <= 250
    assert ReportSendLog.objects.filter(was_successful=True).count() == 5


@override_settings(REPORTS_EMAIL_MAX_BYTES=250)
def test_pdf_mayor_al_limite_va_como_enlace(d):
    chico, grande = d["acta"](d["h1"], tam=100), d["acta"](d["h1"], tam=1000)
    d["c"].post(URL, _ids(chico, grande), format="json")
    assert len(mail.outbox) == 1
    m = mail.outbox[0]
    assert [a[0] for a in m.attachments] == [f"{chico.work_order.wo_code}.pdf"]
    assert "descargar el acta" in m.body
    assert f"/ordenes/{grande.work_order_id}" in m.body
    assert ReportSendLog.objects.filter(was_successful=True).count() == 2


def test_hospital_sin_correo_va_a_skipped(d):
    a1, c1 = d["acta"](d["h1"]), d["acta"](d["h3"])
    r = d["c"].post(URL, _ids(a1, c1), format="json")
    assert r.status_code == 202
    assert [q["hospital"] for q in r.data["queued"]] == ["H1"]
    assert r.data["skipped"] == [{
        "report_id": str(c1.id),
        "wo_code": c1.work_order.wo_code,
        "hospital": "H3 sin correo",
        "reason": "El hospital no tiene correo de contacto",
    }]
    assert len(mail.outbox) == 1


def test_ids_repetidos_se_deduplican(d):
    a1 = d["acta"](d["h1"])
    r = d["c"].post(URL, {"report_ids": [str(a1.id), str(a1.id)]}, format="json")
    assert r.data["queued"][0]["count"] == 1
    assert len(mail.outbox[0].attachments) == 1


def test_no_admin_recibe_403(d):
    a1 = d["acta"](d["h1"])
    for rol in (User.Role.CLI, User.Role.SUP):
        c = APIClient()
        c.force_authenticate(user=_usuario(rol))
        assert c.post(URL, _ids(a1), format="json").status_code == 403
    assert mail.outbox == []


def test_mas_de_50_ids_o_vacio_da_400(d):
    assert d["c"].post(URL, {"report_ids": [str(uuid.uuid4()) for _ in range(51)]}, format="json").status_code == 400
    assert d["c"].post(URL, {"report_ids": []}, format="json").status_code == 400
    assert d["c"].post(URL, {}, format="json").status_code == 400


def test_ids_inexistentes_o_mal_formados_dan_400(d):
    a1 = d["acta"](d["h1"])
    ajeno = uuid.uuid4()
    r = d["c"].post(URL, {"report_ids": [str(a1.id), str(ajeno)]}, format="json")
    assert r.status_code == 400
    assert r.data["missing_ids"] == [str(ajeno)]
    assert d["c"].post(URL, {"report_ids": ["x"]}, format="json").status_code == 400
    assert mail.outbox == []


def test_acta_sin_ot_da_400(d):
    consolidado = GeneratedReport.objects.create(
        title="c", report_type="CUSTOM", file_url="x.pdf", file_hash="h", generated_at=timezone.now(),
    )
    r = d["c"].post(URL, _ids(consolidado), format="json")
    # Sin OT el alcance de hospital la deja fuera del queryset o la rechaza: 400 en ambos casos.
    assert r.status_code == 400


def test_un_lote_fallido_no_reenvia_los_ya_enviados(d):
    with override_settings(REPORTS_EMAIL_MAX_BYTES=250):
        actas = [d["acta"](d["h1"], tam=100) for _ in range(4)]  # 2 lotes de 2
        original = mail.EmailMessage.send
        llamadas = {"n": 0}

        def send_falla_el_segundo(self, *a, **k):
            llamadas["n"] += 1
            if llamadas["n"] == 2:
                raise RuntimeError("smtp caido")
            return original(self, *a, **k)

        with patch.object(mail.EmailMessage, "send", send_falla_el_segundo):
            res = send_reports_bundle.apply(args=(str(d["h1"].id), [str(a.id) for a in actas])).result

    assert len(mail.outbox) == 1
    assert res["status"] == "partial"
    assert res["failed_report_ids"] == [str(actas[2].id), str(actas[3].id)]
    ok = ReportSendLog.objects.filter(was_successful=True)
    ko = ReportSendLog.objects.filter(was_successful=False)
    assert {lg.report_id for lg in ok} == {actas[0].id, actas[1].id}
    assert {lg.report_id for lg in ko} == {actas[2].id, actas[3].id}
    assert all("smtp caido" in lg.error_message for lg in ko)
