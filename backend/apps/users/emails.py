from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(user, temp_password: str) -> None:
    """Envía las credenciales iniciales a un usuario recién creado."""
    subject = "Bienvenido al sistema TodoGas"
    body = (
        f"Hola {user.first_name},\n\n"
        f"Tu cuenta ha sido creada en el sistema TodoGas.\n\n"
        f"  Email:      {user.email}\n"
        f"  Contraseña: {temp_password}\n\n"
        f"Deberás cambiar tu contraseña en el primer inicio de sesión.\n\n"
        f"Gracias,\nEquipo TodoGas"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, new_password: str) -> None:
    """Envía la nueva contraseña temporal tras un reset forzado por ADMIN."""
    subject = "Restablecimiento de contraseña – TodoGas"
    body = (
        f"Hola {user.first_name},\n\n"
        f"Tu contraseña ha sido restablecida por un administrador.\n\n"
        f"  Nueva contraseña: {new_password}\n\n"
        f"Deberás cambiarla en tu próximo inicio de sesión.\n\n"
        f"Si no solicitaste este cambio, contacta al administrador de inmediato.\n\n"
        f"Equipo TodoGas"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_self_service_reset_email(user, uid: str, token: str) -> None:
    """Envía el enlace para que el propio usuario elija una contraseña nueva."""
    query = urlencode({"uid": uid, "token": token})
    link = f"{settings.FRONTEND_URL.rstrip('/')}/restablecer-contrasena?{query}"
    subject = "Restablecer tu contraseña – TodoGas"
    body = (
        f"Hola {user.first_name},\n\n"
        f"Recibimos una solicitud para restablecer la contraseña de tu cuenta.\n\n"
        f"Abre este enlace para elegir una contraseña nueva (vale 1 hora):\n\n"
        f"  {link}\n\n"
        f"Si no la solicitaste, ignora este correo: tu contraseña no cambiará.\n\n"
        f"Equipo TodoGas"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
