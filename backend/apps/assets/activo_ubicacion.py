"""
Protocolos sobre una ubicacion (revision del 2026-10-23).

Instalaciones entrega obras por ubicacion ("Bloque A / Piso 3"), no por
equipo. En vez de que tareas, OT, checklist, acta y app sin red aprendan a
trabajar "con un activo o con una ubicacion", la ubicacion recibe un activo
que la representa (Asset.represents_node) y todo lo demas sigue igual.
"""

from django.db import transaction

from .models import Asset


def codigo_de(node):
    return f"UBI-{node.id.hex[:8].upper()}"


@transaction.atomic
def activo_de_ubicacion(node):
    """El activo que representa la ubicacion; lo crea la primera vez."""
    existente = Asset.objects.filter(represents_node=node).first()
    if existente:
        return existente
    return Asset.objects.create(
        hospital_id=node.hospital_id,
        node=node,
        represents_node=node,
        name=node.name,
        code=codigo_de(node),
        asset_type=Asset.LOCATION_TYPE,
        equipment_location=node.path,
    )
