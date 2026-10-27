"""Importacion de activos desde Excel de Fracttal (solo ADMIN)."""

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.ip import client_ip
from apps.users.permissions import IsAdmin

from . import importacion_fracttal as imp

MAX_BYTES = 10 * 1024 * 1024


class _Base(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser]

    def _leer(self, request):
        """Devuelve (ubicaciones, equipos, nombres) o lanza ImportacionError."""
        archivos = {k: request.FILES.get(k) for k in ("ubicaciones", "equipos")}
        if not any(archivos.values()):
            raise imp.ImportacionError("Sube al menos un archivo: «ubicaciones» o «equipos».")
        for tipo, archivo in archivos.items():
            if archivo is None:
                continue
            if not archivo.name.lower().endswith(".xlsx"):
                raise imp.ImportacionError(f"El archivo de {tipo} debe ser un Excel .xlsx.")
            if archivo.size > MAX_BYTES:
                raise imp.ImportacionError(f"El archivo de {tipo} supera los 10 MB.")
        ubicaciones = imp.leer_ubicaciones(archivos["ubicaciones"]) if archivos["ubicaciones"] else []
        equipos = imp.leer_equipos(archivos["equipos"]) if archivos["equipos"] else []
        nombres = {k: a.name for k, a in archivos.items() if a}
        return ubicaciones, equipos, nombres


class ImportacionFracttalPreviewView(_Base):
    """POST /api/assets/import/fracttal/preview/ — no escribe nada."""

    def post(self, request):
        try:
            ubicaciones, equipos, _ = self._leer(request)
        except imp.ImportacionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        plan = imp.planificar(ubicaciones, equipos)
        return Response(plan.resumen())


class ImportacionFracttalView(_Base):
    """POST /api/assets/import/fracttal/ — rehace el plan y, sin errores, lo aplica."""

    def post(self, request):
        try:
            ubicaciones, equipos, nombres = self._leer(request)
            plan = imp.planificar(ubicaciones, equipos)
            if plan.errores:
                return Response(plan.resumen(), status=status.HTTP_400_BAD_REQUEST)
            conteos = imp.aplicar(plan, request.user)
        except imp.ImportacionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        resumen = plan.resumen(aplicado=True)
        imp.auditar(
            request.user, nombres, resumen, conteos,
            ip=client_ip(request), user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        resumen["applied_counts"] = conteos
        return Response(resumen, status=status.HTTP_201_CREATED)
