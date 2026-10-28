"""
Habeas Data (Ley 1581 de 2012, Decreto 1377 de 2013): consentimiento del aviso
de privacidad, datos personales del titular y anonimizacion de cuentas.

Decisiones:
- El consentimiento es por version del aviso (settings.PRIVACY_NOTICE_VERSION);
  subirla obliga a aceptar de nuevo. Las filas solo se insertan.
- Anonimizar NO toca firmas de actas, OT, fotos ni auditoria: son registros que
  exige la normativa sanitaria. Tampoco toca PrivacyConsent (es la prueba de la
  autorizacion). Si borra la firma guardada del usuario.
- Los 2 anos se cuentan desde lo mas reciente entre la desactivacion, el ultimo
  acceso y la creacion de la cuenta: la fecha de desactivacion (deactivated_at)
  se guarda desde la migracion 0005 y para las cuentas ya inactivas se aproximo
  con updated_at. Tomar el maximo evita anonimizar a alguien que acaba de salir.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.audit.ip import client_ip
from apps.audit.models import AuditLog

from . import permisos
from .models import PrivacyConsent

logger = logging.getLogger(__name__)

ANON_DOMAIN = "anonimizado.invalid"
ANON_NAME = "Usuario anonimizado"


class AnonymizeError(ValueError):
    """La cuenta no se puede anonimizar; el mensaje va al administrador."""


def _meta(request):
    return {
        "ip_address": client_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
    }


def consent_status(user):
    version = settings.PRIVACY_NOTICE_VERSION
    vigente = PrivacyConsent.objects.filter(user=user, version=version).first()
    return {
        "required": vigente is None,
        "version": version,
        "accepted_at": vigente.accepted_at if vigente else None,
        "policy_url": settings.PRIVACY_POLICY_URL,
    }


def accept_consent(user, request):
    """Registra la aceptacion de la version vigente (idempotente)."""
    PrivacyConsent.objects.get_or_create(
        user=user, version=settings.PRIVACY_NOTICE_VERSION, defaults=_meta(request),
    )
    return consent_status(user)


def personal_data(user):
    """Datos personales del usuario, sin la imagen de la firma."""
    from apps.evidence.models import Photo, Signature, UserSignature

    firma = UserSignature.objects.filter(user=user).first()
    return {
        "perfil": {
            "id": str(user.id),
            "nombre": user.first_name,
            "apellido": user.last_name,
            "correo": user.email,
            "telefono": user.phone,
            "codigo_empleado": user.employee_code,
            "rol": user.role,
            "activo": user.is_active,
            "hospital": user.hospital.name if user.hospital_id else None,
            "alcance": user.scope_node.path if user.scope_node_id else None,
            "permisos_extra": permisos.extras_de(user),
            "creado": user.created_at,
        },
        "firma_guardada": {
            "tiene": firma is not None,
            "registrada": firma.created_at if firma else None,
            "actualizada": firma.updated_at if firma else None,
        },
        "consentimientos": [
            {"version": c.version, "aceptado": c.accepted_at, "ip": c.ip_address}
            for c in user.privacy_consents.all()
        ],
        "ultimo_acceso": user.last_login,
        "actividad": {
            "ot_asignadas": user.assigned_work_orders.count(),
            "ot_ejecutadas": user.assigned_work_orders.filter(
                status__in=["IN_REVIEW", "COMPLETED"]
            ).count(),
            "firmas_en_actas": Signature.objects.filter(
                work_order__assigned_to=user, signature_type="TECHNICIAN"
            ).count(),
            "fotos": Photo.objects.filter(uploaded_by=user).count(),
        },
        "generado": timezone.now(),
    }


def log_export(target, by, request):
    AuditLog.objects.create(
        user=by, action=AuditLog.Action.EXPORT, entity_type="User", entity_id=target.id,
        changes={"export": "personal-data", "own": target.pk == by.pk}, **_meta(request),
    )


def inactive_since(user):
    """Desde cuando esta inactiva la cuenta (lo mas reciente de tres fechas)."""
    return max(f for f in (user.deactivated_at, user.last_login, user.created_at) if f)


def check_anonymizable(user, now=None):
    now = now or timezone.now()
    if user.email.endswith("@" + ANON_DOMAIN):
        raise AnonymizeError("Esta cuenta ya esta anonimizada.")
    if user.is_active:
        raise AnonymizeError("La cuenta sigue activa: desactivala primero.")
    dias = settings.ANONYMIZE_MIN_INACTIVE_DAYS
    desde = inactive_since(user)
    if now - desde < timedelta(days=dias):
        raise AnonymizeError(
            f"Solo se anonimizan cuentas con mas de {dias} dias de inactividad "
            f"(desde {desde:%Y-%m-%d})."
        )


@transaction.atomic
def anonymize(user, by, request):
    from apps.evidence.models import UserSignature

    check_anonymizable(user)
    corto = str(user.id)[:8]
    user.first_name = ANON_NAME
    user.last_name = f"#{corto}"
    user.email = f"anonimizado-{corto}@{ANON_DOMAIN}"
    user.phone = ""
    user.employee_code = ""
    user.set_unusable_password()
    user.save()
    # La firma guardada tiene su propio archivo; las firmas de las actas son
    # copias aparte (apps.evidence.copia_firma) y no se tocan.
    claves = list(UserSignature.objects.filter(user=user).values_list("file_url", flat=True))
    UserSignature.objects.filter(user=user).delete()
    firmas = len(claves)
    AuditLog.objects.create(
        user=by, action=AuditLog.Action.ANONYMIZE, entity_type="User", entity_id=user.id,
        changes={"firma_guardada_borrada": bool(firmas), "campos": ["nombre", "correo", "telefono", "codigo_empleado"]},
        **_meta(request),
    )
    for clave in claves:
        try:
            default_storage.delete(clave)
        except Exception:  # un archivo huerfano no debe deshacer la anonimizacion
            logger.warning("No se pudo borrar el archivo de firma %s", clave, exc_info=True)
