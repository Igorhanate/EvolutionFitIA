import asyncio
import logging

import httpx

from app.config import settings
from app.services._meta import _BASE, _auth_headers

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [1, 2, 4]


# Limite do WhatsApp e ~4096 chars no corpo do texto. Usamos margem de seguranca.
_MAX_CHARS_MSG = 3900


def _dividir_texto(texto: str, limite: int = _MAX_CHARS_MSG) -> list[str]:
    """Quebra um texto longo em pedacos <= limite, cortando em quebras de linha
    (nunca no meio de uma palavra). Mensagens curtas voltam como lista de 1 item."""
    if len(texto) <= limite:
        return [texto]

    partes: list[str] = []
    atual = ""
    for linha in texto.split("\n"):
        # Linha sozinha maior que o limite: quebra forcada por tamanho.
        if len(linha) > limite:
            if atual:
                partes.append(atual)
                atual = ""
            for i in range(0, len(linha), limite):
                partes.append(linha[i:i + limite])
            continue
        # Cabe na parte atual?
        if len(atual) + len(linha) + 1 <= limite:
            atual = f"{atual}\n{linha}" if atual else linha
        else:
            partes.append(atual)
            atual = linha
    if atual:
        partes.append(atual)
    return partes


async def _enviar_uma(phone: str, text: str) -> None:
    """Envia UMA mensagem (com retry). Usado internamente por send_message."""
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


async def send_message(phone: str, text: str) -> None:
    """Envia uma mensagem de texto. Se for longa demais pro WhatsApp (>~3900 chars),
    quebra automaticamente em varias mensagens sequenciais. Transparente pra quem chama."""
    partes = _dividir_texto(text or "")
    for parte in partes:
        await _enviar_uma(phone, parte)


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
        "Olá! Para acessar o *Evolution Fit AI*, você precisa de uma assinatura ativa.\n\n"
        "Escolha seu plano:\n\n"
        f"*Trimestral* — R$ 39,99 (3 meses)\n{settings.PAYMENT_LINK_TRIMESTRAL}\n\n"
        f"*Anual* — R$ 29,99/mês (12 meses)\n{settings.PAYMENT_LINK_ANUAL}\n\n"
        "Após o pagamento, sua conta será ativada automaticamente em instantes!"
    )
    await send_message(phone, text)


async def send_welcome_message(phone: str, nome: str | None) -> None:
    primeiro_nome = (nome or "").split()[0] if nome else ""
    saudacao = f"Olá, {primeiro_nome}! 💪" if primeiro_nome else "Olá! 💪"
    text = (
        f"{saudacao}\n"
        "Bem-vindo ao *Evolution Fit AI*!\n\n"
        "Sua assinatura foi ativada.\n\n"
        "Preparado para mudar de verdade?\n\n"
        "Sou o *Evo*, seu personal trainer e nutricionista 24h. 💪\n\n"
        "Mas antes, vamos cadastrar seu perfil — leva 1 minutinho!\n\n"
        "Me manda um *oi* pra começar."
    )
    await send_message(phone, text)
