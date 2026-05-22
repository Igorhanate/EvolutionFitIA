import json
import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services import subscription_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Kiwify"])


def _validate_token(token: str | None, plano: str) -> bool:
    if not token:
        return False
    expected = (
        settings.KIWIFY_WEBHOOK_TOKEN_ANUAL
        if plano == "anual"
        else settings.KIWIFY_WEBHOOK_TOKEN_TRIMESTRAL
    )
    return token == expected


def _extract_fields(data: dict) -> tuple[str | None, str | None, str | None, str | None]:
    """Extrai (phone, nome, email, order_id) do payload Kiwify."""
    # Kiwify envia Customer com C maiúsculo
    customer = data.get("Customer") or data.get("customer") or {}
    phone = (
        customer.get("mobile")
        or customer.get("phone")
        or customer.get("Mobile")
        or None
    )
    nome = customer.get("full_name") or customer.get("name") or None
    email = customer.get("email") or None
    order_id = data.get("order_id") or data.get("id") or None
    return phone, nome, email, order_id


@router.post("/kiwify")
async def kiwify_webhook(
    request: Request,
    plano: str = Query(..., description="anual ou trimestral"),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    body = await request.body()

    if not _validate_token(token, plano):
        logger.warning("Webhook Kiwify com token inválido")
        return {"status": "ok"}

    if plano not in ("anual", "trimestral"):
        logger.warning("Plano inválido recebido: %s", plano)
        return {"status": "ok"}

    try:
        data = json.loads(body)
    except Exception as e:
        logger.error("Erro ao parsear payload Kiwify: %s", e)
        return {"status": "ok"}

    # Log completo para diagnóstico (remover após confirmar formato)
    logger.info("Kiwify webhook recebido", extra={"plano": plano})

    order_status = data.get("order_status") or data.get("status") or ""

    # Compra aprovada ou renovação de assinatura
    if order_status in ("paid", "complete", "approved") or order_status == "":
        try:
            phone, nome, email, order_id = _extract_fields(data)

            user = subscription_service.activate_subscription(
                phone=phone or "",
                nome=nome,
                email=email,
                plano=plano,
                transaction_id=f"kiwify-{order_id}" if order_id else None,
                db=db,
            )

            if phone:
                await whatsapp_service.send_welcome_message(phone, user.nome)
            else:
                logger.warning("Kiwify sem telefone do comprador, order_id=%s", order_id)

        except Exception as e:
            logger.error("Erro ao processar webhook Kiwify: %s", e, exc_info=True)

    # Cancelamento de assinatura
    elif order_status in ("cancelled", "canceled", "refunded", "chargeback"):
        try:
            phone, _, _, _ = _extract_fields(data)
            if phone:
                subscription_service.cancel_subscription_by_phone(phone, db)
                logger.info("Assinatura cancelada via Kiwify para %s", phone)
        except Exception as e:
            logger.error("Erro ao cancelar assinatura Kiwify: %s", e, exc_info=True)

    else:
        logger.info("Kiwify evento ignorado, status=%s", order_status)

    return {"status": "ok"}
