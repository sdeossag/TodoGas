"""Orígenes que pueden llamar a la API desde el navegador (CORS)."""

from urllib.parse import urlsplit

# Capacitor sirve la app Android desde https://localhost (androidScheme
# "https" en frontend/capacitor.config.ts). Sin este origen la app publicada
# no puede ni iniciar sesión: el WebView bloquea la respuesta del login.
ANDROID_APP_ORIGIN = "https://localhost"


def origin(url):
    """Esquema y host de una URL (`https://app.x.co/ruta` -> `https://app.x.co`)."""
    partes = urlsplit((url or "").strip())
    if not partes.scheme or not partes.netloc:
        return None
    return f"{partes.scheme}://{partes.netloc}"


def allowed_origins(frontend_url, extra=""):
    """
    La web (FRONTEND_URL), la app Android y lo que se agregue a mano, separado
    por comas: otra web, o `capacitor://localhost` si algún día hay app de iOS.
    """
    candidatos = [ANDROID_APP_ORIGIN, origin(frontend_url)]
    candidatos += [origin(o) for o in extra.split(",")]
    return sorted({o for o in candidatos if o})
