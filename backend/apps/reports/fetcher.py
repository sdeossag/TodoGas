"""Imagenes del acta leidas directo del almacenamiento.

Antes cada foto y cada firma iba al PDF como una URL (pre-firmada de S3, o
http://localhost:8000/media/... en desarrollo) y WeasyPrint la descargaba por
HTTP, una por una. En desarrollo cada conexion tardaba unos 4 s (y la imagen ni
siquiera llegaba si no habia nadie en el puerto 8000): aprobar una OT con 3
fotos esperaba ~20 s. Ahora la plantilla recibe `storage:<clave>` y este
fetcher lee los bytes con default_storage, sin red.
"""

import mimetypes
from urllib.parse import quote, unquote

from django.core.files.storage import default_storage

ESQUEMA = "storage:"

# Lo que no es del almacenamiento (claves antiguas guardadas como URL
# completa) se sigue descargando, pero sin esperar los 10 s por defecto.
TIEMPO_MAXIMO_RED = 5


def url_de_almacenamiento(clave):
    """La URL que la plantilla pone en <img src> para una clave de storage."""
    return ESQUEMA + quote(clave, safe="/")


def leer_de_almacenamiento(url):
    """(bytes, tipo MIME) de una URL `storage:<clave>`."""
    clave = unquote(url[len(ESQUEMA):])
    with default_storage.open(clave, "rb") as archivo:
        datos = archivo.read()
    return datos, mimetypes.guess_type(clave)[0] or "application/octet-stream"


def fetcher_de_almacenamiento():
    """
    El url_fetcher para HTML(...). WeasyPrint se importa aqui y no arriba: los
    tests sustituyen el modulo `weasyprint` por uno falso.
    """
    try:
        # Del paquete raiz: el falso de los tests no lo trae aunque el
        # submodulo real `weasyprint.urls` siga en sys.modules.
        from weasyprint import URLFetcher
        from weasyprint.urls import URLFetcherResponse
    except ImportError:
        # El weasyprint falso de los tests solo trae HTML.
        return None

    class FetcherDeAlmacenamiento(URLFetcher):
        def fetch(self, url, headers=None):
            if not url.startswith(ESQUEMA):
                return super().fetch(url, headers)
            datos, tipo = leer_de_almacenamiento(url)
            return URLFetcherResponse(url, datos, {"Content-Type": tipo})

    return FetcherDeAlmacenamiento(timeout=TIEMPO_MAXIMO_RED)
