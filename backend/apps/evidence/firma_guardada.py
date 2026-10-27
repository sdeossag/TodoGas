"""
Firma guardada del usuario: GET / PUT / DELETE /api/evidence/my-signature/.

Solo la propia (siempre request.user, nunca un id de la peticion) y solo para
usuarios del sistema: una cuenta de hospital (CLI) no guarda firma, la de quien
recibe se dibuja en cada visita. La imagen vuelve en data URL para que la app
la guarde en el telefono y la use sin red.
"""

import base64
import hashlib
import logging
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.ip import client_ip
from apps.audit.models import AuditLog
from apps.users.models import User

from .models import UserSignature

logger = logging.getLogger(__name__)

MAX_SAVED_SIGNATURE_BYTES = 1024 * 1024  # 1 MB
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class EsUsuarioDelSistema(BasePermission):
    message = "Las cuentas de hospital no guardan firma: quien recibe firma en cada visita."

    def has_permission(self, request, view):
        return bool(request.user and request.user.role != User.Role.CLI)


class SavedSignatureInputSerializer(serializers.Serializer):
    image_data = serializers.CharField()

    def validate_image_data(self, value):
        if "," in value:
            value = value.split(",", 1)[1]
        try:
            raw = base64.b64decode(value, validate=True)
        except Exception:
            raise serializers.ValidationError("image_data no es un base64 valido.")
        if not raw.startswith(PNG_MAGIC):
            raise serializers.ValidationError("La firma debe ser una imagen PNG.")
        if len(raw) > MAX_SAVED_SIGNATURE_BYTES:
            raise serializers.ValidationError("La firma pesa mas de 1 MB.")
        return raw


def _data_url(saved):
    with default_storage.open(saved.file_url) as f:
        raw = f.read()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def _body(saved):
    if saved is None:
        return {"exists": False}
    return {
        "exists": True,
        "id": str(saved.id),
        "image_data": _data_url(saved),
        "hash_sha256": saved.file_hash,
        "created_at": saved.created_at,
        "updated_at": saved.updated_at,
    }


def _borrar_archivo(key):
    try:
        default_storage.delete(key)
    except Exception:  # un archivo huerfano no debe tumbar la operacion
        logger.warning("No se pudo borrar el archivo de firma %s", key, exc_info=True)


def _auditar(request, saved_id, evento, file_hash):
    AuditLog.objects.create(
        user=request.user,
        action={
            "creada": AuditLog.Action.CREATE,
            "reemplazada": AuditLog.Action.UPDATE,
            "borrada": AuditLog.Action.DELETE,
        }[evento],
        entity_type="UserSignature",
        entity_id=saved_id,
        changes={"evento": evento, "hash_sha256": file_hash},
        ip_address=client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


class MySignatureView(APIView):
    permission_classes = [IsAuthenticated, EsUsuarioDelSistema]

    def get(self, request):
        saved = UserSignature.objects.filter(user=request.user).first()
        if saved is not None and not default_storage.exists(saved.file_url):
            saved = None
        return Response(_body(saved))

    def put(self, request):
        ser = SavedSignatureInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        raw = ser.validated_data["image_data"]
        file_hash = hashlib.sha256(raw).hexdigest()
        key = default_storage.save(
            f"evidence/user-signatures/{request.user.id}/{uuid.uuid4().hex}.png",
            ContentFile(raw),
        )

        with transaction.atomic():
            saved = UserSignature.objects.select_for_update().filter(user=request.user).first()
            vieja = None
            if saved is None:
                saved = UserSignature.objects.create(
                    user=request.user, file_url=key, file_hash=file_hash
                )
                evento, code = "creada", status.HTTP_201_CREATED
            else:
                vieja = saved.file_url
                saved.file_url, saved.file_hash = key, file_hash
                saved.save(update_fields=["file_url", "file_hash", "updated_at"])
                evento, code = "reemplazada", status.HTTP_200_OK
            _auditar(request, saved.id, evento, file_hash)
        if vieja:
            _borrar_archivo(vieja)
        return Response(_body(saved), status=code)

    def delete(self, request):
        with transaction.atomic():
            saved = UserSignature.objects.select_for_update().filter(user=request.user).first()
            if saved is None:
                return Response(
                    {"detail": "No tienes una firma guardada."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            key, saved_id, file_hash = saved.file_url, saved.id, saved.file_hash
            saved.delete()
            _auditar(request, saved_id, "borrada", file_hash)
        _borrar_archivo(key)
        return Response(status=status.HTTP_204_NO_CONTENT)
