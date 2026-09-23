from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminOrSup

from .models import ChecklistResponse, ChecklistTemplate, ChecklistTemplateVersion
from .serializers import (
    ChecklistFieldResponseCreateSerializer,
    ChecklistFieldResponseSerializer,
    ChecklistResponseCreateSerializer,
    ChecklistResponseSerializer,
    ChecklistTemplateCreateUpdateSerializer,
    ChecklistTemplateDetailSerializer,
    ChecklistTemplateListSerializer,
    ChecklistTemplateVersionSerializer,
    ChecklistVersionCreateSerializer,
)
from .validators import validate_field_value


class ChecklistTemplateViewSet(viewsets.ModelViewSet):
    queryset = ChecklistTemplate.objects.prefetch_related("versions__fields").all()

    def get_queryset(self):
        qs = ChecklistTemplate.objects.prefetch_related("versions__fields").all()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("true", "1"))
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrSup()]

    def get_serializer_class(self):
        if self.action == "list":
            return ChecklistTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ChecklistTemplateCreateUpdateSerializer
        return ChecklistTemplateDetailSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="publish-version")
    def publish_version(self, request, pk=None):
        template = self.get_object()
        serializer = ChecklistVersionCreateSerializer(
            data=request.data,
            context={"template": template, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        version = serializer.save()
        return Response(
            ChecklistTemplateVersionSerializer(version).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        template = self.get_object()
        version_id = request.data.get("version_id")
        if not version_id:
            return Response(
                {"detail": "Se requiere 'version_id'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        version = get_object_or_404(ChecklistTemplateVersion, pk=version_id, template=template)
        ChecklistTemplateVersion.objects.filter(template=template, is_current=True).update(is_current=False)
        version.is_current = True
        version.save()
        return Response(ChecklistTemplateVersionSerializer(version).data)


class ChecklistResponseViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return ChecklistResponseCreateSerializer
        return ChecklistResponseSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ChecklistResponse.objects.select_related(
            "version", "completed_by", "task__work_order"
        ).prefetch_related("field_responses__field")
        if user.role == "TEC":
            qs = qs.filter(task__work_order__assigned_to=user)
        return qs

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="submit-field")
    def submit_field(self, request, pk=None):
        response = self.get_object()
        if response.completed_at:
            return Response(
                {"detail": "El checklist ya está completado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChecklistFieldResponseCreateSerializer(
            data=request.data,
            context={"response": response, "request": request},
        )
        serializer.is_valid(raise_exception=True)

        field = serializer.validated_data["field"]
        value = serializer.validated_data.get("value", "")
        try:
            extra = validate_field_value(field, value)
        except ValueError as e:
            return Response({"value": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        field_response = serializer.save()
        field_response._out_of_range = extra.get("out_of_range", False)
        # El checklist se crea vacio al programar la tarea: empieza de verdad
        # con la primera respuesta.
        if response.started_at is None:
            response.started_at = timezone.now()
            response.save(update_fields=["started_at"])

        return Response(ChecklistFieldResponseSerializer(field_response).data)

    @action(detail=True, methods=["post"], url_path="block-count")
    def block_count(self, request, pk=None):
        """
        El tecnico encontro otra cantidad de tomas que la del plan. El checklist
        queda con la real; la diferencia la ve el administrador en la OT.
        """
        response = self.get_object()
        if response.completed_at:
            return Response(
                {"detail": "El checklist ya está completado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        grupo = request.data.get("group", "")
        if grupo not in response.version.repeatable_groups:
            return Response(
                {"group": f"«{grupo}» no es un grupo que se repita en este checklist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cuantas = int(request.data.get("count"))
        except (TypeError, ValueError):
            cuantas = 0
        if cuantas < 1:
            return Response(
                {"count": "Tiene que haber al menos una."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Solo se quitan tomas vacias: bajar la cantidad no borra respuestas.
        mayor = max(
            (fr.repetition for fr in response.field_responses.all() if fr.field.group == grupo),
            default=0,
        )
        if cuantas < mayor:
            return Response(
                {"count": f"La {grupo.lower()} {mayor} tiene respuestas; no se puede quitar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response.block_counts = {**response.block_counts, grupo: cuantas}
        response.save(update_fields=["block_counts"])
        return Response(ChecklistResponseSerializer(response).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        response = self.get_object()
        if response.completed_at:
            return Response(
                {"detail": "El checklist ya está completado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Un obligatorio de un grupo repetible lo es en cada toma, no solo en
        # la primera (en Fracttal solo la primera toma tenia obligatorios).
        answered = set(response.field_responses.values_list("field_id", "repetition"))
        unanswered = [
            f"{field.group} {n}: {field.label}" if n else field.label
            for field, n in response.slots()
            if field.is_required and (field.id, n) not in answered
        ]

        if unanswered:
            return Response(
                {"detail": f"Campos requeridos sin responder: {', '.join(unanswered)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response.completed_at = timezone.now()
        response.completed_by = request.user
        response.save()

        return Response(ChecklistResponseSerializer(response).data)
