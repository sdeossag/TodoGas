import uuid

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.users import scope
from apps.users.models import User
from apps.work_orders.models import WorkOrder

from .models import Photo, Signature
from .serializers import (
    PhotoCreateSerializer,
    PhotoSerializer,
    PhotoUpdateSerializer,
    SignatureCreateSerializer,
    SignatureSerializer,
)


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _can_read_wo(user, wo):
    """Misma logica de visibilidad que WorkOrderViewSet.get_queryset."""
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.SUP:
        return scope.can_see_work_order(user, wo)
    if user.role == User.Role.TEC:
        return wo.assigned_to_id == user.id
    if user.role == User.Role.CLI:
        return wo.status == WorkOrder.Status.COMPLETED and scope.can_see_work_order(user, wo)
    return False


def _can_write_evidence(user, wo):
    """
    Quien puede agregar evidencia: el administrador, el asignado (tecnico o
    supervisor que ejecuta la OT) y, para corregir una OT en revision, el
    supervisor que la ve.
    """
    if user.role == User.Role.ADMIN:
        return True
    if user.role in (User.Role.TEC, User.Role.SUP) and wo.assigned_to_id == user.id:
        return True
    if user.role == User.Role.SUP:
        return wo.status == WorkOrder.Status.IN_REVIEW and scope.can_see_work_order(user, wo)
    return False


def _corrige(user, wo):
    """Administrador o supervisor corrigiendo una OT en revision (2026-10-01)."""
    return wo.status == WorkOrder.Status.IN_REVIEW and user.role in (User.Role.ADMIN, User.Role.SUP)


def _acepta_fotos(user, wo):
    """En proceso, quien la ejecuta; en revision, quien la corrige."""
    return wo.status == WorkOrder.Status.IN_PROGRESS or _corrige(user, wo)


def _get_wo_or_error(work_order_id):
    """Devuelve (wo, None) o (None, Response de error)."""
    if not work_order_id:
        return None, Response(
            {"detail": "Se requiere el parametro work_order."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        wo = WorkOrder.objects.select_related("hospital").get(pk=work_order_id)
    except (WorkOrder.DoesNotExist, Exception):
        return None, Response(
            {"detail": "OT no encontrada."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return wo, None


def _foto_ya_subida(offline_uuid):
    """La foto que ya llego con este offline_uuid, o None. Un uuid invalido es None:
    lo rechaza despues la validacion del serializer."""
    if not offline_uuid:
        return None
    try:
        return Photo.objects.filter(offline_uuid=uuid.UUID(str(offline_uuid))).first()
    except ValueError:
        return None


# ── Photos ─────────────────────────────────────────────────────────────────────

class PhotoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def list(self, request, *args, **kwargs):
        wo, err = _get_wo_or_error(request.query_params.get("work_order"))
        if err:
            return err
        if not _can_read_wo(request.user, wo):
            return Response(status=status.HTTP_403_FORBIDDEN)
        photos = Photo.objects.filter(work_order=wo).select_related(
            "uploaded_by", "task__asset", "hidden_by"
        ).order_by("taken_at")
        # El hospital ve lo mismo que el acta: sin las fotos ocultas.
        if request.user.role == User.Role.CLI:
            photos = photos.filter(hidden=False)
        return Response(PhotoSerializer(photos, many=True, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        wo, err = _get_wo_or_error(request.data.get("work_order"))
        if err:
            return err
        if not _can_write_evidence(request.user, wo):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # La app reintenta la subida cuando no le llega la respuesta. Si la foto
        # ya entro, se devuelve la misma: offline_uuid es unico y crearla de
        # nuevo daria un 500 que la cola reintentaria para siempre. Va antes del
        # control de estado porque el reintento puede llegar con la OT ya en
        # revision.
        existente = _foto_ya_subida(request.data.get("offline_uuid"))
        if existente is not None:
            if existente.work_order_id != wo.id:
                return Response(
                    {"offline_uuid": "Ese identificador es de una foto de otra OT."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                PhotoSerializer(existente, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )

        if not _acepta_fotos(request.user, wo):
            return Response(
                {"detail": "Solo se puede agregar evidencia a una OT en proceso, "
                           "o en revisión para corregirla."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PhotoCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        photo = serializer.save(uploaded_by=request.user)

        cambios = {"work_order": str(wo.id), "caption": photo.caption}
        if wo.status == WorkOrder.Status.IN_REVIEW:
            cambios["correccion"] = True
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.CREATE,
            entity_type="Photo",
            entity_id=photo.id,
            changes=cambios,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(
            PhotoSerializer(photo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


    def partial_update(self, request, pk=None):
        """
        Corregir una foto: cambiar su descripcion u ocultarla del acta. No hay
        borrado: la foto sigue en la OT y en la auditoria.
        """
        try:
            photo = Photo.objects.select_related("work_order").get(pk=pk)
        except (Photo.DoesNotExist, ValueError, Exception):
            return Response(status=status.HTTP_404_NOT_FOUND)
        wo = photo.work_order
        if not (_can_read_wo(request.user, wo) and _can_write_evidence(request.user, wo)):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _acepta_fotos(request.user, wo):
            return Response(
                {"detail": "La foto ya no se puede cambiar: la OT no está en proceso ni en revisión."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PhotoUpdateSerializer(photo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        antes = {"caption": photo.caption, "hidden": photo.hidden}
        datos = serializer.validated_data
        if "caption" in datos:
            photo.caption = datos["caption"]
        if "hidden" in datos and datos["hidden"] != photo.hidden:
            photo.hidden = datos["hidden"]
            photo.hidden_by = request.user if photo.hidden else None
            photo.hidden_at = timezone.now() if photo.hidden else None
        photo.save(update_fields=["caption", "hidden", "hidden_by", "hidden_at"])

        despues = {"caption": photo.caption, "hidden": photo.hidden}
        cambios = {k: {"from": antes[k], "to": despues[k]} for k in antes if antes[k] != despues[k]}
        if cambios:
            if wo.status == WorkOrder.Status.IN_REVIEW:
                cambios["correccion"] = True
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.UPDATE,
                entity_type="Photo",
                entity_id=photo.id,
                changes=cambios,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        return Response(PhotoSerializer(photo, context={"request": request}).data)


# ── Signatures ─────────────────────────────────────────────────────────────────

class SignatureViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        wo, err = _get_wo_or_error(request.query_params.get("work_order"))
        if err:
            return err
        if not _can_read_wo(request.user, wo):
            return Response(status=status.HTTP_403_FORBIDDEN)
        sigs = Signature.objects.filter(work_order=wo).order_by("signed_at")
        return Response(SignatureSerializer(sigs, many=True, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        wo, err = _get_wo_or_error(request.data.get("work_order"))
        if err:
            return err
        if not _can_write_evidence(request.user, wo):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if wo.status != WorkOrder.Status.IN_PROGRESS:
            return Response(
                {"detail": "Solo se puede agregar firmas a OTs en estado IN_PROGRESS."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SignatureCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        sig = serializer.save()

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.CREATE,
            entity_type="Signature",
            entity_id=sig.id,
            changes={
                "work_order": str(wo.id),
                "signature_type": sig.signature_type,
                "signer_name": sig.signer_name,
            },
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(
            SignatureSerializer(sig, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
