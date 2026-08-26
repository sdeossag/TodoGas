from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# En desarrollo no se requiere Redis — el throttle funciona con memoria local
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Orígenes permitidos en desarrollo (Vite dev server)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# Sin credenciales AWS → almacenamiento local (ver base.py, bloque S3)
# Agrega AWS_ACCESS_KEY_ID y las otras variables AWS al .env para usar S3.

# Celery: en desarrollo y tests las tareas se ejecutan de forma sincrona
# para evitar depender de Redis. Las excepciones dentro de las tareas no
# se propagan al llamador para no romper el flujo de la OT.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
