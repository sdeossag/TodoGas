"""Exportacion del log de auditoria a CSV para auditorias externas (INVIMA...).

El rango de fechas se acota para que una exportacion no sea una consulta
ilimitada sobre toda la tabla. Sin filtro de fechas se exportan los ultimos
90 dias; con filtro, el rango (extremos incluidos) no puede pasar de 366 dias.
"""

import csv
import datetime as dt
import json
from zoneinfo import ZoneInfo

from django.utils import timezone

BOGOTA_TZ = ZoneInfo("America/Bogota")
DEFAULT_WINDOW_DAYS = 90
MAX_RANGE_DAYS = 366  # rango inclusive: desde y hasta cuentan los dos

COLUMNS = [
    "fecha_hora",
    "usuario",
    "rol",
    "accion",
    "entidad",
    "id_entidad",
    "ip",
    "cambios",
]


class ExportRangeError(ValueError):
    """Rango de fechas no valido; el mensaje va tal cual al cliente."""


def resolve_date_range(date_from, date_to, today=None):
    """Devuelve (desde, hasta) como fechas, aplicando los valores por defecto.

    `date_from` y `date_to` son cadenas ISO (AAAA-MM-DD) o None.
    """
    today = today or timezone.localdate(timezone=BOGOTA_TZ)
    try:
        d_from = dt.date.fromisoformat(date_from) if date_from else None
        d_to = dt.date.fromisoformat(date_to) if date_to else None
    except ValueError:
        raise ExportRangeError("Las fechas deben tener formato AAAA-MM-DD.")

    if d_from is None and d_to is None:
        d_to = today
        d_from = today - dt.timedelta(days=DEFAULT_WINDOW_DAYS - 1)
    elif d_from is None:
        d_from = d_to - dt.timedelta(days=DEFAULT_WINDOW_DAYS - 1)
    elif d_to is None:
        d_to = today

    if d_from > d_to:
        raise ExportRangeError("La fecha 'desde' no puede ser posterior a 'hasta'.")
    if (d_to - d_from).days + 1 > MAX_RANGE_DAYS:
        raise ExportRangeError(
            f"El rango maximo por exportacion es de {MAX_RANGE_DAYS} dias "
            "(desde y hasta incluidos). Reduce el rango de fechas."
        )
    return d_from, d_to


def export_filename(d_from, d_to):
    return f"auditoria_{d_from.isoformat()}_{d_to.isoformat()}.csv"


class _Echo:
    """Pseudo-buffer: csv.writer escribe aqui y recibe la linea ya formateada."""

    def write(self, value):
        return value


def _row(log):
    user = log.user
    ts = timezone.localtime(log.timestamp, timezone=BOGOTA_TZ)
    return [
        ts.strftime("%Y-%m-%d %H:%M:%S"),
        user.email if user else "",
        user.get_role_display() if user else "",
        log.get_action_display(),
        log.entity_type,
        str(log.entity_id),
        log.ip_address or "",
        json.dumps(log.changes, ensure_ascii=False, separators=(",", ":"), default=str),
    ]


def iter_csv_lines(queryset):
    """Genera el CSV linea a linea. El primer trozo lleva el BOM UTF-8.

    Se usa .iterator() para no cargar todo el log en memoria.
    """
    writer = csv.writer(_Echo(), lineterminator="\r\n")
    yield "﻿" + writer.writerow(COLUMNS)
    for log in queryset.iterator(chunk_size=500):
        yield writer.writerow(_row(log))
