from django.core.files.storage import default_storage
from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users import scope
from apps.users.models import User
from apps.users.permissions import IsAdmin

from .models import GeneratedReport, ReportSettings
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
            "work_order", "work_order__hospital"
        ).prefetch_related("send_logs")

        # Hospital o parte del arbol del usuario (apps.users.scope).
        if user.role in (User.Role.ADMIN, User.Role.SUP):
            qs = scope.work_orders(qs, user, prefix="work_order__")
        elif user.role == User.Role.CLI:
            qs = scope.work_orders(
                qs.filter(work_order__status="COMPLETED"), user, prefix="work_order__"
            )
        else:
            qs = qs.none()

        wo_id = self.request.query_params.get("work_order")
        if wo_id:
            qs = qs.filter(work_order_id=wo_id)

        hospital_id = self.request.query_params.get("hospital_id")
        if hospital_id:
            qs = qs.filter(work_order__hospital_id=hospital_id)

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


def _configuracion_del_acta(ajustes):
    from .options import CATALOGO, SIEMPRE_INCLUIDO, efectivas

    return {
        "options": efectivas(ajustes.options),
        "catalog": [{"key": k, "section": s, "label": l} for k, s, l in CATALOGO],
        "always_included": SIEMPRE_INCLUIDO,
        "updated_at": ajustes.updated_at,
        "updated_by_name": (
            f"{ajustes.updated_by.first_name} {ajustes.updated_by.last_name}".strip()
            if ajustes.updated_by else None
        ),
    }


def _opciones_validas(data):
    """Solo claves del catalogo y valores si/no; si no, un mensaje de error."""
    from .options import CLAVES

    opciones = data.get("options")
    if not isinstance(opciones, dict):
        return None, "Falta 'options' con los interruptores del acta."
    desconocidas = sorted(set(opciones) - CLAVES)
    if desconocidas:
        return None, f"Opciones desconocidas: {', '.join(desconocidas)}."
    if any(not isinstance(v, bool) for v in opciones.values()):
        return None, "Cada opción es verdadero o falso."
    return opciones, None


class ReportSettingsView(APIView):
    """
    GET/PATCH /api/report-settings/ — que imprime el acta (#107). Un solo
    formato para todas las actas nuevas; las ya generadas no cambian.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(_configuracion_del_acta(ReportSettings.current()))

    def patch(self, request):
        opciones, error = _opciones_validas(request.data)
        if error:
            return Response({"options": error}, status=status.HTTP_400_BAD_REQUEST)
        ajustes = ReportSettings.current()
        ajustes.options = {**ajustes.options, **opciones}
        ajustes.updated_by = request.user
        ajustes.save()
        return Response(_configuracion_del_acta(ajustes))


class ReportSettingsPreviewView(APIView):
    """
    POST /api/report-settings/preview/ — el acta de la ultima OT finalizada
    como quedaria con estas opciones, antes de guardarlas. No se guarda ni
    se registra.
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        from apps.work_orders.models import WorkOrder

        from .generator import preview_service_report_pdf

        opciones, error = _opciones_validas(request.data)
        if error:
            return Response({"options": error}, status=status.HTTP_400_BAD_REQUEST)
        ot = (
            WorkOrder.objects.filter(status=WorkOrder.Status.COMPLETED)
            .select_related("hospital", "assigned_to", "location")
            .order_by("-completed_at")
            .first()
        )
        if ot is None:
            return Response(
                {"detail": "Todavía no hay OTs finalizadas para mostrar un acta de ejemplo."},
                status=status.HTTP_404_NOT_FOUND,
            )
        pdf = preview_service_report_pdf(ot, {**ReportSettings.current().options, **opciones})
        respuesta = HttpResponse(pdf, content_type="application/pdf")
        respuesta["Content-Disposition"] = f'inline; filename="vista-previa-{ot.wo_code}.pdf"'
        respuesta["X-Work-Order"] = ot.wo_code
        return respuesta
