from decouple import config
from django.core.exceptions import ImproperlyConfigured

from config.cors import allowed_origins

from .base import *  # noqa: F401,F403

DEBUG = False

# Sin clave propia los JWT se firmarian con la de desarrollo, que cualquiera
# puede leer en el repositorio: mejor no arrancar que arrancar abierto.
if SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured("Falta SECRET_KEY (o DJANGO_SECRET_KEY) para producción.")
ALLOWED_HOSTS = [host.strip() for host in config("DJANGO_ALLOWED_HOSTS", default="").split(",") if host.strip()]

# Las cookies de sesion y CSRF solo las usa el panel /admin/ (la API va con
# JWT): que nunca viajen sin cifrar.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Sin default: los enlaces de los correos y el CORS de la web salen de aqui, y
# con el localhost de desarrollo producción fallaría sin avisar.
FRONTEND_URL = config("FRONTEND_URL")
BACKEND_URL = config("BACKEND_URL")

# La evidencia siempre a S3. El disco del contenedor se pierde en cada
# despliegue, y sin DEBUG Django no sirve /media/: con almacenamiento local las
# fotos, firmas y actas desaparecerían y ni siquiera se verían. Las credenciales
# pueden venir del rol de la tarea de ECS en vez de AWS_ACCESS_KEY_ID.
STORAGES = {**STORAGES, "default": {"BACKEND": S3_STORAGE}}  # noqa: F405

# La API y la web viven en dominios distintos (VITE_API_BASE_URL de
# frontend/.env.production), y la app Android llama desde https://localhost.
# La API se autentica con JWT en la cabecera, no con cookies: no hacen falta
# credenciales CORS.
CORS_ALLOWED_ORIGINS = allowed_origins(
    FRONTEND_URL, config("DJANGO_CORS_ALLOWED_ORIGINS", default="")
)

# ── Cabeceras de seguridad ────────────────────────────────────────────────────
# Detrás del ALB de AWS el TLS termina en el balanceador y Django ve HTTP: se
# confía en X-Forwarded-Proto para saber que la petición original era https.
# Por la misma razón hay que poner TRUSTED_PROXY_COUNT=1 en el entorno.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# No hay endpoint de health check en la app. El health check del ALB llega por
# HTTP y recibiría la redirección (301): al crear uno, eximirlo con
# SECURE_REDIRECT_EXEMPT, o aceptar 301 en el health check del target group.
SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("DJANGO_SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Destino de collectstatic (se ejecuta en el build de la imagen).
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
