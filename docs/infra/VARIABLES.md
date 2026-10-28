# Contrato de variables de entorno (producción)

El código y el Terraform usan estos nombres; si uno cambia, cambian los dos.
La misma imagen Docker corre con tres comandos distintos.

## Procesos

| Proceso | Comando | Cuántos |
|---|---|---|
| API | `CMD` de la imagen (gunicorn con `gunicorn.conf.py`) | 1+ |
| Worker | `celery -A config worker -l info --concurrency 2` | 1 |
| Beat | `celery -A config beat -l info` | **siempre 1** |
| Preparar un despliegue (tarea de una vez) | `python manage.py migrate --noinput && python manage.py createcachetable` | 1 por despliegue |

## Variables

| Variable | Ejemplo | Notas |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | Ya es el default de la imagen |
| `SECRET_KEY` | (Parameter Store) | Producción no arranca sin ella |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | | `DB_PASSWORD` en Parameter Store |
| `DB_SSLMODE` | `require` | Nueva. Default `require` en producción |
| `DB_CONN_MAX_AGE` | `60` | Nueva. Segundos; cuidado con la RDS micro |
| `DJANGO_ALLOWED_HOSTS` | `cmms.todogas.com.co` | CloudFront reenvía el Host del visitante |
| `FRONTEND_URL` | `https://cmms.todogas.com.co` | |
| `BACKEND_URL` | `https://cmms.todogas.com.co` | |
| `DJANGO_CORS_ALLOWED_ORIGINS` | | Extra, separados por coma |
| `TRUSTED_PROXY_COUNT` | `2` | Detrás de CloudFront y del ALB |
| `AWS_STORAGE_BUCKET_NAME` | `todogas-prod-evidencia` | |
| `AWS_S3_REGION_NAME` | `us-east-1` | |
| `AWS_REGION` | `us-east-1` | Nueva. Región de SQS y SES |
| `CELERY_BROKER` | `sqs` o `redis` | Nueva. Default `redis` |
| `REDIS_URL` | `redis://…:6379/0` | Solo con `CELERY_BROKER=redis`. Si existe, el caché de Django también usa Redis |
| `CELERY_SQS_QUEUE_URL` | `https://sqs.us-east-1.amazonaws.com/<cuenta>/todogas-prod-celery` | Nueva. Solo con `sqs`. La cola la crea Terraform |
| `SENTRY_DSN` | | Nueva. Vacía = Sentry apagado |
| `SENTRY_ENVIRONMENT` | `production` | Nueva |
| `SENTRY_TRACES_SAMPLE_RATE` | `0` | Nueva |
| `EMAIL_BACKEND` | `django_ses.SESBackend` | Ya existía; ahora acepta SES |
| `AWS_SES_REGION_NAME` | `us-east-1` | Nueva |
| `DEFAULT_FROM_EMAIL` | `TodoGas CMMS <notificaciones@cmms.todogas.com.co>` | |
| `GOOGLE_MAPS_API_KEY` | (Parameter Store) | |
| `GUNICORN_WORKERS` | `2` | |
| `GUNICORN_THREADS` | `4` | Nueva |
| `GUNICORN_TIMEOUT` | `60` | |

Sin `AWS_ACCESS_KEY_ID`: en ECS las credenciales vienen del rol de la tarea.

## Salud

`GET /health/` responde 200 con `{"status": "ok"}` si la base de datos contesta,
y 503 si no. No pide sesión, no redirige a HTTPS y acepta cualquier `Host`,
porque el balanceador lo consulta por la IP privada.
