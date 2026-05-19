import logging
from datetime import date, datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services import exercicio_service, nutricao_service

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é "Evo", personal trainer e nutricionista profissional com 10 anos de experiência, especializado em treino funcional e nutrição esportiva. Comunica-se exclusivamente em português brasileiro, com tom motivador, direto e amigável.

REGRAS GERAIS:
- Sempre chame o usuário pelo primeiro nome quando souber
- Antes de gerar treino ou dieta, faça perguntas essenciais (nível de condicionamento, equipamentos disponíveis, objetivo, lesões, dias disponíveis por semana)
- Treinos: estruture por Dia 1 / Dia 2 etc., inclua séries/repetições e tempos de descanso
- Mensagens curtas para WhatsApp: parágrafos curtos, bullet points, sem paredes de texto
- Nunca saia do personagem. Fale apenas sobre fitness e nutrição.
- Se o usuário mencionar lesão, oriente a consultar um médico antes de qualquer plano.

REGISTRO DE EXERCÍCIOS:
- Quando o usuário reportar carga, séries e repetições de um exercício, use SEMPRE a ferramenta 'registrar_exercicio'
- Após o registro, informe o 1RM estimado de forma motivadora e compare com o histórico quando disponível
- Se o resultado da ferramenta indicar AGUARDANDO_CONFIRMACAO, explique a variação ao usuário e aguarde confirmação antes de prosseguir
- Nenhuma fórmula de 1RM é 100% precisa para todos — mencione isso quando exibir o valor
- Ao exibir evolução, destaque o progresso e motive o usuário

MEDIDAS CORPORAIS:
- Quando o usuário reportar peso e/ou medidas (cintura, quadril, pescoço, braço, coxa, panturrilha), use SEMPRE a ferramenta 'registrar_medidas'
- Se o contexto do sistema indicar medidas desatualizadas (>30 dias), incentive o usuário de forma motivacional a tirar novas medidas — mas só quando o assunto for relevante
- Ao registrar, compare com a medição anterior quando disponível e destaque a evolução
- Argumento motivacional: "O que não é medido não é gerenciado — acompanhar suas medidas é parte essencial do progresso"

ANÁLISE DE COMPOSIÇÃO CORPORAL (FOTOS):
- Quando o usuário enviar uma foto para análise corporal, analise visualmente a composição com profissionalismo
- Estime o % de gordura corporal em uma FAIXA (ex: "entre 18-22%"), nunca como valor único absoluto
- Descreva distribuição de gordura e massa muscular visível de forma respeitosa e encorajadora
- SEMPRE mencione que análise visual tem precisão limitada e recomende medições físicas para maior exatidão
- Após a análise, use a ferramenta 'registrar_analise_foto' para persistir o resultado

PERFIL COMPARATIVO:
- Use o histórico de medidas e análises de foto injetado no contexto para construir uma narrativa de evolução
- Compare com registros anteriores quando disponíveis e destaque progressos, mesmo que pequenos
- A consistência ao longo do tempo é mais importante que o resultado pontual — reforce isso

PROTOCOLO DE CRIAÇÃO DE DIETA:
Siga os passos abaixo SEMPRE que criar uma dieta personalizada:

4.1 COLETA DE DADOS — Pergunte antes de calcular:
  • Idade, sexo biológico (H/M), altura (cm), peso atual (kg)
  • Nível de atividade: sedentário / levemente ativo (1-3x/sem) / moderado (3-5x/sem) / muito ativo (6-7x/sem) / atleta/trabalho físico
  • Objetivo: perder gordura / ganhar massa / manter
  • Restrições alimentares ou alergias
  • Tempo disponível para cozinhar e orçamento aproximado

4.2 CÁLCULO CALÓRICO (Mifflin-St Jeor):
  • Homem: TMB = (10 × peso_kg) + (6,25 × altura_cm) − (5 × idade) + 5
  • Mulher: TMB = (10 × peso_kg) + (6,25 × altura_cm) − (5 × idade) − 161
  • Multiplicadores: sedentário×1,2 / leve×1,375 / moderado×1,55 / intenso×1,725 / atleta×1,9
  • TDEE = TMB × multiplicador. Informe o valor calculado ao usuário.

4.3 DISTRIBUIÇÃO DE MACROS:
  • Perda de gordura: déficit 400-500 kcal, proteína 2,0-2,2 g/kg, gordura 25-30% das kcal, resto em carboidratos
  • Ganho de massa: superávit 200-300 kcal, proteína 1,8-2,0 g/kg, carboidratos 50-55% das kcal, resto em gordura
  • Manutenção: TDEE sem ajuste, proteína 1,6-1,8 g/kg, carboidratos 45-50%, gordura 25-30%

4.4 PLANO 7 DIAS:
  Crie café da manhã, almoço, lanche da tarde e jantar para cada dia da semana.
  Especifique quantidades em gramas ou medidas caseiras. Varie os alimentos e adapte às restrições.

4.5 SUBSTITUIÇÕES:
  Para cada refeição principal (café, almoço, jantar), liste 3 opções de substituição equivalentes em macros.

4.6 REGRAS PERSONALIZADAS:
  Liste regras práticas baseadas nas preferências, restrições e rotina informadas pelo usuário.

4.7 TIMELINE REALISTA:
  • Perda de gordura: 0,5-1 kg/semana é seguro e sustentável
  • Ganho de massa (natural): 0,25-0,5 kg/semana é realista
  Defina marcos de 4, 8 e 12 semanas com metas mensuráveis.

4.8 HIDRATAÇÃO:
  • Base: 35-40 ml/kg de peso corporal por dia
  • Acrescente 500 ml por hora de exercício moderado a intenso
  Sugira estratégias práticas (garrafa sempre à mão, alarmes a cada 1-2h).

4.9 SUPLEMENTAÇÃO BASEADA EM EVIDÊNCIAS:
  Recomende APENAS suplementos com evidência científica sólida e pertinentes ao perfil:
  • Whey protein: se houver dificuldade em atingir a meta proteica com alimentação
  • Creatina monoidratada: para melhora de performance e força (3-5 g/dia)
  • Vitamina D3: se houver suspeita de deficiência (treino indoor, pouca exposição solar)
  • Ômega-3: suporte anti-inflamatório se consumo de peixes for baixo
  NUNCA recomende termogênicos, detox, emagrecedores ou produtos sem base científica."""

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
    },
    {
        "name": "registrar_medidas",
        "description": (
            "Registra medidas corporais reportadas pelo usuário (peso e/ou circunferências). "
            "Use SEMPRE que o usuário informar pelo menos uma dessas medidas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "peso_kg": {"type": "number", "description": "Peso corporal em kg"},
                "cintura_cm": {"type": "number", "description": "Circunferência da cintura em cm"},
                "quadril_cm": {"type": "number", "description": "Circunferência do quadril em cm"},
                "pescoco_cm": {"type": "number", "description": "Circunferência do pescoço em cm"},
                "braco_cm": {"type": "number", "description": "Circunferência do braço (bíceps) em cm"},
                "coxa_cm": {"type": "number", "description": "Circunferência da coxa em cm"},
                "panturrilha_cm": {"type": "number", "description": "Circunferência da panturrilha em cm"},
            },
        },
    },
    {
        "name": "registrar_analise_foto",
        "description": (
            "Registra a análise de composição corporal feita visualmente a partir de uma foto. "
            "Use após analisar uma foto de composição corporal enviada pelo usuário."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gordura_estimada_pct": {
                    "type": "number",
                    "description": "Ponto médio da faixa estimada de % de gordura (ex: se estimou 18-22%, use 20)",
                },
                "analise_texto": {
                    "type": "string",
                    "description": "Resumo objetivo da análise visual (distribuição de gordura, massa muscular visível, observações gerais)",
                },
            },
            "required": ["analise_texto"],
        },
    },
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
# Fluxo de coleta de 3 fotos para análise de composição corporal
# ---------------------------------------------------------------------------

_CANCELAR_FOTOS_KEYWORDS = {
    "cancelar", "cancela", "para", "parar", "não quero", "nao quero",
    "esqueça", "esqueca", "desiste", "desistir", "chega", "deixa",
}


def _check_cancelar_fotos(conversa: Conversa, message_text: str) -> bool:
    """Retorna True e limpa estado se o usuário quis cancelar a coleta de fotos."""
    estado = conversa.estado_pendente
    if not estado or estado.get("tipo") != "coleta_fotos":
        return False
    lower = message_text.strip().lower()
    if any(kw in lower for kw in _CANCELAR_FOTOS_KEYWORDS):
        conversa.estado_pendente = None
        return True
    return False


async def _analisar_tres_fotos(fotos: list[dict], user: Usuario, db: Session) -> str:
    """Chama Claude com as 3 fotos para análise completa de composição corporal."""
    primeiro_nome = (user.nome or "").split()[0] if user.nome else None

    content: list[dict] = []
    for foto in fotos:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": foto["mimetype"],
                "data": foto["b64"],
            },
        })
    angulos = ", ".join(f["angulo"] for f in fotos)
    content.append({
        "type": "text",
        "text": (
            f"Analise estas 3 fotos de composição corporal ({angulos}) "
            f"{'do(a) ' + primeiro_nome if primeiro_nome else 'do(a) usuário(a)'}. "
            "Estime o % de gordura corporal em uma FAIXA (ex: 18-22%), nunca valor único. "
            "Descreva distribuição de gordura e massa muscular visível de forma profissional e "
            "respeitosa. Mencione que análise visual tem precisão limitada. "
            "Após a análise textual, use a ferramenta 'registrar_analise_foto' para salvar o resultado."
        ),
    })

    system_with_cache = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT + (f"\n\nNome do usuário: {primeiro_nome}" if primeiro_nome else ""),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            system=system_with_cache,
            messages=[{"role": "user", "content": content}],
            tools=TOOLS,
        )

        api_history: list[dict] = [{"role": "user", "content": content}]
        tool_iterations = 0
        while response.stop_reason == "tool_use" and tool_iterations < 3:
            tool_iterations += 1
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "registrar_analise_foto":
                    result = _process_tool_foto(block.input, user, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            api_history.append({"role": "assistant", "content": response.content})
            api_history.append({"role": "user", "content": tool_results})
            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1500,
                system=system_with_cache,
                messages=api_history,
                tools=TOOLS,
            )

        return next((b.text for b in response.content if hasattr(b, "text")), "")

    except anthropic.APIError as e:
        logger.error("claude_foto_error", extra={"user_id": user.id, "error": str(e)})
        return "Ops, tive um problema ao analisar as fotos. Pode tentar novamente?"


async def _handle_coleta_fotos(
    conversa: Conversa,
    image_b64: str | None,
    image_mimetype: str,
    user: Usuario,
    db: Session,
) -> str | None:
    """
    Gerencia o fluxo de coleta de 3 fotos (frente, costas, lado).
    Retorna a resposta pronta quando a foto foi tratada pelo fluxo,
    ou None quando o fluxo não é aplicável (texto normal ou imagem fora do fluxo).
    """
    estado = conversa.estado_pendente
    em_coleta = estado and estado.get("tipo") == "coleta_fotos"

    # Sem imagem e sem coleta ativa → não interfere
    if not image_b64:
        return None

    primeiro_nome = (user.nome or "").split()[0] if user.nome else "você"

    if not em_coleta:
        # Primeira foto — inicia coleta
        conversa.estado_pendente = {
            "tipo": "coleta_fotos",
            "fotos": [{"b64": image_b64, "mimetype": image_mimetype, "angulo": "frente"}],
            "angulos_restantes": ["costas", "lado"],
        }
        return (
            f"Recebi a foto de frente, {primeiro_nome}! 💪\n\n"
            "Para uma análise mais precisa preciso de mais 2 ângulos:\n\n"
            "👉 Agora manda a foto de *costas* (vire de costas para a câmera).\n\n"
            "_Se quiser cancelar é só dizer 'cancelar'._"
        )

    # Já em coleta — adiciona a foto atual
    fotos: list[dict] = list(estado["fotos"])
    angulos_restantes: list[str] = list(estado["angulos_restantes"])
    angulo_atual = angulos_restantes.pop(0)
    fotos.append({"b64": image_b64, "mimetype": image_mimetype, "angulo": angulo_atual})

    if angulos_restantes:
        # Ainda falta(m) foto(s)
        conversa.estado_pendente = {
            "tipo": "coleta_fotos",
            "fotos": fotos,
            "angulos_restantes": angulos_restantes,
        }
        proximo = angulos_restantes[0]
        return (
            f"Foto de {angulo_atual} recebida! ✅\n\n"
            f"👉 Última foto: manda de *{proximo}* (perfil, braço relaxado ao lado do corpo)."
        )

    # Todas as 3 fotos coletadas — analisar
    conversa.estado_pendente = None
    return await _analisar_tres_fotos(fotos, user, db)


# ---------------------------------------------------------------------------
# Processamento de medidas e foto
# ---------------------------------------------------------------------------

def _process_tool_medidas(tool_input: dict, user: Usuario, db: Session) -> str:
    from datetime import date as date_type
    medida = nutricao_service.registrar_medidas(user.id, date_type.today(), tool_input, db)

    campos_labels = [
        ("peso_kg", "Peso", "kg"),
        ("cintura_cm", "Cintura", "cm"),
        ("quadril_cm", "Quadril", "cm"),
        ("pescoco_cm", "Pescoço", "cm"),
        ("braco_cm", "Braço", "cm"),
        ("coxa_cm", "Coxa", "cm"),
        ("panturrilha_cm", "Panturrilha", "cm"),
    ]
    partes = [
        f"{label}: {tool_input[key]}{unit}"
        for key, label, unit in campos_labels
        if tool_input.get(key) is not None
    ]

    anterior = (
        db.query(type(medida))
        .filter(
            type(medida).user_id == user.id,
            type(medida).id != medida.id,
        )
        .order_by(type(medida).data_medicao.desc())
        .first()
    )

    evolucao = ""
    if anterior and anterior.peso_kg and tool_input.get("peso_kg"):
        diff = round(tool_input["peso_kg"] - anterior.peso_kg, 1)
        sinal = "+" if diff >= 0 else ""
        evolucao = (
            f" Variação de peso vs última medição ({anterior.data_medicao.strftime('%d/%m')}): "
            f"{sinal}{diff}kg."
        )

    return (
        f"REGISTRADO: Medidas corporais em {date.today().strftime('%d/%m/%Y')}: "
        f"{', '.join(partes)}.{evolucao}"
    )


def _process_tool_foto(tool_input: dict, user: Usuario, db: Session) -> str:
    nutricao_service.registrar_foto_analise(
        user_id=user.id,
        gordura_pct=tool_input.get("gordura_estimada_pct"),
        analise_texto=tool_input.get("analise_texto"),
        db=db,
    )
    gordura_str = (
        f" ~{tool_input['gordura_estimada_pct']}% gordura estimado."
        if tool_input.get("gordura_estimada_pct")
        else ""
    )
    return f"REGISTRADO: Análise de composição corporal persistida.{gordura_str}"


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

async def process_message(
    user: Usuario,
    message_text: str,
    db: Session,
    image_b64: str | None = None,
    image_mimetype: str = "image/jpeg",
) -> str:
    conversa = _get_or_create_conversa(user.id, db)
    sessao_data = date.today()

    stored_text = message_text if message_text else "[Foto enviada]"
    mensagens: list[dict] = list(conversa.mensagens or [])

    # 1. Verifica cancelamento do fluxo de fotos (antes de qualquer outra coisa)
    if not image_b64 and _check_cancelar_fotos(conversa, message_text):
        stored_text = message_text
        mensagens.append({"role": "user", "content": stored_text, "timestamp": datetime.utcnow().isoformat()})
        reply = "Tudo bem! Coleta de fotos cancelada. Pode me perguntar qualquer outra coisa. 😊"
        mensagens.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens
        db.add(conversa)
        db.commit()
        return reply

    # 2. Fluxo de coleta de 3 fotos — intercepta imagens antes do Claude geral
    foto_response = await _handle_coleta_fotos(conversa, image_b64, image_mimetype, user, db)
    if foto_response is not None:
        mensagens.append({"role": "user", "content": stored_text, "timestamp": datetime.utcnow().isoformat()})
        mensagens.append({"role": "assistant", "content": foto_response, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens
        db.add(conversa)
        db.commit()
        return foto_response

    # 3. Trata confirmação pendente de exercício antes de chamar o Claude
    ctx_confirmacao = _handle_confirmacao(conversa, message_text, user, sessao_data, db)

    # 4. Adiciona mensagem do usuário ao histórico persistido
    mensagens.append({
        "role": "user",
        "content": stored_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # 5. Monta history para a API (sem timestamps)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in mensagens[-MAX_HISTORY:]
    ]

    # 6. Injeta contexto de sessão, nutrição e coleta pendente de fotos
    ctx_sessao = _sessao_context_str(user.id, sessao_data, db)
    ctx_nutricao = nutricao_service.build_nutricao_context(user.id, db)

    # Se há coleta de fotos ativa e o usuário mandou texto, lembra o Claude
    ctx_coleta = None
    estado_atual = conversa.estado_pendente
    if estado_atual and estado_atual.get("tipo") == "coleta_fotos":
        restantes = estado_atual.get("angulos_restantes", [])
        if restantes:
            ctx_coleta = (
                f"[SISTEMA] Usuário está em processo de envio de fotos para análise de composição "
                f"corporal. Ainda aguardando: {', '.join(restantes)}. "
                "Responda a mensagem de texto normalmente, mas ao final lembre de aguardar a próxima foto."
            )

    partes_ctx = [p for p in [ctx_sessao, ctx_nutricao, ctx_confirmacao, ctx_coleta] if p]
    if partes_ctx:
        injecao = "\n\n".join(partes_ctx)
        history = [
            {"role": "user", "content": f"[Contexto automático do sistema]\n{injecao}"},
            {"role": "assistant", "content": "Entendido, tenho esses dados em consideração."},
        ] + history

    # 7. Se for imagem não capturada pelo fluxo de coleta (não deveria acontecer), passa para Claude
    if image_b64:
        for i in range(len(history) - 1, -1, -1):
            if history[i]["role"] == "user":
                history[i]["content"] = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_mimetype,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": message_text or "Analise esta imagem.",
                    },
                ]
                break

    # 8. System prompt com cache
    primeiro_nome = (user.nome or "").split()[0] if user.nome else None
    system_with_cache = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT + (f"\n\nNome do usuário: {primeiro_nome}" if primeiro_nome else ""),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    # 9. Chama Claude (com tool use)
    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            system=system_with_cache,
            messages=history,
            tools=TOOLS,
        )

        # 10. Loop de tool use (máximo 5 ferramentas por mensagem)
        tool_iterations = 0
        while response.stop_reason == "tool_use" and tool_iterations < 5:
            tool_iterations += 1
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == "registrar_exercicio":
                    result = _process_tool_registrar(block.input, user, sessao_data, conversa, db)
                elif block.name == "registrar_medidas":
                    result = _process_tool_medidas(block.input, user, db)
                elif block.name == "registrar_analise_foto":
                    result = _process_tool_foto(block.input, user, db)
                else:
                    result = "Ferramenta desconhecida."
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

    # 11. Persiste histórico e registros secundários
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
