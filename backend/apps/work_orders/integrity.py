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

Versiones del algoritmo
-----------------------
Cada acta guarda con que version se calculo su hash, y la verificacion usa esa
misma version. Una version nueva NO reemplaza a las anteriores: si la
verificacion de un acta vieja respondiera "regenera el reporte", regenerar
recalcularia el hash con lo que diga la base ahora y una alteracion quedaria
lavada.

  1  Una OT = un activo y un checklist. Tras pasar al modelo de tareas, el
     activo, la version y las respuestas se leen de la unica tarea de la OT, y
     el resultado es el mismo JSON byte a byte que antes de la migracion.
  2  Una OT = varias tareas. Cubre la cabecera de la OT con su hospital y su
     ubicacion, y cada tarea con su activo, su origen, sus fechas y sus
     respuestas. Fotos, firmas e inventario igual que la 1, mas la tarea de
     cada foto.
  3  Bloques repetibles. Igual que la 2, pero cada respuesta lleva su numero
     de repeticion (la toma 1, la toma 2...) y cada checklist la cantidad de
     cada bloque. Sin eso, intercambiar valores entre tomas no cambiaria el
     hash, y el orden de las respuestas de un mismo campo quedaria indefinido.
  4  Hallazgos. Igual que la 3, mas los hallazgos de la visita con lo que se
     capturo en campo (equipo, descripcion, severidad, fuera de servicio,
     resuelto en sitio y como, quien y cuando) y el hallazgo de cada foto. La
     decision posterior del planificador (convertir o descartar) no entra:
     llega despues de firmada el acta y no la altera.
"""

import hashlib
import json
from dataclasses import dataclass

# Version con la que se calculan las actas nuevas. Las anteriores se siguen
# verificando con la suya (SUPPORTED_VERSIONS).
INTEGRITY_ALGORITHM_VERSION = "4"
SUPPORTED_VERSIONS = ("1", "2", "3", "4")


def _dt(value):
    """Fecha en ISO-8601, o None. Determinista para el mismo instante."""
    return value.isoformat() if value is not None else None


def _id(value):
    return str(value) if value is not None else None


def _num(value):
    """Decimal a str para no depender de la representacion binaria del float."""
    return str(value) if value is not None else None


def _checklist_payload(checklist):
    if checklist is None:
        return None
    return {
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


def _checklist_payload_v3(checklist):
    if checklist is None:
        return None
    return {
        "id": _id(checklist.id),
        "version": _id(checklist.version_id),
        "completed_at": _dt(checklist.completed_at),
        "completed_by": _id(checklist.completed_by_id),
        "block_counts": checklist.block_counts,
        "fields": sorted(
            (
                {
                    "field": _id(fr.field_id),
                    "repetition": fr.repetition,
                    "value": fr.value,
                    "notes": fr.notes,
                    "answered_at": _dt(fr.answered_at),
                }
                for fr in checklist.field_responses.all()
            ),
            key=lambda row: (row["field"], row["repetition"]),
        ),
    }


def _response_of(task):
    from apps.checklists.models import ChecklistResponse

    if task is None:
        return None
    return (
        ChecklistResponse.objects.filter(task=task)
        .prefetch_related("field_responses")
        .first()
    )


def _signatures(work_order):
    from apps.evidence.models import Signature

    return sorted(
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


def _stock(work_order):
    from apps.inventory.models import StockMovement

    return sorted(
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


def _payload_v1(work_order):
    """Forma de la version 1. No se toca: hay actas firmadas con ella."""
    from apps.evidence.models import Photo

    tarea = work_order.tasks.order_by("sort_order", "created_at").first()

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

    return {
        "algorithm_version": "1",
        "work_order": {
            "id": _id(work_order.id),
            "wo_number": work_order.wo_number,
            "task_type": work_order.task_type,
            "status": work_order.status,
            "title": work_order.title,
            "description": work_order.description,
            "notes": work_order.notes,
            "asset": _id(tarea.asset_id if tarea else None),
            "assigned_to": _id(work_order.assigned_to_id),
            "checklist_version": _id(tarea.checklist_version_id if tarea else None),
            "scheduled_date": _dt(work_order.scheduled_date),
            "started_at": _dt(work_order.started_at),
            "completed_at": _dt(work_order.completed_at),
        },
        "checklist_response": _checklist_payload(_response_of(tarea)),
        "photos": photos,
        "signatures": _signatures(work_order),
        "stock_movements": _stock(work_order),
    }


def _payload_v2(work_order, checklist=_checklist_payload, algorithm_version="2"):
    from apps.evidence.models import Photo

    tareas = sorted(
        (
            {
                "id": _id(t.id),
                "asset": _id(t.asset_id),
                "plan_task": _id(t.plan_task_id),
                "status": t.status,
                "title": t.title,
                "task_type": t.task_type,
                "checklist_version": _id(t.checklist_version_id),
                "calculated_date": _dt(t.calculated_date),
                "scheduled_date": _dt(t.scheduled_date),
                "completed_at": _dt(t.completed_at),
                "checklist_response": checklist(_response_of(t)),
            }
            for t in work_order.tasks.all()
        ),
        key=lambda row: row["id"],
    )

    photos = sorted(
        (
            {
                "id": _id(p.id),
                "task": _id(p.task_id),
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

    return {
        "algorithm_version": algorithm_version,
        "work_order": {
            "id": _id(work_order.id),
            "wo_number": work_order.wo_number,
            "task_type": work_order.task_type,
            "status": work_order.status,
            "title": work_order.title,
            "description": work_order.description,
            "notes": work_order.notes,
            "hospital": _id(work_order.hospital_id),
            "location": _id(work_order.location_id),
            "assigned_to": _id(work_order.assigned_to_id),
            "scheduled_date": _dt(work_order.scheduled_date),
            "started_at": _dt(work_order.started_at),
            "completed_at": _dt(work_order.completed_at),
        },
        "tasks": tareas,
        "photos": photos,
        "signatures": _signatures(work_order),
        "stock_movements": _stock(work_order),
    }


def _payload_v3(work_order):
    return _payload_v2(work_order, checklist=_checklist_payload_v3, algorithm_version="3")


def _payload_v4(work_order):
    from apps.evidence.models import Photo

    datos = _payload_v2(work_order, checklist=_checklist_payload_v3, algorithm_version="4")
    de_cada_foto = {
        _id(foto): _id(hallazgo)
        for foto, hallazgo in Photo.objects.filter(work_order=work_order).values_list("id", "finding_id")
    }
    for foto in datos["photos"]:
        foto["finding"] = de_cada_foto.get(foto["id"])
    datos["findings"] = sorted(
        (
            {
                "id": _id(f.id),
                "asset": _id(f.asset_id),
                "description": f.description,
                "severity": f.severity,
                "out_of_service": f.out_of_service,
                "resolved_on_site": f.resolved_on_site,
                "resolution_notes": f.resolution_notes,
                "reported_by": _id(f.reported_by_id),
                "reported_at": _dt(f.reported_at),
            }
            for f in work_order.findings.all()
        ),
        key=lambda row: row["id"],
    )
    return datos


_BUILDERS = {"1": _payload_v1, "2": _payload_v2, "3": _payload_v3, "4": _payload_v4}


def build_integrity_payload(work_order, version=INTEGRITY_ALGORITHM_VERSION):
    """
    Serializacion canonica del contenido probatorio de una OT.

    Ordenada por identificador en cada coleccion para que el resultado no
    dependa del orden que devuelva la base de datos.
    """
    try:
        builder = _BUILDERS[version]
    except KeyError:
        raise ValueError(f"Version de integridad desconocida: {version!r}") from None
    return builder(work_order)


def compute_wo_content_hash(work_order, version=INTEGRITY_ALGORITHM_VERSION):
    """sha256 de la serializacion canonica del contenido probatorio de la OT."""
    canonical = json.dumps(
        build_integrity_payload(work_order, version),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Verificacion ─────────────────────────────────────────────────────────────

VERIFIED = "VERIFIED"
ALTERED = "ALTERED"
NO_REPORT = "NO_REPORT"
NO_HASH = "NO_HASH"
UNKNOWN_VERSION = "UNKNOWN_VERSION"


@dataclass(frozen=True)
class Verification:
    outcome: str
    report: object = None
    recomputed_hash: str = ""

    @property
    def verified(self):
        """True o False si se pudo comprobar; None si no hay con que comparar."""
        if self.outcome == VERIFIED:
            return True
        if self.outcome == ALTERED:
            return False
        return None


def verify_work_order(work_order):
    """
    Compara el hash guardado en la ultima acta de la OT con el que da hoy la
    base, calculado con la version con que se firmo el acta.

    La usan el endpoint de integridad y el comando verify_integrity, para que
    los dos respondan lo mismo.
    """
    from apps.reports.models import GeneratedReport

    report = (
        GeneratedReport.objects.filter(work_order=work_order)
        .order_by("-generated_at")
        .first()
    )
    if report is None:
        return Verification(NO_REPORT)
    if not report.content_hash:
        return Verification(NO_HASH, report)
    if report.integrity_version not in SUPPORTED_VERSIONS:
        return Verification(UNKNOWN_VERSION, report)
    recomputed = compute_wo_content_hash(work_order, report.integrity_version)
    outcome = VERIFIED if recomputed == report.content_hash else ALTERED
    return Verification(outcome, report, recomputed)
