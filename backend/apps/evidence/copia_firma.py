"""
Copia de la firma guardada del usuario a una OT.

La firma de la OT es siempre un archivo propio: cambiar o borrar despues la
firma guardada no toca las OT ya firmadas ni su acta. La usan la firma del
tecnico (use_saved) y la firma de validacion de la aprobacion.
"""

import hashlib
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import UserSignature


def leer_firma_guardada(user):
    """Bytes de la firma guardada del usuario, o None si no la tiene o su archivo no existe."""
    saved = UserSignature.objects.filter(user=user).first()
    if saved is None or not default_storage.exists(saved.file_url):
        return None
    with default_storage.open(saved.file_url) as f:
        return f.read()


def guardar_copia_de_firma(work_order, signature_type, img_bytes):
    """Guarda `img_bytes` como archivo propio de la OT. Devuelve (clave_de_storage, sha256)."""
    key = default_storage.save(
        f"evidence/signatures/{work_order.id}/{signature_type}_{uuid.uuid4().hex}.png",
        ContentFile(img_bytes),
    )
    return key, hashlib.sha256(img_bytes).hexdigest()
