"""Correo por Amazon SES en producción, SMTP y consola en el resto.

Los ajustes se leen al importar, y django-ses lee los suyos al importarse, así
que cada caso corre en un proceso aparte con `importar()`.
"""

import json

from config.tests.test_production import importar

SES = "django_ses.SESBackend"

# Manda un correo real con el cliente de boto3 falso y cuenta qué se le pidió.
ENVIAR = (
    "import json\n"
    "from unittest import mock\n"
    "from django.core.mail import send_mail, EmailMessage\n"
    "from django.conf import settings\n"
    "sesion = mock.MagicMock()\n"
    "cliente = sesion.return_value.client.return_value\n"
    "cliente.send_raw_email.return_value = {'MessageId': 'm1',"
    " 'ResponseMetadata': {'RequestId': 'r1'}}\n"
    "with mock.patch('boto3.Session', sesion):\n"
    "    n = send_mail('Asunto', 'Cuerpo', settings.DEFAULT_FROM_EMAIL,"
    " ['a@hospital.co', 'b@hospital.co'])\n"
    "kw = cliente.send_raw_email.call_args.kwargs\n"
    "print(json.dumps({'n': n, 'source': kw['Source'],"
    " 'destinations': kw['Destinations'],"
    " 'sesion': sesion.call_args.kwargs,"
    " 'cliente': sesion.return_value.client.call_args.kwargs.get('region_name')}))\n"
)

# Desarrollo fuerza consola; el backend elegido por entorno se lee en producción.
PRODUCCION = dict(FRONTEND_URL="https://cmms.todogas.com.co", BACKEND_URL="https://api.cmms.todogas.com.co")


def correr(codigo, **entorno):
    salida = importar("config.settings.production", codigo, **{**PRODUCCION, **entorno})
    assert salida.returncode == 0, salida.stderr[-2000:]
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_la_region_y_el_backend_de_ses_quedan_configurados():
    r = correr(
        "import json, django_ses.settings as s\n"
        "from django.conf import settings\n"
        "print(json.dumps({'b': settings.EMAIL_BACKEND, 'r': s.AWS_SES_REGION_NAME}))",
        EMAIL_BACKEND=SES, AWS_SES_REGION_NAME="us-east-2",
    )
    assert r == {"b": SES, "r": "us-east-2"}


def test_la_region_por_defecto_es_us_east_1():
    r = correr(
        "import json, django_ses.settings as s\n"
        "print(json.dumps({'r': s.AWS_SES_REGION_NAME}))",
        EMAIL_BACKEND=SES, AWS_SES_REGION_NAME="",
    )
    assert r == {"r": "us-east-1"}


def test_send_mail_arma_remitente_y_destinatarios():
    r = correr(
        ENVIAR, EMAIL_BACKEND=SES, AWS_ACCESS_KEY_ID="", AWS_SECRET_ACCESS_KEY="",
        DEFAULT_FROM_EMAIL="TodoGas CMMS <notificaciones@cmms.todogas.com.co>",
    )
    assert r["n"] == 1
    assert r["source"] == "TodoGas CMMS <notificaciones@cmms.todogas.com.co>"
    assert r["destinations"] == ["a@hospital.co", "b@hospital.co"]
    assert r["cliente"] == "us-east-1"


def test_sin_claves_no_pasa_credenciales_vacias_a_boto3():
    """Con '' boto3 no cae a la cadena de credenciales (el rol de ECS)."""
    r = correr(ENVIAR, EMAIL_BACKEND=SES, AWS_ACCESS_KEY_ID="", AWS_SECRET_ACCESS_KEY="")
    assert not r["sesion"].get("aws_access_key_id")
    assert not r["sesion"].get("aws_secret_access_key")


def test_con_claves_explicitas_se_usan():
    r = correr(ENVIAR, EMAIL_BACKEND=SES, AWS_ACCESS_KEY_ID="AKIAX", AWS_SECRET_ACCESS_KEY="s")
    assert r["sesion"]["aws_access_key_id"] == "AKIAX"


def test_conjunto_de_configuracion_opcional():
    r = correr(
        "import json, django_ses.settings as s\n"
        "print(json.dumps({'c': s.AWS_SES_CONFIGURATION_SET}))",
        EMAIL_BACKEND=SES, AWS_SES_CONFIGURATION_SET="todogas-prod",
    )
    assert r["c"] == "todogas-prod"
    r = correr(
        "import json, django_ses.settings as s\n"
        "print(json.dumps({'c': s.AWS_SES_CONFIGURATION_SET}))",
        EMAIL_BACKEND=SES, AWS_SES_CONFIGURATION_SET="",
    )
    assert not r["c"]


def test_no_hace_falta_permiso_de_cuota_de_ses():
    """El limitador por defecto llama a GetSendQuota; el rol no lo necesita."""
    r = correr(
        "import json, django_ses.settings as s\n"
        "print(json.dumps({'t': s.AWS_SES_AUTO_THROTTLE}))",
        EMAIL_BACKEND=SES,
    )
    assert not r["t"]


def test_consola_y_smtp_siguen_como_antes():
    codigo = (
        "import json\nfrom django.conf import settings\n"
        "print(json.dumps({'b': settings.EMAIL_BACKEND, 'h': settings.EMAIL_HOST,"
        " 'p': settings.EMAIL_PORT, 'tls': settings.EMAIL_USE_TLS}))"
    )
    consola = importar("config.settings.development", codigo)
    assert json.loads(consola.stdout.strip().splitlines()[-1])["b"] == (
        "django.core.mail.backends.console.EmailBackend"
    )
    smtp = "django.core.mail.backends.smtp.EmailBackend"
    r = correr(codigo, EMAIL_BACKEND=smtp, EMAIL_HOST="smtp.gmail.com")
    assert r == {"b": smtp, "h": "smtp.gmail.com", "p": 587, "tls": True}
