from django.core.files.storage import default_storage
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from apps.users.permissions import IsAdmin

from .models import GeneratedReport
from .serializers import GeneratedReportSerializer


class GeneratedReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = GeneratedReportSerializer

    def get_queryset(self):
        user = self.request.user
        qs = GeneratedReport.objects.select_related(
            "work_order"
        ).prefetch_related("send_logs")

        if user.role == User.Role.ADMIN:
            pass
        elif user.role == User.Role.SUP:
            pass
        elif user.role == User.Role.CLI:
            qs = qs.filter(
                work_order__asset__hospital=user.hospital
            )
        else:
            qs = qs.none()

        wo_id = self.request.query_params.get("work_order")
        if wo_id:
            qs = qs.filter(work_order_id=wo_id)

        hospital_id = self.request.query_params.get("hospital_id")
        if hospital_id:
            qs = qs.filter(work_order__asset__hospital_id=hospital_id)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(generated_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(generated_at__date__lte=date_to)

        wo_number = self.request.query_params.get("wo_number")
        if wo_number:
            qs = qs.filter(work_order__wo_number=wo_number)

        return qs

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        try:
            url = default_storage.url(report.file_url)
        except Exception:
            url = report.file_url
        return Response({"download_url": url})

    @action(detail=True, methods=["post"], url_path="resend-email")
    def resend_email(self, request, pk=None):
        if request.user.role != User.Role.ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        report = self.get_object()
        if not report.work_order_id:
            return Response(
                {"detail": "Este reporte no tiene OT asociada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .tasks import send_report_email
        send_report_email.delay(str(report.work_order_id))
        return Response({"status": "queued"})


class ConsolidatedReportView(APIView):
    """POST /api/reports/consolidated/ — genera PDF consolidado vía Celery."""

    permission_classes = [IsAdmin]

    def post(self, request):
        date_from = request.data.get("date_from")
        date_to = request.data.get("date_to")
        if not date_from or not date_to:
            return Response(
                {"detail": "Se requieren 'date_from' y 'date_to'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import generate_consolidated_report

        result = generate_consolidated_report.delay(
            hospital_id=request.data.get("hospital_id") or None,
            date_from=date_from,
            date_to=date_to,
            task_type=request.data.get("task_type") or None,
            requested_by_id=str(request.user.id),
        )
        return Response({"task_id": result.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)
