import asyncio
import logging

import httpx

from app.config import settings
from app.services._meta import _BASE, _auth_headers

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [1, 2, 4]


async def send_message(phone: str, text: str) -> None:
    url = f"{_BASE}/{settings.META_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=15) as client:
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                r = await client.post(url, json=payload, headers=_auth_headers())
                r.raise_for_status()
                return
            except httpx.HTTPError as e:
                last_error = e
                logger.warning("send_retry", extra={
                    "attempt": attempt,
                    "max": len(_RETRY_DELAYS),
                    "phone": phone,
                    "error": str(e),
                })
                if attempt < len(_RETRY_DELAYS):
                    await asyncio.sleep(delay)

    logger.error("send_failed", extra={
        "phone": phone,
        "text_preview": text[:50],
        "error": str(last_error),
    })
    raise last_error


async def send_image(phone: str, image_bytes: bytes, caption: str = "") -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        upload_r = await client.post(
            f"{_BASE}/{settings.META_PHONE_NUMBER_ID}/media",
            headers=_auth_headers(),
            data={"messaging_product": "whatsapp"},
            files={"file": ("evolucao.png", image_bytes, "image/png")},
        )
        upload_r.raise_for_status()
        media_id = upload_r.json()["id"]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "image",
            "image": {"id": media_id, "caption": caption},
        }
        r = await client.post(
            f"{_BASE}/{settings.META_PHONE_NUMBER_ID}/messages",
            json=payload,
            headers=_auth_headers(),
        )
        r.raise_for_status()


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
