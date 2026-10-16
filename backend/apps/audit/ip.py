"""IP del cliente para la auditoria.

X-Forwarded-For lo escribe el cliente y cada proxy agrega al final la IP que
vio. Solo lo que agregaron NUESTROS proxies es de fiar, asi que se cuenta desde
la derecha: con TRUSTED_PROXY_COUNT=1 (un ALB) vale el ultimo valor. Con 0 se
ignora la cabecera por completo.
"""

from django.conf import settings


def client_ip(request):
    remota = request.META.get("REMOTE_ADDR") or None
    proxies = getattr(settings, "TRUSTED_PROXY_COUNT", 0) or 0
    if proxies <= 0:
        return remota
    cabecera = request.META.get("HTTP_X_FORWARDED_FOR", "")
    valores = [v.strip() for v in cabecera.split(",")] if cabecera else []
    if len(valores) < proxies:
        return remota
    return valores[-proxies] or remota
