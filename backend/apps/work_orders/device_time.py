"""
Hora del telefono para lo que el tecnico hizo en campo.

Sin red, respuestas, cierres de checklist y firmas se suben al sincronizar.
Si el servidor les pusiera su propia hora, el acta diria que el trabajo se
hizo cuando volvio la red: es lo que volvia falsas las actas del cliente en
Fracttal ("finalizacion 15:09" de un trabajo hecho a las 10:43). Se acepta la
hora que manda el telefono mientras sea posible: ni en el futuro ni antes de
que existiera la OT. Fuera de eso el reloj del telefono esta mal y manda la
hora del servidor.
"""

from datetime import timedelta

from django.utils import timezone

# Diferencia normal entre el reloj del telefono y el del servidor.
TOLERANCIA = timedelta(minutes=5)


def device_time(valor, work_order):
    """La hora del telefono si es creible; si no (o si no vino), la del servidor."""
    ahora = timezone.now()
    if valor is None:
        return ahora
    if valor > ahora + TOLERANCIA:
        return ahora
    if work_order is not None and valor < work_order.created_at - TOLERANCIA:
        return ahora
    return min(valor, ahora)
