"""
Google Maps en el servidor (decision del 2026-09-24), como el campo
*LOCALIZACION de Fracttal: el GPS se muestra como direccion y el acta lleva
un mapa pequeno.

- Geocoding API: coordenadas -> "Cra. 4h Bis #341, Ibague, Tolima, Colombia".
  Se pide una sola vez, al sincronizar la respuesta, y se guarda.
- Maps Static API: la imagen del mapa para el acta.

Sin clave (GOOGLE_MAPS_API_KEY vacia) o sin respuesta de Google, todo sigue
funcionando con las coordenadas: nada de esto puede tumbar una sincronizacion
ni un acta.
"""

import base64
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 8
_COORD = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def parse_latlng(texto):
    """"4.437887,-75.220034" -> (4.437887, -75.220034), o None si no son coordenadas."""
    m = _COORD.match(texto or "")
    if not m:
        return None
    lat, lng = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lat, lng


def enabled():
    return bool(settings.GOOGLE_MAPS_API_KEY)


def _get(url, params):
    """GET a Google con la clave. Devuelve los bytes o None si algo falla."""
    query = urllib.parse.urlencode({**params, "key": settings.GOOGLE_MAPS_API_KEY})
    try:
        with urllib.request.urlopen(f"{url}?{query}", timeout=TIMEOUT) as r:
            return r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Google Maps no respondio (%s): %s", url, exc)
        return None


def reverse_geocode(lat, lng):
    """La direccion de unas coordenadas, en español, o "" si no se pudo."""
    if not enabled():
        return ""
    datos = _get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        {"latlng": f"{lat},{lng}", "language": "es"},
    )
    if not datos:
        return ""
    try:
        cuerpo = json.loads(datos)
    except ValueError:
        return ""
    if cuerpo.get("status") != "OK" or not cuerpo.get("results"):
        if cuerpo.get("status") not in ("OK", "ZERO_RESULTS"):
            logger.warning("Geocoding respondio %s: %s", cuerpo.get("status"), cuerpo.get("error_message", ""))
        return ""
    return cuerpo["results"][0].get("formatted_address", "")[:300]


def static_map_data_uri(lat, lng, width=520, height=200, zoom=17):
    """El mapa con el punto como imagen incrustable en el PDF, o "" si no se pudo."""
    if not enabled():
        return ""
    datos = _get(
        "https://maps.googleapis.com/maps/api/staticmap",
        {
            "center": f"{lat},{lng}",
            "zoom": zoom,
            "size": f"{width}x{height}",
            "scale": 2,
            "markers": f"color:red|{lat},{lng}",
            "language": "es",
        },
    )
    # Google devuelve una imagen de error (no PNG) cuando la clave no sirve.
    if not datos or not datos.startswith(b"\x89PNG"):
        return ""
    return "data:image/png;base64," + base64.b64encode(datos).decode()


def maps_link(lat, lng):
    """Abrir el punto en Google Maps: no necesita clave."""
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
