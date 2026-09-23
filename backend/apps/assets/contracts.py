"""
Que cubre cada contrato y cada garantia (decision del 2026-09-23).

- Un contrato de mantenimiento cubre su hospital entero o una rama del arbol:
  un equipo esta bajo contrato si su ubicacion cuelga de esa rama.
- Una garantia cubre los equipos que lista.

Nada de esto bloquea: son avisos para el planificador y datos para el hospital.
"""

from datetime import timedelta

from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone

from .models import AssetNode, Contract, Hospital


def hoy():
    return timezone.localdate()


def resumen(contract, on_date=None):
    """Lo minimo para mostrar un documento en una ficha o en el portal."""
    on_date = on_date or hoy()
    return {
        "id": str(contract.id),
        "kind": contract.kind,
        "name": contract.name,
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat(),
        "status": contract.status_on(on_date),
        "days_left": (contract.end_date - on_date).days,
    }


def _ancestros(node_id):
    ids = []
    while node_id:
        ids.append(node_id)
        node_id = AssetNode.objects.filter(pk=node_id).values_list("parent_id", flat=True).first()
    return ids


def cobertura_del_activo(asset, on_date=None):
    """
    {"warranty": ..., "contract": ...} vigentes hoy, o None en cada uno. Si
    hay varios vigentes, el que dura mas.
    """
    on_date = on_date or hoy()
    garantia = (
        Contract.objects
        .filter(Contract.active_q(on_date), kind=Contract.Kind.WARRANTY, asset_links__asset=asset)
        .order_by("-end_date").first()
    )
    ramas = _ancestros(asset.node_id)
    contrato = (
        Contract.objects
        .filter(Contract.active_q(on_date), kind=Contract.Kind.MAINTENANCE, hospital_id=asset.hospital_id)
        .filter(Q(node__isnull=True) | Q(node_id__in=ramas))
        .order_by("-end_date").first()
    )
    return {
        "warranty": resumen(garantia, on_date) if garantia else None,
        "contract": resumen(contrato, on_date) if contrato else None,
    }


def prefetch_contratos_vigentes(on_date=None):
    """Para listar hospitales sin una consulta por fila."""
    on_date = on_date or hoy()
    return Prefetch(
        "contracts",
        queryset=Contract.objects.filter(
            Contract.active_q(on_date), kind=Contract.Kind.MAINTENANCE,
        ).order_by("-end_date"),
        to_attr="contratos_vigentes",
    )


def estado_del_hospital(hospital, on_date=None):
    """
    {"has_active": bool, "current": resumen | None}. Usa el prefetch si lo
    hay. Un contrato que cubre solo una sede tambien cuenta: el hospital
    tiene relacion comercial vigente.
    """
    on_date = on_date or hoy()
    vigentes = getattr(hospital, "contratos_vigentes", None)
    if vigentes is None:
        vigentes = list(
            hospital.contracts.filter(Contract.active_q(on_date), kind=Contract.Kind.MAINTENANCE)
            .order_by("-end_date")
        )
    actual = vigentes[0] if vigentes else None
    return {"has_active": actual is not None, "current": resumen(actual, on_date) if actual else None}


def hospitales_sin_contrato(on_date=None):
    """Hospitales activos sin ningun contrato de mantenimiento vigente."""
    on_date = on_date or hoy()
    vigente = Contract.objects.filter(
        Contract.active_q(on_date), kind=Contract.Kind.MAINTENANCE, hospital_id=OuterRef("pk"),
    )
    return Hospital.objects.filter(is_active=True).exclude(Exists(vigente))


def renovado(contract):
    """
    True si ya hay otro contrato del mismo hospital y la misma rama que
    arranca a mas tardar al dia siguiente y dura mas: avisar del vencimiento
    seria ruido. Solo contratos; una garantia no se "renueva" igual.
    """
    if contract.kind != Contract.Kind.MAINTENANCE:
        return False
    return Contract.objects.filter(
        kind=Contract.Kind.MAINTENANCE,
        hospital_id=contract.hospital_id,
        node_id=contract.node_id,
        start_date__lte=contract.end_date + timedelta(days=1),
        end_date__gt=contract.end_date,
    ).exclude(pk=contract.pk).exists()


_RANGO = {
    Contract.Notice.NONE: 0,
    Contract.Notice.DAYS_60: 1,
    Contract.Notice.DAYS_30: 2,
    Contract.Notice.EXPIRED: 3,
}


def _aviso_que_toca(contract, on_date):
    dias = (contract.end_date - on_date).days
    if dias < 0:
        return Contract.Notice.EXPIRED
    if dias <= 30:
        return Contract.Notice.DAYS_30
    if dias <= Contract.EXPIRING_DAYS:
        return Contract.Notice.DAYS_60
    return Contract.Notice.NONE


def avisos_pendientes(on_date=None):
    """
    [(contrato, aviso)] que todavia no se han mandado: cada documento avisa
    una vez a 60 dias, una a 30 y una al vencer. Lo vencido hace mas de 30
    dias no se avisa (al cargar los contratos viejos llegaria un correo con
    todo el historial). Un contrato ya renovado se marca sin avisar.
    """
    on_date = on_date or hoy()
    candidatos = Contract.objects.filter(
        end_date__gte=on_date - timedelta(days=30),
        end_date__lte=on_date + timedelta(days=Contract.EXPIRING_DAYS),
    ).exclude(last_notice=Contract.Notice.EXPIRED).select_related("hospital", "node")
    pendientes = []
    for c in candidatos:
        aviso = _aviso_que_toca(c, on_date)
        if _RANGO[aviso] <= _RANGO[Contract.Notice(c.last_notice)]:
            continue
        if renovado(c):
            c.last_notice = aviso
            c.save(update_fields=["last_notice"])
            continue
        pendientes.append((c, aviso))
    return pendientes
