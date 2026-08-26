from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = [host.strip() for host in config("DJANGO_ALLOWED_HOSTS", default="").split(",") if host.strip()]
