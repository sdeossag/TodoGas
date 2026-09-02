"""
Hash de integridad de una OT completada.

RF-TR-03 y RNF-COM-01 piden poder demostrar ante un auditor que el registro de
una intervencion no fue alterado despues de firmarse. Eso obliga a que el hash
cubra la evidencia real, no solo la cabecera: si las respuestas del checklist,
las fotos o las firmas quedan fuera, alterarlas es indetectable y el mecanismo
no prueba nada.

Dos hashes distintos, que no deben confundirse:

  - hash del PDF      sha256 de los bytes del archivo. Va en
                      GeneratedReport.file_hash. Prueba que el artefacto
                      entregado al cliente es el que se genero.
  - hash de contenido  sha256 de la serializacion canonica de abajo. Va en
                      GeneratedReport.content_hash. Prueba que el registro en
                      base de datos sigue diciendo lo mismo.

Comparar uno contra otro nunca coincide.
"""

import hashlib
import json

# Cualquier cambio en build_integrity_payload obliga a subir esta version: un
# hash calculado con otra forma de payload no es comparable, y sin el sello la
# verificacion reportaria alteracion sobre registros intactos.
INTEGRITY_ALGORITHM_VERSION = "1"


def _dt(value):
    """Fecha en ISO-8601, o None. Determinista para el mismo instante."""
    return value.isoformat() if value is not None else None


def _id(value):
    return str(value) if value is not None else None


def _num(value):
    """Decimal a str para no depender de la representacion binaria del float."""
    return str(value) if value is not None else None


def build_integrity_payload(work_order):
    """
    Serializacion canonica del contenido probatorio de una OT.

    Ordenada por identificador en cada coleccion para que el resultado no
    dependa del orden que devuelva la base de datos.
    """
    from apps.checklists.models import ChecklistResponse
    from apps.evidence.models import Photo, Signature
    from apps.inventory.models import StockMovement

    checklist = (
        ChecklistResponse.objects.filter(work_order=work_order)
        .prefetch_related("field_responses")
        .first()
    )
    if checklist is None:
        checklist_payload = None
    else:
        checklist_payload = {
            "id": _id(checklist.id),
            "version": _id(checklist.version_id),
            "completed_at": _dt(checklist.completed_at),
            "completed_by": _id(checklist.completed_by_id),
            "fields": sorted(
                (
                    {
                        "field": _id(fr.field_id),
                        "value": fr.value,
                        "notes": fr.notes,
                        "answered_at": _dt(fr.answered_at),
                    }
                    for fr in checklist.field_responses.all()
                ),
                key=lambda row: row["field"],
            ),
        }

    photos = sorted(
        (
            {
                "id": _id(p.id),
                "file_hash": p.file_hash,
                "taken_at": _dt(p.taken_at),
                "latitude": _num(p.latitude),
                "longitude": _num(p.longitude),
                "uploaded_by": _id(p.uploaded_by_id),
            }
            for p in Photo.objects.filter(work_order=work_order)
        ),
        key=lambda row: row["id"],
    )

    signatures = sorted(
        (
            {
                "id": _id(s.id),
                "signature_type": s.signature_type,
                "file_hash": s.file_hash,
                "signer_name": s.signer_name,
                "signer_role": s.signer_role,
                "signed_at": _dt(s.signed_at),
            }
            for s in Signature.objects.filter(work_order=work_order)
        ),
        key=lambda row: row["id"],
    )

    stock = sorted(
        (
            {
                "id": _id(m.id),
                "item": _id(m.item_id),
                "movement_type": m.movement_type,
                "quantity": _num(m.quantity),
            }
            for m in StockMovement.objects.filter(work_order=work_order)
        ),
        key=lambda row: row["id"],
    )

    return {
        "algorithm_version": INTEGRITY_ALGORITHM_VERSION,
        "work_order": {
            "id": _id(work_order.id),
            "wo_number": work_order.wo_number,
            "task_type": work_order.task_type,
            "status": work_order.status,
            "title": work_order.title,
            "description": work_order.description,
            "notes": work_order.notes,
            "asset": _id(work_order.asset_id),
            "assigned_to": _id(work_order.assigned_to_id),
            "checklist_version": _id(work_order.checklist_version_id),
            "scheduled_date": _dt(work_order.scheduled_date),
            "started_at": _dt(work_order.started_at),
            "completed_at": _dt(work_order.completed_at),
        },
        "checklist_response": checklist_payload,
        "photos": photos,
        "signatures": signatures,
        "stock_movements": stock,
    }


def compute_wo_content_hash(work_order):
    """sha256 de la serializacion canonica del contenido probatorio de la OT."""
    canonical = json.dumps(
        build_integrity_payload(work_order),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
