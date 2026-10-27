import os
from datetime import timedelta

from decouple import config

BASE_DIR = __import__("pathlib").Path(__file__).resolve().parents[2]

# Fuerza mensajes de libpq en ASCII para evitar UnicodeDecodeError de psycopg2
# en Windows con locale español.
os.environ.setdefault("LC_ALL", "C")
os.environ.setdefault("LANG", "C")

# La de desarrollo esta en el codigo: produccion se niega a arrancar con ella.
DEV_SECRET_KEY = "unsafe-development-key"
# Una variable vacia cuenta como ausente.
SECRET_KEY = config("SECRET_KEY", default="") or config("DJANGO_SECRET_KEY", default="") or DEV_SECRET_KEY

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "apps.users",
    "apps.assets",
    "apps.checklists",
    "apps.work_orders",
    "apps.maintenance",
    "apps.evidence",
    "apps.inventory",
    "apps.audit",
    "apps.reports",
    "apps.notifications",
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    # Primero: el ALB consulta /health/ por HTTP y con la IP privada como Host,
    # y todo lo que viene despues (redireccion a HTTPS, CommonMiddleware) la
    # rechazaria. Ver config/health.py.
    "config.health.HealthCheckMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditMiddleware",
]

# La vista previa del acta dice de que OT es el ejemplo en este encabezado;
# sin exponerlo, el navegador no se lo deja leer a la web (otro origen).
CORS_EXPOSE_HEADERS = ["X-Work-Order"]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

AUTH_USER_MODEL = "users.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── AWS S3 ─────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="todogas-media-dev")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-2")
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_EXPIRE = 86400  # URLs pre-firmadas validas 24 h
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

# Django 5.1 elimino DEFAULT_FILE_STORAGE: sigue siendo un setting valido pero
# nadie lo lee, y con el las fotos, firmas y actas iban al disco local aunque
# hubiera claves de AWS. El almacenamiento se configura en STORAGES.
S3_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
LOCAL_STORAGE = "django.core.files.storage.FileSystemStorage"
# Con claves AWS, S3; sin ellas, disco local (desarrollo). Produccion usa S3
# siempre: en ECS las credenciales vienen del rol de la tarea y no hay claves.
USE_S3 = config("USE_S3", default=bool(AWS_ACCESS_KEY_ID), cast=bool)
STORAGES = {
    "default": {"BACKEND": S3_STORAGE if USE_S3 else LOCAL_STORAGE},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.users.validators.StrongPasswordValidator"},
]

# Broker de Celery y caché (ver config/broker.py). CELERY_BROKER es "redis"
# (default) o "sqs". REDIS_URL ya no es obligatoria aquí: solo la pide
# production.py cuando el broker es redis. Si existe, el caché usa Redis; si
# no, la tabla django_cache (la crea `createcachetable` al desplegar).
from config import broker as _broker

CELERY_BROKER = _broker.elegir(config("CELERY_BROKER", default="redis"))
REDIS_URL = config("REDIS_URL", default="")
CELERY_SQS_QUEUE_URL = config("CELERY_SQS_QUEUE_URL", default="")
AWS_REGION = config("AWS_REGION", default="")

CACHES = _broker.cache(REDIS_URL)
globals().update(
    _broker.ajustes_de_celery(CELERY_BROKER, REDIS_URL, CELERY_SQS_QUEUE_URL, AWS_REGION)
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Cuantos proxies propios (ALB, etc.) hay delante de la app. Lo usan la IP de
# auditoria (apps.audit.ip) y el throttling de DRF (NUM_PROXIES). Con 0 se
# ignora X-Forwarded-For, que lo escribe el cliente.
TRUSTED_PROXY_COUNT = config("TRUSTED_PROXY_COUNT", default=0, cast=int)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # Sin esto cada list endpoint devuelve la tabla entera (RF-AC-05,
    # RNF-REN-01). Afecta solo a las acciones `list` de ViewSet y a las
    # ListAPIView: las @action que construyen su propia Response no pasan por
    # paginate_queryset y siguen devolviendo el objeto que ya devolvian.
    "DEFAULT_PAGINATION_CLASS": "config.pagination.DefaultPagination",
    "PAGE_SIZE": 50,
    "NUM_PROXIES": TRUSTED_PROXY_COUNT,
}

# ── Email ──────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="TodoGas CMMS <noreply@todogas.com.co>",
)
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
# Tope de adjuntos por correo al reenviar varias actas juntas. Los buzones del
# cliente aceptan 25-35 MB; 20 deja margen para la codificacion base64 (~33 %).
REPORTS_EMAIL_MAX_BYTES = config("REPORTS_EMAIL_MAX_MB", default=20, cast=int) * 1024 * 1024

# Amazon SES (django_ses.SESBackend). En ECS las credenciales salen del rol de
# la tarea: django-ses lee AWS_ACCESS_KEY_ID de arriba (vacío por defecto, por
# S3) y se lo pasaría a boto3. Con '' boto3 hoy cae a la cadena normal, pero
# dependería de un detalle de boto3; por eso las claves propias de SES van en
# None cuando no hay claves, y el rol queda como única fuente.
AWS_SES_REGION_NAME = config("AWS_SES_REGION_NAME", default="") or "us-east-1"
AWS_SES_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID or None
AWS_SES_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY or None
# El limitador de django-ses (0.5 por defecto) pide ses:GetSendQuota al enviar;
# con ~3.000 correos al mes no hace falta y así el rol necesita solo SendRawEmail.
AWS_SES_AUTO_THROTTLE = None
# Opcional: conjunto de configuración de SES (métricas de rebotes y quejas).
AWS_SES_CONFIGURATION_SET = config("AWS_SES_CONFIGURATION_SET", default="") or None

# Google Maps (decision del 2026-09-24): el servidor convierte el GPS del
# checklist en direccion (Geocoding API) y pone un mapa pequeno en el acta
# (Maps Static API). Sin clave, el acta sale con las coordenadas y nada falla.
def config_opcional(nombre):
    """
    Vacía o "sin-configurar" cuenta como ausente. Parameter Store no admite
    valores vacíos, así que Terraform deja ese relleno hasta que alguien pegue
    la clave real (infra/terraform/ssm.tf).
    """
    valor = config(nombre, default="")
    return "" if valor.strip().lower() == "sin-configurar" else valor


GOOGLE_MAPS_API_KEY = config_opcional("GOOGLE_MAPS_API_KEY")
BACKEND_URL = config("BACKEND_URL", default="http://localhost:8000")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ── Mantenimiento ──────────────────────────────────────────────────────────
# Convertir en OT, cada dia, las tareas pendientes que vencen. Equivale a
# "Permitir que la generacion automatica de OTs se active por la fecha de
# programacion" de Fracttal, que el cliente tiene apagado: alli las OTs las
# arma el planificador desde las tareas pendientes (decision D1). Apagado: el
# proceso diario solo garantiza que cada activo tenga su tarea pendiente.
MAINTENANCE_AUTO_CREATE_WORK_ORDERS = False
