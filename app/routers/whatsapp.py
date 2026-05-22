import base64
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.whatsapp import MetaWebhookPayload
from app.services import claude_service, file_reader, media_service, subscription_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])


@router.get("/whatsapp")
async def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.META_WEBHOOK_VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()

    if settings.META_APP_SECRET:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            settings.META_APP_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig_header):
            logger.warning("invalid_webhook_signature")
            return {"status": "rejected"}

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("invalid_webhook_json")
        return {"status": "rejected"}

    try:
        payload = MetaWebhookPayload(**body)

        if not payload.is_message_event():
            return {"status": "ignored"}

        phone = payload.get_phone()
        text = payload.get_text()
        message_id = payload.get_message_id()
        push_name = payload.get_push_name()

        if not phone:
            return {"status": "ignored"}

        image_b64: str | None = None
        image_mimetype: str = "image/jpeg"
        audio_transcricao: str | None = None

        if payload.is_image():
            media_id = payload.get_image_id()
            if media_id:
                result = await media_service.get_media_bytes(media_id)
                if result:
                    raw_bytes, image_mimetype = result
                    image_b64 = base64.b64encode(raw_bytes).decode()

        elif payload.is_audio():
            await whatsapp_service.send_message(
                phone,
                "No momento processo apenas mensagens de *texto* e *fotos*. 📝📷\n\n"
                "Em breve a funcionalidade de áudio estará disponível! 🎤",
            )
            return {"status": "ok"}

        elif payload.is_document():
            media_id = payload.get_document_id()
            doc_mimetype = payload.get_document_mimetype()
            doc_filename = payload.get_document_filename()
            if media_id:
                result = await media_service.get_media_bytes(media_id)
                if result:
                    raw_bytes, _ = result
                    extracted = file_reader.extrair_texto(raw_bytes, doc_mimetype, doc_filename)
                    if extracted:
                        text = f"[Arquivo recebido: {doc_filename}]\n\n{extracted}"
                        logger.info(
                            "document_extracted",
                            extra={"phone": phone, "filename": doc_filename, "chars": len(extracted)},
                        )
                    else:
                        await whatsapp_service.send_message(
                            phone,
                            f"Recebi o arquivo *{doc_filename}*, mas não consigo ler esse tipo de documento. 📄\n\n"
                            "Envie em formato *PDF* ou *Excel (.xlsx)*.",
                        )
                        return {"status": "ok"}

        if not text and not image_b64:
            return {"status": "ignored"}

        user = subscription_service.get_or_create_user(phone, db)

        if push_name and not user.nome:
            user.nome = push_name
            db.commit()

        if message_id and user.ultima_mensagem_id == message_id:
            logger.info("duplicate_message", extra={"user_id": user.id, "message_id": message_id})
            return {"status": "duplicate"}

        assinatura = subscription_service.check_active_subscription(user.id, db)
        if not assinatura:
            await whatsapp_service.send_no_subscription_message(phone)
            return {"status": "no_subscription"}

        if message_id:
            user.ultima_mensagem_id = message_id
            db.commit()

        if audio_transcricao:
            await whatsapp_service.send_message(phone, f"🎤 _Áudio transcrito:_\n\n_{audio_transcricao}_")

        reply = await claude_service.process_message(
            user, text or "", db, image_b64=image_b64, image_mimetype=image_mimetype, phone=phone
        )
        await whatsapp_service.send_message(phone, reply)

    except Exception as e:
        logger.error("webhook_error", extra={"error": str(e)}, exc_info=True)

    return {"status": "ok"}
