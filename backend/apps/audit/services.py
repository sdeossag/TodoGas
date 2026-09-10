"""Escritura de auditoria desde las vistas, para lo que el middleware no ve.

AuditMiddleware resuelve el autor con `request.user`, asi que solo sabe quien
actua cuando la peticion ya viene autenticada. En /api/auth/login/ todavia es
anonima: por eso todos los inicios de sesion quedaban atribuidos a "Sistema" y
los intentos fallidos no decian contra que cuenta iban. LoginView si conoce esa
identidad, y la registra con esta funcion.
"""

import logging
import uuid

from .models import AuditLog

logger = logging.getLogger(__name__)

# Tipo de entidad unico para los eventos de autenticacion. Antes se guardaba la
# ruta cruda ('/api/auth/login/'), que no coincide con ninguna opcion del filtro
# de la pantalla de auditoria y por tanto dejaba esos eventos sin poder filtrar.
AUTH_ENTITY_TYPE = "Authentication"

_SENTINEL_UUID = uuid.UUID(int=0)


class LoginOutcome:
    SUCCESS = "success"
    BAD_CREDENTIALS = "bad_credentials"
    UNKNOWN_EMAIL = "unknown_email"
    INACTIVE = "inactive"
    THROTTLED = "throttled"
    INCOMPLETE = "incomplete"


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def log_login_attempt(request, *, email, outcome, user=None, target=None):
    """Registra un intento de inicio de sesion con su identidad.

    `user` solo se rellena cuando la autenticacion tuvo exito: es quien actuo.
    En un intento fallido el autor es desconocido —atribuirselo al dueño de la
    cuenta daria a entender que fue el—, asi que se deja en None y la cuenta
    apuntada viaja en `target` y en el email, que es lo que hace falta para
    investigar un ataque de fuerza bruta.
    """
    changes = {"email": email, "outcome": outcome}
    if outcome != LoginOutcome.SUCCESS:
        changes["failed"] = True

    subject = user or target
    try:
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.LOGIN,
            entity_type=AUTH_ENTITY_TYPE,
            entity_id=subject.id if subject else _SENTINEL_UUID,
            changes=changes,
            ip_address=client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
    except Exception:
        # La auditoria no puede tumbar un login. Queda en el log del servidor.
        logger.exception(
            "No se pudo registrar en auditoria el intento de login de %s", email
        )
