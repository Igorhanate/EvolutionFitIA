import asyncio
import base64
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INSTANCE = settings.EVOLUTION_API_INSTANCE
_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 2, 4]  # segundos


def _base_url() -> str:
    return settings.EVOLUTION_API_URL.rstrip("/")


def _headers() -> dict:
    return {
        "apikey": settings.EVOLUTION_API_TOKEN,
        "Content-Type": "application/json",
    }


async def send_message(phone: str, text: str) -> None:
    url = f"{_base_url()}/message/sendText/{INSTANCE}"
    payload = {"number": phone, "text": text}
    last_error: Exception | None = None

    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=payload, headers=_headers())
                response.raise_for_status()
                return
        except httpx.HTTPError as e:
            last_error = e
            logger.warning("send_retry", extra={
                "attempt": attempt,
                "max": _MAX_RETRIES,
                "phone": phone,
                "error": str(e),
            })
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)

    logger.error("send_failed", extra={
        "phone": phone,
        "text_preview": text[:50],
        "error": str(last_error),
    })
    raise last_error


async def send_image(phone: str, image_bytes: bytes, caption: str = "") -> None:
    url = f"{_base_url()}/message/sendMedia/{INSTANCE}"
    payload = {
        "number": phone,
        "mediatype": "image",
        "mimetype": "image/png",
        "caption": caption,
        "media": base64.b64encode(image_bytes).decode(),
        "fileName": "evolucao.png",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=_headers())
        response.raise_for_status()


async def send_no_subscription_message(phone: str) -> None:
    text = (
        "Olá! Para acessar o *Evolution Fit IA*, você precisa de uma assinatura ativa.\n\n"
        "Escolha seu plano:\n\n"
        f"*Trimestral* — R$ 39,99 (3 meses)\n{settings.PAYMENT_LINK_TRIMESTRAL}\n\n"
        f"*Anual* — R$ 29,99/mês (12 meses)\n{settings.PAYMENT_LINK_ANUAL}\n\n"
        "Após o pagamento, sua conta será ativada automaticamente em instantes!"
    )
    await send_message(phone, text)


async def send_welcome_message(phone: str, nome: str | None) -> None:
    primeiro_nome = (nome or "").split()[0] if nome else "você"
    text = (
        f"Olá, *{primeiro_nome}*! Bem-vindo(a) ao *Evolution Fit IA*! 💪\n\n"
        "Sua assinatura foi ativada com sucesso.\n\n"
        "Sou o *Evo*, seu personal trainer e nutricionista virtual.\n\n"
        "Me conta: qual é o seu *objetivo principal*?\n"
        "• Perda de gordura\n"
        "• Ganho de massa muscular\n"
        "• Condicionamento físico\n"
        "• Outro\n\n"
        "A partir daí crio seu treino e dieta 100% personalizados!"
    )
    await send_message(phone, text)
