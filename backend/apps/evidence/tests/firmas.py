"""Ayuda para las pruebas: darle a un usuario una firma guardada, como pide aprobar una OT."""

import hashlib
import io

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from apps.evidence.models import UserSignature


def png_bytes(color=(0, 0, 0)):
    buf = io.BytesIO()
    Image.new("RGB", (12, 12), color=color).save(buf, format="PNG")
    return buf.getvalue()


def firmar(user, color=(10, 20, 30)):
    """Guarda (o reemplaza) la firma guardada del usuario. Devuelve la fila."""
    raw = png_bytes(color)
    key = default_storage.save(f"evidence/user-signatures/{user.id}/test.png", ContentFile(raw))
    saved, _ = UserSignature.objects.update_or_create(
        user=user, defaults={"file_url": key, "file_hash": hashlib.sha256(raw).hexdigest()}
    )
    return saved
