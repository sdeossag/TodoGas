import hashlib
import logging

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from apps.maintenance.models import task_type_label
from apps.work_orders.models import WorkOrder

from .failures import record_report_failure
from .generator import field_facts, generate_service_report_pdf
from .models import GeneratedReport, ReportSendLog
from .utils import get_logo_base64

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_work_order_pdf(self, work_order_id):
    try:
        work_order = WorkOrder.objects.select_related(
            "hospital", "assigned_to"
        ).get(id=work_order_id)

        _pdf_bytes, file_url, _report_hash = generate_service_report_pdf(work_order)

        send_report_email.delay(work_order_id)

        return {"status": "ok", "file_url": file_url}
    except Exception as exc:
        # En desarrollo las tareas corren en modo eager con EAGER_PROPAGATES a
        # False: sin este log el fallo no aparece en ningun sitio y la OT queda
        # completada pero sin PDF, con la pestaña Reportes girando en vacio.
        logger.exception(
            "No se pudo generar el PDF de la OT %s: %s", work_order_id, exc
        )

        # En modo eager (desarrollo, CELERY_TASK_ALWAYS_EAGER) self.retry() NO
        # reintenta: levanta Retry, y apply() la traga porque EAGER_PROPAGATES
        # esta en False. `retries` nunca crecia, asi que la rama de abajo no se
        # alcanzaba jamas y el fallo no quedaba registrado en ningun sitio: la
        # OT se cerraba sin acta y sin rastro. Por eso la condicion no es "ya
        # agote los reintentos" sino "no va a haber otro intento".
        will_retry = (
            not self.request.is_eager
            and self.request.retries < self.max_retries
        )
        if not will_retry:
            # El log del servidor deja de ser el unico sitio donde consta:
            # queda en la traza de auditoria, que si tiene interfaz, y el
            # detalle de la OT lo expone como report_status='failed' para
            # avisar y ofrecer el reintento manual.
            record_report_failure(work_order_id, exc)
            return {"status": "failed", "error": str(exc)}

        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(bind=True, max_retries=3)
def send_report_email(self, work_order_id):
    report = None
    recipient_email = ""
    try:
        work_order = WorkOrder.objects.select_related(
            "hospital", "assigned_to"
        ).get(id=work_order_id)
        hospital = work_order.hospital

        report = GeneratedReport.objects.filter(
            work_order=work_order
        ).latest("generated_at")

        if not hospital.contact_email:
            return {"status": "skipped", "reason": "no email"}

        recipient_email = hospital.contact_email

        activos = _assets_label(work_order)
        subject = f"Reporte de servicio - {work_order.wo_code} | {activos or work_order.title}"
        body = render_to_string(
            "reports/email_report.html",
            {
                "work_order": work_order,
                "assets_label": activos,
                "hospital": hospital,
                "report": report,
                "frontend_url": settings.FRONTEND_URL,
                # Lo mismo que dice el acta: cuando y quien, segun el campo.
                **field_facts(work_order),
            },
        )

        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.content_subtype = "html"
        msg.send()

        ReportSendLog.objects.create(
            report=report,
            recipient_email=recipient_email,
            recipient_name=hospital.contact_name or "",
            was_successful=True,
        )
        return {"status": "sent", "to": recipient_email}

    except Exception as exc:
        if report is not None and recipient_email:
            ReportSendLog.objects.create(
                report=report,
                recipient_email=recipient_email,
                was_successful=False,
                error_message=str(exc),
            )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


def _url_del_acta(report):
    """Enlace al PDF si el almacenamiento da uno absoluto; si no, a la OT en la plataforma."""
    try:
        url = default_storage.url(report.file_url)
    except Exception:
        url = ""
    if url.startswith("http"):
        return url
    return f"{settings.FRONTEND_URL}/ordenes/{report.work_order_id}"


def _armar_lotes(items, limite):
    """
    Reparte las actas en lotes cuyos adjuntos suman <= limite. Un PDF que solo
    ya supera el limite no se adjunta (item["pdf"] = None): viaja como enlace
    en el lote abierto en ese momento.
    """
    lotes, actual, peso = [], [], 0
    for item in items:
        if len(item["pdf"]) > limite:
            item["pdf"] = None
            item["oversize"] = True
            actual.append(item)
            continue
        tam = len(item["pdf"])
        if actual and peso + tam > limite:
            lotes.append(actual)
            actual, peso = [], 0
        actual.append(item)
        peso += tam
    if actual:
        lotes.append(actual)
    return lotes


@shared_task(bind=True, max_retries=3)
def send_reports_bundle(self, hospital_id, report_ids):
    """
    Reenvia varias actas de un hospital con los PDF adjuntos, en uno o varios
    correos segun settings.REPORTS_EMAIL_MAX_BYTES.

    Reintentos: se procesa lote a lote; los lotes enviados no se repiten. Si
    alguno falla, se anota el fallo en ReportSendLog de sus actas y el reintento
    se encola solo con las actas de los lotes fallidos (args nuevos), asi nunca
    se reenvia lo que ya salio. Sin reintentos disponibles (o en modo eager) se
    devuelve el resumen con lo que fallo.
    """
    from apps.assets.models import Hospital

    hospital = Hospital.objects.get(id=hospital_id)
    if not hospital.contact_email:
        return {"status": "skipped", "reason": "no email"}
    to = hospital.contact_email

    reportes = {
        str(r.id): r
        for r in GeneratedReport.objects.filter(id__in=report_ids).select_related("work_order")
    }
    items, ilegibles = [], []
    nombres = set()
    for rid in report_ids:
        r = reportes.get(str(rid))
        if r is None or r.work_order_id is None:
            continue
        try:
            with default_storage.open(r.file_url, "rb") as f:
                pdf = f.read()
        except Exception as exc:
            logger.exception("No se pudo leer el PDF del acta %s: %s", rid, exc)
            ilegibles.append((r, str(exc)))
            continue
        wo = r.work_order
        nombre = f"{wo.wo_code}.pdf"
        if nombre in nombres:
            nombre = f"{wo.wo_code}-{str(r.id)[:8]}.pdf"
        nombres.add(nombre)
        items.append({"report": r, "wo": wo, "pdf": pdf, "name": nombre, "oversize": False})

    lotes = _armar_lotes(items, settings.REPORTS_EMAIL_MAX_BYTES)
    enviados, lotes_fallidos = 0, []
    for i, lote in enumerate(lotes, start=1):
        asunto = f"Actas de servicio - {hospital.name}"
        if len(lotes) > 1:
            asunto += f" ({i} de {len(lotes)})"
        try:
            filas = []
            for it in lote:
                wo = it["wo"]
                inicio = (field_facts(wo).get("field_work") or {}).get("start")
                filas.append({
                    "wo_code": wo.wo_code,
                    "assets": _assets_label(wo) or wo.title,
                    "date": inicio or wo.scheduled_date,
                    "link": _url_del_acta(it["report"]) if it["oversize"] else "",
                })
            body = render_to_string(
                "reports/email_reports_bundle.html",
                {
                    "hospital": hospital,
                    "items": filas,
                    "frontend_url": settings.FRONTEND_URL,
                    "batch_index": i,
                    "batch_total": len(lotes),
                },
            )
            msg = EmailMessage(
                subject=asunto,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to],
            )
            msg.content_subtype = "html"
            for it in lote:
                if it["pdf"] is not None:
                    msg.attach(it["name"], it["pdf"], "application/pdf")
            msg.send()
        except Exception as exc:
            logger.exception("No se pudo enviar el lote %s de actas a %s: %s", i, to, exc)
            for it in lote:
                ReportSendLog.objects.create(
                    report=it["report"], recipient_email=to, was_successful=False,
                    error_message=str(exc),
                )
            lotes_fallidos.append(lote)
            continue
        enviados += 1
        for it in lote:
            ReportSendLog.objects.create(
                report=it["report"], recipient_email=to,
                recipient_name=hospital.contact_name or "", was_successful=True,
            )

    for r, error in ilegibles:
        ReportSendLog.objects.create(
            report=r, recipient_email=to, was_successful=False, error_message=error,
        )

    pendientes = [str(it["report"].id) for lote in lotes_fallidos for it in lote]
    pendientes += [str(r.id) for r, _ in ilegibles]
    resultado = {
        "status": "sent" if not pendientes else "partial" if enviados else "failed",
        "to": to,
        "batches": len(lotes),
        "sent_batches": enviados,
        "failed_report_ids": pendientes,
    }
    if pendientes and not self.request.is_eager and self.request.retries < self.max_retries:
        raise self.retry(
            args=(hospital_id, pendientes),
            countdown=60 * (self.request.retries + 1),
        )
    return resultado


@shared_task(bind=True, max_retries=3)
def generate_consolidated_report(
    self, hospital_id, date_from, date_to, task_type=None, requested_by_id=None
):
    from apps.users.models import User

    requested_by = None
    if requested_by_id:
        try:
            requested_by = User.objects.get(id=requested_by_id)
        except User.DoesNotExist:
            pass

    try:
        return _generar_consolidado(
            hospital_id, date_from, date_to, task_type, requested_by
        )
    except Exception as exc:
        logger.exception(
            "No se pudo generar el reporte consolidado %s - %s: %s",
            date_from, date_to, exc,
        )
        _avisar_consolidado_fallido(requested_by, hospital_id, date_from, date_to)
        raise


def _generar_consolidado(hospital_id, date_from, date_to, task_type, requested_by):
    from weasyprint import HTML

    from apps.assets.models import Hospital

    try:
        hospital = Hospital.objects.get(id=hospital_id) if hospital_id else None
    except Hospital.DoesNotExist:
        hospital = None

    qs = WorkOrder.objects.select_related(
        "hospital", "assigned_to"
    ).prefetch_related("tasks__asset").filter(
        scheduled_date__gte=date_from,
        scheduled_date__lte=date_to,
    )
    if hospital:
        qs = qs.filter(hospital=hospital)
    if task_type:
        qs = qs.filter(task_type=task_type)

    total_ots = qs.count()
    completed_count = qs.filter(status=WorkOrder.Status.COMPLETED).count()
    pct_completed = round(completed_count / total_ots * 100, 1) if total_ots else 0.0
    # Activos distintos atendidos: pasan por las tareas, una OT puede llevar
    # varios.
    from apps.maintenance.models import Task
    assets_count = (
        Task.objects.filter(work_order__in=qs).values("asset").distinct().count()
    )

    from django.db.models import Count as DjCount
    status_summary = [
        {"status": item["status"], "count": item["cnt"]}
        for item in qs.values("status").annotate(cnt=DjCount("id"))
    ]

    generated_at = timezone.now()
    context = {
        "hospital": hospital,
        "date_from": date_from,
        "date_to": date_to,
        "task_type": task_type_label(task_type) if task_type else None,
        "work_orders": list(qs.order_by("scheduled_date")),
        "summary": {
            "total_ots": total_ots,
            "pct_completed": pct_completed,
            "assets_count": assets_count,
        },
        "status_summary": status_summary,
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M"),
        "logo_base64": get_logo_base64("on_light"),
    }

    html_str = render_to_string("reports/consolidated_report.html", context)
    pdf_bytes = HTML(string=html_str, base_url=settings.BACKEND_URL).write_pdf()

    hospital_code = hospital.code if hospital else "all"
    filename = f"reports/consolidated/{hospital_code}_{date_from}_{date_to}.pdf"
    s3_key = default_storage.save(filename, ContentFile(pdf_bytes))

    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    report = GeneratedReport.objects.create(
        report_type=GeneratedReport.ReportType.CUSTOM,
        title=f"Consolidado {date_from} – {date_to}",
        file_url=s3_key,
        file_hash=file_hash,
        generated_by=requested_by,
        generated_at=generated_at,
    )

    try:
        download_url = default_storage.url(s3_key)
    except Exception:
        download_url = s3_key

    _enviar_consolidado(
        requested_by, hospital, date_from, date_to, pdf_bytes, download_url
    )

    return {"status": "done", "report_id": str(report.id), "download_url": download_url}


def _etiqueta_consolidado(hospital, date_from, date_to):
    lugar = hospital.name if hospital else "todos los hospitales"
    return f"{lugar} {date_from}–{date_to}"


def _enlace_consolidado(download_url):
    """Enlace absoluto al PDF; si el almacenamiento da una ruta relativa, a la pantalla de reportes."""
    if download_url and download_url.startswith("http"):
        return download_url
    return f"{settings.FRONTEND_URL}/reportes"


def _enviar_consolidado(requested_by, hospital, date_from, date_to, pdf_bytes, download_url):
    """
    Manda el PDF consolidado a quien lo pidio. Va adjunto si pesa menos de
    settings.REPORTS_EMAIL_MAX_BYTES; si no, va el enlace de descarga.
    Sin correo del solicitante no se envia nada y queda en el log.
    """
    if requested_by is None or not requested_by.email:
        logger.warning(
            "Reporte consolidado %s - %s listo, pero el solicitante no tiene correo: no se envia",
            date_from, date_to,
        )
        return
    adjunto = len(pdf_bytes) <= settings.REPORTS_EMAIL_MAX_BYTES
    try:
        msg = EmailMessage(
            subject=f"Reporte consolidado {_etiqueta_consolidado(hospital, date_from, date_to)}",
            body=render_to_string("reports/email_consolidated_report.html", {
                "etiqueta": _etiqueta_consolidado(hospital, date_from, date_to),
                "hospital_name": hospital.name if hospital else "Todos los hospitales",
                "date_from": date_from,
                "date_to": date_to,
                "solicitante": requested_by.first_name or requested_by.email,
                "adjunto": adjunto,
                "enlace": "" if adjunto else _enlace_consolidado(download_url),
                "fallido": False,
                "frontend_url": settings.FRONTEND_URL,
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[requested_by.email],
        )
        msg.content_subtype = "html"
        if adjunto:
            msg.attach(
                f"consolidado_{date_from}_{date_to}.pdf", pdf_bytes, "application/pdf"
            )
        msg.send()
    except Exception as exc:
        logger.exception(
            "No se pudo enviar el reporte consolidado %s - %s a %s: %s",
            date_from, date_to, requested_by.email, exc,
        )


def _avisar_consolidado_fallido(requested_by, hospital_id, date_from, date_to):
    """Correo corto cuando la generacion falla. Nunca lanza: el error original es el que importa."""
    if requested_by is None or not requested_by.email:
        return
    try:
        from apps.assets.models import Hospital

        hospital = Hospital.objects.filter(id=hospital_id).first() if hospital_id else None
        etiqueta = _etiqueta_consolidado(hospital, date_from, date_to)
        msg = EmailMessage(
            subject=f"No se pudo generar el reporte consolidado {etiqueta}",
            body=render_to_string("reports/email_consolidated_report.html", {
                "etiqueta": etiqueta,
                "hospital_name": hospital.name if hospital else "Todos los hospitales",
                "date_from": date_from,
                "date_to": date_to,
                "solicitante": requested_by.first_name or requested_by.email,
                "adjunto": False,
                "enlace": "",
                "fallido": True,
                "frontend_url": settings.FRONTEND_URL,
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[requested_by.email],
        )
        msg.content_subtype = "html"
        msg.send()
    except Exception as exc:
        logger.exception("No se pudo avisar el fallo del consolidado a %s: %s", requested_by.email, exc)


def _assets_label(work_order):
    """"Alarma 3 gases" o "Alarma 3 gases y 2 activos mas" para el asunto y el correo."""
    tareas = list(work_order.tasks.exclude(status="CANCELLED").select_related("asset"))
    if not tareas:
        return ""
    primero = tareas[0].asset.name
    resto = len({t.asset_id for t in tareas}) - 1
    if resto <= 0:
        return primero
    return f"{primero} y {resto} activo{'s' if resto > 1 else ''} más"


def _destinatarios_de_hallazgos(work_order, graves):
    """
    El contacto del hospital y las biomedicas cuyo alcance incluye alguno de
    los equipos con hallazgo grave (una limitada a Urgencias no recibe lo de
    Cirugia).
    """
    from apps.assets.models import Asset
    from apps.users import scope
    from apps.users.models import User

    correos = {work_order.hospital.contact_email} if work_order.hospital.contact_email else set()
    activos = Asset.objects.filter(pk__in={f.asset_id for f in graves})
    for u in User.objects.filter(role=User.Role.CLI, is_active=True, hospital=work_order.hospital):
        if u.email and scope.assets(activos, u).exists():
            correos.add(u.email)
    return sorted(correos)


@shared_task(bind=True, max_retries=3)
def send_serious_findings_email(self, work_order_id):
    """
    Aviso al hospital al aprobar una OT con hallazgos criticos o que dejan un
    equipo fuera de servicio (decision del 2026-09-23). El detalle va en el
    acta y en el portal; el correo es para que no espere a leerla.
    """
    try:
        work_order = WorkOrder.objects.select_related("hospital").get(id=work_order_id)
        graves = [f for f in work_order.findings.select_related("asset__node") if f.is_serious]
        if not graves:
            return {"status": "skipped", "reason": "sin hallazgos graves"}
        para = _destinatarios_de_hallazgos(work_order, graves)
        if not para:
            return {"status": "skipped", "reason": "no email"}
        cuantos = len(graves)
        msg = EmailMessage(
            subject=(
                f"{'Hallazgo importante' if cuantos == 1 else f'{cuantos} hallazgos importantes'}"
                f" - {work_order.wo_code} | {work_order.hospital.name}"
            ),
            body=render_to_string("reports/email_findings.html", {
                "work_order": work_order,
                "findings": graves,
                "hospital": work_order.hospital,
                "frontend_url": settings.FRONTEND_URL,
                "logo_base64": get_logo_base64("on_dark"),
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=para,
        )
        msg.content_subtype = "html"
        msg.send()
        return {"status": "sent", "to": para}
    except Exception as exc:
        logger.exception("No se pudo avisar los hallazgos de la OT %s: %s", work_order_id, exc)
        if self.request.is_eager or self.request.retries >= self.max_retries:
            return {"status": "failed", "error": str(exc)}
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
