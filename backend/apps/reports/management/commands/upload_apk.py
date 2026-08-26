"""Sube el APK compilado al storage y devuelve la URL de descarga.

    python manage.py upload_apk TodoGas-v1.0.0.apk --apk-version 1.0.0

Con credenciales de AWS la URL es pre-firmada y vive AWS_QUERYSTRING_EXPIRE
(24 h). Sin ellas cae a FileSystemStorage y la URL es local, para pruebas.
"""

import os

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sube el APK a S3 y genera URL de descarga"

    def add_arguments(self, parser):
        parser.add_argument("apk_path", type=str)
        # No puede llamarse --version: BaseCommand ya registra esa opcion para
        # imprimir la version de Django y argparse aborta por el conflicto.
        parser.add_argument("--apk-version", dest="version", default="1.0.0")

    def handle(self, *args, **options):
        apk_path = options["apk_path"]
        version = options["version"]

        if not os.path.isfile(apk_path):
            raise CommandError(f"No existe el archivo: {apk_path}")
        if not apk_path.lower().endswith(".apk"):
            raise CommandError("El archivo no parece un APK.")

        size_mb = os.path.getsize(apk_path) / (1024 * 1024)
        s3_key = f"apk/TodoGas-v{version}.apk"

        with open(apk_path, "rb") as f:
            # AWS_S3_FILE_OVERWRITE = False: si la clave ya existe, el backend
            # guarda con sufijo. Hay que usar la clave devuelta, no la pedida,
            # o la URL apuntaria a la version anterior.
            saved_key = default_storage.save(s3_key, File(f))

        url = default_storage.url(saved_key)

        if saved_key != s3_key:
            self.stdout.write(
                self.style.WARNING(
                    f"Ya existia {s3_key}; se subio como {saved_key}."
                )
            )

        expires_h = getattr(settings, "AWS_QUERYSTRING_EXPIRE", 0) // 3600
        validity = (
            f"URL de descarga (valida {expires_h}h):"
            if getattr(settings, "AWS_ACCESS_KEY_ID", "")
            else "URL de descarga (storage local, sin firmar):"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"APK subido exitosamente ({size_mb:.1f} MB).\n"
                f"{validity}\n{url}"
            )
        )
