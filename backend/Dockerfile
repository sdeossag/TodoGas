FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc libpango-1.0-0 libpangoft2-1.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.production

# collectstatic no toca la base ni S3, pero production.py exige estas variables
# al importarse: valores falsos solo para este paso, no quedan en la imagen.
RUN DJANGO_SECRET_KEY=build-only-not-a-secret \
    FRONTEND_URL=http://build.invalid BACKEND_URL=http://build.invalid \
    python manage.py collectstatic --noinput

RUN useradd --system --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60}"]
