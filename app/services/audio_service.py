import logging

from app.config import settings

logger = logging.getLogger(__name__)

_EXT_MAP = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/wav": "wav",
    "audio/webm": "webm",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
    "audio/aac": "aac",
}


async def transcrever_audio(audio_bytes: bytes, mimetype: str = "audio/ogg") -> str | None:
    """
    Transcreve áudio usando OpenAI Whisper (whisper-1).
    Retorna o texto transcrito ou None em caso de falha.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("whisper_skipped", extra={"reason": "OPENAI_API_KEY not configured"})
        return None

    import openai

    base_mime = mimetype.split(";")[0].strip()
    ext = _EXT_MAP.get(base_mime, "ogg")
    filename = f"audio.{ext}"

    try:
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes, base_mime),
            language="pt",
        )
        texto = response.text.strip()
        logger.info("whisper_ok", extra={"chars": len(texto)})
        return texto if texto else None
    except Exception as e:
        logger.error("whisper_error", extra={"error": str(e)})
        return None
