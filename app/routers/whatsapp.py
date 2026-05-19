import base64
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.whatsapp import EvolutionWebhookPayload
from app.services import claude_service, media_service, subscription_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        payload = EvolutionWebhookPayload(**body)

        if payload.is_from_me():
            return {"status": "ignored"}

        if payload.event not in ("messages.upsert", "MESSAGES_UPSERT"):
            return {"status": "ignored"}

        phone = payload.get_phone()
        text = payload.get_text()
        message_id = payload.get_message_id()

        if not phone:
            return {"status": "ignored"}

        image_b64: str | None = None
        image_mimetype: str = "image/jpeg"

        if payload.is_image() and payload.data and payload.data.message:
            message_data: dict = {}
            if payload.data.key:
                message_data["key"] = payload.data.key.model_dump()
            message_data["message"] = payload.data.message
            result = await media_service.get_media_bytes(message_data)
            if result:
                raw_bytes, image_mimetype = result
                image_b64 = base64.b64encode(raw_bytes).decode()

        if not text and not image_b64:
            return {"status": "ignored"}

        user = subscription_service.get_or_create_user(phone, db)

        if payload.data and payload.data.pushName and not user.nome:
            user.nome = payload.data.pushName
            db.commit()

        # Deduplicação: ignora mensagem já processada
        if message_id and user.ultima_mensagem_id == message_id:
            logger.info("duplicate_message", extra={"user_id": user.id, "message_id": message_id})
            return {"status": "duplicate"}

        assinatura = subscription_service.check_active_subscription(user.id, db)

        if not assinatura:
            await whatsapp_service.send_no_subscription_message(phone)
            return {"status": "no_subscription"}

        # Persiste ID antes do envio para dedup funcionar mesmo se send falhar
        if message_id:
            user.ultima_mensagem_id = message_id
            db.commit()

        reply = await claude_service.process_message(
            user, text or "", db, image_b64=image_b64, image_mimetype=image_mimetype
        )
        await whatsapp_service.send_message(phone, reply)

    except Exception as e:
        logger.error("webhook_error", extra={"error": str(e)}, exc_info=True)

    return {"status": "ok"}
