import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.EVOLUTION_API_URL.rstrip("/")
HEADERS = {
    "apikey": settings.EVOLUTION_API_TOKEN,
    "Content-Type": "application/json",
}
INSTANCE = settings.EVOLUTION_API_INSTANCE


async def send_message(phone: str, text: str) -> None:
    url = f"{BASE_URL}/message/sendText/{INSTANCE}"
    payload = {
        "number": phone,
        "text": text,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers=HEADERS)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Erro ao enviar mensagem WhatsApp para %s: %s", phone, e)


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
