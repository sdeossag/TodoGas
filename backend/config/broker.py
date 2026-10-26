"""Broker de Celery (Redis o SQS) y caché de Django según el entorno.

`CELERY_BROKER` se decide con el cliente sin tocar código: "redis" (default) o
"sqs". Aquí solo se arman los ajustes; `base.py` los aplica y `production.py`
llama a `validar()`. La validación no vive en `base.py` porque desarrollo
también lo importa y allí las tareas corren eager y el caché es local: no
debería exigir REDIS_URL ni una cola de SQS.
"""

from django.core.exceptions import ImproperlyConfigured

BROKERS = ("redis", "sqs")

# El PDF del acta es la tarea más larga. Si el mensaje vuelve a ser visible
# antes de que el worker termine, SQS lo entrega otra vez y se genera dos veces.
SQS_VISIBILITY_TIMEOUT = 15 * 60
# Long polling: SQS cobra por pedido, y con 20 s de espera el worker no hace
# un pedido vacío por segundo. 20 es el máximo que admite SQS.
SQS_WAIT_TIME_SECONDS = 20


def nombre_de_la_cola(url):
    """El nombre es el último tramo de la URL: https://sqs.<region>.amazonaws.com/<cuenta>/<nombre>."""
    return url.rstrip("/").rsplit("/", 1)[-1]


def elegir(broker):
    broker = (broker or "redis").strip().lower()
    if broker not in BROKERS:
        raise ImproperlyConfigured(
            f"CELERY_BROKER debe ser 'redis' o 'sqs' (llegó {broker!r})."
        )
    return broker


def validar(broker, redis_url, queue_url, region):
    """Falla al arrancar, con el nombre de la variable que falta."""
    if broker == "redis" and not redis_url:
        raise ImproperlyConfigured("Falta REDIS_URL: CELERY_BROKER=redis la necesita.")
    if broker == "sqs":
        if not queue_url:
            raise ImproperlyConfigured("Falta CELERY_SQS_QUEUE_URL: CELERY_BROKER=sqs la necesita.")
        if not region:
            raise ImproperlyConfigured("Falta AWS_REGION: CELERY_BROKER=sqs la necesita.")


def cache(redis_url):
    """Redis si hay REDIS_URL; si no, la base (tabla django_cache, de `createcachetable`)."""
    if redis_url:
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": redis_url,
            }
        }
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
        }
    }


def ajustes_de_celery(broker, redis_url, queue_url, region):
    """Los CELERY_* según el broker (la app los lee con namespace CELERY)."""
    # Nadie lee resultados de tareas (solo se devuelve el id al pedir el
    # consolidado), así que no se guardan: con Redis ocuparían memoria y SQS
    # no tiene dónde ponerlos.
    comunes = {"CELERY_TASK_IGNORE_RESULT": True}
    if broker == "redis":
        return {**comunes, "CELERY_BROKER_URL": redis_url}

    cola = nombre_de_la_cola(queue_url) if queue_url else None
    return {
        **comunes,
        # Sin usuario ni clave: boto3 toma las credenciales del rol de la tarea de ECS.
        "CELERY_BROKER_URL": "sqs://",
        "CELERY_BROKER_TRANSPORT_OPTIONS": {
            "region": region,
            # Con la cola declarada por URL el worker no necesita ListQueues
            # ni CreateQueue (la cola la crea Terraform).
            "predefined_queues": {cola: {"url": queue_url}} if cola else {},
            "visibility_timeout": SQS_VISIBILITY_TIMEOUT,
            "wait_time_seconds": SQS_WAIT_TIME_SECONDS,
            "polling_interval": 1,
        },
        "CELERY_TASK_DEFAULT_QUEUE": cola,
        # Con predefined_queues cualquier otra cola es un error. El control
        # remoto (pidbox) crearía colas fanout, que SQS no tiene.
        "CELERY_TASK_CREATE_MISSING_QUEUES": False,
        "CELERY_WORKER_ENABLE_REMOTE_CONTROL": False,
        "CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP": True,
    }
