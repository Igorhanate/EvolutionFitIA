import hashlib
import hmac
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.assinatura import Assinatura
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

OFFER_PLAN_MAP: dict[str, str] = {
    settings.HOTMART_OFFER_ID_TRIMESTRAL: "trimestral",
    settings.HOTMART_OFFER_ID_ANUAL: "anual",
}

PLAN_DURATIONS: dict[str, int] = {
    "trimestral": 90,
    "anual": 365,
}


def normalize_phone(phone: str) -> str:
    digits = "".join(filter(str.isdigit, phone))
    # Celular brasileiro sem o nono dígito: 55 + DDD (2 dig) + 8 dig começando em 6-9 = 12 dig.
    # Kiwify às vezes omite o 9; WhatsApp sempre envia com 9. Canoniza para 13 dígitos.
    if len(digits) == 12 and digits.startswith("55") and digits[4] in "6789":
        digits = digits[:4] + "9" + digits[4:]
    return digits


def get_or_create_user(telefone: str, db: Session) -> Usuario:
    telefone = normalize_phone(telefone)
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(telefone=telefone)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def check_active_subscription(user_id: int, db: Session) -> Assinatura | None:
    today = date.today()
    return (
        db.query(Assinatura)
        .filter(
            Assinatura.user_id == user_id,
            Assinatura.status == "ativo",
            Assinatura.data_fim >= today,
        )
        .first()
    )


def map_offer_to_plan(offer_code: str | None) -> str | None:
    if not offer_code:
        return None
    return OFFER_PLAN_MAP.get(offer_code)


def activate_subscription(
    phone: str,
    nome: str | None,
    email: str | None,
    plano: str,
    transaction_id: str | None,
    db: Session,
) -> Usuario:
    # Previne duplicatas por transaction_id
    if transaction_id:
        existing = (
            db.query(Assinatura)
            .filter(Assinatura.hotmart_transaction_id == transaction_id)
            .first()
        )
        if existing:
            logger.info("Transacao %s ja processada, ignorando.", transaction_id)
            return db.query(Usuario).filter(Usuario.id == existing.user_id).first()

    # Upsert usuário
    telefone = normalize_phone(phone) if phone else None
    user = None
    if telefone:
        user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user and email:
        user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        user = Usuario(telefone=telefone, nome=nome, email=email)
        db.add(user)
        db.flush()
    else:
        if nome and not user.nome:
            user.nome = nome
        if email and not user.email:
            user.email = email
        if telefone and not user.telefone:
            user.telefone = telefone

    hoje = date.today()
    duracao = PLAN_DURATIONS.get(plano, 90)
    assinatura = Assinatura(
        user_id=user.id,
        plano=plano,
        data_inicio=hoje,
        data_fim=hoje + timedelta(days=duracao),
        status="ativo",
        hotmart_transaction_id=transaction_id,
    )
    db.add(assinatura)
    db.commit()
    db.refresh(user)
    return user


def cancel_subscription_by_phone(phone: str, db: Session) -> None:
    telefone = normalize_phone(phone)
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        return
    today = date.today()
    subs = (
        db.query(Assinatura)
        .filter(Assinatura.user_id == user.id, Assinatura.status == "ativo", Assinatura.data_fim >= today)
        .all()
    )
    for sub in subs:
        sub.status = "cancelado"
    db.commit()


def validate_hotmart_webhook(body: bytes, token_header: str | None) -> bool:
    if not token_header:
        return False
    expected = hmac.new(
        settings.HOTMART_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, token_header)
