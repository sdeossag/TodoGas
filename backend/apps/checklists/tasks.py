import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="checklists.geocode_field_response")
def geocode_field_response(field_response_id):
    """
    La direccion de las coordenadas de un campo GPS (decision del 2026-09-24).
    Sin clave o sin respuesta de Google queda vacia y se ven las coordenadas.
    """
    from apps.assets.geo import parse_latlng, reverse_geocode

    from .models import ChecklistFieldResponse

    fr = ChecklistFieldResponse.objects.filter(pk=field_response_id).first()
    if fr is None:
        return {"status": "skipped", "reason": "no existe"}
    punto = parse_latlng(fr.value)
    if punto is None:
        return {"status": "skipped", "reason": "sin coordenadas"}
    direccion = reverse_geocode(*punto)
    # Solo si la respuesta no cambio mientras tanto.
    ChecklistFieldResponse.objects.filter(pk=fr.pk, value=fr.value).update(geo_address=direccion)
    return {"status": "ok" if direccion else "empty", "address": direccion}
