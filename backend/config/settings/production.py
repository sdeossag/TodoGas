from decouple import config
from django.core.exceptions import ImproperlyConfigured

from config import broker as _broker
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

# Broker de Celery: aquí sí se exige lo que cada uno necesita (REDIS_URL con
# redis; la URL de la cola y la región con sqs). Desarrollo no lo exige.
_broker.validar(CELERY_BROKER, REDIS_URL, CELERY_SQS_QUEUE_URL, AWS_REGION)

# La evidencia siempre a S3. El disco del contenedor se pierde en cada
# despliegue, y sin DEBUG Django no sirve /media/: con almacenamiento local las
# fotos, firmas y actas desaparecerían y ni siquiera se verían. Las credenciales
# pueden venir del rol de la tarea de ECS en vez de AWS_ACCESS_KEY_ID.
STORAGES = {**STORAGES, "default": {"BACKEND": S3_STORAGE}}  # noqa: F405

# En producción la web y la API comparten dominio (CloudFront), así que el
# navegador no necesita CORS; sí lo necesita la app Android, que llama desde
# https://localhost (y cualquier web en otro dominio que se agregue a mano).
# La API se autentica con JWT en la cabecera, no con cookies: no hacen falta
# credenciales CORS.
CORS_ALLOWED_ORIGINS = allowed_origins(
    FRONTEND_URL, config("DJANGO_CORS_ALLOWED_ORIGINS", default="")
)

# ── Cabeceras de seguridad ────────────────────────────────────────────────────
# Detrás del ALB de AWS el TLS termina en el balanceador y Django ve HTTP: se
# confía en X-Forwarded-Proto para saber que la petición original era https.
# Por la misma razón hay que poner TRUSTED_PROXY_COUNT en el entorno: 2 con
# CloudFront + ALB (1 si solo hubiera ALB).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# El health check del ALB llega por HTTP y con la IP privada como Host, y
# recibiría la redirección (301) o un 400 por ALLOWED_HOSTS. /health/ lo
# responde HealthCheckMiddleware (config/health.py), que va primero en
# MIDDLEWARE y por eso nunca llega a SecurityMiddleware ni a get_host().
SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("DJANGO_SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Destino de collectstatic (se ejecuta en el build de la imagen).
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# ── Archivos estáticos (panel /admin/) ────────────────────────────────────────
# Gunicorn no sirve /static/: WhiteNoise lo hace desde STATIC_ROOT, justo
# después de SecurityMiddleware. El manifest pone hash en el nombre (caché
# eterna) y exige collectstatic, que el Dockerfile ya corre en el build. Solo
# aquí: desarrollo y pruebas no deben requerir collectstatic.
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ── Base de datos ─────────────────────────────────────────────────────────────
# Una variable vacía cuenta como no definida (ECS entrega "" si el parámetro
# no existe).
#
# Conexiones en el peor caso: cada hilo de gunicorn guarda su conexión abierta
# durante CONN_MAX_AGE, así que una tarea de la API abre hasta
#   GUNICORN_WORKERS x GUNICORN_THREADS = 2 x 4 = 8
# En régimen, con 2 tareas de API + 1 worker de Celery (--concurrency 2) +
# 1 beat + la tarea de migrate de un despliegue:
#   2 x 8 + 2 + 1 + 1 = 20  (19 sin el migrate, que dura segundos)
# Una RDS db.t4g.micro (1 GB) trae max_connections ~ 112, de las que quedan
# ~80 útiles tras las reservadas y las de mantenimiento. Hay holgura, pero
# cada tarea de API más suma 8: con más de ~8 tareas hay que bajar los hilos,
# acortar DB_CONN_MAX_AGE o poner RDS Proxy.
# CONN_HEALTH_CHECKS descarta una conexión muerta (reinicio de la RDS, corte de
# red) antes de usarla, en vez de fallar la primera petición.
DATABASES = {
    "default": {
        **DATABASES["default"],  # noqa: F405
        "CONN_MAX_AGE": int(config("DB_CONN_MAX_AGE", default="") or 60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"sslmode": config("DB_SSLMODE", default="") or "require"},
    }
}

# ── Sentry ────────────────────────────────────────────────────────────────────
# Solo con SENTRY_DSN: vacía o ausente = apagado, y producción arranca igual.
# send_default_pii=False porque hay datos de hospitales (usuarios, IP, cookies
# y cabeceras no deben salir hacia Sentry).
SENTRY_DSN = config_opcional("SENTRY_DSN")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=config("SENTRY_ENVIRONMENT", default="") or "production",
        traces_sample_rate=float(config("SENTRY_TRACES_SAMPLE_RATE", default="") or 0),
        send_default_pii=False,
        integrations=[DjangoIntegration(), CeleryIntegration()],
    )
