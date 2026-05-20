from app.config import settings

_BASE = "https://graph.facebook.com/v19.0"


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"}
