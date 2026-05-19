import base64
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INSTANCE = settings.EVOLUTION_API_INSTANCE


def _base_url() -> str:
    return settings.EVOLUTION_API_URL.rstrip("/")


def _headers() -> dict:
    return {
        "apikey": settings.EVOLUTION_API_TOKEN,
        "Content-Type": "application/json",
    }


async def get_media_bytes(message_data: dict) -> tuple[bytes, str] | None:
    """
    Download media from Evolution API.
    Returns (raw_bytes, media_type) or None on failure.
    """
    url = f"{_base_url()}/chat/getBase64FromMediaMessage/{INSTANCE}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url, json={"message": message_data}, headers=_headers()
            )
            response.raise_for_status()
            data = response.json()
            b64_str: str = data.get("base64", "")
            media_type = "image/jpeg"
            if "," in b64_str:
                prefix, b64_str = b64_str.split(",", 1)
                if ":" in prefix and ";" in prefix:
                    media_type = prefix.split(":")[1].split(";")[0]
            raw = base64.b64decode(b64_str) if b64_str else None
            return (raw, media_type) if raw else None
    except Exception as e:
        logger.error("media_download_error", extra={"error": str(e)})
        return None
