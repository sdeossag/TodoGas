"""
El reporte consolidado se envia por correo a quien lo pidio (REV-31, issue #145).
El PDF va adjunto si pesa menos de settings.REPORTS_EMAIL_MAX_BYTES; si no, va el enlace.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.core import mail
from django.test import override_settings

from apps.assets.models import Hospital
from apps.reports.tasks import generate_consolidated_report
from apps.users.models import User

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 consolidado de prueba"
DESDE, HASTA = "2026-01-01", "2026-01-31"


def _usuario(correo=None):
    usuario = User.objects.create_user(
        email=correo or f"{uuid.uuid4()}@test.com",
        password="x",
        first_name="Samuel",
        last_name="Deossa",
        role=User.Role.ADMIN,
    )
    if correo == "":
        User.objects.filter(pk=usuario.pk).update(email="")
        usuario.refresh_from_db()
    return usuario


def _html_falso():
    """Sustituye a WeasyPrint: devuelve el PDF de prueba sin renderizar nada."""
    html = MagicMock()
    html.return_value.write_pdf.return_value = PDF
    return patch("weasyprint.HTML", html)


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(
        name="Hospital Central", code=uuid.uuid4().hex[:8], contact_email="h@hosp.co",
    )


def test_envia_el_pdf_adjunto_al_solicitante(hospital):
    admin = _usuario("admin.pdf@test.com")
    with _html_falso():
        resultado = generate_consolidated_report(
            hospital_id=str(hospital.id), date_from=DESDE, date_to=HASTA,
            requested_by_id=str(admin.id),
        )

    assert resultado["status"] == "done"
    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.to == ["admin.pdf@test.com"]
    assert correo.subject == f"Reporte consolidado Hospital Central {DESDE}–{HASTA}"
    assert correo.content_subtype == "html"
    assert "Hola Samuel" in correo.body
    adjuntos = correo.attachments
    assert len(adjuntos) == 1
    nombre, contenido, tipo = adjuntos[0]
    assert nombre == f"consolidado_{DESDE}_{HASTA}.pdf"
    assert contenido == PDF
    assert tipo == "application/pdf"


def test_sin_hospital_el_asunto_dice_todos_los_hospitales():
    admin = _usuario("admin.todos@test.com")
    with _html_falso():
        generate_consolidated_report(
            hospital_id=None, date_from=DESDE, date_to=HASTA, requested_by_id=str(admin.id),
        )

    assert mail.outbox[0].subject == f"Reporte consolidado todos los hospitales {DESDE}–{HASTA}"


@override_settings(REPORTS_EMAIL_MAX_BYTES=10)
def test_pdf_mayor_que_el_limite_va_como_enlace():
    admin = _usuario("admin.enlace@test.com")
    with _html_falso():
        generate_consolidated_report(
            hospital_id=None, date_from=DESDE, date_to=HASTA, requested_by_id=str(admin.id),
        )

    correo = mail.outbox[0]
    assert correo.attachments == []
    assert "Descargar reporte" in correo.body
    assert f'href="{settings.FRONTEND_URL}/reportes"' in correo.body


def test_sin_correo_del_solicitante_no_se_envia():
    sin_correo = _usuario("")
    with _html_falso(), patch("apps.reports.tasks.logger") as log:
        resultado = generate_consolidated_report(
            hospital_id=None, date_from=DESDE, date_to=HASTA,
            requested_by_id=str(sin_correo.id),
        )

    assert resultado["status"] == "done"
    assert mail.outbox == []
    log.warning.assert_called_once()


def test_sin_solicitante_no_se_envia():
    with _html_falso():
        resultado = generate_consolidated_report(
            hospital_id=None, date_from=DESDE, date_to=HASTA, requested_by_id=None,
        )

    assert resultado["status"] == "done"
    assert mail.outbox == []


def test_si_la_generacion_falla_avisa_al_solicitante_y_relanza():
    admin = _usuario("admin.fallo@test.com")
    html = MagicMock()
    html.return_value.write_pdf.side_effect = RuntimeError("weasyprint roto")
    with patch("weasyprint.HTML", html):
        with pytest.raises(RuntimeError, match="weasyprint roto"):
            generate_consolidated_report(
                hospital_id=None, date_from=DESDE, date_to=HASTA,
                requested_by_id=str(admin.id),
            )

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.to == ["admin.fallo@test.com"]
    assert correo.subject.startswith("No se pudo generar el reporte consolidado")
    assert correo.attachments == []
    assert "No fue posible generar" in correo.body


def test_si_falla_el_aviso_no_tapa_el_error_original():
    admin = _usuario("admin.doble@test.com")
    html = MagicMock()
    html.return_value.write_pdf.side_effect = RuntimeError("error original")
    with patch("weasyprint.HTML", html), patch(
        "apps.reports.tasks.EmailMessage.send", side_effect=OSError("smtp caido")
    ):
        with pytest.raises(RuntimeError, match="error original"):
            generate_consolidated_report(
                hospital_id=None, date_from=DESDE, date_to=HASTA,
                requested_by_id=str(admin.id),
            )
