"""
OTs historicas importadas de Fracttal: son solo consulta.

Nunca pasaron por nuestras transiciones, no tienen acta automatica y su
evidencia es lo que Fracttal tenia. Todo punto de escritura sobre una OT (o
sobre algo que cuelga de ella) llama a `bloqueo_historica` y devuelve su
respuesta si no es None.
"""

from rest_framework import status
from rest_framework.response import Response

MENSAJE_HISTORICA = "Esta OT es histórica (importada de Fracttal) y no se puede modificar"


def es_historica(wo):
    """True si la OT viene de una importacion (origin distinto de vacio)."""
    return wo is not None and bool(getattr(wo, "origin", ""))


def bloqueo_historica(wo):
    """409 con el motivo si la OT es historica; None si admite cambios."""
    if not es_historica(wo):
        return None
    return Response(
        {"detail": MENSAJE_HISTORICA, "code": "ot_historica"},
        status=status.HTTP_409_CONFLICT,
    )
