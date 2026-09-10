"""Rastro durable de un acta que no se pudo generar.

Cuando la generacion del PDF falla, la OT queda cerrada sin acta. Sin este
registro el unico rastro estaba en los logs del servidor, y en la interfaz la
pestaña de reportes era indistinguible de "todavia se esta generando".

El escritor y el lector viven juntos a proposito: comparten el marcador que
distingue un fallo de las demas entradas de auditoria sobre GeneratedReport
(por ejemplo una regeneracion manual), y separarlos los haria derivar.
"""

import logging

logger = logging.getLogger(__name__)

REPORT_ENTITY_TYPE = "GeneratedReport"
FAILURE_MARKER = "fallo"


def record_report_failure(work_order_id, exc):
    """Anota en auditoria que una OT cerrada se quedo sin acta."""
    from apps.audit.models import AuditLog

    try:
        AuditLog.objects.create(
            user=None,
            action=AuditLog.Action.CREATE,
            entity_type=REPORT_ENTITY_TYPE,
            entity_id=work_order_id,
            changes={
                "resultado": FAILURE_MARKER,
                "detalle": "No se pudo generar el acta de servicio.",
                "error": str(exc)[:500],
            },
        )
    except Exception:
        # Si ni la auditoria se puede escribir, el log del servidor es lo que hay.
        logger.exception(
            "Tampoco se pudo registrar en auditoria el fallo del acta de la OT %s",
            work_order_id,
        )


def has_report_failure(work_order_id):
    """True si consta un fallo de generacion para esa OT.

    Se apoya en el indice (entity_type, entity_id) de AuditLog.
    """
    from apps.audit.models import AuditLog

    return AuditLog.objects.filter(
        entity_type=REPORT_ENTITY_TYPE,
        entity_id=work_order_id,
        changes__resultado=FAILURE_MARKER,
    ).exists()
