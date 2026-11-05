"""Las imagenes del acta se leen del storage, no por HTTP.

Regresion: WeasyPrint descargaba cada foto y firma por su URL, una por una, y
aprobar una OT con 3 fotos tardaba ~20 s (unos 4 s por conexion).
"""

import uuid
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.reports.fetcher import ESQUEMA, leer_de_almacenamiento, url_de_almacenamiento
from apps.reports.generator import _resolve_url

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01"
    b"\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_resolve_url_points_to_storage_not_http():
    assert _resolve_url("photos/a b.png") == ESQUEMA + "photos/a%20b.png"
    # Lo que ya era una URL completa se deja como estaba.
    assert _resolve_url("https://x.test/f.png") == "https://x.test/f.png"
    assert _resolve_url("") == ""


def test_fetcher_reads_bytes_from_storage_without_network():
    clave = default_storage.save(f"tests/fetcher/{uuid.uuid4()}.png", ContentFile(PNG))
    try:
        with patch("urllib.request.OpenerDirector.open") as red:
            datos, tipo = leer_de_almacenamiento(url_de_almacenamiento(clave))
            assert red.call_count == 0
        assert datos == PNG
        assert tipo == "image/png"
    finally:
        default_storage.delete(clave)
