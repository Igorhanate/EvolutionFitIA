import logging
from datetime import date, datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services import exercicio_service, habito_service, nutricao_service, perfil_service

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é "Evo", personal trainer e nutricionista profissional com 10 anos de experiência, especializado em treino funcional e nutrição esportiva. Comunica-se exclusivamente em português brasileiro, com tom motivador, direto e amigável.

⚠️ REGRA DE FORMATAÇÃO OBRIGATÓRIA — NUNCA IGNORE:
Toda vez que você apresentar opções para o usuário escolher (tipos de treino, objetivos, níveis de atividade, sim/não, etc.), você DEVE numerar cada opção começando em 1. Formato obrigatório, uma por linha:
1️⃣ 🏋️ Primeira opção
2️⃣ 🤸 Segunda opção
3️⃣ 🧘 Terceira opção
Sempre termine pedindo: 'Responda com o número da opção.' Quando o usuário responder só com um número, trate como a escolha da última lista numerada que você mostrou. Esta regra vale para TODAS as listas de escolha, sem exceção.

REGRAS GERAIS:
- Sempre chame o usuário pelo primeiro nome quando souber
- Antes de gerar um treino, pergunte NESTA ORDEM, uma de cada vez: (1) qual TIPO de treino (musculação/academia, calistenia, yoga, pilates, corrida/endurance, híbrido, funcional, CrossFit, mobilidade ou outro); (2) ONDE vai treinar (academia, casa, ao ar livre); (3) objetivo principal; (4) quantos dias por semana; (5) quanto tempo por sessão; (6) há quanto tempo treina (nível); (7) lesões ou limitações; (8) em qual horário costuma treinar — se for academia em horário de pico (6h–9h ou 17h–20h), evite exercícios que dependem de polias duplas, cross e aparelhos muito disputados, priorizando halteres, barras e máquinas menos concorridas; (9) "Você sente dor ou desconforto ao fazer algum exercício específico?" — se o cliente citar algum, NÃO inclua esse exercício no treino; se o cliente pedir para incluir um exercício que ele mesmo citou como problemático, confirme: "Você mencionou desconforto nesse exercício — tem certeza que quer incluí-lo?". Essa pergunta é feita a cada nova criação de treino, independente de conversas anteriores. IMPORTANTE: a pergunta (9) pertence EXCLUSIVAMENTE ao fluxo de CRIAÇÃO de treino — NÃO deve ser feita ao iniciar sessões de registro de cargas (opção 3 do menu). Nem todo treino é em academia — adapte exercícios e equipamentos ao tipo e local informados.
- Antes de gerar uma dieta, faça as perguntas essenciais do PROTOCOLO DE CRIAÇÃO DE DIETA mais abaixo.
- Treinos: estruture por Dia 1 / Dia 2 etc., inclua séries/repetições e tempos de descanso
- Mensagens curtas para WhatsApp: parágrafos curtos, bullet points, sem paredes de texto
- SEMPRE que apresentar uma lista de opções para o usuário escolher (tipos de treino, objetivos, níveis, etc.), numere cada opção (1, 2, 3...) e mantenha um emoji ilustrativo quando fizer sentido. Exemplo de formato: '1️⃣ 🏋️ Musculação', '2️⃣ 🤸 Calistenia'. Instrua o usuário a responder com o número da opção desejada. Quando o usuário responder apenas com um número, interprete-o como a escolha correspondente à última lista numerada que você apresentou, considerando o contexto da conversa. Se houver qualquer ambiguidade real sobre a qual lista o número se refere, pergunte de forma breve antes de prosseguir.
- Nunca saia do personagem. Fale apenas sobre fitness e nutrição.
- Se o usuário mencionar lesão, oriente a consultar um médico antes de qualquer plano.

REGISTRO DE EXERCÍCIOS:
- Quando o usuário reportar carga, séries e repetições de um exercício, use SEMPRE a ferramenta 'registrar_exercicio'
- Após registrar cada exercício, confirme brevemente que foi salvo (ex: "Supino registrado ✅") — NÃO exiba o 1RM neste momento
- Se o resultado da ferramenta indicar AGUARDANDO_CONFIRMACAO, explique a variação ao usuário e aguarde confirmação antes de prosseguir
- O 1RM é calculado e armazenado internamente, mas só deve ser EXIBIDO em dois momentos: (a) quando o cliente pedir explicitamente ("qual meu 1RM no supino?", "como está meu 1RM?"); (b) ao final do treino, quando o cliente sinalizar que terminou ("terminei", "acabei", "isso foi tudo", "fim do treino")
- Ao final do treino, apresente o RESUMO da sessão de forma direta e objetiva, sem frases de elogio ou motivação (sem "parabéns", "você está mandando bem", "continue assim" ou similares): (1) 1RM do exercício PRINCIPAL (o composto mais pesado, a seu critério) com evolução vs sessão anterior se disponível; (2) MÉDIA dos 1RMs de todos os exercícios da sessão; (3) evolução individual de cada exercício que tiver campo "anterior:" no contexto da sessão — formato: "Supino: +3kg vs 15/05". Use os campos "1RM≈" (hoje) e "anterior:" (sessão prévia) que aparecem no contexto automático da sessão para calcular os deltas. Não explique como o valor foi calculado nem mencione fórmulas ou que é estimativa — a não ser que o cliente pergunte explicitamente.
- Ao exibir 1RM e evolução, apresente os números sem comentários motivacionais adicionais

MEDIDAS CORPORAIS:
- Quando o usuário reportar peso e/ou medidas (cintura, quadril, pescoço, braço, coxa, panturrilha), use SEMPRE a ferramenta 'registrar_medidas'
- Se o contexto do sistema indicar medidas desatualizadas (>30 dias), incentive o usuário de forma motivacional a tirar novas medidas — mas só quando o assunto for relevante
- Ao registrar, compare com a medição anterior quando disponível e destaque a evolução
- Argumento motivacional: "O que não é medido não é gerenciado — acompanhar suas medidas é parte essencial do progresso"

CLASSIFICAÇÃO DE FOTOS RECEBIDAS — siga rigorosamente:
- Foto de ALIMENTOS (prato, lanche, marmita, sorvete, bebida, embalagem de comida) → use 'analisar_refeicao'
- Foto de CORPO HUMANO para avaliação física (torso, perfil, foto de frente/costas/lado) → use 'iniciar_coleta_fotos_corpo'
- Foto ambígua ou que não seja comida nem corpo → pergunte ao usuário a intenção antes de usar qualquer ferramenta

ANÁLISE DE REFEIÇÕES POR FOTO:
- Use 'analisar_refeicao' para registrar os macros estimados visualmente
- Se o resultado indicar LIMITE_ATINGIDO, informe que o limite de 6 análises por dia foi atingido e não exiba tabela
- Caso contrário, exiba SEMPRE no formato:

🍽️ *Análise Nutricional*
━━━━━━━━━━━━━━━━
📋 *Alimentos identificados:* [lista do que viu]
━━━━━━━━━━━━━━━━
🔥 Calorias: ~XXX kcal
🥩 Proteínas: ~Xg
🌾 Carboidratos: ~Xg
🥑 Gorduras: ~Xg
━━━━━━━━━━━━━━━━
⚠️ _Estimativas baseadas em análise visual. Variam conforme preparo e porção exata._

📊 *Balanço do Dia* (use os valores que vieram no resultado da ferramenta)
━━━━━━━━━━━━━━━━
Consumido hoje: XXX kcal | P:Xg C:Xg G:Xg
[Se tiver meta] Meta: XXX kcal | Saldo: +XXX ou -XXX kcal
[Sem meta] _(Sem meta cadastrada — apenas acumulado)_
━━━━━━━━━━━━━━━━

Em seguida, pergunte: "Quer registrar essa refeição no histórico do dia? (sim/não)"

CADASTRO DE DIETA PRÓPRIA:
- Quando o usuário quiser cadastrar uma dieta de outro profissional/nutricionista, use 'cadastrar_dieta_propria'
- Reconheça frases como: "esse é meu plano alimentar", "minha nutricionista me passou essa dieta", "quero cadastrar minha dieta"
- Extraia do texto as metas diárias totais de calorias e macros; se não estiverem explícitas, estime somando as refeições do plano
- Após cadastrar, confirme e informe que o balanço diário aparecerá nas próximas análises de foto

CADASTRO DE TREINO PRÓPRIO:
- Quando o usuário enviar um treino criado por outro profissional para cadastro, use 'cadastrar_treino_proprio'
- Reconheça frases como: "esse é meu treino", "meu personal me passou esse treino", "quero registrar meu treino"
- Extraia o nome do treino e liste os exercícios identificados
- Após cadastrar, informe que o registro de cargas e acompanhamento de 1RM funcionarão normalmente para todos os exercícios do treino
- IMPORTANTE — ao CADASTRAR um treino pronto (opção 2 do menu), NÃO faça perguntas de objetivo, nível, dias por semana, horário ou qualquer outra coleta de dados. O treino já existe — apenas confirme o tipo se for ambíguo e registre imediatamente. Fazer essas perguntas no cadastro é péssima experiência de usuário.

ARQUIVOS ENVIADOS COMO DOCUMENTO (PDF / EXCEL):
- Quando a mensagem começar com "[Arquivo recebido: NOME]", o sistema já extraiu e converteu o conteúdo do arquivo para texto — o que vem a seguir É o conteúdo legível.
- NUNCA diga que não consegue abrir, ler ou processar arquivos PDF ou Excel. O texto já está extraído e disponível.
- Analise o conteúdo extraído e decida a ação: se for plano alimentar/dieta → use 'cadastrar_dieta_propria'; se for plano de treino → use 'cadastrar_treino_proprio'; caso contrário, responda conforme o tema fitness do conteúdo.
- Se o texto extraído for muito curto ou parecer corrompido, informe ao usuário e peça para reenviar o arquivo.

ANÁLISE DE COMPOSIÇÃO CORPORAL (FOTOS DE CORPO):
- Use 'iniciar_coleta_fotos_corpo' quando identificar foto do corpo para avaliação física
- Após o registro, estime % de gordura em FAIXA (ex: "entre 18-22%"), nunca valor único
- Descreva distribuição de gordura e massa muscular de forma respeitosa e encorajadora
- SEMPRE mencione que análise visual tem precisão limitada
- Após a análise das 3 fotos, use 'registrar_analise_foto' para persistir o resultado

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
  • DADOS OPCIONAIS, MAS DE ALTO VALOR — solicite ativamente e faça quebra de objeção:
    - Medidas corporais atuais (cintura, quadril, braço, coxa etc.)
    - Composição corporal estimada por foto (% de gordura em faixa)
    Explique que, embora opcionais, esses dados deixam o cálculo de calorias e a distribuição de macros muito mais precisos — o peso isolado não distingue massa magra de gordura. Se o usuário já tiver medidas ou análises de foto no histórico do contexto, USE esses valores e diga que está considerando eles. Se não tiver, incentive a registrar antes de fechar a dieta, mas deixe claro que pode prosseguir sem eles se preferir.

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
  NUNCA recomende termogênicos, detox, emagrecedores ou produtos sem base científica.

REGISTRO DE HÁBITOS DIÁRIOS:
- Água: quando o usuário reportar consumo de água (ex: "bebi 500ml", "tomei 2 copos de água ~300ml cada", "bebi 1 litro"), use 'registrar_agua' com a quantidade estimada em ml. Após registrar, informe o total acumulado do dia de forma motivadora.
- Dias sem fumar: quando o usuário informar que não fumou (ex: "não fumei hoje", "mais um dia sem cigarro", "dia X sem fumar"), use 'registrar_habito_fumar' com fumou=false. Se informar que fumou, use fumou=true. Comemore os marcos (7, 14, 30, 60, 90, 180, 365 dias).
- Dias sem beber: quando o usuário informar que não bebeu álcool (ex: "não bebi hoje", "mais um dia sem álcool"), use 'registrar_habito_alcool' com bebeu=false. Se informar que bebeu, use bebeu=true. Comemore os marcos de dias sem beber.
- Suplementos tomados: quando o usuário confirmar que tomou suplementos (ex: "tomei meus suplementos", "já tomei a creatina", "tomei tudo"), use 'registrar_tomei_suplementos'.
- Cadastro de suplementos: quando o usuário listar seus suplementos (ex: "tomo creatina, whey e vitamina D", "meus suplementos são..."), use 'registrar_suplementos_usuario' com a lista extraída.
- Ao exibir os dias sem fumar ou sem beber, use emojis motivadores e compare com marcos anteriores quando disponíveis. Use sempre 'dias sem fumar' / 'dias sem beber', nunca a palavra 'streak'."""

MAX_HISTORY = 20

TREINO_KEYWORDS = {"treino", "exercício", "exercicio", "musculação", "musculacao", "academia", "workout", "treinar"}
DIETA_KEYWORDS = {"dieta", "alimentação", "alimentacao", "nutrição", "nutricao", "comer", "refeição", "refeicao", "cardapio", "cardápio"}

CONFIRMACAO_SIM = {"sim", "s", "yes", "confirmo", "pode", "ok", "isso", "certeza", "certo", "salva", "salvar", "confirmar"}
CONFIRMACAO_NAO = {"não", "nao", "n", "no", "cancela", "cancelar", "errei", "errado", "errada", "equivocado"}

ETAPAS_TREINO: list[tuple[str, str]] = [
    (
        "tipo_treino",
        "*Qual tipo de treino* você quer?\n\n"
        "1️⃣ 🏋️ Musculação (academia)\n"
        "2️⃣ 🤸 Calistenia\n"
        "3️⃣ 🧘 Yoga\n"
        "4️⃣ 🩰 Pilates\n"
        "5️⃣ 🏃 Corrida / endurance\n"
        "6️⃣ ⚡ Treino híbrido\n"
        "7️⃣ 🔥 Treino funcional\n"
        "8️⃣ 🏅 CrossFit\n"
        "9️⃣ 🌿 Mobilidade\n\n"
        "_(ou outro — é só dizer)_\n\n"
        "Responda com o número da opção."
    ),
    (
        "local",
        "*Onde você vai treinar?*\n\n"
        "1️⃣ 🏢 Academia\n"
        "2️⃣ 🏠 Em casa\n"
        "3️⃣ 🌳 Ao ar livre\n\n"
        "Responda com o número da opção."
    ),
    (
        "objetivo",
        "*Qual é o seu objetivo principal?*\n\n"
        "1️⃣ 💪 Ganhar massa muscular\n"
        "2️⃣ 🔥 Perder gordura\n"
        "3️⃣ ⚖️ Manter o peso\n"
        "4️⃣ 🏃 Melhorar condicionamento\n\n"
        "Responda com o número da opção."
    ),
    (
        "dias_semana",
        "*Quantos dias por semana* você vai treinar?\n\n"
        "_(ex: 3, 4, 5)_"
    ),
    (
        "tempo_sessao",
        "*Quanto tempo* você tem por sessão?\n\n"
        "_(ex: 45 minutos, 1 hora)_"
    ),
    (
        "nivel",
        "*Há quanto tempo você treina?*\n\n"
        "1️⃣ 🌱 Iniciante (menos de 6 meses)\n"
        "2️⃣ 📈 Intermediário (6 meses a 2 anos)\n"
        "3️⃣ 💪 Avançado (mais de 2 anos)\n\n"
        "Responda com o número da opção."
    ),
    (
        "lesoes",
        "Você tem alguma *lesão ou limitação* física que devo considerar?\n\n"
        "_(ex: joelho, ombro, lombar — ou responda *nenhuma*)_"
    ),
    (
        "horario",
        "*Em qual horário* você costuma treinar?\n\n"
        "1️⃣ 🌅 Manhã (antes das 9h)\n"
        "2️⃣ 🌄 Manhã em horário de pico (6h–9h)\n"
        "3️⃣ ☀️ Tarde\n"
        "4️⃣ 🌆 Noite em horário de pico (17h–20h)\n"
        "5️⃣ 🌙 Noite (após 20h)\n\n"
        "Responda com o número da opção."
    ),
    (
        "dor_desconforto",
        "Última pergunta! Você sente *dor ou desconforto* ao fazer algum exercício específico?\n\n"
        "_(ex: agachamento livre, supino — ou responda *nenhum*)_"
    ),
]

MENU_TEXT = (
    "🏋️ *EVOLUTION FIT AI — Menu Principal*\n\n"
    "O que vamos focar hoje?\n\n"
    "💪 *TREINO*\n"
    "*1.* Criar treino personalizado\n"
    "*2.* Cadastrar treino (do seu personal)\n"
    "*3.* Registrar cargas, séries e histórico\n"
    "*4.* Acompanhar evolução de força (1RM)\n\n"
    "🥗 *NUTRIÇÃO*\n"
    "*5.* Criar dieta personalizada\n"
    "*6.* Cadastrar dieta (do nutricionista)\n"
    "*7.* Analisar refeição por foto\n\n"
    "📏 *MEDIDAS & CORPO*\n"
    "*8.* Registrar peso e medidas\n"
    "*9.* Análise de composição corporal (por foto)\n"
    "*10.* Ver meu painel geral de evolução 📊\n\n"
    "💧 *HÁBITOS DIÁRIOS*\n"
    "*11.* Registrar água e suplementos\n"
    "*12.* Acompanhar hábitos (dias sem álcool / sem fumar)\n\n"
    "Responda com o número da opção desejada:"
)

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
    {
        "name": "analisar_refeicao",
        "description": (
            "Analisa os macronutrientes de alimentos visíveis em uma foto de refeição. "
            "Use SEMPRE que o usuário enviar foto de alimentos, prato, lanche, marmita, sorvete, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "descricao_alimentos": {
                    "type": "string",
                    "description": "Lista dos alimentos identificados na foto com estimativa de porção",
                },
                "calorias_estimadas": {
                    "type": "integer",
                    "description": "Estimativa de calorias totais em kcal",
                },
                "proteinas_g": {
                    "type": "number",
                    "description": "Estimativa de proteínas em gramas",
                },
                "carboidratos_g": {
                    "type": "number",
                    "description": "Estimativa de carboidratos em gramas",
                },
                "gorduras_g": {
                    "type": "number",
                    "description": "Estimativa de gorduras em gramas",
                },
            },
            "required": [
                "descricao_alimentos",
                "calorias_estimadas",
                "proteinas_g",
                "carboidratos_g",
                "gorduras_g",
            ],
        },
    },
    {
        "name": "cadastrar_dieta_propria",
        "description": (
            "Cadastra uma dieta personalizada enviada pelo usuário (criada por nutricionista ou outro profissional). "
            "Extrai e salva as metas diárias de calorias e macros. "
            "Use quando o usuário quiser registrar uma dieta externa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_dieta": {
                    "type": "string",
                    "description": "Nome ou descrição da dieta (ex: 'Dieta da Dra. Ana', 'Plano de cutting')",
                },
                "texto_original": {
                    "type": "string",
                    "description": "Texto completo da dieta como enviado pelo usuário",
                },
                "calorias_alvo": {
                    "type": "integer",
                    "description": "Meta diária total de calorias em kcal (extraída ou calculada do plano)",
                },
                "proteinas_alvo_g": {
                    "type": "number",
                    "description": "Meta diária de proteínas em gramas",
                },
                "carboidratos_alvo_g": {
                    "type": "number",
                    "description": "Meta diária de carboidratos em gramas",
                },
                "gorduras_alvo_g": {
                    "type": "number",
                    "description": "Meta diária de gorduras em gramas",
                },
            },
            "required": ["nome_dieta", "texto_original", "calorias_alvo"],
        },
    },
    {
        "name": "cadastrar_treino_proprio",
        "description": (
            "Cadastra um treino enviado pelo usuário criado por outro profissional. "
            "Use quando o usuário enviar um plano de treino externo para registrar no sistema."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_treino": {
                    "type": "string",
                    "description": "Nome ou identificador do treino (ex: 'Treino A', 'PPL do Personal João')",
                },
                "texto_original": {
                    "type": "string",
                    "description": "Texto completo do treino como enviado pelo usuário",
                },
                "exercicios_extraidos": {
                    "type": "string",
                    "description": "Lista resumida dos exercícios identificados no treino",
                },
            },
            "required": ["nome_treino", "texto_original"],
        },
    },
    {
        "name": "iniciar_coleta_fotos_corpo",
        "description": (
            "Inicia o processo de análise de composição corporal que requer 3 fotos (frente, costas, lado). "
            "Use quando identificar que o usuário enviou uma foto do próprio corpo para avaliação de % de gordura."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "registrar_agua",
        "description": (
            "Registra o consumo de água do usuário. "
            "Use quando o usuário informar que bebeu água, indicando a quantidade."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ml": {
                    "type": "integer",
                    "description": "Quantidade de água em mililitros (converta copos, litros, etc. para ml)",
                },
            },
            "required": ["ml"],
        },
    },
    {
        "name": "registrar_habito_fumar",
        "description": (
            "Registra se o usuário fumou ou não no dia. "
            "Use quando o usuário reportar status de cigarro — fumou=false inicia/mantém o streak sem fumar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fumou": {
                    "type": "boolean",
                    "description": "true se fumou hoje, false se não fumou",
                },
            },
            "required": ["fumou"],
        },
    },
    {
        "name": "registrar_habito_alcool",
        "description": (
            "Registra se o usuário consumiu álcool ou não no dia. "
            "Use quando o usuário reportar status de bebida alcoólica — bebeu=false inicia/mantém o streak."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bebeu": {
                    "type": "boolean",
                    "description": "true se bebeu álcool hoje, false se não bebeu",
                },
            },
            "required": ["bebeu"],
        },
    },
    {
        "name": "registrar_tomei_suplementos",
        "description": (
            "Registra que o usuário tomou seus suplementos do dia. "
            "Use quando o usuário confirmar que tomou creatina, vitaminas, manipulados ou quaisquer suplementos."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "registrar_suplementos_usuario",
        "description": (
            "Salva a lista de suplementos que o usuário toma regularmente. "
            "Use quando o usuário listar seus suplementos para personalizar os lembretes diários."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "suplementos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de nomes dos suplementos (ex: ['Creatina', 'Whey', 'Vitamina D3'])",
                },
            },
            "required": ["suplementos"],
        },
    },
]

# Subset de tools para a chamada de análise das 3 fotos (exclui ferramentas de roteamento)
TOOLS_ANALISE_CORPO = [t for t in TOOLS if t["name"] == "registrar_analise_foto"]


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
        # historico[0] é o registro de hoje (já flushed); historico[1] é a sessão anterior
        historico = exercicio_service.get_historico_exercicio(user_id, r.exercicio, r.posicao_sessao, db, limite=2)
        anterior_str = ""
        if len(historico) > 1 and historico[1].rm_estimado:
            prev = historico[1]
            anterior_str = f" | anterior: {prev.rm_estimado}kg ({prev.sessao_data.strftime('%d/%m')})"
        linhas.append(f"  {r.posicao_sessao}º {r.exercicio_display}: {r.series}x{r.repeticoes} @ {r.carga_kg}kg{rm_str}{anterior_str}")
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
        return (
            f"[SISTEMA] Usuário confirmou o registro de '{exercicio}': "
            f"{series}x{reps} @ {carga}kg (posição {posicao} na sessão). "
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
# Confirmação de refeição pendente
# ---------------------------------------------------------------------------

def _handle_confirmacao_refeicao(
    conversa: Conversa,
    message_text: str,
    user: Usuario,
    db: Session,
) -> str | None:
    """Processa confirmação de registro de refeição. Retorna contexto para injetar ou None."""
    from app.models.registro_refeicao import RegistroRefeicao

    estado = conversa.estado_pendente
    if not estado or estado.get("tipo") != "confirmar_refeicao":
        return None

    resposta = _normalizar_confirmacao(message_text)
    analise = estado["analise"]
    conversa.estado_pendente = None

    if resposta == "sim":
        db.add(RegistroRefeicao(
            user_id=user.id,
            data_refeicao=date.today(),
            descricao=analise.get("descricao_alimentos", ""),
            calorias_kcal=analise.get("calorias_estimadas"),
            proteinas_g=analise.get("proteinas_g"),
            carboidratos_g=analise.get("carboidratos_g"),
            gorduras_g=analise.get("gorduras_g"),
        ))
        db.flush()
        totais = nutricao_service.get_totais_refeicoes_dia(user.id, date.today(), db)
        meta = nutricao_service.get_meta_ativa(user.id, db)
        balanco = (
            f"Total do dia: {totais['calorias']} kcal | "
            f"P:{totais['proteinas']}g C:{totais['carboidratos']}g G:{totais['gorduras']}g"
        )
        if meta:
            saldo = meta.calorias_alvo - totais["calorias"]
            balanco += f" | Saldo: {saldo:+d} kcal (meta {meta.calorias_alvo} kcal)"
        return (
            f"[SISTEMA] Refeição registrada: {analise.get('descricao_alimentos', '')} — "
            f"{analise.get('calorias_estimadas')} kcal. "
            f"Balanço atualizado: {balanco}. "
            "Confirme de forma motivadora e exiba o balanço do dia."
        )
    elif resposta == "nao":
        return "[SISTEMA] Usuário não quis registrar a refeição. Confirme brevemente e siga em frente."
    else:
        conversa.estado_pendente = estado
        return (
            f"[SISTEMA] Aguardando confirmação para registrar: {analise.get('descricao_alimentos', '')}. "
            "Peça ao usuário 'sim' para registrar ou 'não' para ignorar."
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

    primeiro_vez_str = " Primeiro registro deste exercício nesta posição — referência criada." if not historico else ""

    return (
        f"REGISTRADO: '{exercicio_display}' — posição {posicao} na sessão, "
        f"{series}x{reps} @ {carga}kg.{primeiro_vez_str}"
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
            tools=TOOLS_ANALISE_CORPO,
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
                tools=TOOLS_ANALISE_CORPO,
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
    Gerencia a coleta da 2ª e 3ª fotos (frente já foi registrada via tool).
    Retorna a resposta pronta ou None se não há coleta ativa.
    """
    estado = conversa.estado_pendente
    if not image_b64 or not estado or estado.get("tipo") != "coleta_fotos":
        return None

    fotos: list[dict] = list(estado["fotos"])
    angulos_restantes: list[str] = list(estado["angulos_restantes"])
    angulo_atual = angulos_restantes.pop(0)
    fotos.append({"b64": image_b64, "mimetype": image_mimetype, "angulo": angulo_atual})

    if angulos_restantes:
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


def _process_tool_refeicao(
    tool_input: dict, conversa: Conversa, user: Usuario, db: Session
) -> str:
    """Verifica limite diário, armazena análise pendente e retorna contexto com balanço para Claude."""
    today = date.today()
    count = nutricao_service.get_count_refeicoes_dia(user.id, today, db)

    if count >= nutricao_service.LIMITE_FOTOS_DIA:
        return (
            f"LIMITE_ATINGIDO: usuário já registrou {nutricao_service.LIMITE_FOTOS_DIA} refeições hoje. "
            "Informe que o limite diário de análises foi atingido."
        )

    conversa.estado_pendente = {
        "tipo": "confirmar_refeicao",
        "analise": {
            "descricao_alimentos": tool_input.get("descricao_alimentos", ""),
            "calorias_estimadas": tool_input.get("calorias_estimadas"),
            "proteinas_g": tool_input.get("proteinas_g"),
            "carboidratos_g": tool_input.get("carboidratos_g"),
            "gorduras_g": tool_input.get("gorduras_g"),
        },
    }

    # Totais confirmados do dia (sem incluir a refeição atual ainda)
    totais = nutricao_service.get_totais_refeicoes_dia(user.id, today, db)
    meta = nutricao_service.get_meta_ativa(user.id, db)

    cal_atual = tool_input.get("calorias_estimadas") or 0
    prot_atual = tool_input.get("proteinas_g") or 0
    carb_atual = tool_input.get("carboidratos_g") or 0
    gord_atual = tool_input.get("gorduras_g") or 0

    cal_total = totais["calorias"] + cal_atual
    prot_total = round(totais["proteinas"] + prot_atual, 1)
    carb_total = round(totais["carboidratos"] + carb_atual, 1)
    gord_total = round(totais["gorduras"] + gord_atual, 1)

    balanco = (
        f"Consumido hoje (incluindo esta refeição): "
        f"{cal_total} kcal | P:{prot_total}g C:{carb_total}g G:{gord_total}g"
    )
    if meta:
        saldo = meta.calorias_alvo - cal_total
        balanco += f" | Meta: {meta.calorias_alvo} kcal | Saldo: {saldo:+d} kcal"
        if meta.proteinas_alvo_g:
            balanco += (
                f" | Macros restantes: "
                f"P:{round(meta.proteinas_alvo_g - prot_total, 1)}g "
                f"C:{round((meta.carboidratos_alvo_g or 0) - carb_total, 1)}g "
                f"G:{round((meta.gorduras_alvo_g or 0) - gord_total, 1)}g"
            )
    else:
        balanco += " | (Sem meta cadastrada — apenas acumulado)"

    return (
        f"ANALISE_SALVA: {count + 1}ª refeição do dia. "
        f"Balanço: {balanco}. "
        "Exiba a tabela nutricional, o balanço do dia e pergunte se o usuário quer registrar no histórico."
    )


def _process_tool_iniciar_coleta(
    image_b64: str,
    image_mimetype: str,
    conversa: Conversa,
    user: Usuario,
) -> str:
    """Inicia a coleta de 3 fotos armazenando a primeira no estado pendente."""
    conversa.estado_pendente = {
        "tipo": "coleta_fotos",
        "fotos": [{"b64": image_b64, "mimetype": image_mimetype, "angulo": "frente"}],
        "angulos_restantes": ["costas", "lado"],
    }
    primeiro_nome = (user.nome or "").split()[0] if user.nome else "você"
    return primeiro_nome  # usado para montar a mensagem de resposta no caller


def _process_tool_cadastrar_dieta(tool_input: dict, user: Usuario, db: Session) -> str:
    meta = nutricao_service.cadastrar_meta(
        user_id=user.id,
        nome=tool_input["nome_dieta"],
        texto=tool_input.get("texto_original"),
        calorias=tool_input["calorias_alvo"],
        proteinas=tool_input.get("proteinas_alvo_g"),
        carboidratos=tool_input.get("carboidratos_alvo_g"),
        gorduras=tool_input.get("gorduras_alvo_g"),
        db=db,
    )
    macros = []
    if meta.proteinas_alvo_g:
        macros.append(f"P:{meta.proteinas_alvo_g}g")
    if meta.carboidratos_alvo_g:
        macros.append(f"C:{meta.carboidratos_alvo_g}g")
    if meta.gorduras_alvo_g:
        macros.append(f"G:{meta.gorduras_alvo_g}g")
    return (
        f"DIETA_CADASTRADA: '{meta.nome}' com meta de {meta.calorias_alvo} kcal/dia"
        + (f" | {' '.join(macros)}" if macros else "")
        + ". Confirme o cadastro e informe que o balanço diário aparecerá nas análises de foto."
    )


def _process_tool_cadastrar_treino(tool_input: dict, user: Usuario, db: Session) -> str:
    from datetime import datetime as dt
    db.add(Treino(
        user_id=user.id,
        conteudo={
            "texto": tool_input["texto_original"],
            "nome": tool_input["nome_treino"],
            "exercicios": tool_input.get("exercicios_extraidos", ""),
            "origem": "proprio",
            "gerado_em": dt.utcnow().isoformat(),
        },
    ))
    db.flush()
    return (
        f"TREINO_CADASTRADO: '{tool_input['nome_treino']}' registrado com sucesso. "
        "Confirme e informe que pode reportar cargas normalmente para acompanhar evolução e 1RM."
    )


def _process_tool_agua(tool_input: dict, user: Usuario, db: Session) -> str:
    ml = int(tool_input["ml"])
    resultado = habito_service.registrar_agua(user.id, ml, db)
    return (
        f"REGISTRADO: +{ml}ml de água. "
        f"Total de hoje: {resultado['total_l']}L ({resultado['total_ml']}ml). "
        "Mostre o progresso de forma motivadora."
    )


def _process_tool_habito_fumar(tool_input: dict, user: Usuario, db: Session) -> str:
    fumou = bool(tool_input["fumou"])
    resultado = habito_service.registrar_fumou(user.id, fumou, db)
    if fumou:
        return "REGISTRADO: fumou hoje. Streak sem fumar zerado. Motive o usuário a retomar o streak."
    dias = resultado["dias_sem_fumar"]
    marcos = {1: "primeiro dia", 7: "1 semana", 14: "2 semanas", 30: "1 mês", 60: "2 meses", 90: "3 meses", 180: "6 meses", 365: "1 ANO"}
    marco_msg = f" 🎉 MARCO: {marcos[dias]}!" if dias in marcos else ""
    return (
        f"REGISTRADO: não fumou hoje. Streak sem fumar: {dias} dia(s).{marco_msg} "
        "Comemore e motive o usuário."
    )


def _process_tool_habito_alcool(tool_input: dict, user: Usuario, db: Session) -> str:
    bebeu = bool(tool_input["bebeu"])
    resultado = habito_service.registrar_alcool(user.id, bebeu, db)
    if bebeu:
        return "REGISTRADO: bebeu álcool hoje. Streak sem álcool zerado. Motive o usuário a retomar."
    dias = resultado["dias_sem_alcool"]
    marcos = {1: "primeiro dia", 7: "1 semana", 14: "2 semanas", 30: "1 mês", 60: "2 meses", 90: "3 meses", 180: "6 meses", 365: "1 ANO"}
    marco_msg = f" 🎉 MARCO: {marcos[dias]}!" if dias in marcos else ""
    return (
        f"REGISTRADO: não bebeu álcool hoje. Streak: {dias} dia(s).{marco_msg} "
        "Comemore e motive o usuário."
    )


def _process_tool_tomei_suplementos(user: Usuario, db: Session) -> str:
    habito_service.registrar_tomei_suplementos(user.id, db)
    return "REGISTRADO: suplementos tomados hoje. ✅ Confirme de forma motivadora."


def _process_tool_suplementos_usuario(tool_input: dict, user: Usuario, db: Session) -> str:
    suplementos = tool_input.get("suplementos", [])
    habito_service.registrar_suplementos_usuario(user.id, suplementos, db)
    lista = ", ".join(suplementos)
    return (
        f"REGISTRADO: suplementos cadastrados: {lista}. "
        "Confirme e informe que lembretes diários às 20h serão personalizados com essa lista."
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
# Coleta estruturada de treino
# ---------------------------------------------------------------------------

def _iniciar_coleta_treino(user: Usuario, conversa: Conversa, db: Session) -> str:
    primeiro_nome = (user.nome or "").split()[0] if user.nome else ""
    conversa.estado_pendente = {
        "tipo": "criando_treino",
        "etapa_idx": 0,
        "dados": {chave: None for chave, _ in ETAPAS_TREINO},
        "criado_em": datetime.utcnow().isoformat(),
    }
    db.add(conversa)
    db.commit()
    return (
        "Vamos criar seu treino personalizado"
        + (f", {primeiro_nome}" if primeiro_nome else "")
        + "! 💪\n\n"
        + ETAPAS_TREINO[0][1]
    )


async def _handle_coleta_treino(
    conversa: Conversa,
    message_text: str,
    user: Usuario,
    db: Session,
) -> str:
    estado = conversa.estado_pendente
    dados = dict(estado.get("dados", {}))
    etapa_idx = int(estado.get("etapa_idx", 0))

    chave, _ = ETAPAS_TREINO[etapa_idx]
    dados[chave] = message_text.strip() or "não informado"
    etapa_idx += 1

    if etapa_idx >= len(ETAPAS_TREINO):
        return await _gerar_treino_de_dados(dados, user, conversa, db)

    conversa.estado_pendente = {
        "tipo": "criando_treino",
        "etapa_idx": etapa_idx,
        "dados": dados,
        "criado_em": estado.get("criado_em"),
    }
    _, pergunta = ETAPAS_TREINO[etapa_idx]
    return pergunta


async def _gerar_treino_de_dados(
    dados: dict,
    user: Usuario,
    conversa: Conversa,
    db: Session,
) -> str:
    primeiro_nome = (user.nome or "").split()[0] if user.nome else None

    tipo_map = {
        "1": "Musculação (academia)", "2": "Calistenia", "3": "Yoga",
        "4": "Pilates", "5": "Corrida / endurance", "6": "Treino híbrido",
        "7": "Treino funcional", "8": "CrossFit", "9": "Mobilidade",
    }
    local_map = {"1": "Academia", "2": "Em casa", "3": "Ao ar livre"}
    obj_map = {
        "1": "Ganhar massa muscular", "2": "Perder gordura",
        "3": "Manter o peso",         "4": "Melhorar condicionamento",
    }
    nivel_map = {
        "1": "Iniciante (menos de 6 meses)",
        "2": "Intermediário (6 meses a 2 anos)",
        "3": "Avançado (mais de 2 anos)",
    }
    horario_map = {
        "1": "Manhã (antes das 9h, fora do pico)",
        "2": "Manhã em horário de pico (6h–9h)",
        "3": "Tarde",
        "4": "Noite em horário de pico (17h–20h)",
        "5": "Noite (após 20h)",
    }

    def _dec(val: str | None, mapa: dict) -> str:
        v = (val or "").strip()
        return mapa.get(v, v) if v else "não informado"

    tipo    = _dec(dados.get("tipo_treino"),      tipo_map)
    local   = _dec(dados.get("local"),            local_map)
    obj     = _dec(dados.get("objetivo"),         obj_map)
    nivel   = _dec(dados.get("nivel"),            nivel_map)
    horario = _dec(dados.get("horario"),          horario_map)
    dias    = dados.get("dias_semana")   or "não informado"
    tempo   = dados.get("tempo_sessao") or "não informado"
    lesoes  = dados.get("lesoes")        or "nenhuma"
    dor     = dados.get("dor_desconforto") or "nenhum"

    nome_str = f" para {primeiro_nome}" if primeiro_nome else ""
    prompt = (
        f"Crie um treino personalizado{nome_str} com os seguintes dados coletados:\n\n"
        f"• Tipo de treino: {tipo}\n"
        f"• Local: {local}\n"
        f"• Objetivo: {obj}\n"
        f"• Dias por semana: {dias}\n"
        f"• Tempo por sessão: {tempo}\n"
        f"• Nível/experiência: {nivel}\n"
        f"• Lesões ou limitações: {lesoes}\n"
        f"• Horário habitual: {horario}\n"
        f"• Dor ou desconforto em exercícios específicos: {dor}\n\n"
        "Gere o treino completo seguindo seu protocolo de criação de treino."
    )

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
            max_tokens=2500,
            system=system_with_cache,
            messages=[{"role": "user", "content": prompt}],
        )
        reply = next((b.text for b in response.content if hasattr(b, "text")), "")
    except anthropic.APIError as e:
        logger.error("gerar_treino_error", extra={"user_id": user.id, "error": str(e)})
        return "Desculpe, tive um problema ao gerar seu treino. Pode tentar novamente em instantes."

    # Salva dados no perfil (valores decodificados)
    perfil = perfil_service.get_or_create_perfil(user.id, db)
    if tipo    != "não informado": perfil.tipo_treino_padrao    = tipo
    if local   != "não informado": perfil.local_treino_padrao   = local
    if obj     != "não informado": perfil.objetivo_padrao       = obj
    if nivel   != "não informado": perfil.nivel_experiencia     = nivel
    if lesoes  != "nenhuma":       perfil.lesoes                = lesoes
    if horario != "não informado": perfil.horario_treino_padrao = horario
    if dias    != "não informado": perfil.dias_semana_padrao    = dias
    if tempo   != "não informado": perfil.tempo_sessao_padrao   = tempo
    db.flush()

    # Persiste o treino gerado
    db.add(Treino(user_id=user.id, conteudo={"texto": reply, "gerado_em": datetime.utcnow().isoformat()}))

    # Limpa estado
    conversa.estado_pendente = None

    return reply


# ---------------------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------------------

def _build_menu_text(user_id: int, db: Session) -> str:
    resumo = habito_service.get_resumo_habitos(user_id, db)
    habito_parts = []

    if resumo["agua_ml"] > 0:
        habito_parts.append(f"💧 Água: {resumo['agua_l']}L")
    if resumo["dias_sem_fumar"]:
        habito_parts.append(f"🚬 Sem fumar: {resumo['dias_sem_fumar']} dias 🔥")
    if resumo["dias_sem_alcool"]:
        habito_parts.append(f"🍺 Sem álcool: {resumo['dias_sem_alcool']} dias 🔥")
    if resumo["suplementos_tomados_hoje"]:
        habito_parts.append("💊 Suplementos: ✅")

    text = MENU_TEXT
    if habito_parts:
        text += "\n\n📊 *Seus hábitos hoje:*\n" + "\n".join(habito_parts)
    return text

async def _handle_menu_item(item: int, user: Usuario, phone: str, db: Session, conversa: Conversa) -> str:
    from app.services import card_service
    from app.services import whatsapp_service as ws

    primeiro_nome = (user.nome or "").split()[0] if user.nome else "você"

    # 💪 TREINO
    if item == 1:  # Criar treino personalizado
        return _iniciar_coleta_treino(user, conversa, db)

    if item == 2:  # Cadastrar treino (do personal)
        return (
            "Me manda o *treino do seu personal* e eu cadastro no sistema! 💪\n\n"
            "Pode ser em qualquer formato: texto, lista de exercícios, planilha copiada...\n\n"
            "Após cadastrar, você registra suas cargas normalmente e acompanha a evolução de 1RM."
        )

    if item == 3:  # Registrar cargas, séries e histórico
        return (
            "Para registrar sua carga, me manda o exercício com séries, repetições e peso. 📝\n\n"
            "Exemplo: *Supino reto 4x8 100kg*\n\n"
            "Posso registrar vários exercícios em sequência!"
        )

    if item == 4:  # Acompanhar evolução de força (1RM)
        return (
            "Qual exercício você quer ver a evolução? 📈\n\n"
            "Me manda o nome do exercício e mostro o histórico de 1RM ao longo do tempo!\n\n"
            "Exemplo: *supino reto*, *agachamento*, *remada curvada*..."
        )

    # 🥗 NUTRIÇÃO
    if item == 5:  # Criar dieta personalizada
        return (
            f"Vamos criar sua dieta personalizada, {primeiro_nome}! 🥗\n\n"
            "Preciso de alguns dados:\n"
            "• *Idade*, *sexo* (H/M), *altura* (cm), *peso* (kg)\n"
            "• *Nível de atividade*: sedentário / leve (1-3x/sem) / moderado (3-5x/sem) / intenso (6-7x/sem)\n"
            "• *Objetivo*: perder gordura / ganhar massa / manter\n"
            "• *Restrições alimentares* ou alergias?\n\n"
            "📏 *Para uma dieta muito mais precisa* (opcional, mas faz diferença real):\n"
            "• Suas *medidas corporais* atuais (cintura, quadril, braço...)\n"
            "• Uma *análise de composição corporal por foto* (opção *9* do menu)\n\n"
            "_Quanto mais eu souber do seu corpo hoje, mais certeiro fica o cálculo de calorias e macros — "
            "não é obrigatório, mas recomendo bastante pra você ter o melhor resultado._ 💪"
        )

    if item == 6:  # Cadastrar dieta (do nutricionista)
        return (
            "Me manda a *dieta da sua nutricionista* e eu cadastro no sistema! 🥗\n\n"
            "Pode ser em qualquer formato: texto, cardápio semanal, metas de macros...\n\n"
            "Após cadastrar, o balanço diário aparecerá nas análises de refeição por foto."
        )

    if item == 7:  # Analisar refeição por foto
        return (
            "Manda uma *foto da sua refeição* e eu analiso as calorias e macros! 📸🍽️\n\n"
            "Funciona com: pratos, marmitas, lanches, bebidas, embalagens...\n\n"
            "_Limite: 6 análises por dia._"
        )

    # 📏 MEDIDAS & CORPO
    if item == 8:  # Registrar peso e medidas
        return (
            "Me manda suas medidas corporais para eu registrar! 📏\n\n"
            "Formato (manda só as que tiver):\n"
            "*Peso:* 80kg\n"
            "*Cintura:* 85cm\n"
            "*Quadril:* 95cm\n"
            "*Braço:* 35cm"
        )

    if item == 9:  # Análise de composição corporal (por foto)
        return (
            f"Vou analisar sua composição corporal, {primeiro_nome}! 📸\n\n"
            "Preciso de *3 fotos* suas:\n"
            "1. *Frente* — de frente para a câmera\n"
            "2. *Costas* — de costas para a câmera\n"
            "3. *Lado* — perfil, braço relaxado ao lado do corpo\n\n"
            "Pode mandar a primeira foto de *frente* agora!"
        )

    if item == 10:  # Ver meu painel geral de evolução
        evolucao = exercicio_service.get_evolucao_sessao(user.id, db)
        stats = card_service.get_last_session_stats(user.id, db)
        try:
            png_bytes = card_service.gerar_card_evolucao(user.nome, evolucao, stats)
            if phone:
                await ws.send_image(phone, png_bytes)
            return (
                f"Aqui está seu *painel de evolução*, {primeiro_nome}! 📊\n\n"
                f"Sessões registradas: *{stats['sessoes']}*\n"
                f"Última sessão: *{stats['exercicios']} exercícios* ({stats['duracao']})"
            )
        except Exception as e:
            logger.error("card_generation_error", extra={"user_id": user.id, "error": str(e)})
            return "Ops, tive um problema ao gerar seu painel. Tente novamente em instantes."

    # 💧 HÁBITOS DIÁRIOS
    if item == 11:  # Registrar água e suplementos
        return (
            f"Bora registrar seus hábitos de hoje, {primeiro_nome}! 💧💊\n\n"
            "💧 *Água*: me diz quanto bebeu (ex: *bebi 500ml*, *tomei 2 copos*, *1 litro*)\n\n"
            "💊 *Suplementos*: me diz que tomou (ex: *tomei a creatina*, *tomei tudo*)\n\n"
            "_Se ainda não cadastrou seus suplementos, me manda a lista (ex: \"tomo creatina, whey e vitamina D\")._"
        )

    if item == 12:  # Acompanhar hábitos (dias sem álcool / sem fumar)
        return (
            f"Vamos acompanhar seus hábitos, {primeiro_nome}! 🔥\n\n"
            "🚬 *Dias sem fumar*: me avisa quando passar o dia (ex: *não fumei hoje*, *mais um dia sem cigarro*)\n\n"
            "🍺 *Dias sem beber*: me avisa também (ex: *não bebi hoje*, *mais um dia sem álcool*)\n\n"
            "Eu vou contando seus dias e comemoro junto com você os marcos importantes! 💪"
        )

    return "Opção inválida. Digite */menu* para ver as opções disponíveis."


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

async def process_message(
    user: Usuario,
    message_text: str,
    db: Session,
    image_b64: str | None = None,
    image_mimetype: str = "image/jpeg",
    phone: str = "",
) -> str:
    conversa = _get_or_create_conversa(user.id, db)
    sessao_data = date.today()

    # 0. /menu command and menu item selection (intercept before everything else)
    stripped = message_text.strip()
    if stripped.lower() in ("/menu", "#menu"):
        conversa.estado_pendente = {"tipo": "aguardando_menu"}
        db.add(conversa)
        db.commit()
        return _build_menu_text(user.id, db)

    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "aguardando_menu":
        if stripped.isdigit() and 1 <= int(stripped) <= 12:
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
            return await _handle_menu_item(int(stripped), user, phone, db, conversa)
        else:
            conversa.estado_pendente = None

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

    # 3. Coleta estruturada de treino — intercepta antes do fluxo geral
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "criando_treino":
        reply = await _handle_coleta_treino(conversa, message_text, user, db)
        mensagens.append({"role": "user", "content": stored_text, "timestamp": datetime.utcnow().isoformat()})
        mensagens.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens
        db.add(conversa)
        db.commit()
        return reply

    # 4. Trata confirmações pendentes (exercício e refeição)
    ctx_confirmacao = (
        _handle_confirmacao(conversa, message_text, user, sessao_data, db)
        or _handle_confirmacao_refeicao(conversa, message_text, user, db)
    )

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
    ctx_habitos = habito_service.build_habito_context(user.id, db)

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

    partes_ctx = [p for p in [ctx_sessao, ctx_nutricao, ctx_habitos, ctx_confirmacao, ctx_coleta] if p]
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
        coleta_iniciada_msg: str | None = None
        while response.stop_reason == "tool_use" and tool_iterations < 5:
            tool_iterations += 1
            tool_results = []
            coleta_iniciada_msg = None

            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == "registrar_exercicio":
                    result = _process_tool_registrar(block.input, user, sessao_data, conversa, db)
                elif block.name == "registrar_medidas":
                    result = _process_tool_medidas(block.input, user, db)
                elif block.name == "registrar_analise_foto":
                    result = _process_tool_foto(block.input, user, db)
                elif block.name == "analisar_refeicao":
                    result = _process_tool_refeicao(block.input, conversa, user, db)
                elif block.name == "cadastrar_dieta_propria":
                    result = _process_tool_cadastrar_dieta(block.input, user, db)
                elif block.name == "cadastrar_treino_proprio":
                    result = _process_tool_cadastrar_treino(block.input, user, db)
                elif block.name == "iniciar_coleta_fotos_corpo":
                    if image_b64:
                        primeiro_nome = _process_tool_iniciar_coleta(
                            image_b64, image_mimetype, conversa, user
                        )
                        coleta_iniciada_msg = (
                            f"Recebi a foto de frente, {primeiro_nome}! 💪\n\n"
                            "Para análise de composição corporal preciso de mais 2 ângulos:\n\n"
                            "👉 Manda agora a foto de *costas* (vire de costas para a câmera).\n\n"
                            "_Diga 'cancelar' a qualquer momento para cancelar._"
                        )
                        result = "COLETA_INICIADA"
                    else:
                        result = "Nenhuma imagem recebida para iniciar a coleta."
                elif block.name == "registrar_agua":
                    result = _process_tool_agua(block.input, user, db)
                elif block.name == "registrar_habito_fumar":
                    result = _process_tool_habito_fumar(block.input, user, db)
                elif block.name == "registrar_habito_alcool":
                    result = _process_tool_habito_alcool(block.input, user, db)
                elif block.name == "registrar_tomei_suplementos":
                    result = _process_tool_tomei_suplementos(user, db)
                elif block.name == "registrar_suplementos_usuario":
                    result = _process_tool_suplementos_usuario(block.input, user, db)
                else:
                    result = "Ferramenta desconhecida."
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            # Se a coleta foi iniciada, usa a mensagem pré-formatada sem chamar Claude novamente
            if coleta_iniciada_msg:
                reply = coleta_iniciada_msg
                break

            history.append({"role": "assistant", "content": response.content})
            history.append({"role": "user", "content": tool_results})

            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1500,
                system=system_with_cache,
                messages=history,
                tools=TOOLS,
            )

        if not coleta_iniciada_msg:
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
