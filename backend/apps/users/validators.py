import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class StrongPasswordValidator:
    """
    Valida que la contraseña cumpla los requisitos mínimos de seguridad:
    - Mínimo 8 caracteres
    - Al menos 1 letra mayúscula
    - Al menos 1 número
    - Al menos 1 carácter especial
    """

    SPECIAL_CHARS = r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>/?\\|`~]'

    def validate(self, password, user=None):
        errors = []
        if len(password) < 8:
            errors.append(
                ValidationError(_("La contraseña debe tener al menos 8 caracteres."), code="password_too_short")
            )
        if not re.search(r"[A-Z]", password):
            errors.append(
                ValidationError(_("La contraseña debe contener al menos una letra mayúscula."), code="no_uppercase")
            )
        if not re.search(r"\d", password):
            errors.append(
                ValidationError(_("La contraseña debe contener al menos un número."), code="no_digit")
            )
        if not re.search(self.SPECIAL_CHARS, password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos un carácter especial (!@#$%^&*...)."),
                    code="no_special",
                )
            )
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "La contraseña debe tener mínimo 8 caracteres, "
            "al menos una letra mayúscula, un número y un carácter especial (!@#$%^&*...)."
        )
