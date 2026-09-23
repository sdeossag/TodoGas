"""
API de hallazgos (bloque E): /api/findings/.

El tecnico los registra en su OT abierta (tambien sin red: el id lo pone el
telefono y un reintento no duplica); el planificador ve los pendientes en su
bandeja (?status=PENDING) y los convierte en correctivo o los descarta; el
hospital los ve en sus OTs finalizadas. Todo dentro del alcance del usuario.
"""

import uuid

from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users import scope
from apps.users.models import User
from apps.users.permissions import IsAdminOrSup

from . import findings as servicio
from .device_time import device_time
from .models import Finding, WorkOrder


class FindingSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    reported_at = serializers.DateTimeField(required=False, allow_null=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    asset_info = serializers.SerializerMethodField()
    work_order_info = serializers.SerializerMethodField()
    reported_by_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()
    corrective_task_info = serializers.SerializerMethodField()
    photos_count = serializers.SerializerMethodField()

    class Meta:
        model = Finding
        fields = [
            "id", "work_order", "asset", "description", "severity", "severity_display",
            "out_of_service", "resolved_on_site", "resolution_notes",
            "reported_by", "reported_by_name", "reported_at",
            "status", "status_display", "decided_by_name", "decided_at", "decision_note",
            "corrective_task", "corrective_task_info",
            "asset_info", "work_order_info", "photos_count",
        ]
        read_only_fields = [
            "reported_by", "status", "decided_at", "decision_note", "corrective_task",
        ]

    def get_asset_info(self, obj):
        a = obj.asset
        return {"id": str(a.id), "code": a.code, "name": a.name,
                "node_path": a.node.path if a.node_id else ""}

    def get_work_order_info(self, obj):
        wo = obj.work_order
        return {"id": str(wo.id), "wo_code": wo.wo_code, "status": wo.status,
                "hospital": wo.hospital.name}

    def get_reported_by_name(self, obj):
        u = obj.reported_by
        return f"{u.first_name} {u.last_name}".strip()

    def get_decided_by_name(self, obj):
        u = obj.decided_by
        return f"{u.first_name} {u.last_name}".strip() if u else None

    def get_corrective_task_info(self, obj):
        t = obj.corrective_task
        if t is None:
            return None
        wo = t.work_order
        return {"id": str(t.id), "status": t.status, "scheduled_date": t.scheduled_date,
                "work_order": {"id": str(wo.id), "wo_code": wo.wo_code} if wo else None}

    def get_photos_count(self, obj):
        return obj.n_fotos if hasattr(obj, "n_fotos") else obj.photos.count()

    def validate(self, attrs):
        wo = attrs.get("work_order") or getattr(self.instance, "work_order", None)
        asset = attrs.get("asset") or getattr(self.instance, "asset", None)
        if self.instance is not None and "work_order" in attrs and attrs["work_order"] != self.instance.work_order:
            raise serializers.ValidationError({"work_order": "Un hallazgo no cambia de OT."})
        if wo is not None and asset is not None and not wo.tasks.filter(asset=asset).exclude(
            status="CANCELLED"
        ).exists():
            raise serializers.ValidationError(
                {"asset": "El equipo no es parte de esta OT."}
            )
        if not (attrs.get("description", getattr(self.instance, "description", "")) or "").strip():
            raise serializers.ValidationError({"description": "Describe el hallazgo."})
        resuelto = attrs.get("resolved_on_site", getattr(self.instance, "resolved_on_site", False))
        notas = attrs.get("resolution_notes", getattr(self.instance, "resolution_notes", ""))
        if resuelto and not (notas or "").strip():
            raise serializers.ValidationError(
                {"resolution_notes": "Si se resolvió en sitio, di qué se hizo."}
            )
        return attrs


def _puede_registrar(user, wo):
    if user.role in (User.Role.ADMIN, User.Role.SUP):
        return scope.can_see_work_order(user, wo)
    return user.role == User.Role.TEC and wo.assigned_to_id == user.id


class FindingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    serializer_class = FindingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Finding.objects.select_related(
            "asset__node", "work_order__hospital", "reported_by", "decided_by",
            "corrective_task__work_order",
        ).annotate(n_fotos=Count("photos"))
        if user.role == User.Role.TEC:
            qs = qs.filter(work_order__assigned_to=user)
        elif user.role == User.Role.CLI:
            # Como sus OTs: lo de visitas finalizadas, dentro de su alcance.
            qs = scope.work_orders(qs.filter(work_order__status=WorkOrder.Status.COMPLETED),
                                   user, prefix="work_order__")
        elif user.role in (User.Role.ADMIN, User.Role.SUP):
            qs = scope.work_orders(qs, user, prefix="work_order__")
        else:
            return qs.none()

        p = self.request.query_params
        if p.get("work_order"):
            qs = qs.filter(work_order_id=p["work_order"])
        if p.get("asset"):
            qs = qs.filter(asset_id=p["asset"])
        estados = [e for e in p.get("status", "").split(",") if e]
        if estados:
            qs = qs.filter(status__in=estados)
        if p.get("severity"):
            qs = qs.filter(severity__in=p["severity"].split(","))
        if p.get("hospital_id"):
            qs = qs.filter(work_order__hospital_id=p["hospital_id"])
        # La bandeja muestra lo mas grave primero.
        orden = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        from django.db.models import Case, IntegerField, Value, When

        return qs.annotate(
            _grave=Case(*[When(severity=k, then=Value(v)) for k, v in orden.items()],
                        output_field=IntegerField())
        ).order_by("_grave", "-reported_at")

    # ── Registrar y corregir (tecnico, con la OT abierta) ────────────────────

    def create(self, request, *args, **kwargs):
        if request.user.role == User.Role.CLI:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # Reintento desde la cola offline: el hallazgo ya llego, no se duplica.
        try:
            id_telefono = uuid.UUID(str(request.data.get("id"))) if request.data.get("id") else None
        except ValueError:
            return Response({"id": "Identificador inválido."}, status=status.HTTP_400_BAD_REQUEST)
        existente = Finding.objects.filter(pk=id_telefono).first() if id_telefono else None
        if existente is not None:
            if not _puede_registrar(request.user, existente.work_order):
                return Response(status=status.HTTP_403_FORBIDDEN)
            return Response(self.get_serializer(existente).data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wo = serializer.validated_data["work_order"]
        if not _puede_registrar(request.user, wo):
            return Response(
                {"detail": "Solo el técnico de la OT registra sus hallazgos."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if wo.status not in servicio.EDITABLE:
            return Response(
                {"detail": "La OT ya se envió a revisión: no se agregan hallazgos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        datos = serializer.validated_data
        hallazgo = serializer.save(
            reported_by=request.user,
            reported_at=device_time(datos.get("reported_at"), wo),
            status=Finding.Status.RESOLVED if datos.get("resolved_on_site") else Finding.Status.PENDING,
        )
        return Response(self.get_serializer(hallazgo).data, status=status.HTTP_201_CREATED)

    def _editable(self, request, hallazgo):
        if request.user.role == User.Role.CLI or not _puede_registrar(request.user, hallazgo.work_order):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if hallazgo.work_order.status not in servicio.EDITABLE:
            return Response(
                {"detail": "La OT ya se envió a revisión: el hallazgo es evidencia y no se modifica."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def update(self, request, *args, **kwargs):
        hallazgo = self.get_object()
        if (bloqueo := self._editable(request, hallazgo)) is not None:
            return bloqueo
        serializer = self.get_serializer(hallazgo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        resuelto = serializer.validated_data.get("resolved_on_site", hallazgo.resolved_on_site)
        # La hora del reporte y el id los fija el alta; editar no los cambia.
        serializer.validated_data.pop("reported_at", None)
        serializer.validated_data.pop("id", None)
        hallazgo = serializer.save(
            status=Finding.Status.RESOLVED if resuelto else Finding.Status.PENDING
        )
        return Response(self.get_serializer(hallazgo).data)

    def destroy(self, request, *args, **kwargs):
        hallazgo = self.get_object()
        if (bloqueo := self._editable(request, hallazgo)) is not None:
            return bloqueo
        # Sus fotos quedan como evidencia de la OT, sin hallazgo.
        hallazgo.photos.update(finding=None)
        hallazgo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Bandeja del planificador ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSup])
    def convert(self, request, pk=None):
        hallazgo = self.get_object()
        fecha = request.data.get("scheduled_date")
        fecha = parse_date(fecha) if isinstance(fecha, str) else None
        try:
            hallazgo = servicio.convert(hallazgo, request.user, scheduled_date=fecha,
                                        note=request.data.get("note", ""))
        except servicio.FindingStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_queryset().get(pk=hallazgo.pk)).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSup])
    def dismiss(self, request, pk=None):
        hallazgo = self.get_object()
        try:
            hallazgo = servicio.dismiss(hallazgo, request.user, request.data.get("note", ""))
        except servicio.FindingStateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_queryset().get(pk=hallazgo.pk)).data)

    @action(detail=False, methods=["get"], url_path="summary", permission_classes=[IsAdminOrSup])
    def summary(self, request):
        """Cuántos pendientes hay en la bandeja, por severidad (para el menú y el tablero)."""
        pendientes = self.get_queryset().filter(
            status=Finding.Status.PENDING,
            work_order__status__in=servicio.DECIDIBLE,
        )
        por_sev = dict(pendientes.order_by().values_list("severity").annotate(n=Count("id")))
        return Response({
            "pending": sum(por_sev.values()),
            "by_severity": por_sev,
            "serious": pendientes.filter(Q(severity="CRITICAL") | Q(out_of_service=True)).count(),
        })
