import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.whatsapp import EvolutionWebhookPayload
from app.services import claude_service, subscription_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        payload = EvolutionWebhookPayload(**body)

        # Ignora mensagens enviadas pelo próprio bot
        if payload.is_from_me():
            return {"status": "ignored"}

        # Apenas processa mensagens de texto
        if payload.event not in ("messages.upsert", "MESSAGES_UPSERT"):
            return {"status": "ignored"}

        phone = payload.get_phone()
        text = payload.get_text()

        if not phone or not text:
            return {"status": "ignored"}

        user = subscription_service.get_or_create_user(phone, db)

        # Atualiza nome se disponível
        if payload.data and payload.data.pushName and not user.nome:
            user.nome = payload.data.pushName
            db.commit()

        assinatura = subscription_service.check_active_subscription(user.id, db)

        if not assinatura:
            await whatsapp_service.send_no_subscription_message(phone)
            return {"status": "no_subscription"}

        reply = await claude_service.process_message(user, text, db)
        await whatsapp_service.send_message(phone, reply)

    except Exception as e:
        logger.error("Erro no webhook WhatsApp: %s", e, exc_info=True)

    # Sempre retorna 200 para evitar retries do Evolution API
    return {"status": "ok"}
