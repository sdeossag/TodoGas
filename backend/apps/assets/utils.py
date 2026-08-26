import base64
import io

import qrcode
from decouple import config


def generate_asset_qr(asset) -> bytes:
    frontend_url = config("FRONTEND_URL", default="http://localhost:5173")
    url = f"{frontend_url}/activos/{asset.id}"
    img = qrcode.make(url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def get_or_create_qr_url(asset) -> str:
    if not asset.qr_code:
        png_bytes = generate_asset_qr(asset)
        b64 = base64.b64encode(png_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    return asset.qr_code
