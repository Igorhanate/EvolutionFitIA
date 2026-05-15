import json
import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.hotmart import HotmartWebhookPayload
from app.services import subscription_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Hotmart"])


@router.post("/hotmart")
async def hotmart_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hotmart_webhook_token: str | None = Header(default=None),
):
    # Lê body uma única vez
    body = await request.body()

    if not subscription_service.validate_hotmart_webhook(body, x_hotmart_webhook_token):
        logger.warning("Webhook Hotmart com token invalido recebido.")
        return {"status": "ok"}

    try:
        data = json.loads(body)
        payload = HotmartWebhookPayload(**data)
    except Exception as e:
        logger.error("Erro ao parsear payload Hotmart: %s", e)
        return {"status": "ok"}

    if payload.event != "PURCHASE_APPROVED":
        return {"status": "ignored"}

    try:
        buyer = payload.get_buyer()
        purchase = payload.get_purchase()
        offer_code = payload.get_offer_code()
        phone = payload.get_buyer_phone()

        plano = subscription_service.map_offer_to_plan(offer_code)
        if not plano:
            logger.warning("Offer code desconhecido: %s", offer_code)
            return {"status": "ok"}

        user = subscription_service.activate_subscription(
            phone=phone or "",
            nome=buyer.name,
            email=buyer.email,
            plano=plano,
            transaction_id=purchase.transaction,
            db=db,
        )

        if phone:
            await whatsapp_service.send_welcome_message(phone, user.nome)

    except Exception as e:
        logger.error("Erro ao processar webhook Hotmart: %s", e, exc_info=True)

    return {"status": "ok"}
