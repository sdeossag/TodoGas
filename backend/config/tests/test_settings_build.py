"""Settings de build (collectstatic en la imagen Docker).

`config.settings.build` se importa sin ninguna variable de entorno y sirve los
mismos estáticos que producción. Las pruebas que importan settings corren en un
proceso aparte con el entorno vacío, como en test_production.py.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
DOCKERFILE = BACKEND / "Dockerfile"


def entorno_limpio():
    """Solo lo que Python necesita para arrancar: sin DB_*, SECRET ni similares."""
    env = {"PATH": os.environ.get("PATH", "")}
    if "SYSTEMROOT" in os.environ:  # Windows no arranca Python sin esto
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


def correr(codigo):
    return subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=BACKEND,
        env=entorno_limpio(),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_build_importa_sin_variables_de_entorno():
    salida = correr("import config.settings.build")
    assert salida.returncode == 0, salida.stderr[-2000:]


def test_estaticos_de_build_coinciden_con_produccion():
    codigo = (
        "import json, sys\n"
        "import config.settings.build as b\n"
        "p = sys.modules['config.settings.production']\n"
        "def datos(m):\n"
        "    return {\n"
        "        'STATIC_ROOT': str(m.STATIC_ROOT),\n"
        "        'STATIC_URL': m.STATIC_URL,\n"
        "        'STORAGES_STATIC': m.STORAGES['staticfiles'],\n"
        "        'INSTALLED_APPS': list(m.INSTALLED_APPS),\n"
        "        'MIDDLEWARE': list(m.MIDDLEWARE),\n"
        "    }\n"
        "print(json.dumps({'build': datos(b), 'produccion': datos(p)}))\n"
    )
    salida = correr(codigo)
    assert salida.returncode == 0, salida.stderr[-2000:]
    datos = json.loads(salida.stdout.strip().splitlines()[-1])
    assert datos["build"] == datos["produccion"]

    estaticos = datos["build"]["STORAGES_STATIC"]["BACKEND"]
    assert estaticos == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    assert datos["build"]["STATIC_URL"] == "static/"
    assert datos["build"]["STATIC_ROOT"].endswith("staticfiles")
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in datos["build"]["MIDDLEWARE"]


def test_build_no_conecta_a_base_de_datos():
    codigo = (
        "import json\n"
        "import config.settings.build as b\n"
        "print(json.dumps(b.DATABASES['default']['ENGINE']))\n"
    )
    salida = correr(codigo)
    assert salida.returncode == 0, salida.stderr[-2000:]
    assert json.loads(salida.stdout.strip().splitlines()[-1]) == "django.db.backends.dummy"


def test_dockerfile_sin_credenciales_falsas():
    texto = DOCKERFILE.read_text(encoding="utf-8")
    assert "DB_PASSWORD=" not in texto
    assert "DJANGO_SECRET_KEY=" not in texto
    assert "DJANGO_SETTINGS_MODULE=config.settings.build python manage.py collectstatic --noinput" in texto
