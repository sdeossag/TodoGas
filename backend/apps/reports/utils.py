"""Utilidades compartidas para la generacion de reportes."""

import base64
import os

# El logo vive como estatico de la app, no en frontend/: el contenedor del
# backend se construye con `build: ./backend` y no monta esa carpeta.
_LOGO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static", "reports"
)

# Ambos archivos estan reescalados a 800px de ancho: en el PDF se dibujan a
# unos 45px de alto y van incrustados en base64 en cada documento.
LOGO_FILES = {
    "on_light": "logo.png",           # arte indigo, para fondos claros
    "on_dark": "logo-invertido.png",  # arte blanco, para fondos oscuros
}


def get_logo_base64(variant="on_light"):
    """
    Devuelve el logo en base64, o None si el archivo no existe.

    Se incrusta en el HTML como data URI para que WeasyPrint lo renderice sin
    necesidad de acceso a red ni al storage.

    variant:
        "on_light" — acta consolidada, cabecera blanca
        "on_dark"  — acta de servicio, cabecera navy
    """
    filename = LOGO_FILES.get(variant)
    if filename is None:
        raise ValueError(f"Variante de logo desconocida: {variant!r}")

    logo_path = os.path.join(_LOGO_DIR, filename)
    if not os.path.exists(logo_path):
        return None

    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode()
