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
            "version", "completed_by", "work_order"
        ).prefetch_related("field_responses__field")
        if user.role == "TEC":
            qs = qs.filter(work_order__assigned_to=user)
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

        return Response(ChecklistFieldResponseSerializer(field_response).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        response = self.get_object()
        if response.completed_at:
            return Response(
                {"detail": "El checklist ya está completado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_fields = response.version.fields.filter(is_required=True)
        answered_ids = set(response.field_responses.values_list("field_id", flat=True))
        unanswered = [f.label for f in required_fields if f.id not in answered_ids]

        if unanswered:
            return Response(
                {"detail": f"Campos requeridos sin responder: {', '.join(unanswered)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response.completed_at = timezone.now()
        response.completed_by = request.user
        response.save()

        return Response(ChecklistResponseSerializer(response).data)
