import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    return _scheduler


async def _enviar_lembretes_suplemento() -> None:
    from app.database import SessionLocal
    from app.models.usuario import Usuario
    from app.services import habito_service, subscription_service, whatsapp_service

    db = SessionLocal()
    try:
        users = db.query(Usuario).filter(Usuario.telefone.isnot(None)).all()
        enviados = 0
        for user in users:
            try:
                assinatura = subscription_service.check_active_subscription(user.id, db)
                if not assinatura:
                    continue
                if not habito_service.precisa_lembrete_suplemento(user.id, db):
                    continue

                suplementos = habito_service.get_suplementos_usuario(user.id, db)
                primeiro_nome = (user.nome or "").split()[0] if user.nome else "você"

                if suplementos:
                    lista = "\n".join(f"• {s}" for s in suplementos)
                    texto = (
                        f"💊 *Lembrete de Suplementação, {primeiro_nome}!*\n\n"
                        f"Não esqueça de tomar seus suplementos:\n{lista}\n\n"
                        "Já tomou? Me manda *tomei meus suplementos* para registrar! ✅"
                    )
                else:
                    texto = (
                        f"💊 *Lembrete de Suplementação, {primeiro_nome}!*\n\n"
                        "Não esqueça de tomar sua creatina, vitaminas e manipulados! 💪\n\n"
                        "Já tomou? Me manda *tomei meus suplementos* para registrar! ✅\n\n"
                        "_Dica: me conta quais suplementos você toma para eu personalizar seus lembretes!_"
                    )

                await whatsapp_service.send_message(user.telefone, texto)
                enviados += 1
            except Exception as e:
                logger.error("supplement_reminder_error", extra={"user_id": user.id, "error": str(e)})

        logger.info("supplement_reminders_sent", extra={"total": enviados})
    finally:
        db.close()


async def _disparar_lembretes_remedio() -> None:
    from app.database import SessionLocal
    from app.services import lembrete_service

    db = SessionLocal()
    try:
        enviados = await lembrete_service.disparar_lembretes_vencidos(db)
        if enviados:
            logger.info("lembretes_remedio_enviados", extra={"total": enviados})
    except Exception as e:
        logger.error("cron_lembrete_remedio_erro", extra={"error": str(e)})
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler = get_scheduler()
    # Lembrete das 20h desativado a pedido do usuário (25/05). Sistema de lembretes opt-in (continuo/pontual/horario) entrará quando a confiabilidade do disparo for resolvida (Render pago ou cron externo).
    # scheduler.add_job(
    #     _enviar_lembretes_suplemento,
    #     CronTrigger(hour=20, minute=0, timezone="America/Sao_Paulo"),
    #     id="lembretes_suplemento",
    #     replace_existing=True,
    #     misfire_grace_time=600,
    # )
    scheduler.add_job(
        _disparar_lembretes_remedio,
        CronTrigger(minute="*/15", timezone="America/Sao_Paulo"),
        id="lembretes_remedio",
        replace_existing=True,
        misfire_grace_time=600,
    )
    scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
