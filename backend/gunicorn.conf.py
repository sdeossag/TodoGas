"""Configuración de gunicorn para la imagen (ECS Fargate detrás de un ALB).

`gunicorn config.wsgi:application -c gunicorn.conf.py`. Las variables vienen del
entorno de la tarea; una variable vacía cuenta como no definida.
"""

import os


def _entero(nombre, defecto):
    return int(os.environ.get(nombre) or defecto)


bind = "0.0.0.0:8000"

# Cada hilo mantiene su propia conexión a la base (CONN_MAX_AGE): el total de
# conexiones es workers x threads x tareas. Ver el cálculo en production.py.
workers = _entero("GUNICORN_WORKERS", 2)
threads = _entero("GUNICORN_THREADS", 4)
worker_class = "gthread"
timeout = _entero("GUNICORN_TIMEOUT", 60)

# Contenedor sin disco útil: CloudWatch lee la salida estándar.
accesslog = "-"
errorlog = "-"

# Solo el ALB llega al contenedor (el grupo de seguridad lo garantiza), así que
# se confía en su X-Forwarded-For / X-Forwarded-Proto.
forwarded_allow_ips = "*"

# Recicla los workers de vez en cuando para acotar fugas de memoria (WeasyPrint,
# Pillow); el jitter evita que todos se reinicien a la vez.
max_requests = 1000
max_requests_jitter = 100
