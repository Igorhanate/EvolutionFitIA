"""Lembretes de remédio sob demanda (item 14 do /menu).

Regras (travadas 14/06):
- Cliente cria por texto livre; IA extrai nome+quantidade+intervalo+duracao.
- Limites: duracao <= 5 dias, no maximo 3 lembretes ativos por usuario.
- Nao pode recadastrar o MESMO remedio (nome_norm) enquanto ativo, nem dentro
  de 7 dias apos o termino (natural ou cancelado).
- Tudo em UTC (intervalos relativos).
"""
import logging
import unicodedata
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.lembrete_remedio import LembreteRemedio

logger = logging.getLogger(__name__)

MAX_DIAS = 5
MAX_ATIVOS = 3
BLOQUEIO_DIAS = 7


def _normalizar_nome_remedio(nome: str) -> str:
    """lowercase + sem acento + espacos colapsados. Ex: '  Amoxicilina ' -> 'amoxicilina'."""
    if not nome:
        return ""
    txt = unicodedata.normalize("NFKD", nome)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.lower().strip()
    txt = " ".join(txt.split())
    return txt


def listar_ativos(user_id: int, db: Session) -> list[LembreteRemedio]:
    return (
        db.query(LembreteRemedio)
        .filter(LembreteRemedio.user_id == user_id, LembreteRemedio.ativo.is_(True))
        .order_by(LembreteRemedio.proximo_em.asc())
        .all()
    )


def _bloqueado_por_7_dias(user_id: int, nome_norm: str, db: Session) -> bool:
    """True se existe um lembrete do mesmo remedio que terminou ha menos de 7 dias."""
    limite = datetime.utcnow() - timedelta(days=BLOQUEIO_DIAS)
    existe = (
        db.query(LembreteRemedio)
        .filter(
            LembreteRemedio.user_id == user_id,
            LembreteRemedio.nome_norm == nome_norm,
            LembreteRemedio.terminado_em.isnot(None),
            LembreteRemedio.terminado_em > limite,
        )
        .first()
    )
    return existe is not None


def criar_lembrete(
    user_id: int,
    nome: str,
    quantidade: str | None,
    intervalo_horas: int,
    duracao_dias: int,
    db: Session,
) -> tuple[bool, str]:
    """Valida e cria um lembrete. Retorna (ok, mensagem_pro_usuario)."""
    nome = (nome or "").strip()
    if not nome:
        return False, "Não entendi o nome do remédio. Tenta de novo, ex: *me lembra de tomar Amoxicilina a cada 8h por 3 dias*."

    try:
        intervalo_horas = int(intervalo_horas)
        duracao_dias = int(duracao_dias)
    except (TypeError, ValueError):
        return False, "Não entendi o intervalo ou a duração. Tenta ex: *a cada 8h por 3 dias*."

    if intervalo_horas < 1 or intervalo_horas > 72:
        return False, "O intervalo precisa ser entre 1h e 72h. Tenta de novo. 🙂"

    if duracao_dias < 1:
        return False, "A duração precisa ser de pelo menos 1 dia. Tenta de novo. 🙂"

    if duracao_dias > MAX_DIAS:
        return False, (
            f"Só consigo criar lembretes de até *{MAX_DIAS} dias*. "
            "Manda de novo com até 5 dias, beleza? 🙂"
        )

    nome_norm = _normalizar_nome_remedio(nome)

    ativos = listar_ativos(user_id, db)
    if len(ativos) >= MAX_ATIVOS:
        return False, (
            f"Você já tem *{MAX_ATIVOS} lembretes ativos* (o máximo). "
            "Cancela um antes de criar outro. 🙂"
        )

    for a in ativos:
        if a.nome_norm == nome_norm:
            return False, f"Você já tem um lembrete ativo pra *{a.nome}*. 🙂"

    if _bloqueado_por_7_dias(user_id, nome_norm, db):
        return False, (
            f"O período de lembrete desse remédio já acabou. "
            f"Por segurança, só dá pra recadastrar *{nome}* depois de {BLOQUEIO_DIAS} dias do término. 🙂"
        )

    agora = datetime.utcnow()
    lembrete = LembreteRemedio(
        user_id=user_id,
        nome=nome,
        nome_norm=nome_norm,
        quantidade=(quantidade or "").strip() or None,
        intervalo_horas=intervalo_horas,
        proximo_em=agora + timedelta(hours=intervalo_horas),
        fim_em=agora + timedelta(days=duracao_dias),
        ativo=True,
        terminado_em=None,
    )
    db.add(lembrete)
    db.commit()

    qtd_txt = f" ({lembrete.quantidade})" if lembrete.quantidade else ""
    msg = (
        f"✅ Lembrete criado!\n\n"
        f"💊 *{lembrete.nome}*{qtd_txt}\n"
        f"⏰ A cada *{intervalo_horas}h*, por *{duracao_dias} dia(s)*.\n\n"
        f"Vou te avisar na hora certa. O primeiro aviso chega daqui a {intervalo_horas}h "
        f"(tome a primeira dose agora se for o caso). 💪"
    )
    return True, msg


async def disparar_lembretes_vencidos(db: Session) -> int:
    """Varre TODOS os lembretes ativos vencidos (proximo_em <= agora), envia e avança.

    Usada pelo disparo lazy (a cada mensagem recebida) e pelo cron (Render pago).
    Retorna quantos avisos foram enviados. Cada lembrete é isolado por try/except,
    então um erro em um nao derruba os outros nem a resposta principal do usuario.
    """
    from app.models.usuario import Usuario
    from app.services import whatsapp_service

    agora = datetime.utcnow()
    vencidos = (
        db.query(LembreteRemedio)
        .filter(LembreteRemedio.ativo.is_(True), LembreteRemedio.proximo_em <= agora)
        .all()
    )
    enviados


async def disparar_lembretes_vencidos(db: Session) -> int:
    """Varre TODOS os lembretes ativos vencidos (proximo_em <= agora), envia e avança.

    Usada pelo disparo lazy (a cada mensagem recebida) e pelo cron (Render pago).
    Retorna quantos avisos foram enviados. Cada lembrete é isolado por try/except,
    então um erro em um nao derruba os outros nem a resposta principal do usuario.
    """
    from app.models.usuario import Usuario
    from app.services import whatsapp_service

    agora = datetime.utcnow()
    vencidos = (
        db.query(LembreteRemedio)
        .filter(LembreteRemedio.ativo.is_(True), LembreteRemedio.proximo_em <= agora)
        .all()
    )
    enviados = 0
    for lemb in vencidos:
        try:
            # Ja passou do fim agendado -> encerra sem enviar (termino natural, inicia bloqueio 7 dias)
            if lemb.proximo_em > lemb.fim_em:
                lemb.ativo = False
                lemb.terminado_em = lemb.fim_em
                db.add(lemb)
                continue

            user = db.query(Usuario).filter(Usuario.id == lemb.user_id).first()
            if user and user.telefone:
                qtd = f" ({lemb.quantidade})" if lemb.quantidade else ""
                texto = (
                    f"💊 *Hora do remédio!*\n\n"
                    f"Está na hora de tomar *{lemb.nome}*{qtd}. 💪\n\n"
                    f"_Lembrete a cada {lemb.intervalo_horas}h._"
                )
                await whatsapp_service.send_message(user.telefone, texto)
                enviados += 1

            # Avanca pro proximo horario
            lemb.proximo_em = lemb.proximo_em + timedelta(hours=lemb.intervalo_horas)
            # Se o proximo ja passou do fim, encerra agora (inicia bloqueio 7 dias)
            if lemb.proximo_em > lemb.fim_em:
                lemb.ativo = False
                lemb.terminado_em = lemb.fim_em
            db.add(lemb)
        except Exception as e:
            logger.error("disparo_lembrete_erro", extra={"lembrete_id": lemb.id, "error": str(e)})
    db.commit()
    return enviados
