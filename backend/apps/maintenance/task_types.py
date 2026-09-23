"""
Catalogo de tipos de tarea (decision del 2026-09-23): lo que usan los
indicadores y la validacion de los formularios.
"""

import re
import unicodedata

from rest_framework import serializers

from .models import TaskTypeCatalog


def codes_counting_as(counts_as):
    """Codigos que entran en un indicador: cumplimiento (PREVENTIVE) o MTTR (CORRECTIVE)."""
    return list(TaskTypeCatalog.objects.filter(counts_as=counts_as).values_list("code", flat=True))


def code_from_name(name):
    """"Cambio de filtros" -> "CAMBIO_DE_FILTROS", sin tildes ni signos."""
    ascii_ = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    code = re.sub(r"[^A-Z0-9]+", "_", ascii_.upper()).strip("_")[:50]
    return code or "TIPO"


class TaskTypeField(serializers.CharField):
    """
    Un codigo del catalogo que este activo. Al editar, el valor que ya tenia
    se acepta aunque el tipo se haya desactivado despues: desactivar un tipo
    no obliga a cambiar lo que ya lo usa.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 50)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        code = super().to_internal_value(data)
        instancia = getattr(self.parent, "instance", None)
        actual = getattr(instancia, self.source, None) if instancia is not None and not isinstance(instancia, list) else None
        if code == actual:
            return code
        if not TaskTypeCatalog.objects.filter(code=code, is_active=True).exists():
            raise serializers.ValidationError("Ese tipo de tarea no existe o esta desactivado.")
        return code
