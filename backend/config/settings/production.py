from decouple import config

from config.cors import allowed_origins

from .base import *  # noqa: F401,F403

DEBUG = False
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
