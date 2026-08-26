import django
from django.conf import settings


def pytest_configure():
    pass  # DJANGO_SETTINGS_MODULE ya definido en pytest.ini
