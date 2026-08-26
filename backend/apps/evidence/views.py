from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.users.models import User
from apps.work_orders.models import WorkOrder

from .models import Photo, Signature
from .serializers import (
    PhotoCreateSerializer,
    PhotoSerializer,
    SignatureCreateSerializer,
    SignatureSerializer,
)


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _can_read_wo(user, wo):
    """Misma logica de visibilidad que WorkOrderViewSet.get_queryset."""
    if user.role in (User.Role.ADMIN, User.Role.SUP):
        return True
    if user.role == User.Role.TEC:
        return wo.assigned_to_id == user.id
    if user.role == User.Role.CLI:
        return (
            wo.status == WorkOrder.Status.COMPLETED
            and wo.asset.hospital_id == user.hospital_id
        )
    return False


def _can_write_evidence(user, wo):
    """Solo ADMIN o TEC asignado pueden agregar evidencia."""
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.TEC:
        return wo.assigned_to_id == user.id
    return False


def _get_wo_or_error(work_order_id):
    """Devuelve (wo, None) o (None, Response de error)."""
    if not work_order_id:
        return None, Response(
            {"detail": "Se requiere el parametro work_order."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        wo = WorkOrder.objects.select_related("asset").get(pk=work_order_id)
    except (WorkOrder.DoesNotExist, Exception):
        return None, Response(
            {"detail": "OT no encontrada."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return wo, None


# ── Photos ─────────────────────────────────────────────────────────────────────

class PhotoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        wo, err = _get_wo_or_error(request.query_params.get("work_order"))
        if err:
            return err
        if not _can_read_wo(request.user, wo):
            return Response(status=status.HTTP_403_FORBIDDEN)
        photos = Photo.objects.filter(work_order=wo).select_related("uploaded_by").order_by("taken_at")
        return Response(PhotoSerializer(photos, many=True, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        wo, err = _get_wo_or_error(request.data.get("work_order"))
        if err:
            return err
        if not _can_write_evidence(request.user, wo):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if wo.status != WorkOrder.Status.IN_PROGRESS:
            return Response(
                {"detail": "Solo se puede agregar evidencia a OTs en estado IN_PROGRESS."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PhotoCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        photo = serializer.save(uploaded_by=request.user)

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.CREATE,
            entity_type="Photo",
            entity_id=photo.id,
            changes={"work_order": str(wo.id), "caption": photo.caption},
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(
            PhotoSerializer(photo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


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
