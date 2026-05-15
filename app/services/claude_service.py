import logging
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é "Evo", personal trainer e nutricionista profissional com 10 anos de experiência, especializado em treino funcional e nutrição esportiva. Comunica-se exclusivamente em português brasileiro, com tom motivador, direto e amigável.

REGRAS:
- Sempre chame o usuário pelo primeiro nome quando souber
- Antes de gerar treino ou dieta, faça perguntas essenciais (nível de condicionamento, equipamentos disponíveis, objetivo, lesões, dias disponíveis por semana)
- Treinos: estruture por Dia 1 / Dia 2 etc., inclua séries/repetições e tempos de descanso
- Dietas: inclua café da manhã, almoço, lanche e jantar; pergunte sobre restrições alimentares
- Mensagens curtas para WhatsApp: parágrafos curtos, bullet points, sem paredes de texto
- Nunca saia do personagem. Fale apenas sobre fitness e nutrição.
- Se o usuário mencionar lesão, oriente a consultar um médico antes de qualquer plano."""

MAX_HISTORY = 20

TREINO_KEYWORDS = {"treino", "exercício", "exercicio", "musculação", "musculacao", "academia", "workout", "treinar"}
DIETA_KEYWORDS = {"dieta", "alimentação", "alimentacao", "nutrição", "nutricao", "comer", "refeição", "refeicao", "cardapio", "cardápio"}


def _get_or_create_conversa(user_id: int, db: Session) -> Conversa:
    conversa = db.query(Conversa).filter(Conversa.user_id == user_id).first()
    if not conversa:
        conversa = Conversa(user_id=user_id, mensagens=[])
        db.add(conversa)
        db.flush()
    return conversa


def _contains_keywords(text: str, keywords: set[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


async def process_message(user: Usuario, message_text: str, db: Session) -> str:
    conversa = _get_or_create_conversa(user.id, db)

    mensagens: list[dict] = list(conversa.mensagens or [])
    mensagens.append({
        "role": "user",
        "content": message_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Monta histórico para a Claude (sem timestamps)
    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in mensagens[-MAX_HISTORY:]
    ]

    system = SYSTEM_PROMPT
    if user.nome:
        system += f"\n\nNome do usuário: {user.nome.split()[0]}"

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system,
            messages=api_messages,
        )
        reply = response.content[0].text
    except anthropic.APIError as e:
        logger.error("Erro Claude API: %s", e)
        reply = "Ops, tive um problema técnico agora. Pode repetir sua mensagem?"

    mensagens.append({
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.utcnow().isoformat(),
    })

    conversa.mensagens = mensagens
    db.add(conversa)

    if _contains_keywords(reply, TREINO_KEYWORDS):
        db.add(Treino(user_id=user.id, conteudo={"texto": reply, "gerado_em": datetime.utcnow().isoformat()}))

    if _contains_keywords(reply, DIETA_KEYWORDS):
        db.add(Dieta(user_id=user.id, conteudo={"texto": reply, "gerado_em": datetime.utcnow().isoformat()}))

    db.commit()
    return reply
