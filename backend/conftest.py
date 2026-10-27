import pytest


def pytest_configure():
    pass  # DJANGO_SETTINGS_MODULE ya definido en pytest.ini


@pytest.fixture(autouse=True)
def _almacenamiento_temporal(settings, tmp_path):
    """
    Los archivos que crean las pruebas (firmas, fotos, actas) van a una carpeta
    temporal y no al MEDIA_ROOT de desarrollo.
    """
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path / "media"), "base_url": "/media/"},
        },
    }
    # UserSettingsHolder trae SETTINGS_MODULE = None y seed_demo lo lee: se repone
    # en el holder (que se descarta al terminar la prueba).
    import os

    from django.conf import settings as django_settings

    django_settings._wrapped.SETTINGS_MODULE = os.environ.get("DJANGO_SETTINGS_MODULE", "")
