"""Settings solo para `collectstatic` en el build de la imagen Docker.

No conecta a nada: la base es `dummy`, y las variables que producción exige al
importarse (base de datos, URLs, clave) se sustituyen por valores de relleno
mientras dura la importación. Los estáticos salen de `production`, así que
STATIC_ROOT, STATIC_URL, STORAGES y WhiteNoise son los mismos que en producción.
No usar para arrancar la app: el resto de los ajustes queda sin validar.
"""

import secrets

import decouple as _decouple

# Lo que el código de producción trata como "no configurado" (ver config_opcional).
_RELLENO = "sin-configurar"
# validar() del broker exige una URL de Redis cuando CELERY_BROKER=redis.
_REDIS_RELLENO = "redis://sin-conexion:6379/0"
_SIN_DEFAULT = object()


def _config_de_build(nombre, default=_SIN_DEFAULT, cast=None):
    """Sustituto de `decouple.config`: nunca lee el entorno ni el .env."""
    if nombre in ("SECRET_KEY", "DJANGO_SECRET_KEY"):
        return secrets.token_urlsafe(50)
    if nombre == "REDIS_URL":
        return _REDIS_RELLENO
    if default is _SIN_DEFAULT:
        return _RELLENO
    return default


_config_original = _decouple.config
_decouple.config = _config_de_build
try:
    from config.settings.production import *  # noqa: F401,F403
finally:
    _decouple.config = _config_original

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
