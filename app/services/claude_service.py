import logging
from datetime import date, datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services import exercicio_service

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é "Evo", personal trainer e nutricionista profissional com 10 anos de experiência, especializado em treino funcional e nutrição esportiva. Comunica-se exclusivamente em português brasileiro, com tom motivador, direto e amigável.

REGRAS GERAIS:
- Sempre chame o usuário pelo primeiro nome quando souber
- Antes de gerar treino ou dieta, faça perguntas essenciais (nível de condicionamento, equipamentos disponíveis, objetivo, lesões, dias disponíveis por semana)
- Treinos: estruture por Dia 1 / Dia 2 etc., inclua séries/repetições e tempos de descanso
- Dietas: inclua café da manhã, almoço, lanche e jantar; pergunte sobre restrições alimentares
- Mensagens curtas para WhatsApp: parágrafos curtos, bullet points, sem paredes de texto
- Nunca saia do personagem. Fale apenas sobre fitness e nutrição.
- Se o usuário mencionar lesão, oriente a consultar um médico antes de qualquer plano.

REGISTRO DE EXERCÍCIOS:
- Quando o usuário reportar carga, séries e repetições de um exercício, use SEMPRE a ferramenta 'registrar_exercicio'
- Após o registro, informe o 1RM estimado de forma motivadora e compare com o histórico quando disponível
- Se o resultado da ferramenta indicar AGUARDANDO_CONFIRMACAO, explique a variação ao usuário e aguarde confirmação antes de prosseguir
- Nenhuma fórmula de 1RM é 100% precisa para todos — mencione isso quando exibir o valor
- Ao exibir evolução, destaque o progresso e motive o usuário"""

MAX_HISTORY = 20

TREINO_KEYWORDS = {"treino", "exercício", "exercicio", "musculação", "musculacao", "academia", "workout", "treinar"}
DIETA_KEYWORDS = {"dieta", "alimentação", "alimentacao", "nutrição", "nutricao", "comer", "refeição", "refeicao", "cardapio", "cardápio"}

CONFIRMACAO_SIM = {"sim", "s", "yes", "confirmo", "pode", "ok", "isso", "certeza", "certo", "salva", "salvar", "confirmar"}
CONFIRMACAO_NAO = {"não", "nao", "n", "no", "cancela", "cancelar", "errei", "errado", "errada", "equivocado"}

TOOLS = [
    {
        "name": "registrar_exercicio",
        "description": (
            "Registra o desempenho de um exercício reportado pelo usuário durante um treino. "
            "Use SEMPRE que o usuário informar séries, repetições e carga de um exercício específico."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "exercicio": {
                    "type": "string",
                    "description": "Nome do exercício exatamente como o usuário reportou",
                },
                "series": {"type": "integer", "description": "Número de séries realizadas"},
                "repeticoes": {"type": "integer", "description": "Repetições por série"},
                "carga_kg": {"type": "number", "description": "Carga utilizada em kg"},
            },
            "required": ["exercicio", "series", "repeticoes", "carga_kg"],
        },
    }
]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_or_create_conversa(user_id: int, db: Session) -> Conversa:
    conversa = db.query(Conversa).filter(Conversa.user_id == user_id).first()
    if not conversa:
        conversa = Conversa(user_id=user_id, mensagens=[], estado_pendente=None)
        db.add(conversa)
        db.flush()
    return conversa


def _contains_keywords(text: str, keywords: set[str]) -> bool:
    return any(kw in text.lower() for kw in keywords)


def _normalizar_confirmacao(text: str) -> str | None:
    """Retorna 'sim', 'nao' ou None se não for clara."""
    lower = text.strip().lower()
    if any(p in lower for p in CONFIRMACAO_SIM):
        return "sim"
    if any(p in lower for p in CONFIRMACAO_NAO):
        return "nao"
    return None


def _fmt_rm(rm_result: dict | None) -> str:
    if not rm_result:
        return ""
    formulas = {k: v for k, v in rm_result.items() if k != "media"}
    nomes = {"epley": "Epley", "brzycki": "Brzycki", "lander": "Lander"}
    partes = [f"{nomes.get(k, k)}: {v}kg" for k, v in formulas.items()]
    return f"1RM estimado: *{rm_result['media']}kg* ({', '.join(partes)}) ⚠️ estimativa"


def _sessao_context_str(user_id: int, sessao_data: date, db: Session) -> str | None:
    registros = exercicio_service.get_registros_sessao(user_id, sessao_data, db)
    if not registros:
        return None
    linhas = [f"Treino de hoje ({sessao_data.strftime('%d/%m/%Y')}):"]
    for r in registros:
        rm_str = f" | 1RM≈{r.rm_estimado}kg" if r.rm_estimado else ""
        linhas.append(f"  {r.posicao_sessao}º {r.exercicio_display}: {r.series}x{r.repeticoes} @ {r.carga_kg}kg{rm_str}")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Processamento de confirmação pendente
# ---------------------------------------------------------------------------

def _handle_confirmacao(
    conversa: Conversa,
    message_text: str,
    user: Usuario,
    sessao_data: date,
    db: Session,
) -> str | None:
    """
    Verifica se há confirmação pendente e processa.
    Retorna string de contexto para injetar no histórico, ou None se não havia pendência.
    """
    estado = conversa.estado_pendente
    if not estado or estado.get("tipo") != "confirmar_exercicio":
        return None

    resposta = _normalizar_confirmacao(message_text)

    exercicio = estado["exercicio_display"]
    series = estado["series"]
    reps = estado["repeticoes"]
    carga = estado["carga_kg"]
    posicao = estado["posicao"]
    ultima_carga = estado["ultima_carga"]
    variacao_pct = estado["variacao_pct"]

    conversa.estado_pendente = None

    if resposta == "sim":
        registro = exercicio_service.registrar(
            user_id=user.id,
            sessao_data=date.fromisoformat(estado["sessao_data"]),
            posicao=posicao,
            exercicio_display=exercicio,
            series=series,
            repeticoes=reps,
            carga_kg=carga,
            db=db,
        )
        rm_str = _fmt_rm(exercicio_service.calcular_rm(carga, reps))
        return (
            f"[SISTEMA] Usuário confirmou o registro de '{exercicio}': "
            f"{series}x{reps} @ {carga}kg (posição {posicao} na sessão). "
            f"{rm_str}. "
            f"Variação de {variacao_pct:+.0f}% em relação ao último ({ultima_carga}kg) foi aceita."
        )
    elif resposta == "nao":
        return (
            f"[SISTEMA] Usuário cancelou o registro de '{exercicio}' com {carga}kg. "
            f"Dado não foi salvo. Pergunte qual a carga correta para registrar."
        )
    else:
        # Resposta ambígua — mantém pendente para próxima mensagem
        conversa.estado_pendente = estado
        return (
            f"[SISTEMA] Ainda aguardando confirmação para registrar '{exercicio}': "
            f"{series}x{reps} @ {carga}kg (variação {variacao_pct:+.0f}% vs último: {ultima_carga}kg). "
            f"Peça ao usuário para confirmar com 'sim' ou cancelar com 'não'."
        )


# ---------------------------------------------------------------------------
# Processamento de tool call
# ---------------------------------------------------------------------------

def _process_tool_registrar(
    tool_input: dict,
    user: Usuario,
    sessao_data: date,
    conversa: Conversa,
    db: Session,
) -> str:
    exercicio_display = tool_input["exercicio"]
    series = int(tool_input["series"])
    reps = int(tool_input["repeticoes"])
    carga = float(tool_input["carga_kg"])

    exercicio_norm = exercicio_service.normalizar_nome(exercicio_display)
    posicao = exercicio_service.get_proxima_posicao(user.id, sessao_data, db)
    historico = exercicio_service.get_historico_exercicio(user.id, exercicio_norm, posicao, db)
    anormal, variacao_pct = exercicio_service.detectar_variacao_anormal(carga, historico)

    if anormal:
        ultima_carga = historico[0].carga_kg
        conversa.estado_pendente = {
            "tipo": "confirmar_exercicio",
            "exercicio_display": exercicio_display,
            "exercicio_norm": exercicio_norm,
            "posicao": posicao,
            "series": series,
            "repeticoes": reps,
            "carga_kg": carga,
            "ultima_carga": ultima_carga,
            "variacao_pct": variacao_pct,
            "sessao_data": sessao_data.isoformat(),
        }
        return (
            f"AGUARDANDO_CONFIRMACAO: '{exercicio_display}' com {carga}kg representa variação "
            f"de {variacao_pct:+.0f}% em relação ao último registro ({ultima_carga}kg) "
            f"na posição {posicao} da sessão. Informe o usuário e aguarde confirmação."
        )

    registro = exercicio_service.registrar(
        user_id=user.id,
        sessao_data=sessao_data,
        posicao=posicao,
        exercicio_display=exercicio_display,
        series=series,
        repeticoes=reps,
        carga_kg=carga,
        db=db,
    )

    rm_result = exercicio_service.calcular_rm(carga, reps)
    rm_str = _fmt_rm(rm_result)

    evolucao_str = ""
    if historico and registro.rm_estimado and historico[0].rm_estimado:
        diff = registro.rm_estimado - historico[0].rm_estimado
        sinal = "+" if diff >= 0 else ""
        evolucao_str = (
            f" Evolução de 1RM vs sessão anterior (mesma posição): "
            f"{sinal}{diff:.1f}kg ({historico[0].sessao_data.strftime('%d/%m')})."
        )
    elif not historico:
        evolucao_str = " Primeiro registro deste exercício nesta posição — referência criada."

    return (
        f"REGISTRADO: '{exercicio_display}' — posição {posicao} na sessão, "
        f"{series}x{reps} @ {carga}kg. {rm_str}.{evolucao_str}"
    )


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

async def process_message(user: Usuario, message_text: str, db: Session) -> str:
    conversa = _get_or_create_conversa(user.id, db)
    sessao_data = date.today()

    mensagens: list[dict] = list(conversa.mensagens or [])

    # 1. Trata confirmação pendente antes de qualquer chamada ao Claude
    ctx_confirmacao = _handle_confirmacao(conversa, message_text, user, sessao_data, db)

    # 2. Adiciona mensagem do usuário ao histórico persistido
    mensagens.append({
        "role": "user",
        "content": message_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # 3. Monta history para a API (sem timestamps)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in mensagens[-MAX_HISTORY:]
    ]

    # 4. Injeta contexto de sessão (exercícios já registrados hoje) antes da última mensagem
    ctx_sessao = _sessao_context_str(user.id, sessao_data, db)
    if ctx_sessao or ctx_confirmacao:
        partes = []
        if ctx_sessao:
            partes.append(ctx_sessao)
        if ctx_confirmacao:
            partes.append(ctx_confirmacao)
        injecao = "\n".join(partes)
        # Insere como par user/assistant antes do histórico real para não quebrar a alternância
        history = [
            {"role": "user", "content": f"[Contexto automático do sistema]\n{injecao}"},
            {"role": "assistant", "content": "Entendido, tenho esses dados em consideração."},
        ] + history

    # 5. System prompt com cache
    primeiro_nome = (user.nome or "").split()[0] if user.nome else None
    system_with_cache = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT + (f"\n\nNome do usuário: {primeiro_nome}" if primeiro_nome else ""),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    # 6. Chama Claude (com tool use para captura de exercícios)
    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            system=system_with_cache,
            messages=history,
            tools=TOOLS,
        )

        # 7. Loop de tool use (máximo 3 ferramentas por mensagem)
        tool_iterations = 0
        while response.stop_reason == "tool_use" and tool_iterations < 3:
            tool_iterations += 1
            tool_results = []

            for block in response.content:
                if block.type == "tool_use" and block.name == "registrar_exercicio":
                    result = _process_tool_registrar(block.input, user, sessao_data, conversa, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            history.append({"role": "assistant", "content": response.content})
            history.append({"role": "user", "content": tool_results})

            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1500,
                system=system_with_cache,
                messages=history,
                tools=TOOLS,
            )

        reply = next((b.text for b in response.content if hasattr(b, "text")), "")

    except anthropic.APIError as e:
        logger.error("claude_error", extra={"user_id": user.id, "error": str(e)})
        reply = "Ops, tive um problema técnico agora. Pode repetir sua mensagem?"

    # 8. Persiste histórico e registros secundários
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
