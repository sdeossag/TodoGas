FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libcurl y libssl: pycurl, que el worker de Celery necesita para leer SQS (el
# cliente asíncrono de kombu solo existe con curl). No trae wheels de Linux.
RUN apt-get update && apt-get install -y \
    libpq-dev gcc libpango-1.0-0 libpangoft2-1.0-0 \
    libffi-dev libcairo2 libcurl4-openssl-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN PYCURL_SSL_LIBRARY=openssl pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.production

# collectstatic usa config.settings.build: no necesita variables de entorno, no
# conecta a la base ni a S3/broker, y sirve los mismos estaticos que produccion.
RUN DJANGO_SETTINGS_MODULE=config.settings.build python manage.py collectstatic --noinput

RUN useradd --system --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

# La misma imagen corre con distintos comandos (ver docs/infra/VARIABLES.md);
# en ECS se cambian con "command" de la definición de tarea:
#   API (este CMD):  gunicorn config.wsgi:application -c gunicorn.conf.py
#   Worker:          celery -A config worker -l info --concurrency 2
#   Beat (siempre 1): celery -A config beat -l info
#   Despliegue (tarea de una vez):
#     sh -c "python manage.py migrate --noinput && python manage.py createcachetable"
# Workers, hilos y timeout de gunicorn: GUNICORN_WORKERS, GUNICORN_THREADS y
# GUNICORN_TIMEOUT (gunicorn.conf.py). /health/ lo responde la propia app.
CMD ["gunicorn", "config.wsgi:application", "-c", "gunicorn.conf.py"]
