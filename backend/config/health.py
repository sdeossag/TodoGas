"""Health check del balanceador (ALB) de AWS.

Es un middleware y no una vista de DRF a propósito: el ALB consulta por HTTP y
con la IP privada de la tarea como Host. Una vista pasaría por
SecurityMiddleware (redirección a HTTPS, 301) y por CommonMiddleware
(`get_host()` contra ALLOWED_HOSTS, 400). Aquí se responde antes de todo eso y
sin llamar nunca a `request.get_host()`.

También queda fuera de CSRF, de la sesión, del throttling de DRF y de la
auditoría: el ALB lo llama cada pocos segundos desde varias zonas.
"""

import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)

RUTA = "/health/"


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ruta exacta y solo GET/HEAD: cualquier otra cosa sigue el flujo normal.
        if request.path_info == RUTA and request.method in ("GET", "HEAD"):
            return self.responder()
        return self.get_response(request)

    @staticmethod
    def responder():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            # El detalle va al log (CloudWatch), nunca al cuerpo: lo ve quien
            # llegue al balanceador.
            logger.exception("Health check: la base de datos no contesta")
            return JsonResponse({"status": "error"}, status=503)
        return JsonResponse({"status": "ok"})
