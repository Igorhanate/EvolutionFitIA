import logging

import httpx

from app.services._meta import _BASE, _auth_headers

logger = logging.getLogger(__name__)


async def get_media_bytes(media_id: str) -> tuple[bytes, str] | None:
    # Meta requires two requests: first resolves the temp download URL, second fetches bytes.
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            meta_r = await client.get(f"{_BASE}/{media_id}", headers=_auth_headers())
            meta_r.raise_for_status()
            data = meta_r.json()

            dl_r = await client.get(data["url"], headers=_auth_headers())
            dl_r.raise_for_status()
            return dl_r.content, data.get("mime_type", "application/octet-stream")
    except Exception as e:
        logger.error("media_download_error", extra={"media_id": media_id, "error": str(e)})
        return None
