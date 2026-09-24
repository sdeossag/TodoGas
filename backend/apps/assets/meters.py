"""
Medidores y lecturas (decision del 2026-09-24).

Las lecturas entran por dos caminos: el campo "Lectura de medidor" del
checklist atado a una unidad (cuenta en cuanto llega del telefono y se corrige
con la respuesta) y el registro manual desde la ficha del equipo. Cada lectura
nueva se evalua contra los activadores del plan del equipo.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import Meter, MeterReading, MeterUnit


def unit_of_field(field):
    """La unidad a la que esta atado un campo METER del checklist, o None."""
    opciones = field.options_json if isinstance(field.options_json, dict) else {}
    unit_id = opciones.get("meter_unit")
    if not unit_id:
        return None
    return MeterUnit.objects.filter(pk=unit_id).first()


def meter_for(asset, unit):
    meter, _ = Meter.objects.get_or_create(asset=asset, unit=unit)
    return meter


def recompute_accumulated(meter):
    """
    Uso acumulado de un contador, lectura por lectura en orden de fecha. Si la
    lectura baja respecto a la anterior (o viene marcada como reinicio), el
    horometro se reinicio o se cambio: cuenta desde cero, no resta.
    """
    if not meter.unit.is_counter:
        return
    acumulado, anterior = None, None
    for r in meter.readings.order_by("read_at", "created_at"):
        if anterior is None:
            acumulado = r.value
        elif r.is_reset or r.value < anterior:
            acumulado += r.value
        else:
            acumulado += r.value - anterior
        anterior = r.value
        if r.accumulated != acumulado:
            MeterReading.objects.filter(pk=r.pk).update(accumulated=acumulado)
            r.accumulated = acumulado


def latest(meter):
    return meter.readings.order_by("-read_at", "-created_at").first()


def accumulated_at(meter, when):
    """Uso acumulado del contador en un momento: el de la ultima lectura hasta entonces."""
    r = meter.readings.filter(read_at__lte=when).order_by("-read_at", "-created_at").first()
    return r.accumulated if r is not None and r.accumulated is not None else None


def _despues(reading):
    """
    Recalcula el acumulado y evalua los activadores en la misma transaccion:
    si algo falla, la tarea que abriera tambien se deshace. El correo del
    umbral sale al confirmar.
    """
    recompute_accumulated(reading.meter)
    reading.refresh_from_db()

    from apps.maintenance.meters import evaluate_reading

    evaluate_reading(reading.pk)
    return reading


@transaction.atomic
def record_manual(meter, value, read_at=None, *, user=None, is_reset=False, note=""):
    reading = MeterReading.objects.create(
        meter=meter, value=value, read_at=read_at or timezone.now(),
        source=MeterReading.Source.MANUAL, is_reset=is_reset, note=note, recorded_by=user,
    )
    return _despues(reading)


def _decimal(texto):
    try:
        valor = Decimal(str(texto).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return valor if valor.is_finite() else None


@transaction.atomic
def record_from_checklist(field_response, user=None):
    """
    La respuesta a un campo METER atado a una unidad queda como lectura del
    medidor del equipo de la tarea. Una respuesta corregida corrige su lectura;
    una borrada la quita. Devuelve la lectura o None.
    """
    field = field_response.field
    if field.field_type != "METER":
        return None
    unit = unit_of_field(field)
    if unit is None:
        return None
    existente = MeterReading.objects.filter(field_response=field_response).first()
    valor = _decimal(field_response.value)
    if valor is None:
        if existente is not None:
            meter = existente.meter
            existente.triggered_tasks.update(trigger_reading=None)
            existente.delete()
            recompute_accumulated(meter)
        return None

    task = field_response.response.task
    meter = meter_for(task.asset, unit)
    if existente is None:
        reading = MeterReading.objects.create(
            meter=meter, value=valor, read_at=field_response.answered_at,
            source=MeterReading.Source.CHECKLIST, field_response=field_response,
            task=task, recorded_by=user,
        )
    else:
        if existente.value == valor and existente.read_at == field_response.answered_at:
            return existente
        existente.value = valor
        existente.read_at = field_response.answered_at
        existente.save(update_fields=["value", "read_at"])
        reading = existente
    return _despues(reading)
