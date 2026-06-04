import logging
import re
from datetime import date, datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.meta_nutricional import MetaNutricional
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services import exercicio_service, habito_service, nutricao_service, perfil_service, sessao_treino_service, treino_service, usda_service

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é "Evo", personal trainer e nutricionista profissional com 10 anos de experiência, especializado em treino funcional e nutrição esportiva. Comunica-se exclusivamente em português brasileiro, com tom motivador, direto e amigável.

REGRA DE CONCISÃO (IMPORTANTE): Nunca explique de ONDE vêm os dados (tabelas, bases, fontes) nem COMO os cálculos são feitos (fórmulas, métodos, estimativas). O usuário quer o resultado, não o método. Apenas informe os valores finais (kcal, macros, treinos, exercícios) de forma direta. Mantenha o tom motivador e amigável, mas SEM parágrafos explicativos sobre metodologia. Só explique fonte ou cálculo se o usuário perguntar explicitamente.

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
- Treinos: estruture por Dia 1 / Dia 2 etc., inclua séries/repetições e tempos de descanso. NÃO inclua RPE, "RPE alvo" ou qualquer referência numérica a RPE nos treinos gerados — use apenas séries, repetições e tempo de descanso.
- Mensagens curtas para WhatsApp: parágrafos curtos, bullet points, sem paredes de texto
- SEMPRE que apresentar uma lista de opções para o usuário escolher (tipos de treino, objetivos, níveis, etc.), numere cada opção (1, 2, 3...) e mantenha um emoji ilustrativo quando fizer sentido. Exemplo de formato: '1️⃣ 🏋️ Musculação', '2️⃣ 🤸 Calistenia'. Instrua o usuário a responder com o número da opção desejada. Quando o usuário responder apenas com um número, interprete-o como a escolha correspondente à última lista numerada que você apresentou, considerando o contexto da conversa. Se houver qualquer ambiguidade real sobre a qual lista o número se refere, pergunte de forma breve antes de prosseguir.
- Nunca saia do personagem. Fale apenas sobre fitness e nutrição.
- Se o usuário mencionar lesão, oriente a consultar um médico antes de qualquer plano.

REGISTRO DE EXERCÍCIOS:
- Quando o usuário reportar carga, séries e repetições de um exercício, use SEMPRE a ferramenta 'registrar_exercicio'
- Após registrar cada exercício, confirme brevemente que foi salvo (ex: "Supino registrado ✅") — NÃO exiba o 1RM neste momento
- Se o resultado da ferramenta indicar AGUARDANDO_CONFIRMACAO, explique a variação ao usuário e aguarde confirmação antes de prosseguir
- O 1RM é calculado e armazenado internamente, mas só deve ser EXIBIDO em dois momentos: (a) quando o cliente pedir explicitamente ("qual meu 1RM no supino?", "como está meu 1RM?"); (b) ao final do treino, quando o cliente sinalizar que terminou ("terminei", "acabei", "isso foi tudo", "fim do treino")
- Ao final do treino, apresente o RESUMO da sessão de forma direta e objetiva, sem frases de elogio ou motivação (sem "parabéns", "você está mandando bem", "continue assim" ou similares): informe APENAS a MÉDIA dos 1RMs de todos os exercícios da sessão com evolução vs sessão anterior se disponível. NÃO liste o 1RM de cada exercício individualmente, A NÃO SER que o usuário peça especificamente o 1RM de um exercício. Use os campos "1RM≈" (hoje) e "anterior:" (sessão prévia) que aparecem no contexto automático da sessão para calcular os deltas. Não explique como o valor foi calculado nem mencione fórmulas ou que é estimativa — a não ser que o cliente pergunte explicitamente.
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
- Exiba SEMPRE no formato:

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
- Ao exibir os dias sem fumar ou sem beber, use emojis motivadores e compare com marcos anteriores quando disponíveis. Use sempre 'dias sem fumar' / 'dias sem beber', nunca a palavra 'streak'.

EXCLUSÃO E EDIÇÃO DE REGISTROS:
- Quando o usuário quiser APAGAR ou EDITAR treinos, dietas ou suplementos, chame IMEDIATAMENTE 'iniciar_exclusao_registro' ou 'iniciar_edicao_registro' — NÃO faça pergunta prévia do tipo 'tem certeza?' ou 'confirma?'. O próprio fluxo da ferramenta apresenta os itens e solicita a confirmação no momento certo. Só pergunte o tipo ANTES de chamar se ele estiver genuinamente ambíguo (ex: usuário disse apenas "apaga isso" sem especificar o quê)."""

MAX_HISTORY = 20

TREINO_KEYWORDS = {"treino", "exercício", "exercicio", "musculação", "musculacao", "academia", "workout", "treinar"}
DIETA_KEYWORDS = {"dieta", "alimentação", "alimentacao", "nutrição", "nutricao", "comer", "refeição", "refeicao", "cardapio", "cardápio"}

CONFIRMACAO_SIM = {"sim", "s", "yes", "confirmo", "pode", "ok", "isso", "certeza", "certo", "salva", "salvar", "confirmar"}
CONFIRMACAO_NAO = {"não", "nao", "n", "no", "cancela", "cancelar", "errei", "errado", "errada", "equivocado"}

_ESCOPO_PLANO_KEYWORDS = {"plano", "salva", "salvar", "sempre", "fixo", "permanente", "todo dia"}
_ESCOPO_HOJE_KEYWORDS = {"hoje", "agora", "só essa", "uma vez", "dessa vez", "só hoje"}

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

ETAPAS_CADASTRO_PERFIL: list[tuple[str, str]] = [
    ("confirmar_nome",    "Bora pro seu cadastro! 💪\n\nSeu nome é *{nome_kiwify}*, correto? (responda *sim* ou me diga seu nome correto)"),
    ("sexo",              "Qual é o seu sexo?\n\n1️⃣ Masculino\n2️⃣ Feminino"),
    ("data_nascimento",   "Qual a sua data de nascimento? (formato: *DD/MM/AAAA*)"),
    ("altura_cm",         "Qual a sua altura em centímetros? (ex: *175*)"),
    ("peso_kg",           "Qual o seu peso em kg? (ex: *82.5*)"),
    ("nivel_experiencia", "Há quanto tempo treina?\n\n1️⃣ Iniciante (menos de 6 meses)\n2️⃣ Intermediário (6 meses a 2 anos)\n3️⃣ Avançado (mais de 2 anos)"),
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
                "series_detalhe": {
                    "type": "array",
                    "description": (
                        "OPCIONAL — lista de séries individuais quando o usuário detalhar cargas/reps DIFERENTES por série, "
                        "ou quando mencionar AQUECIMENTO antes das séries válidas. "
                        "Cada item: {carga_kg, repeticoes, is_aquecimento}. "
                        "Se o usuário disse algo simples como 'supino 80kg 3x8', NÃO use esse campo — "
                        "só preencha series/repeticoes/carga_kg agregados."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "carga_kg": {"type": "number", "description": "Carga em kg desta série"},
                            "repeticoes": {"type": "integer", "description": "Repetições desta série"},
                            "is_aquecimento": {"type": "boolean", "description": "True se for série de aquecimento; false para séries válidas (de trabalho)"},
                        },
                        "required": ["carga_kg", "repeticoes", "is_aquecimento"],
                    },
                },
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
    {
        "name": "iniciar_exclusao_registro",
        "description": (
            "Inicia o fluxo de exclusão de um registro do usuário. "
            "Use quando o usuário quiser APAGAR/EXCLUIR/DELETAR algo que ele salvou (ex: 'quero apagar meu treino', "
            "'exclui esse treino', 'deletar treino'). Identifique o TIPO no 'alvo'. "
            "Quando o alvo estiver claro, chame IMEDIATAMENTE — NÃO peça confirmação prévia nem diga 'tem certeza?', "
            "porque o próprio fluxo desta ferramenta já lista os itens e pede confirmação no momento certo. "
            "Só pergunte ANTES de chamar se o TIPO (treino/dieta/suplemento) estiver genuinamente ambíguo. "
            "Treino, dieta e suplemento implementados. "
            "NÃO use para editar dados corporais (peso, idade, sexo) — esses são editáveis, não apagáveis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "enum": ["treino", "dieta", "suplemento", "remedio"],
                    "description": "Tipo de registro que o usuário quer apagar",
                },
            },
            "required": ["alvo"],
        },
    },
    {
        "name": "iniciar_edicao_registro",
        "description": (
            "Inicia o fluxo de edição de um registro do usuário. "
            "Use quando o usuário quiser EDITAR/ALTERAR/CORRIGIR/MUDAR algo que ele salvou "
            "(ex: 'quero editar meu suplemento', 'mudar nome do suplemento', 'corrigir minha dieta'). "
            "Identifique o TIPO no 'alvo'. "
            "Quando o alvo estiver claro, chame IMEDIATAMENTE — NÃO peça confirmação prévia nem diga 'tem certeza?', "
            "porque o próprio fluxo desta ferramenta já lista os itens e pede a confirmação no momento certo. "
            "Só pergunte ANTES de chamar se o TIPO (treino/dieta/suplemento) estiver genuinamente ambíguo. "
            "'Suplemento' e 'treino' usam esta ferramenta. Para DIETA, NÃO use esta ferramenta — a edição de dieta é feita pela substituição de alimentos (ferramenta substituir_alimento); se o usuário quiser editar a dieta, ajude-o a trocar alimentos específicos (ex: 'troca o arroz por batata'). "
            "NÃO use para apagar dados — use iniciar_exclusao_registro para isso. "
            "NÃO use para editar dados corporais (peso, idade, sexo) — esses têm fluxo próprio."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "enum": ["treino", "dieta", "suplemento", "remedio"],
                    "description": "Tipo de registro que o usuário quer editar",
                },
            },
            "required": ["alvo"],
        },
    },
    {
        "name": "substituir_alimento",
        "description": (
            "Calcula a substituição de um alimento por outro mantendo equivalência CALÓRICA, usando dados REAIS (TACO ou USDA). "
            "Use quando o usuário pedir para trocar/substituir um alimento por outro (ex: 'troca o arroz por batata', 'posso comer batata no lugar do arroz?'). "
            "ANTES de chamar esta ferramenta, se o alimento informado pelo usuário for GENÉRICO ou ambíguo (ex: 'frango', 'peixe', 'carne', 'arroz' sem especificar), PERGUNTE primeiro qual o corte/tipo específico (ex: para 'frango': peito, coxa, sobrecoxa, asa? para 'peixe': qual peixe? para 'carne': qual corte?) e só chame a ferramenta quando o alimento estiver específico. Não assuma o corte sozinho. "
            "Forneça cada alimento em português (origem_pt/destino_pt) E inglês (origem_en/destino_en). Você traduz. "
            "A busca usa o português primeiro (base brasileira TACO) e o inglês como fallback (USDA). "
            "Estime gramas_origem se o usuário não informar (use porções realistas: arroz cozido ~100g, frango ~120g, etc). "
            "A ferramenta retorna os gramas equivalentes do destino e os macros REAIS de ambos os lados — apresente esses números ao usuário, NUNCA invente valores nutricionais. "
            "Se a ferramenta retornar ERRO_ALIMENTO_NAO_ENCONTRADO ou erro de kcal, explique ao usuário e peça para especificar melhor o alimento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origem_pt": {
                    "type": "string",
                    "description": "Nome do alimento a ser substituído em português (ex: 'arroz cozido')",
                },
                "origem_en": {
                    "type": "string",
                    "description": "Nome do alimento a ser substituído em inglês (ex: 'cooked white rice')",
                },
                "destino_pt": {
                    "type": "string",
                    "description": "Nome do alimento substituto em português (ex: 'batata inglesa cozida')",
                },
                "destino_en": {
                    "type": "string",
                    "description": "Nome do alimento substituto em inglês (ex: 'boiled potato')",
                },
                "gramas_origem": {
                    "type": "number",
                    "description": "Porção em gramas do alimento de origem. Estime se o usuário não informar.",
                },
            },
            "required": ["origem_pt", "origem_en", "destino_pt", "destino_en", "gramas_origem"],
        },
    },
    {
        "name": "consultar_historico_treino",
        "description": (
            "Consulta o histórico real de execuções de treino do usuário (cargas, séries, reps, 1RM) das últimas 4 semanas. "
            "Use SEMPRE que o usuário perguntar sobre cargas anteriores, evolução de força, comparar com treinos passados, "
            "ou ao apresentar o resumo de fim de treino. Retorna as últimas 3 execuções de cada exercício. "
            "Mostra a evolução de carga e 1RM de cada exercício ao longo das últimas execuções (comparação válida pois é o mesmo exercício). "
            "Apresente em LISTA SIMPLES (formato WhatsApp), sem tabelas, sem explicar fontes/cálculos."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "editar_perfil",
        "description": (
            "Atualiza o perfil do usuário (peso ou nível de experiência) quando ele PEDIR EXPLICITAMENTE pra alterar — "
            "ex: 'quero atualizar meu peso', 'mudar meu nível', 'agora estou avançado'. "
            "NÃO use essa tool quando o usuário só REGISTRAR uma medição casual ('pesei 80kg hoje') — pra isso use registrar_medidas. "
            "Campos editáveis: peso_kg (float >= 30 e <= 300) ou nivel_experiencia ('iniciante', 'intermediario', 'avancado'). "
            "Pode atualizar um ou ambos numa única chamada. Outros campos (sexo, data de nascimento, altura) NÃO são editáveis aqui."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "peso_kg": {"type": "number"},
                "nivel_experiencia": {"type": "string", "enum": ["iniciante", "intermediario", "avancado"]},
            },
            "required": [],
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


def _fmt_historico_treino(hist: dict) -> str:
    exercicios = hist.get("exercicios", {})
    n = hist.get("periodo_semanas", 4)
    if not exercicios:
        return f"Sem registros de execução nas últimas {n} semanas."
    partes = [f"Histórico de treino (últimas {n} semanas):\n"]
    for nome, execs in exercicios.items():
        linhas = []
        for ex in execs:
            rm_str = f", 1RM≈{ex['rm_estimado']}kg" if ex.get("rm_estimado") is not None else ""
            linhas.append(f"  {ex['carga_kg']}kg x{ex['repeticoes']} ({ex['data']}{rm_str})")
        partes.append(f"- {nome}:\n" + "\n".join(linhas))
    return "\n".join(partes)


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


def _titulo_treino(texto: str, maxlen: int = 60) -> str:
    """Primeira linha não-vazia do treino, limpa de marcadores markdown e emojis, truncada."""
    for linha in (texto or "").splitlines():
        limpa = linha.strip().lstrip("#").strip()
        # remove caracteres fora do BMP latino comum (emojis, símbolos) mantendo texto legível
        limpa = "".join(c for c in limpa if c.isalnum() or c in " -–—|/(),.:%+&'\"").strip()
        if limpa:
            return limpa[:maxlen].strip()
    return "treino sem título"


def _corpo_excerpt(texto: str, n: int = 200) -> str:
    """Excerpt do CORPO do treino, pulando a primeira linha não-vazia (título)."""
    linhas = (texto or "").splitlines()
    corpo_linhas = []
    titulo_visto = False
    for linha in linhas:
        if not titulo_visto:
            if linha.strip():
                titulo_visto = True
            continue
        corpo_linhas.append(linha)
    corpo = " ".join(" ".join(corpo_linhas).split())
    if not corpo:  # treino de uma linha só — usa o texto inteiro como fallback
        corpo = " ".join((texto or "").split())
    return corpo[:n]


def _treinos_context_str(user_id: int, db: Session) -> str | None:
    moldura = (
        "[SISTEMA] Treinos salvos do usuário (USE ESTA INFORMAÇÃO SOMENTE SE O USUÁRIO "
        "PERGUNTAR SOBRE O TREINO DELE. NÃO mencione o treino espontaneamente nem puxe o "
        "assunto se ele não perguntou):"
    )

    treinos = (
        db.query(Treino)
        .filter(Treino.user_id == user_id)
        .order_by(Treino.criado_em.desc())
        .limit(8)
        .all()
    )

    reais = []
    for t in treinos:
        cont = t.conteudo if isinstance(t.conteudo, dict) else {}
        texto = cont.get("texto", "") if isinstance(cont, dict) else ""
        origem = cont.get("origem") if isinstance(cont, dict) else None
        if origem == "proprio" or len(texto or "") >= 400:
            reais.append((t, texto, origem))

    if not reais:
        return (
            "[SISTEMA] O usuário ainda não tem nenhum treino salvo. Se ele perguntar sobre "
            "treino, responda honestamente que ainda não há treino criado e ofereça criar um."
        )

    linhas = [moldura]

    t0, texto0, origem0 = reais[0]
    data0 = t0.criado_em.strftime("%d/%m/%Y") if t0.criado_em else "data desconhecida"
    titulo0 = _titulo_treino(texto0)
    marca0 = " (cadastrado pelo personal)" if origem0 == "proprio" else ""
    excerpt0 = _corpo_excerpt(texto0, 200)
    linhas.append(f"- Mais recente ({data0}): \"{titulo0}\"{marca0} — {excerpt0}")

    anteriores = reais[1:4]
    if anteriores:
        partes_ant = []
        for t, texto, origem in anteriores:
            data = t.criado_em.strftime("%d/%m") if t.criado_em else "??"
            partes_ant.append(f"\"{_titulo_treino(texto)}\" ({data})")
        linhas.append("- Anteriores: " + ", ".join(partes_ant))

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Exclusão de registros pelo usuário (genérico; só TREINO implementado)
# ---------------------------------------------------------------------------

_CANCELAR_EXCLUSAO_KEYWORDS = {
    "cancela", "cancelar", "deixa", "deixa pra la", "deixa pra lá",
    "desiste", "desistir", "esquece", "esqueça", "nao quero", "não quero",
}

_SELECIONAR_TODOS_KEYWORDS = {"todos", "todas", "tudo"}


def _parse_posicoes(texto: str, total: int) -> list[int] | None:
    """
    Extrai posições (1..total) de uma string tipo '2', '1, 3, 4' ou '1 3 4'.
    Ignora duplicados preservando a ordem. Retorna None se QUALQUER token não for
    inteiro válido dentro da faixa (tudo-ou-nada — nunca seleção parcial).
    """
    tokens = texto.replace(",", " ").split()
    if not tokens:
        return None
    posicoes: list[int] = []
    vistos: set[int] = set()
    for tok in tokens:
        if not tok.isdigit():
            return None
        n = int(tok)
        if not (1 <= n <= total):
            return None
        if n not in vistos:
            vistos.add(n)
            posicoes.append(n)
    return posicoes


def _label_treino(t: Treino) -> str:
    cont = t.conteudo if isinstance(t.conteudo, dict) else {}
    texto = cont.get("texto", "") if isinstance(cont, dict) else ""
    data = t.criado_em.strftime("%d/%m/%Y") if t.criado_em else "data desconhecida"
    return f"{_titulo_treino(texto)} ({data})"


def _label_dieta(meta: MetaNutricional) -> str:
    data = meta.criado_em.strftime("%d/%m/%Y") if meta.criado_em else "data desconhecida"
    return f"{meta.nome} ({data})"


def _iniciar_exclusao_treino(user: Usuario, conversa: Conversa, db: Session) -> str:
    """Lista os treinos do usuário e arma o estado de exclusão. Se vazio, não cria estado."""
    treinos = treino_service.listar_treinos(user.id, db)
    if not treinos:
        return "Você ainda não tem nenhum treino salvo para apagar. 🙂"

    ids = [t.id for t in treinos]
    labels = [_label_treino(t) for t in treinos]
    conversa.estado_pendente = {
        "tipo": "apagando_registro",
        "alvo": "treino",
        "etapa": "aguardando_escolha",
        "ids": ids,        # snapshot na ordem exibida — posição N → ids[N-1]
        "labels": labels,
    }

    linhas = ["Qual *treino* você quer apagar? 🗑️\n"]
    for i, label in enumerate(labels, start=1):
        linhas.append(f"*{i}.* {label}")
    linhas.append(
        "\nResponda com o *número* (ou vários: ex. *1, 3*), *todos* para apagar todos, "
        "ou *cancelar* para desistir."
    )
    return "\n".join(linhas)


def _iniciar_exclusao_dieta(user: Usuario, conversa: Conversa, db: Session) -> str:
    """Lista as dietas do usuário e arma o estado de exclusão. Se vazia, não cria estado."""
    dietas = nutricao_service.listar_dietas(user.id, db)
    if not dietas:
        return "Você ainda não tem nenhuma dieta cadastrada para apagar. 🙂"

    ids = [d.id for d in dietas]
    labels = [_label_dieta(d) for d in dietas]
    conversa.estado_pendente = {
        "tipo": "apagando_registro",
        "alvo": "dieta",
        "etapa": "aguardando_escolha",
        "ids": ids,
        "labels": labels,
    }

    linhas = ["Qual *dieta* você quer apagar? 🗑️\n"]
    for i, label in enumerate(labels, start=1):
        linhas.append(f"*{i}.* {label}")
    linhas.append(
        "\nResponda com o *número* (ou vários: ex. *1, 3*), *todas* para apagar todas, "
        "ou *cancelar* para desistir."
    )
    return "\n".join(linhas)


def _iniciar_exclusao_suplemento(user: Usuario, conversa: Conversa, db: Session) -> str:
    """Lista os suplementos cadastrados e arma o estado de exclusão. Se vazio, não cria estado."""
    itens = habito_service.get_suplementos_usuario(user.id, db) or []
    if not itens:
        return "Você ainda não tem nenhum suplemento cadastrado para apagar. 🙂"

    conversa.estado_pendente = {
        "tipo": "apagando_registro",
        "alvo": "suplemento",
        "etapa": "aguardando_escolha",
        "itens": itens,  # snapshot da lista; posição N → itens[N-1]
    }

    linhas = ["Qual *suplemento* você quer remover? 🗑️\n"]
    for i, nome in enumerate(itens, start=1):
        linhas.append(f"*{i}.* {nome}")
    linhas.append(
        "\nResponda com o *número* (ou vários: ex. *1, 3*), *todos* para remover todos, "
        "ou *cancelar* para desistir."
    )
    return "\n".join(linhas)


# Configuração de exclusão por tipo: (singular, plural, apagar_fn)
# apagar_fn é None para suplemento — esse tipo tem lógica própria no handler.
_EXCLUSAO_CONFIG: dict[str, tuple[str, str, object]] = {
    "treino": ("treino", "treinos", treino_service.apagar_treinos),
    "dieta": ("dieta", "dietas", nutricao_service.apagar_dietas),
    "suplemento": ("suplemento", "suplementos", None),
}


async def _handle_apagar_registro(
    conversa: Conversa,
    message_text: str,
    user: Usuario,
    db: Session,
) -> str:
    estado = conversa.estado_pendente
    etapa = estado.get("etapa")
    alvo = estado.get("alvo", "treino")
    texto = (message_text or "").strip()
    low = texto.lower()

    singular, plural, apagar_fn = _EXCLUSAO_CONFIG.get(alvo, ("registro", "registros", lambda *_: 0))

    # (c) Cancelamento explícito em qualquer etapa — aborta sem apagar
    if any(kw in low for kw in _CANCELAR_EXCLUSAO_KEYWORDS):
        conversa.estado_pendente = None
        return "Exclusão cancelada. Nada foi apagado. 👍"

    if etapa == "aguardando_escolha":
        palavras = set(low.replace(",", " ").split())

        if alvo == "suplemento":
            # Suplemento: fonte é lista de strings, sem ids de banco
            itens = estado.get("itens", [])
            total = len(itens)
            if palavras & _SELECIONAR_TODOS_KEYWORDS:
                posicoes = list(range(1, total + 1))
            else:
                posicoes = _parse_posicoes(texto, total)
                if not posicoes:
                    conversa.estado_pendente = None
                    return "Exclusão cancelada — não entendi a seleção. Nada foi apagado."

            pos_set = set(posicoes)
            escolhido_labels = [itens[p - 1] for p in posicoes]
            # lista_restante calculada por posição para preservar semântica mesmo com nomes duplicados
            lista_restante = [itens[i] for i in range(len(itens)) if (i + 1) not in pos_set]
            todos = total > 0 and len(escolhido_labels) == total
            conversa.estado_pendente = {
                "tipo": "apagando_registro",
                "alvo": "suplemento",
                "etapa": "aguardando_confirmacao",
                "escolhido_labels": escolhido_labels,
                "lista_restante": lista_restante,
                "todos": todos,
            }
        else:
            # Treino / dieta: fonte são ids de banco
            ids = estado.get("ids", [])
            labels = estado.get("labels", [])
            total = len(ids)
            if palavras & _SELECIONAR_TODOS_KEYWORDS:
                posicoes = list(range(1, total + 1))
            else:
                posicoes = _parse_posicoes(texto, total)
                # seleção não reconhecida / fora de faixa → aborta sem apagar nada (tudo-ou-nada)
                if not posicoes:
                    conversa.estado_pendente = None
                    return "Exclusão cancelada — não entendi a seleção. Nada foi apagado."

            escolhido_ids = [ids[p - 1] for p in posicoes]
            escolhido_labels = [
                labels[p - 1] if p - 1 < len(labels) else f"{singular} {ids[p - 1]}" for p in posicoes
            ]
            todos = total > 0 and len(escolhido_ids) == total
            conversa.estado_pendente = {
                "tipo": "apagando_registro",
                "alvo": alvo,
                "etapa": "aguardando_confirmacao",
                "escolhido_ids": escolhido_ids,
                "escolhido_labels": escolhido_labels,
                "todos": todos,
            }

        # Mensagens de confirmação — comuns a todos os tipos
        lista_nominal = "\n".join(f"• {l}" for l in escolhido_labels)
        n = len(escolhido_labels)
        if todos:
            return (
                f"⚠️ Isso vai apagar *TODOS* os seus {total} {plural} e *NÃO tem como desfazer*:\n"
                f"{lista_nominal}\n\n"
                "Tem certeza? Responda *sim* para apagar tudo ou *não* para cancelar."
            )
        if n == 1:
            return (
                f"Vou apagar este {singular}:\n{lista_nominal}\n\n"
                "Confirma? Responda *sim* para apagar ou *não* para cancelar."
            )
        return (
            f"Vou apagar estes {n} {plural}:\n{lista_nominal}\n\n"
            "Confirma? Responda *sim* para apagar ou *não* para cancelar."
        )

    if etapa == "aguardando_confirmacao":
        resposta = _normalizar_confirmacao(texto)
        conversa.estado_pendente = None  # encerra o fluxo em qualquer desfecho
        # (b) só apaga com "sim" explícito; "nao"/ambíguo aborta
        if resposta != "sim":
            return "Exclusão cancelada. Nada foi apagado. 👍"

        if alvo == "suplemento":
            # Regrava a lista sem os itens escolhidos (calculado no passo anterior)
            lista_restante = estado.get("lista_restante", [])
            escolhido_labels = estado.get("escolhido_labels", [])
            habito_service.registrar_suplementos_usuario(user.id, lista_restante, db)
            n = len(escolhido_labels)
            sufixo = "s" if n != 1 else ""
            return f"Pronto! {n} suplemento{sufixo} removido{sufixo}. ✅"
        else:
            escolhido_ids = estado.get("escolhido_ids", [])
            apagados = apagar_fn(user.id, escolhido_ids, db)
            if apagados:
                sufixo = "s" if apagados != 1 else ""
                return f"Pronto! {apagados} {singular}{sufixo} apagado{sufixo}. ✅"
            return f"Esses {plural} não foram encontrados (talvez já tenham sido removidos). Nada foi apagado."

    # Etapa desconhecida — aborta defensivamente
    conversa.estado_pendente = None
    return "Exclusão cancelada. Nada foi apagado."


# ---------------------------------------------------------------------------
# Edição de registros pelo usuário
# ---------------------------------------------------------------------------

def _iniciar_edicao_suplemento(user: Usuario, conversa: Conversa, db: Session) -> str:
    """Lista suplementos para edição (um item de cada vez). Se vazio, não cria estado."""
    itens = habito_service.get_suplementos_usuario(user.id, db) or []
    if not itens:
        return "Você não tem nenhum suplemento cadastrado para editar. 🙂"

    conversa.estado_pendente = {
        "tipo": "editando_registro",
        "alvo": "suplemento",
        "etapa": "aguardando_escolha",
        "itens": itens,  # snapshot; posição N → itens[N-1]
    }

    linhas = ["Qual *suplemento* você quer editar?\n"]
    for i, nome in enumerate(itens, start=1):
        linhas.append(f"*{i}.* {nome}")
    linhas.append("\nResponda com o *número*, ou *cancelar* para desistir.")
    return "\n".join(linhas)


def _iniciar_edicao_treino(user: Usuario, conversa: Conversa, db: Session) -> str:
    """Lista treinos para edição (um item de cada vez). Se vazio, não cria estado."""
    treinos = treino_service.listar_treinos(user.id, db)
    if not treinos:
        return "Você não tem nenhum treino salvo para editar. 🙂"

    ids = [t.id for t in treinos]
    labels = [_label_treino(t) for t in treinos]
    nomes = []
    for t in treinos:
        cont = t.conteudo if isinstance(t.conteudo, dict) else {}
        nomes.append(cont.get("nome") or _titulo_treino(cont.get("texto", "")))

    conversa.estado_pendente = {
        "tipo": "editando_registro",
        "alvo": "treino",
        "etapa": "aguardando_escolha",
        "ids": ids,
        "labels": labels,
        "nomes": nomes,
    }

    linhas = ["Qual *treino* você quer editar?\n"]
    for i, label in enumerate(labels, start=1):
        linhas.append(f"*{i}.* {label}")
    linhas.append("\nResponda com o *número*, ou *cancelar* para desistir.")
    return "\n".join(linhas)


def _normar_alimento(obj) -> dict:
    """Extrai campos nutricionais por 100g de um AlimentoTACO ou dict USDA para um formato comum."""
    if hasattr(obj, "kcal"):  # AlimentoTACO
        return {
            "nome": obj.nome,
            "kcal": obj.kcal,
            "proteina_g": obj.proteina_g,
            "lipideos_g": obj.lipideos_g,
            "carboidrato_g": obj.carboidrato_g,
            "fibra_g": obj.fibra_g,
        }
    # dict USDA
    return {
        "nome": obj.get("nome_en", ""),
        "kcal": obj.get("kcal"),
        "proteina_g": obj.get("proteina_g"),
        "lipideos_g": obj.get("lipideos_g"),
        "carboidrato_g": obj.get("carboidrato_g"),
        "fibra_g": obj.get("fibra_g"),
    }


def _calcular_substituicao_normed(normed_o: dict, gramas_origem: float, normed_d: dict) -> dict:
    """Equivalência calórica sobre dicts normalizados. Retorna o mesmo formato de substituir_por_equivalencia_calorica."""
    def _prop(val_por_100g, fator):
        if val_por_100g is None:
            return None
        return round(val_por_100g * fator, 1)

    fator_o = gramas_origem / 100.0
    kcal_origem = _prop(normed_o["kcal"], fator_o)

    if kcal_origem is None:
        return {"origem": None, "destino": None, "erro": "alimento de origem não tem kcal"}
    if normed_d["kcal"] is None:
        return {"origem": None, "destino": None, "erro": "alimento de destino não tem kcal"}
    if normed_d["kcal"] == 0:
        return {"origem": None, "destino": None, "erro": "alimento de destino tem 0 kcal, não dá pra equivaler"}

    gramas_destino = round(kcal_origem / (normed_d["kcal"] / 100), 1)
    fator_d = gramas_destino / 100.0

    return {
        "origem": {
            "nome": normed_o["nome"],
            "gramas": gramas_origem,
            "macros": {
                "kcal": kcal_origem,
                "proteina_g": _prop(normed_o["proteina_g"], fator_o),
                "lipideos_g": _prop(normed_o["lipideos_g"], fator_o),
                "carboidrato_g": _prop(normed_o["carboidrato_g"], fator_o),
                "fibra_g": _prop(normed_o["fibra_g"], fator_o),
            },
        },
        "destino": {
            "nome": normed_d["nome"],
            "gramas": gramas_destino,
            "macros": {
                "kcal": _prop(normed_d["kcal"], fator_d),
                "proteina_g": _prop(normed_d["proteina_g"], fator_d),
                "lipideos_g": _prop(normed_d["lipideos_g"], fator_d),
                "carboidrato_g": _prop(normed_d["carboidrato_g"], fator_d),
                "fibra_g": _prop(normed_d["fibra_g"], fator_d),
            },
        },
        "erro": None,
    }


async def _resolver_alimento(termo_pt: str, termo_en: str, db: "Session"):
    """Cascata TACO → USDA. Retorna (obj_ou_dict, fonte) ou (None, None)."""
    taco = nutricao_service.buscar_alimento(termo_pt, db)
    if taco:
        return taco[0], "TACO"
    usda = await usda_service.buscar_alimento_usda(termo_en, settings.USDA_API_KEY)
    if usda:
        return usda[0], "USDA"
    return None, None


def _fmt_substituicao(res: dict) -> str:
    def _v(val):
        return "n/d" if val is None else str(val)

    o = res["origem"]
    d = res["destino"]
    om = o["macros"]
    dm = d["macros"]
    return (
        f"SUBSTITUICAO_OK | "
        f"ORIGEM: {o['nome']} {o['gramas']}g = {_v(om['kcal'])}kcal, "
        f"P{_v(om['proteina_g'])}g C{_v(om['carboidrato_g'])}g G{_v(om['lipideos_g'])}g | "
        f"DESTINO: {d['nome']} {d['gramas']}g = {_v(dm['kcal'])}kcal, "
        f"P{_v(dm['proteina_g'])}g C{_v(dm['carboidrato_g'])}g G{_v(dm['lipideos_g'])}g"
    )


async def _handle_editar_registro(
    conversa: Conversa,
    message_text: str,
    user: Usuario,
    db: Session,
) -> str:
    estado = conversa.estado_pendente
    etapa = estado.get("etapa")
    alvo = estado.get("alvo", "suplemento")
    texto = (message_text or "").strip()
    low = texto.lower()

    # Cancelamento explícito em qualquer etapa — aborta sem alterar nada
    if any(kw in low for kw in _CANCELAR_EXCLUSAO_KEYWORDS):
        conversa.estado_pendente = None
        return "Edição cancelada. Nada foi alterado. 👍"

    if etapa == "aguardando_escolha":
        if alvo == "suplemento":
            itens = estado.get("itens", [])
            total = len(itens)
            # Aceita só UM número válido — sem "todos", sem múltiplos
            posicoes = _parse_posicoes(texto, total)
            if not posicoes or len(posicoes) != 1:
                conversa.estado_pendente = None
                return "Edição cancelada — não entendi o número. Nada foi alterado."
            pos = posicoes[0]
            old_nome = itens[pos - 1]
            conversa.estado_pendente = {
                "tipo": "editando_registro",
                "alvo": "suplemento",
                "etapa": "aguardando_novo_valor",
                "itens": itens,    # snapshot completo para a troca
                "pos": pos,        # 1-based
                "old_nome": old_nome,
            }
            return f"Qual o novo nome para *{old_nome}*? (ou *cancelar*)"
        elif alvo == "treino":
            ids = estado.get("ids", [])
            labels = estado.get("labels", [])
            nomes = estado.get("nomes", [])
            total = len(ids)
            # Aceita só UM número — sem múltiplos, sem "todos"
            posicoes = _parse_posicoes(texto, total)
            if not posicoes or len(posicoes) != 1:
                conversa.estado_pendente = None
                return "Edição cancelada — não entendi o número. Nada foi alterado."
            pos = posicoes[0]
            old_id = ids[pos - 1]
            old_label = labels[pos - 1] if pos - 1 < len(labels) else f"treino {old_id}"
            old_nome = nomes[pos - 1] if pos - 1 < len(nomes) else old_label
            conversa.estado_pendente = {
                "tipo": "editando_registro",
                "alvo": "treino",
                "etapa": "aguardando_novo_valor",
                "old_id": old_id,
                "old_label": old_label,
                "old_nome": old_nome,
            }
            return f"Me manda a versão nova do treino *{old_label}* (cole o texto do treino). Ou *cancelar*."
        else:
            conversa.estado_pendente = None
            return "Edição cancelada. Tipo não suportado."

    if etapa == "aguardando_novo_valor":
        if alvo == "suplemento":
            novo_nome = texto
            if not novo_nome:
                conversa.estado_pendente = None
                return "Edição cancelada — nome vazio. Nada foi alterado."
            itens = list(estado.get("itens", []))  # cópia mutável do snapshot
            pos = estado.get("pos", 1)
            old_nome = estado.get("old_nome", "")
            # Troca por posição — seguro mesmo com nomes duplicados na lista
            itens[pos - 1] = novo_nome
            habito_service.registrar_suplementos_usuario(user.id, itens, db)
            conversa.estado_pendente = None
            return f"Pronto! *{old_nome}* virou *{novo_nome}*. ✅"
        elif alvo == "treino":
            novo_texto = texto
            if not novo_texto.strip():
                conversa.estado_pendente = None
                return "Edição cancelada — texto vazio. O treino original foi mantido."
            old_id = estado.get("old_id")
            old_label = estado.get("old_label", "treino")
            old_nome = estado.get("old_nome", old_label)
            # Salva PRIMEIRO — só apaga o antigo se o save não lançar exceção
            try:
                treino_service.cadastrar_treino_proprio(
                    user_id=user.id,
                    nome=old_nome,
                    texto=novo_texto,
                    db=db,
                )
            except Exception as e:
                logger.error("editar_treino_save_error", extra={"user_id": user.id, "error": str(e)})
                conversa.estado_pendente = None
                return "Erro ao salvar o novo treino. O treino original foi mantido. Tente novamente."
            if old_id:
                treino_service.apagar_treinos(user.id, [old_id], db)
            conversa.estado_pendente = None
            return f"Treino *{old_label}* atualizado! ✅"
        else:
            conversa.estado_pendente = None
            return "Edição cancelada. Tipo não suportado."

    # Etapa desconhecida — aborta defensivamente
    conversa.estado_pendente = None
    return "Edição cancelada. Nada foi alterado."


def _handle_substituicao_dieta(
    conversa: Conversa,
    message_text: str,
    user: "Usuario",
    db: Session,
) -> str:
    estado = conversa.estado_pendente
    etapa = estado.get("etapa")
    low = (message_text or "").strip().lower()
    descricao = estado.get("descricao", "")

    if etapa == "aguardando_escopo":
        if any(kw in low for kw in _ESCOPO_PLANO_KEYWORDS):
            conversa.estado_pendente = None
            ok = nutricao_service.anexar_troca_ao_plano(user.id, descricao, db)
            if ok:
                return f"Pronto, ajustei no seu plano: {descricao} 👍"
            return "Você ainda não tem um plano salvo pra ajustar, mas anotei a troca pra hoje. 👍"

        if any(kw in low for kw in _ESCOPO_HOJE_KEYWORDS):
            conversa.estado_pendente = None
            return "Belê, só por hoje então. Não mexi no seu plano. 👍"

        return "É só pra hoje ou pra salvar no seu plano alimentar?"

    conversa.estado_pendente = None
    return "Belê, cancelei a pergunta."


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
            series_detalhe=estado.get("series_detalhe"),
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

def _derivar_agregados_de_series(series_detalhe: list) -> dict | None:
    """Deriva {series, repeticoes, carga_kg} a partir de séries individuais.
    Considera apenas válidas (is_aquecimento=False).
    - series  = count das válidas
    - carga_kg = max(carga_kg das válidas)
    - repeticoes = reps da série de maior carga
    Retorna None se não houver séries válidas.
    """
    validas = [s for s in series_detalhe if not s.get("is_aquecimento", False)]
    if not validas:
        return None
    serie_max = max(validas, key=lambda s: float(s.get("carga_kg", 0)))
    return {
        "series": len(validas),
        "repeticoes": int(serie_max.get("repeticoes", 0)),
        "carga_kg": float(serie_max.get("carga_kg", 0)),
    }


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

    series_detalhe_raw = tool_input.get("series_detalhe")
    if series_detalhe_raw and isinstance(series_detalhe_raw, list) and len(series_detalhe_raw) > 0:
        agregados = _derivar_agregados_de_series(series_detalhe_raw)
        if agregados is not None:
            series = agregados["series"]
            reps = agregados["repeticoes"]
            carga = agregados["carga_kg"]

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
            "series_detalhe": series_detalhe_raw,
        }
        return (
            f"AGUARDANDO_CONFIRMACAO: '{exercicio_display}' com {carga}kg representa variação "
            f"de {variacao_pct:+.0f}% em relação ao último registro ({ultima_carga}kg) "
            f"na posição {posicao} da sessão. Informe o usuário e aguarde confirmação."
        )

    sessao = sessao_treino_service.get_sessao_ativa(user.id, db)
    treino_nome = sessao.treino_nome if sessao else None

    registro = exercicio_service.registrar(
        user_id=user.id,
        sessao_data=sessao_data,
        posicao=posicao,
        exercicio_display=exercicio_display,
        series=series,
        repeticoes=reps,
        carga_kg=carga,
        db=db,
        treino_nome=treino_nome,
        series_detalhe=series_detalhe_raw,
    )

    primeiro_vez_str = " Primeiro registro deste exercício nesta posição — referência criada." if not historico else ""
    sem_sessao_str = (
        " ⚠️ Você ainda não iniciou um treino — manda 'treinar [nome do treino]' antes pra eu agrupar os registros."
        if sessao is None else ""
    )

    return (
        f"REGISTRADO: '{exercicio_display}' — posição {posicao} na sessão, "
        f"{series}x{reps} @ {carga}kg.{primeiro_vez_str}{sem_sessao_str}"
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


async def _process_tool_cadastrar_treino(tool_input: dict, user: Usuario, db: Session) -> str:
    texto_original = tool_input["texto_original"]
    treino = treino_service.cadastrar_treino_proprio(
        user_id=user.id,
        nome=tool_input["nome_treino"],
        texto=texto_original,
        db=db,
        exercicios=tool_input.get("exercicios_extraidos", ""),
    )
    estrutura = await extrair_estrutura_treino(texto_original, client)
    if estrutura and isinstance(estrutura.get("dias"), list) and len(estrutura["dias"]) > 0:
        novo_conteudo = dict(treino.conteudo)
        novo_conteudo["dias"] = estrutura["dias"]
        treino.conteudo = novo_conteudo
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
# Cadastro de perfil obrigatório
# ---------------------------------------------------------------------------

def _iniciar_cadastro_perfil(user: Usuario, conversa: Conversa, db: Session) -> str:
    conversa.estado_pendente = {
        "tipo": "cadastro_perfil",
        "fase": "confirmar_nome",
        "dados": {},
        "criado_em": datetime.utcnow().isoformat(),
    }
    db.add(conversa)
    db.commit()
    primeiro_nome = (user.nome or "").split()[0].strip() if user.nome else ""
    if primeiro_nome:
        _, pergunta = ETAPAS_CADASTRO_PERFIL[0]
        return pergunta.replace("{nome_kiwify}", primeiro_nome)
    return "Bora pro seu cadastro! 💪\n\nQual é o seu nome?"


async def _handle_cadastro_perfil(conversa: Conversa, message_text: str, user: Usuario, db: Session) -> str:
    estado = conversa.estado_pendente or {}
    fase = estado.get("fase", "confirmar_nome")
    dados: dict = dict(estado.get("dados", {}))
    resposta = message_text.strip()

    proxima_fase: str | None

    if fase == "confirmar_nome":
        norm = _normalizar_confirmacao(resposta)
        if norm == "sim":
            dados["nome"] = user.nome
        else:
            novo_nome = resposta.strip()
            if novo_nome:
                user.nome = novo_nome
                db.flush()
            dados["nome"] = user.nome
        proxima_fase = "sexo"

    elif fase == "sexo":
        r = resposta.lower()
        if r in ("1", "masculino", "homem", "m", "masc"):
            dados["sexo"] = "M"
            proxima_fase = "data_nascimento"
        elif r in ("2", "feminino", "mulher", "f", "fem"):
            dados["sexo"] = "F"
            proxima_fase = "data_nascimento"
        else:
            return "Por favor, responda *1* ou *2*."

    elif fase == "data_nascimento":
        try:
            partes = resposta.strip().split("/")
            if len(partes) != 3:
                raise ValueError
            d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
            dt = date(a, m, d)
            if dt.year < 1900 or dt.year > date.today().year:
                raise ValueError
            idade = perfil_service.calcular_idade(dt)
            if idade is None or idade < 10 or idade > 100:
                raise ValueError
            dados["data_nascimento"] = dt.isoformat()
            proxima_fase = "altura_cm"
        except (ValueError, IndexError):
            return "Formato inválido. Tente *DD/MM/AAAA* (ex: 15/03/1990)."

    elif fase == "altura_cm":
        try:
            h = int(resposta.replace("cm", "").replace(" ", ""))
            if not 100 <= h <= 250:
                raise ValueError
            dados["altura_cm"] = h
            proxima_fase = "peso_kg"
        except ValueError:
            return "Altura inválida. Em cm, ex: *175*."

    elif fase == "peso_kg":
        try:
            p = float(resposta.replace(",", ".").replace("kg", "").replace(" ", ""))
            if not 30.0 <= p <= 300.0:
                raise ValueError
            dados["peso_kg"] = p
            proxima_fase = "nivel_experiencia"
        except ValueError:
            return "Peso inválido. Ex: *82.5*."

    elif fase == "nivel_experiencia":
        mapa = {
            "1": "iniciante", "2": "intermediario", "3": "avancado",
            "iniciante": "iniciante",
            "intermediário": "intermediario", "intermediario": "intermediario",
            "avançado": "avancado", "avancado": "avancado",
        }
        nivel = mapa.get(resposta.lower())
        if nivel:
            dados["nivel_experiencia"] = nivel
            proxima_fase = None
        else:
            return "Responda *1*, *2* ou *3*."

    elif fase == "oferta_extras":
        r = resposta.lower()
        if r in ("1", "medidas", "medida"):
            conversa.estado_pendente = None
            db.add(conversa)
            db.commit()
            return (
                "Beleza! Me manda suas medidas: *cintura*, *quadril*, *pescoço*, *braço*, *coxa*, *panturrilha*. "
                "Pode mandar todas juntas ou uma por vez. 📏"
            )
        elif r in ("2", "fotos", "foto"):
            conversa.estado_pendente = None
            db.add(conversa)
            db.commit()
            primeiro_nome_local = (user.nome or "").split()[0] if user.nome else "você"
            return (
                f"Vou analisar sua composição corporal, {primeiro_nome_local}! 📸\n\n"
                "Preciso de *3 fotos* suas:\n"
                "1. *Frente* — de frente para a câmera\n"
                "2. *Costas* — de costas para a câmera\n"
                "3. *Lado* — perfil, braço relaxado ao lado do corpo\n\n"
                "Pode mandar a primeira foto de *frente* agora!"
            )
        elif r in ("3", "pular", "nao", "não", "depois", "agora não", "agora nao"):
            conversa.estado_pendente = None
            db.add(conversa)
            db.commit()
            return "Beleza! Pode usar tudo agora. Digite */menu* pra começar. 💪"
        else:
            return "Por favor, responda *1*, *2* ou *3*."

    else:
        proxima_fase = None

    if proxima_fase is not None:
        conversa.estado_pendente = {
            "tipo": "cadastro_perfil",
            "fase": proxima_fase,
            "dados": dados,
            "criado_em": estado.get("criado_em"),
        }
        db.add(conversa)
        db.commit()
        for etapa_nome, etapa_pergunta in ETAPAS_CADASTRO_PERFIL:
            if etapa_nome == proxima_fase:
                return etapa_pergunta
        return "Próxima etapa do cadastro."

    # Todas as fases concluídas — persiste no perfil e abre oferta de extras
    perfil = perfil_service.get_or_create_perfil(user.id, db)
    perfil.sexo = dados.get("sexo")
    if dados.get("data_nascimento"):
        perfil.data_nascimento = date.fromisoformat(dados["data_nascimento"])
    perfil.altura_cm = dados.get("altura_cm")
    if dados.get("peso_kg") is not None:
        perfil.peso_kg = dados["peso_kg"]
    perfil.nivel_experiencia = dados.get("nivel_experiencia")
    db.flush()

    nome_salvo = user.nome or ""
    primeiro_nome = nome_salvo.split()[0] if nome_salvo else ""
    sexo_legivel = {"M": "Masculino", "F": "Feminino"}.get(dados.get("sexo", ""), "—")
    nivel_legivel = {
        "iniciante": "Iniciante",
        "intermediario": "Intermediário",
        "avancado": "Avançado",
    }.get(dados.get("nivel_experiencia", ""), "—")
    dt_nasc = date.fromisoformat(dados["data_nascimento"]) if dados.get("data_nascimento") else None
    idade = perfil_service.calcular_idade(dt_nasc)

    conversa.estado_pendente = {
        "tipo": "cadastro_perfil",
        "fase": "oferta_extras",
        "criado_em": estado.get("criado_em"),
    }
    db.add(conversa)
    db.commit()

    return (
        "Perfil cadastrado! 🎯\n\n"
        f"👤 {primeiro_nome}\n"
        f"⚧ {sexo_legivel}\n"
        + (f"🎂 {idade} anos\n" if idade else "")
        + f"📏 {dados.get('altura_cm')}cm\n"
        f"⚖️ {dados.get('peso_kg')}kg\n"
        f"📊 {nivel_legivel}\n\n"
        "Pra deixar tudo ainda mais preciso, posso registrar suas *medidas corporais* "
        "(cintura, quadril, braço, etc.) e fazer uma *análise por fotos*.\n\n"
        "É *opcional*, e caso queira pode enviar depois em outro momento.\n\n"
        "1️⃣ Registrar medidas\n"
        "2️⃣ Enviar fotos pra análise\n"
        "3️⃣ Pular por agora"
    )


# ---------------------------------------------------------------------------
# Coleta estruturada de treino
# ---------------------------------------------------------------------------

def _iniciar_coleta_treino(user: Usuario, conversa: Conversa, db: Session) -> str:
    primeiro_nome = (user.nome or "").split()[0] if user.nome else ""
    perfil = perfil_service.get_or_create_perfil(user.id, db)
    tem_perfil = perfil.dias_semana_padrao is not None

    dados: dict[str, str | None] = {chave: None for chave, _ in ETAPAS_TREINO}

    if tem_perfil:
        _local_d   = {"academia": "Academia", "casa": "Em casa", "ar_livre": "Ao ar livre"}
        _obj_d     = {
            "ganhar_massa": "Ganhar massa", "perder_gordura": "Perder gordura",
            "manter": "Manter peso", "condicionamento": "Condicionamento",
        }
        _nivel_d   = {"iniciante": "Iniciante", "intermediario": "Intermediário", "avancado": "Avançado"}
        _horario_d = {
            "manha": "Manhã", "manha_pico": "Manhã pico (6h–9h)", "tarde": "Tarde",
            "noite_pico": "Noite pico (17h–20h)", "noite": "Noite",
        }

        def _d(val: str | None, mapa: dict) -> str:
            return mapa.get(val or "", val or "—") if val else "—"

        perfil_resumo = {
            "local":        perfil.local_treino_padrao,
            "objetivo":     perfil.objetivo_padrao,
            "dias_semana":  perfil.dias_semana_padrao,
            "tempo_sessao": perfil.tempo_sessao_padrao,
            "nivel":        perfil.nivel_experiencia,
            "lesoes":       perfil.lesoes,
            "horario":      perfil.horario_treino_padrao,
        }

        conversa.estado_pendente = {
            "tipo": "criando_treino",
            "fase": "confirmando_perfil",
            "dados": dados,
            "perfil_resumo": perfil_resumo,
            "criado_em": datetime.utcnow().isoformat(),
        }
        db.add(conversa)
        db.commit()

        return (
            "Bora pro seu treino"
            + (f", {primeiro_nome}" if primeiro_nome else "")
            + "! 💪 Tenho seu perfil salvo:\n\n"
            + f"📍 *Local:* {_d(perfil.local_treino_padrao, _local_d)}\n"
            + f"🎯 *Objetivo:* {_d(perfil.objetivo_padrao, _obj_d)}\n"
            + f"📅 *Dias:* {perfil.dias_semana_padrao or '—'}\n"
            + f"⏱️ *Tempo:* {perfil.tempo_sessao_padrao or '—'}\n"
            + f"📊 *Nível:* {_d(perfil.nivel_experiencia, _nivel_d)}\n"
            + f"🩹 *Lesões:* {perfil.lesoes or 'nenhuma'}\n"
            + f"🕐 *Horário:* {_d(perfil.horario_treino_padrao, _horario_d)}\n\n"
            + "Quer manter tudo isso? Responda *sim* pra manter, ou me diga o que quer mudar."
        )

    # 1º treino — coleta completa, sem etapa de confirmação
    conversa.estado_pendente = {
        "tipo": "criando_treino",
        "fase": "coletando",
        "etapa_idx": 0,
        "dados": dados,
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
    fase = estado.get("fase", "coletando")
    dados = dict(estado.get("dados", {}))

    # --- Fase de nomeação do treino (fase final — grava com nome) ---
    if fase == "nomeando_treino":
        nome = message_text.strip()
        if not nome:
            return "Por favor, me manda o nome do plano (ex: Plano Hipertrofia)."
        if len(nome) > 60:
            return "Nome muito longo (máx 60 caracteres). Tenta de novo."
        if nome.lower() in {"cancelar", "/menu", "menu", "#menu"} or nome.lower().startswith("/"):
            conversa.estado_pendente = None
            db.add(conversa)
            db.commit()
            return "Cancelei a criação do treino. Os dados não foram salvos."
        texto_gerado = estado.get("texto_gerado", "")
        conteudo_treino = {
            "texto": texto_gerado,
            "nome": nome,
            "modalidade": estado.get("modalidade"),
            "gerado_em": datetime.utcnow().isoformat(),
        }
        estrutura = estado.get("estrutura")
        if isinstance(estrutura, dict) and isinstance(estrutura.get("dias"), list):
            conteudo_treino["dias"] = estrutura["dias"]
        db.add(Treino(user_id=user.id, conteudo=conteudo_treino))
        conversa.estado_pendente = None
        db.add(conversa)
        db.commit()
        return f"Plano *{nome}* salvo! 💪\n\nQuando quiser treinar, manda *treinar* e eu mostro os treinos do plano."

    # --- Fase de confirmação do perfil (2º treino em diante) ---
    if fase == "confirmando_perfil":
        perfil_resumo: dict = estado.get("perfil_resumo", {})
        resposta = _normalizar_confirmacao(message_text)

        if resposta == "sim":
            dados["local"]        = perfil_resumo.get("local")
            dados["objetivo"]     = perfil_resumo.get("objetivo")
            dados["dias_semana"]  = perfil_resumo.get("dias_semana")
            dados["tempo_sessao"] = perfil_resumo.get("tempo_sessao")
            dados["nivel"]        = perfil_resumo.get("nivel")
            dados["lesoes"]       = perfil_resumo.get("lesoes") or "nenhuma"
            dados["horario"]      = perfil_resumo.get("horario")
            # tipo_treino e dor_desconforto ficam None → perguntados a seguir
            etapa_idx = next(
                (i for i, (chave, _) in enumerate(ETAPAS_TREINO) if dados[chave] is None),
                len(ETAPAS_TREINO),
            )
        else:
            # Quer mudar algo — coleta completa do zero
            etapa_idx = 0
            conversa.estado_pendente = {
                "tipo": "criando_treino",
                "fase": "coletando",
                "etapa_idx": etapa_idx,
                "dados": dados,
                "criado_em": estado.get("criado_em"),
            }
            return "Beleza, vamos refazer do zero então.\n\n" + ETAPAS_TREINO[0][1]

        conversa.estado_pendente = {
            "tipo": "criando_treino",
            "fase": "coletando",
            "etapa_idx": etapa_idx,
            "dados": dados,
            "criado_em": estado.get("criado_em"),
        }
        _, pergunta = ETAPAS_TREINO[etapa_idx]
        return pergunta

    # --- Fase normal de coleta ---
    etapa_idx = int(estado.get("etapa_idx", 0))
    chave, _ = ETAPAS_TREINO[etapa_idx]
    dados[chave] = message_text.strip() or "não informado"
    etapa_idx += 1

    # Pula etapas cujo valor já veio do perfil (não-None)
    while etapa_idx < len(ETAPAS_TREINO) and dados.get(ETAPAS_TREINO[etapa_idx][0]) is not None:
        etapa_idx += 1

    if etapa_idx >= len(ETAPAS_TREINO):
        return await _gerar_treino_de_dados(dados, user, conversa, db)

    conversa.estado_pendente = {
        "tipo": "criando_treino",
        "fase": "coletando",
        "etapa_idx": etapa_idx,
        "dados": dados,
        "criado_em": estado.get("criado_em"),
    }
    _, pergunta = ETAPAS_TREINO[etapa_idx]
    return pergunta


_TOOL_EXTRACAO_TREINO = {
    "name": "salvar_treino_estruturado",
    "description": "Extrai a estrutura do plano de treino em formato JSON (dias e exercícios) a partir do texto livre.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nome_plano": {"type": "string", "description": "Nome curto do plano (ex: 'Plano Hipertrofia')"},
            "dias": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {"type": "integer", "description": "Número do dia (1, 2, 3...)"},
                        "nome": {"type": "string", "description": "Nome do dia (ex: 'Peito A', 'Push', 'Pernas')"},
                        "foco": {"type": "string", "description": "Grupos musculares trabalhados (opcional)"},
                        "exercicios": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "nome": {"type": "string", "description": "Nome do exercício"},
                                    "series_validas": {"type": "integer", "description": "Séries de trabalho (sem contar aquecimento)"},
                                    "aquecimento": {"type": "integer", "description": "Séries de aquecimento (0 se não houver)"},
                                    "reps": {"type": "string", "description": "Faixa de repetições (ex: '8-10', '12', 'até falha')"},
                                    "descanso_seg": {"type": "integer", "description": "Tempo de descanso em segundos"},
                                    "observacoes": {"type": "string", "description": "Observação opcional sobre o exercício"},
                                },
                                "required": ["nome", "series_validas", "aquecimento", "reps", "descanso_seg"],
                            },
                        },
                    },
                    "required": ["numero", "nome", "exercicios"],
                },
            },
        },
        "required": ["nome_plano", "dias"],
    },
}


async def extrair_estrutura_treino(texto_plano: str, anthropic_client) -> dict | None:
    """Faz 2ª chamada Claude com tool salvar_treino_estruturado pra extrair dias/exercícios do texto livre.
    Retorna dict com {nome_plano, dias: [...]} se sucesso, ou None após 2 tentativas (degradação graciosa).
    """
    prompt = (
        "Você recebeu um plano de treino em texto livre abaixo. Sua tarefa é EXTRAIR a estrutura "
        "em JSON usando a tool salvar_treino_estruturado.\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "1. SEMPRE retorne o array 'dias' PREENCHIDO com TODOS os dias do plano (1 entrada por dia de treino).\n"
        "2. NÃO retorne apenas 'nome_plano' — o campo 'dias' é OBRIGATÓRIO e não pode ser vazio.\n"
        "3. NÃO invente exercícios ou números que não estejam no texto.\n"
        "4. Se algum campo opcional estiver ausente no texto, omita-o. Para 'aquecimento', use 0 se não houver. Para 'descanso_seg', use 60 como padrão.\n"
        "5. Se o texto tem N dias diferentes, retorne N entradas em 'dias'.\n\n"
        f"PLANO:\n{texto_plano}"
    )

    for tentativa in range(2):
        try:
            prompt_atual = prompt
            if tentativa > 0:
                prompt_atual = prompt + (
                    "\n\nATENÇÃO: sua resposta anterior estava INCOMPLETA (faltou o array 'dias'). "
                    "Retorne a estrutura COMPLETA agora, com TODOS os dias preenchidos."
                )
            resp = await anthropic_client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=4000,
                tools=[_TOOL_EXTRACAO_TREINO],
                tool_choice={"type": "tool", "name": "salvar_treino_estruturado"},
                messages=[{"role": "user", "content": prompt_atual}],
            )
            for block in resp.content:
                if hasattr(block, "name") and block.name == "salvar_treino_estruturado":
                    dados = block.input
                    if isinstance(dados, dict) and isinstance(dados.get("dias"), list) and len(dados["dias"]) > 0:
                        return dados
                    logger.warning(
                        "extrair_estrutura_treino_validacao_falhou",
                        extra={
                            "tentativa": tentativa + 1,
                            "dados": str(dados)[:200],
                            "stop_reason": getattr(resp, "stop_reason", "unknown"),
                            "usage": str(getattr(resp, "usage", "")),
                        },
                    )
                    break
            else:
                logger.warning("extrair_estrutura_treino_tool_nao_usada", extra={"tentativa": tentativa + 1})
        except Exception as e:
            logger.warning("extrair_estrutura_treino_erro", extra={"tentativa": tentativa + 1, "error": str(e)})

    logger.error("extrair_estrutura_treino_falhou_todas_tentativas")
    return None


async def _gerar_treino_de_dados(
    dados: dict,
    user: Usuario,
    conversa: Conversa,
    db: Session,
) -> str:
    primeiro_nome = (user.nome or "").split()[0] if user.nome else None

    # Maps descritivos — usados APENAS no prompt (Claude e cliente veem texto longo)
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

    # Maps canônicos — usados APENAS para salvar no perfil (dentro dos limites VARCHAR)
    tipo_canon = {
        "1": "musculacao", "2": "calistenia", "3": "yoga",
        "4": "pilates",    "5": "corrida",    "6": "hibrido",
        "7": "funcional",  "8": "crossfit",   "9": "mobilidade",
    }
    local_canon   = {"1": "academia",      "2": "casa",           "3": "ar_livre"}
    obj_canon     = {
        "1": "ganhar_massa", "2": "perder_gordura",
        "3": "manter",       "4": "condicionamento",
    }
    nivel_canon   = {"1": "iniciante", "2": "intermediario", "3": "avancado"}
    horario_canon = {
        "1": "manha", "2": "manha_pico", "3": "tarde",
        "4": "noite_pico", "5": "noite",
    }

    def _dec(val: str | None, mapa: dict) -> str:
        v = (val or "").strip()
        return mapa.get(v, v) if v else "não informado"

    def _canon(val: str | None, mapa: dict, maxlen: int) -> str | None:
        v = (val or "").strip()
        if not v:
            return None
        return mapa.get(v, v[:maxlen])

    # Valores descritivos para o prompt (sem alteração)
    tipo    = _dec(dados.get("tipo_treino"),      tipo_map)
    local   = _dec(dados.get("local"),            local_map)
    obj     = _dec(dados.get("objetivo"),         obj_map)
    nivel   = _dec(dados.get("nivel"),            nivel_map)
    horario = _dec(dados.get("horario"),          horario_map)
    dias    = dados.get("dias_semana")   or "não informado"
    tempo   = dados.get("tempo_sessao") or "não informado"
    lesoes  = dados.get("lesoes")        or "nenhuma"
    dor     = dados.get("dor_desconforto") or "nenhum"

    # Valores canônicos para salvar no perfil (curtos, dentro dos limites de coluna)
    tipo_p    = _canon(dados.get("tipo_treino"), tipo_canon,    30)
    local_p   = _canon(dados.get("local"),       local_canon,   30)
    obj_p     = _canon(dados.get("objetivo"),    obj_canon,     30)
    nivel_p   = _canon(dados.get("nivel"),       nivel_canon,   20)
    horario_p = _canon(dados.get("horario"),     horario_canon, 20)
    dias_p    = (dados.get("dias_semana")  or "").strip()[:10] or None
    tempo_p   = (dados.get("tempo_sessao") or "").strip()[:20] or None
    lesoes_p  = dados.get("lesoes") or None  # TEXT — sem limite de tamanho

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

    # Reply vazio sem exceção (resposta da IA sem bloco de texto): trata como falha —
    # não salva treino vazio e pede para tentar novamente.
    if not reply.strip():
        logger.error("gerar_treino_reply_vazio", extra={"user_id": user.id})
        return "Desculpe, tive um problema ao gerar seu treino. Pode tentar novamente em instantes."

    # A partir daqui o reply é válido: o salvamento do perfil e do treino é garantido antes do return.

    # Salva valores canônicos (curtos) no perfil — nunca estoura nenhuma coluna VARCHAR
    perfil = perfil_service.get_or_create_perfil(user.id, db)
    if tipo_p:    perfil.tipo_treino_padrao    = tipo_p
    if local_p:   perfil.local_treino_padrao   = local_p
    if obj_p:     perfil.objetivo_padrao       = obj_p
    if nivel_p:   perfil.nivel_experiencia     = nivel_p
    if lesoes_p and lesoes_p != "nenhuma": perfil.lesoes = lesoes_p
    if horario_p: perfil.horario_treino_padrao = horario_p
    if dias_p:    perfil.dias_semana_padrao    = dias_p
    if tempo_p:   perfil.tempo_sessao_padrao   = tempo_p
    db.flush()

    # Extrai estrutura JSON (dias/exercícios) do texto gerado — degradação graciosa se falhar
    estrutura = await extrair_estrutura_treino(reply, client)

    # Pede nome antes de gravar — fase "nomeando_treino" persiste texto e estrutura, aguarda resposta
    conversa.estado_pendente = {
        "tipo": "criando_treino",
        "fase": "nomeando_treino",
        "texto_gerado": reply,
        "estrutura": estrutura,
        "modalidade": tipo_p,
        "criado_em": datetime.utcnow().isoformat(),
    }
    db.add(conversa)
    db.commit()

    return reply + "\n\n---\n\nComo quer chamar esse *plano*? (ex: Plano Hipertrofia, Treino Verão, ABC)"


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
        _falta = perfil_service.faltam_medidas_ou_fotos(user.id, db)
        if _falta["medidas"] and _falta["fotos"]:
            _aviso = "📝 _Aviso: você ainda não enviou medidas corporais nem fotos pra análise. É opcional, mas ajuda a calibrar melhor. Pode enviar a qualquer momento._\n\n"
        elif _falta["medidas"]:
            _aviso = "📝 _Aviso: você ainda não enviou medidas corporais. É opcional, mas ajuda a calibrar melhor. Pode enviar a qualquer momento._\n\n"
        elif _falta["fotos"]:
            _aviso = "📝 _Aviso: você ainda não enviou fotos pra análise de composição corporal. É opcional, mas ajuda a calibrar melhor. Pode enviar a qualquer momento._\n\n"
        else:
            _aviso = ""
        return (
            _aviso
            + f"Vamos criar sua dieta personalizada, {primeiro_nome}! 🥗\n\n"
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
            "Funciona com: pratos, marmitas, lanches, bebidas, embalagens..."
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
# Confirmação de registro de medida após variação grande de peso no perfil
# ---------------------------------------------------------------------------

async def _handle_confirmar_historico_medida(
    conversa: Conversa,
    message_text: str,
    user: Usuario,
    db: Session,
) -> str:
    estado = conversa.estado_pendente or {}
    resposta = _normalizar_confirmacao(message_text)
    if resposta == "sim":
        nutricao_service.registrar_medidas(
            user_id=user.id,
            data_medicao=date.today(),
            campos={"peso_kg": float(estado.get("peso_kg"))},
            db=db,
        )
        conversa.estado_pendente = None
        db.add(conversa)
        db.commit()
        return f"Pronto, registrei {estado.get('peso_kg')}kg no seu histórico corporal também. 📊"
    elif resposta == "nao":
        conversa.estado_pendente = None
        db.add(conversa)
        db.commit()
        return "Beleza, mantenho só no perfil. 👍"
    else:
        return "Por favor, responda *sim* ou *não*."


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

    # 0.5. Guard: perfil obrigatório — intercepts before everything including /menu
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "cadastro_perfil":
        return await _handle_cadastro_perfil(conversa, message_text, user, db)
    _perfil = perfil_service.get_or_create_perfil(user.id, db)
    if not perfil_service.perfil_minimo_completo(_perfil):
        return _iniciar_cadastro_perfil(user, conversa, db)

    # 0.8. Guard: comando "treinar [nome]" — inicia sessão de treino
    stripped = message_text.strip()
    stripped_lower = stripped.lower()

    _PALAVRAS_RESERVADAS = {"cancelar", "/menu", "menu", "#menu", "treinar"}

    def _nome_display_treino(t: Treino) -> str:
        cont = t.conteudo if isinstance(t.conteudo, dict) else {}
        nome = (cont.get("nome") or "").strip()
        return nome if nome else _titulo_treino(cont.get("texto") or "")

    def _eh_comando_reservado(s_lower: str) -> bool:
        return (
            s_lower in {"/menu", "menu", "#menu"}
            or s_lower.startswith("treinar")
            or s_lower.startswith("/")
        )

    def _dias_do_plano(plano: Treino) -> list[str]:
        cont = plano.conteudo if isinstance(plano.conteudo, dict) else {}
        dias = cont.get("dias")
        nomes: list[str] = []
        if isinstance(dias, list):
            for i, d in enumerate(dias, 1):
                if not isinstance(d, dict):
                    continue
                nome = (d.get("nome") or "").strip()
                if not nome:
                    nome = f"Dia {d.get('numero') or i}"
                nomes.append(nome)
        return nomes

    def _casar_dia(texto: str, dias_nomes: list[str]) -> str | None:
        alvo = texto.strip().lower()
        if not alvo or not dias_nomes:
            return None
        for nome in dias_nomes:
            if nome.lower() == alvo:
                return nome
        candidatos = [n for n in dias_nomes if alvo in n.lower() or n.lower() in alvo]
        return candidatos[0] if len(candidatos) == 1 else None

    def _exercicios_do_dia(plano: Treino, nome_dia: str) -> list | None:
        cont = plano.conteudo if isinstance(plano.conteudo, dict) else {}
        dias = cont.get("dias")
        if not isinstance(dias, list):
            return None
        alvo = (nome_dia or "").strip().lower()
        for d in dias:
            if isinstance(d, dict) and (d.get("nome") or "").strip().lower() == alvo:
                exs = d.get("exercicios")
                return exs if isinstance(exs, list) and exs else None
        return None

    def _prescricao_str(ex: dict) -> str:
        sv = ex.get("series_validas") or 0
        aq = ex.get("aquecimento") or 0
        reps = (ex.get("reps") or "").strip()
        partes = []
        if aq:
            partes.append(f"{aq} aquecimento{'s' if aq > 1 else ''}")
        partes.append(f"{sv} série{'s' if sv != 1 else ''} válida{'s' if sv != 1 else ''}")
        base = " e ".join(partes)
        if reps:
            base += f" com {reps} repetições"
        return base

    def _apresentar_treino(nome_dia: str, exercicios: list) -> str:
        linhas_ex = []
        for ex in exercicios:
            if not isinstance(ex, dict):
                continue
            nome_ex = (ex.get("nome") or "exercício").strip()
            linhas_ex.append(f"*{nome_ex}* - {_prescricao_str(ex)}")
        corpo = "\n\n".join(linhas_ex)
        return (
            f"Segue seu treino de *{nome_dia}*:\n\n"
            f"{corpo}\n\n"
            "Envie *treinar* para iniciarmos o treino"
        )

    def _apresentar_ou_iniciar(nome_treino: str, plano_id) -> str:
        # E3: se o dia tem exercicios estruturados, apresenta e aguarda confirmacao;
        # senao (plano sem dias), inicia a sessao direto (comportamento antigo).
        plano = db.query(Treino).filter(Treino.id == plano_id).first() if plano_id else None
        exercicios = _exercicios_do_dia(plano, nome_treino) if plano else None
        if exercicios:
            conversa.estado_pendente = {
                "tipo": "aguardando_inicio_treino",
                "treino_nome": nome_treino,
                "plano_id": plano_id,
                "criado_em": datetime.utcnow().isoformat(),
            }
            return _apresentar_treino(nome_treino, exercicios)
        sessao_treino_service.iniciar_sessao(user.id, nome_treino, db)
        conversa.estado_pendente = None
        return (
            f"Sessão iniciada: *{nome_treino}* 💪\n"
            "Manda os exercícios que você fizer (ex: 'supino 80kg 3x10') e eu vou registrando."
        )

    def _mostrar_dias_plano(plano: Treino) -> str:
        dias_nomes = _dias_do_plano(plano)
        nome_plano = _nome_display_treino(plano)
        if dias_nomes:
            linhas = [f"Plano: *{nome_plano}*\n", "Qual treino você vai fazer?\n"]
            for i, dn in enumerate(dias_nomes, 1):
                linhas.append(f"*{i}.* {dn}")
            linhas.append("\nResponda com o *número* ou o *nome* (ou *cancelar*).")
            conversa.estado_pendente = {
                "tipo": "escolhendo_treino",
                "dias_nomes": dias_nomes,
                "plano_id": plano.id,
                "criado_em": datetime.utcnow().isoformat(),
            }
            return "\n".join(linhas)
        conversa.estado_pendente = {
            "tipo": "escolhendo_treino",
            "dias_nomes": [],
            "plano_id": plano.id,
            "criado_em": datetime.utcnow().isoformat(),
        }
        return (
            f"O plano *{nome_plano}* ainda não tem treinos separados por dia.\n"
            "Me diz o *nome do treino* que você vai fazer hoje (ex: 'Peito A') e eu inicio a sessão. Ou *cancelar*."
        )

    def _parse_set(texto: str):
        t = texto.strip().lower()
        is_aq = False
        for kw in ("aquecimento", "aquec", "aq"):
            if t.startswith(kw):
                is_aq = True
                t = t[len(kw):].strip()
                break
            if t.endswith(kw):
                is_aq = True
                t = t[:-len(kw)].strip()
                break
        m = re.match(r'^(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(?:kg)?$', t)
        if not m:
            return None
        return {
            "repeticoes": int(m.group(1)),
            "carga_kg": float(m.group(2).replace(",", ".")),
            "is_aquecimento": is_aq,
        }

    def _parse_exercicio_avulso(texto: str):
        t = texto.strip()
        m = re.search(r'(\d+)\s*[x×]\s*(\d+)', t)
        if not m:
            return None
        carga = None
        mp = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', t, re.IGNORECASE)
        if mp:
            carga = float(mp.group(1).replace(",", "."))
        nome = t
        if mp:
            nome = nome.replace(mp.group(0), " ")
        nome = nome.replace(m.group(0), " ")
        nome = re.sub(r"\s+", " ", nome).strip()
        if not nome or not re.search(r"[A-Za-zÀ-ÿ]", nome):
            return None
        return {
            "nome": nome,
            "series": int(m.group(1)),
            "reps": int(m.group(2)),
            "carga_kg": carga,
        }

    def _historico_exercicio_str(nome_ex: str) -> str:
        sessao = sessao_treino_service.get_sessao_ativa(user.id, db)
        treino_nome = sessao.treino_nome if sessao else None
        exercicio_norm = exercicio_service.normalizar_nome(nome_ex)
        ultimo = exercicio_service.get_ultima_execucao(
            user.id, exercicio_norm, treino_nome, db
        )
        if not ultimo:
            return "📊 Sem histórico ainda — bora marcar a primeira!"
        detalhe = ultimo.series_detalhe
        if detalhe:
            aquec = [s for s in detalhe if s.get("is_aquecimento")]
            validas = [s for s in detalhe if not s.get("is_aquecimento")]
            partes = []
            if aquec:
                partes.append("aquec " + " · ".join(f"{s.get('repeticoes')}×{s.get('carga_kg'):g}kg" for s in aquec))
            if validas:
                partes.append("válidas " + " · ".join(f"{s.get('repeticoes')}×{s.get('carga_kg'):g}kg" for s in validas))
            if partes:
                return "📊 Último: " + " · ".join(partes)
        return f"📊 Último: {ultimo.series}×{ultimo.repeticoes} @ {ultimo.carga_kg:g}kg"

    def _anunciar_exercicio_guiado(exercicios: list, idx: int) -> str:
        ex = exercicios[idx]
        nome_ex = (ex.get("nome") or "exercício").strip()
        return (
            f"Exercício {idx + 1}/{len(exercicios)} — *{nome_ex}*: {_prescricao_str(ex)}\n"
            f"{_historico_exercicio_str(nome_ex)}\n"
            "Manda cada série: *reps x peso* (ex: 8 x80). "
            "Aquecimento: comece com \"aquecimento\" (ex: aquecimento 12 x40). "
            "Pra pular: *pular*. Equipamento ocupado? *ocupado*. Pra encerrar: *finalizar*."
        )

    def _registrar_guiado(exercicio_dict: dict, buffer: list, treino_nome: str) -> bool:
        agregados = _derivar_agregados_de_series(buffer)
        if agregados is None:
            return False
        nome_ex = (exercicio_dict.get("nome") or "exercício").strip()
        posicao = exercicio_service.get_proxima_posicao(user.id, sessao_data, db)
        exercicio_service.registrar(
            user_id=user.id,
            sessao_data=sessao_data,
            posicao=posicao,
            exercicio_display=nome_ex,
            series=agregados["series"],
            repeticoes=agregados["repeticoes"],
            carga_kg=agregados["carga_kg"],
            db=db,
            treino_nome=treino_nome,
            series_detalhe=buffer,
        )
        return True

    # Handler: usuário está escolhendo treino da lista numerada
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "escolhendo_treino":
        estado = conversa.estado_pendente
        dias_nomes = estado.get("dias_nomes", [])
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])

        if stripped_lower == "cancelar":
            conversa.estado_pendente = None
            reply = "Beleza, cancelei. Quando quiser começar, manda *treinar*."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif dias_nomes and stripped.isdigit():
            idx = int(stripped) - 1
            if 0 <= idx < len(dias_nomes):
                nome_treino = dias_nomes[idx]
                reply = _apresentar_ou_iniciar(nome_treino, estado.get("plano_id"))
                mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
                mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
                conversa.mensagens = mensagens_tmp
                db.add(conversa)
                db.commit()
                return reply
            else:
                reply = f"Número inválido. Responda *1* a *{len(dias_nomes)}* ou o nome do treino (ou *cancelar*)."
                mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
                mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
                conversa.mensagens = mensagens_tmp
                db.add(conversa)
                db.commit()
                return reply
        elif stripped and not _eh_comando_reservado(stripped_lower):
            # Nome digitado — Q1: casa contra os dias do plano; Q2: aceita livre se o plano não tem dias
            if dias_nomes:
                nome_treino = _casar_dia(stripped, dias_nomes)
                if nome_treino is None:
                    reply = (
                        "Não achei esse treino na lista. Responda com o *número* "
                        f"(*1* a *{len(dias_nomes)}*) ou o *nome* exato (ou *cancelar*)."
                    )
                    mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
                    mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
                    conversa.mensagens = mensagens_tmp
                    db.add(conversa)
                    db.commit()
                    return reply
            else:
                nome_treino = stripped
            reply = _apresentar_ou_iniciar(nome_treino, estado.get("plano_id"))
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        else:
            # Comando reservado — limpa estado e deixa os guards seguintes processarem
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()

    # Handler: usuário está escolhendo o PLANO (quando há 2+ planos)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "escolhendo_plano":
        estado = conversa.estado_pendente
        plano_ids = estado.get("plano_ids", [])
        plano_labels = estado.get("plano_labels", [])
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])
        plano_escolhido_id = None

        if stripped_lower == "cancelar":
            conversa.estado_pendente = None
            reply = "Beleza, cancelei. Quando quiser começar, manda *treinar*."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped.isdigit():
            idx = int(stripped) - 1
            if 0 <= idx < len(plano_ids):
                plano_escolhido_id = plano_ids[idx]
            else:
                reply = f"Número inválido. Responda *1* a *{len(plano_ids)}* ou o nome do plano (ou *cancelar*)."
                mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
                mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
                conversa.mensagens = mensagens_tmp
                db.add(conversa)
                db.commit()
                return reply
        elif stripped and not _eh_comando_reservado(stripped_lower):
            alvo = stripped.lower()
            candidatos = [pid for pid, lb in zip(plano_ids, plano_labels) if alvo in lb.lower() or lb.lower() in alvo]
            if len(candidatos) == 1:
                plano_escolhido_id = candidatos[0]
            else:
                reply = "Não achei esse plano. Responda com o *número* ou o *nome* (ou *cancelar*)."
                mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
                mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
                conversa.mensagens = mensagens_tmp
                db.add(conversa)
                db.commit()
                return reply
        else:
            # Comando reservado — limpa estado e deixa os guards seguintes processarem
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()

        if plano_escolhido_id is not None:
            plano = db.query(Treino).filter(Treino.id == plano_escolhido_id).first()
            dias_nomes = _dias_do_plano(plano) if plano else []
            nome_plano = _nome_display_treino(plano) if plano else "plano"
            if dias_nomes:
                linhas = [f"Plano: *{nome_plano}*\n", "Qual treino você vai fazer?\n"]
                for i, dn in enumerate(dias_nomes, 1):
                    linhas.append(f"*{i}.* {dn}")
                linhas.append("\nResponda com o *número* ou o *nome* (ou *cancelar*).")
                reply = "\n".join(linhas)
                conversa.estado_pendente = {
                    "tipo": "escolhendo_treino",
                    "dias_nomes": dias_nomes,
                    "plano_id": plano.id if plano else None,
                    "criado_em": datetime.utcnow().isoformat(),
                }
            else:
                reply = (
                    f"O plano *{nome_plano}* ainda não tem treinos separados por dia.\n"
                    "Me diz o *nome do treino* que você vai fazer hoje (ex: 'Peito A') e eu inicio a sessão. Ou *cancelar*."
                )
                conversa.estado_pendente = {
                    "tipo": "escolhendo_treino",
                    "dias_nomes": [],
                    "plano_id": plano.id if plano else None,
                    "criado_em": datetime.utcnow().isoformat(),
                }
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply

    # Handler: usuário escolhe entre importar, criar do zero ou cancelar (lista vazia)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "lista_vazia_treino":
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])

        if stripped == "3" or stripped_lower == "cancelar":
            conversa.estado_pendente = None
            reply = "Beleza, cancelei. Quando quiser, manda /menu pra ver as opções."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped == "1":
            # Importar treino próprio → equivalente ao item 2 do menu
            conversa.estado_pendente = None
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            reply = await _handle_menu_item(2, user, phone, db, conversa)
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped == "2":
            # Criar do zero → equivalente ao item 1 do menu
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            reply = _iniciar_coleta_treino(user, conversa, db)
            # _iniciar_coleta_treino já define estado_pendente=criando_treino e faz commit
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif _eh_comando_reservado(stripped_lower):
            # Comando reservado — limpa estado e deixa próximos guards processarem
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        else:
            reply = "Responda *1* (importar), *2* (criar do zero) ou *3* (cancelar)."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply

    # Handler: "treinar [nome]" nao casou nada -> pontual / importar / criar (E3c2)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "treinar_nao_casou":
        estado = conversa.estado_pendente
        nome = estado.get("nome", "treino")
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])
        if stripped == "4" or stripped_lower == "cancelar":
            conversa.estado_pendente = None
            reply = "Beleza, cancelei. Quando quiser, manda *treinar* ou /menu."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped == "1":
            sessao_treino_service.iniciar_sessao(user.id, nome, db)
            conversa.estado_pendente = None
            reply = (
                f"Sessão iniciada: *{nome}* 💪\n"
                "Manda os exercícios que você fizer (ex: 'supino 80kg 3x10') e eu vou registrando."
            )
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped == "2":
            conversa.estado_pendente = None
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            reply = await _handle_menu_item(2, user, phone, db, conversa)
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped == "3":
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            reply = _iniciar_coleta_treino(user, conversa, db)
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif _eh_comando_reservado(stripped_lower):
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        else:
            reply = "Responda *1* (treinar assim mesmo), *2* (importar), *3* (criar do zero) ou *4* (cancelar)."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply

    # Handler: usuário está digitando nome livre (sem lista)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "aguardando_nome_treino":
        if stripped_lower == "cancelar":
            conversa.estado_pendente = None
            reply = "Beleza, cancelei. Quando quiser começar, manda 'treinar [nome]'."
            mensagens_tmp: list[dict] = list(conversa.mensagens or [])
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif _eh_comando_reservado(stripped_lower):
            # É um novo comando — limpa estado e deixa os guards seguintes processarem
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        elif stripped:
            nome_treino = stripped
            sessao_treino_service.iniciar_sessao(user.id, nome_treino, db)
            conversa.estado_pendente = None
            reply = (
                f"Sessão iniciada: *{nome_treino}* 💪\n"
                "Manda os exercícios que você fizer (ex: 'supino 80kg 3x10') e eu vou registrando."
            )
            mensagens_tmp: list[dict] = list(conversa.mensagens or [])
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        # stripped vazio → permanece aguardando; nenhuma ação

    # Handler: treino apresentado, aguardando confirmacao "treinar" pra abrir a sessao (E3)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "aguardando_inicio_treino":
        estado = conversa.estado_pendente
        nome_treino = estado.get("treino_nome", "")
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])
        if stripped_lower in {"treinar", "sim", "iniciar", "bora", "comecar", "começar", "vamos"}:
            sessao_treino_service.iniciar_sessao(user.id, nome_treino, db)
            plano_id = estado.get("plano_id")
            plano = db.query(Treino).filter(Treino.id == plano_id).first() if plano_id else None
            exercicios = _exercicios_do_dia(plano, nome_treino) if plano else None
            if exercicios:
                conversa.estado_pendente = {
                    "tipo": "sessao_guiada",
                    "treino_nome": nome_treino,
                    "plano_id": plano_id,
                    "ordem": list(range(len(exercicios))),
                    "buffers": {},
                    "criado_em": datetime.utcnow().isoformat(),
                }
                reply = "Bora! 💪\n\n" + _anunciar_exercicio_guiado(exercicios, 0)
            else:
                conversa.estado_pendente = None
                reply = (
                    f"Sessão iniciada: *{nome_treino}* 💪\n"
                    "Manda os exercícios que você fizer (ex: 'supino 80kg 3x10') e eu vou registrando."
                )
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif stripped_lower == "cancelar":
            conversa.estado_pendente = None
            reply = "Beleza, cancelei. Quando quiser, manda *treinar*."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply
        elif _eh_comando_reservado(stripped_lower):
            # Comando reservado (ex: /menu, ou "treinar Peito B") - limpa estado e deixa os guards seguintes processarem
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        else:
            reply = f"Quando estiver pronto, envie *treinar* pra iniciar o treino de *{nome_treino}* (ou *cancelar*)."
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply

    # Handler: sessao guiada - bot conduz exercicio a exercicio (G1)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "sessao_guiada":
        estado = conversa.estado_pendente
        plano_id = estado.get("plano_id")
        nome_treino = estado.get("treino_nome", "")
        ordem = list(estado.get("ordem", []))
        buffers = dict(estado.get("buffers", {}))
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])

        def _persistir(reply_text: str, novo_estado):
            conversa.estado_pendente = novo_estado
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply_text, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply_text

        def _finalizar(prefixo: str = ""):
            sessao = sessao_treino_service.get_sessao_ativa(user.id, db)
            if sessao:
                sessao.finalizada_em = datetime.utcnow()
            return _persistir(f"{prefixo}Treino concluído 💪", None)

        def _estado_guiado():
            return {**estado, "ordem": ordem, "buffers": buffers}

        plano = db.query(Treino).filter(Treino.id == plano_id).first() if plano_id else None
        exercicios = _exercicios_do_dia(plano, nome_treino) if plano else None
        if not exercicios or not ordem:
            return _finalizar()

        idx = ordem[0]
        while idx >= len(exercicios):
            ordem.pop(0)
            if not ordem:
                return _finalizar()
            idx = ordem[0]
        ex_atual = exercicios[idx]
        buffer = list(buffers.get(str(idx), []))

        if stripped_lower in {"finalizar", "finalizar treino", "encerrar", "encerrar treino"}:
            ex_nome = (ex_atual.get("nome") or "exercício").strip()
            registrou = _registrar_guiado(ex_atual, buffer, nome_treino)
            prefixo = f"{ex_nome} registrado!\n\n" if registrou else ""
            return _finalizar(prefixo)
        elif stripped_lower == "cancelar":
            sessao = sessao_treino_service.get_sessao_ativa(user.id, db)
            if sessao:
                sessao.finalizada_em = datetime.utcnow()
            return _persistir("Treino encerrado. Quando quiser, manda *treinar*.", None)
        elif stripped_lower in {"ocupado", "ta ocupado", "tá ocupado", "esta ocupado", "está ocupado", "equipamento ocupado"}:
            if len(ordem) < 2:
                return _persistir(
                    "Esse é o último da fila, não tem com quem trocar. Manda a série, ou *finalizar*.",
                    _estado_guiado(),
                )
            ordem[0], ordem[1] = ordem[1], ordem[0]
            return _persistir(
                "Beleza, troquei com o próximo. Volto nesse exercício depois.\n\n"
                + _anunciar_exercicio_guiado(exercicios, ordem[0]),
                _estado_guiado(),
            )
        elif stripped_lower in {"pular", "pular esse", "pular exercicio", "pular exercício", "skip"}:
            buffers.pop(str(idx), None)
            ordem.pop(0)
            if not ordem:
                return _finalizar("Pulado. ")
            return _persistir("Pulado. " + _anunciar_exercicio_guiado(exercicios, ordem[0]), _estado_guiado())
        elif stripped_lower in {"proximo", "próximo", "next", "ok", "feito"}:
            ex_nome = (ex_atual.get("nome") or "exercício").strip()
            registrou = _registrar_guiado(ex_atual, buffer, nome_treino)
            prefixo = f"{ex_nome} registrado!\n\n" if registrou else ""
            buffers.pop(str(idx), None)
            ordem.pop(0)
            if not ordem:
                return _finalizar(prefixo)
            return _persistir(prefixo + _anunciar_exercicio_guiado(exercicios, ordem[0]), _estado_guiado())
        elif _eh_comando_reservado(stripped_lower):
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        else:
            parsed = _parse_set(stripped)
            if parsed is None:
                avulso = _parse_exercicio_avulso(stripped)
                if avulso is None:
                    return _persistir(
                        "Não entendi. Manda a série: *reps x peso* (ex: 8 x80). "
                        "Aquecimento: \"aquecimento 12 x40\". Ou *próximo* / *pular* / *finalizar* / *cancelar*.",
                        _estado_guiado(),
                    )
                nome_av = avulso["nome"].lower()
                alvo = None
                for i, e in enumerate(exercicios):
                    if not isinstance(e, dict):
                        continue
                    n = (e.get("nome") or "").strip().lower()
                    if n and (nome_av in n or n in nome_av):
                        alvo = i
                        break
                if alvo is None:
                    carga_txt = f" a {avulso['carga_kg']:g}kg" if avulso.get("carga_kg") else ""
                    return _persistir(
                        f"*{avulso['nome']}* não está no treino de hoje. "
                        f"Quer registrar {avulso['series']}x{avulso['reps']}{carga_txt} só pra hoje?\n\n"
                        "1️⃣ Sim, registrar (pontual)\n"
                        "2️⃣ Deixa pra lá",
                        {
                            "tipo": "exercicio_fora_treino",
                            "guiado": _estado_guiado(),
                            "avulso": avulso,
                            "criado_em": datetime.utcnow().isoformat(),
                        },
                    )
                nome_alvo = (exercicios[alvo].get("nome") or "exercício").strip()
                if alvo == idx:
                    return _persistir(f"Você já está no *{nome_alvo}* — manda a série (ex: 8 x80).", _estado_guiado())
                if alvo not in ordem:
                    return _persistir(f"*{nome_alvo}* você já fez hoje. Manda a série do atual, ou *próximo*/*pular*.", _estado_guiado())
                return _persistir(
                    f"*{nome_alvo}* é o exercício n°{alvo + 1} do treino. Vai fazer agora?\n\n"
                    "1️⃣ SIM, vou fazer agora\n"
                    "2️⃣ NÃO, sigo a ordem",
                    {
                        "tipo": "jump_exercicio",
                        "guiado": _estado_guiado(),
                        "alvo_idx": alvo,
                        "criado_em": datetime.utcnow().isoformat(),
                    },
                )
            aq_prescrito = ex_atual.get("aquecimento") or 0
            aq_no_buffer = sum(1 for s in buffer if s.get("is_aquecimento"))
            if not parsed["is_aquecimento"] and aq_no_buffer < aq_prescrito:
                parsed["is_aquecimento"] = True
            buffer.append(parsed)
            buffers[str(idx)] = buffer
            validas = [s for s in buffer if not s.get("is_aquecimento")]
            sv_prescrito = ex_atual.get("series_validas") or 0
            peso_fmt = f"{parsed['carga_kg']:g}"
            if parsed["is_aquecimento"]:
                ack = f"Aquecimento: {parsed['repeticoes']} reps × {peso_fmt}kg ✅"
            else:
                ack = f"Válida {len(validas)}/{sv_prescrito}: {parsed['repeticoes']} reps × {peso_fmt}kg ✅"
            if sv_prescrito and len(validas) >= sv_prescrito:
                ex_nome = (ex_atual.get("nome") or "exercício").strip()
                _registrar_guiado(ex_atual, buffer, nome_treino)
                buffers.pop(str(idx), None)
                ordem.pop(0)
                if not ordem:
                    return _finalizar(f"{ack} — {ex_nome} registrado!\n\n")
                return _persistir(f"{ack} — {ex_nome} registrado!\n\n" + _anunciar_exercicio_guiado(exercicios, ordem[0]), _estado_guiado())
            return _persistir(ack, _estado_guiado())

    # Handler: exercicio fora do treino durante o guiado (E4 c1: pontual)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "exercicio_fora_treino":
        estado = conversa.estado_pendente
        guiado = estado.get("guiado") or {}
        avulso = estado.get("avulso") or {}
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])

        def _persistir_eft(reply_text: str, novo_estado):
            conversa.estado_pendente = novo_estado
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply_text, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply_text

        g_plano_id = guiado.get("plano_id")
        g_nome_treino = guiado.get("treino_nome", "")
        g_ordem = guiado.get("ordem", [])
        g_idx = g_ordem[0] if g_ordem else 0
        g_plano = db.query(Treino).filter(Treino.id == g_plano_id).first() if g_plano_id else None
        g_exs = _exercicios_do_dia(g_plano, g_nome_treino) if g_plano else None
        g_ex_nome = (g_exs[g_idx].get("nome") or "exercício").strip() if g_exs and g_idx < len(g_exs) else "exercício"

        if stripped == "1" or stripped_lower in {"sim", "pontual", "registrar"}:
            posicao = exercicio_service.get_proxima_posicao(user.id, sessao_data, db)
            exercicio_service.registrar(
                user_id=user.id,
                sessao_data=sessao_data,
                posicao=posicao,
                exercicio_display=avulso.get("nome", "exercício"),
                series=avulso.get("series") or 1,
                repeticoes=avulso.get("reps") or 0,
                carga_kg=avulso.get("carga_kg") or 0,
                db=db,
                treino_nome=g_nome_treino,
                series_detalhe=None,
            )
            return _persistir_eft(
                f"*{avulso.get('nome', 'exercício')}* registrado (pontual) ✅\n"
                f"Voltando pro *{g_ex_nome}* — manda a próxima série.",
                guiado,
            )
        elif stripped == "2" or stripped_lower in {"nao", "não", "deixa", "deixa pra la", "deixa pra lá", "cancelar"}:
            return _persistir_eft(
                f"Beleza, ignorei. Voltando pro *{g_ex_nome}* — manda a série.",
                guiado,
            )
        elif _eh_comando_reservado(stripped_lower):
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        else:
            return _persistir_eft(
                "Responda *1* (registrar pontual) ou *2* (deixa pra lá).",
                estado,
            )

    # Handler: pulo pra um exercicio do dia (E4: "vai fazer agora?")
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "jump_exercicio":
        estado = conversa.estado_pendente
        guiado = estado.get("guiado") or {}
        alvo_idx = estado.get("alvo_idx")
        mensagens_tmp: list[dict] = list(conversa.mensagens or [])

        def _persistir_jump(reply_text: str, novo_estado):
            conversa.estado_pendente = novo_estado
            mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
            mensagens_tmp.append({"role": "assistant", "content": reply_text, "timestamp": datetime.utcnow().isoformat()})
            conversa.mensagens = mensagens_tmp
            db.add(conversa)
            db.commit()
            return reply_text

        g_plano_id = guiado.get("plano_id")
        g_nome_treino = guiado.get("treino_nome", "")
        g_ordem = list(guiado.get("ordem", []))
        g_plano = db.query(Treino).filter(Treino.id == g_plano_id).first() if g_plano_id else None
        g_exs = _exercicios_do_dia(g_plano, g_nome_treino) if g_plano else None
        atual_idx = g_ordem[0] if g_ordem else 0
        atual_nome = (g_exs[atual_idx].get("nome") or "exercício").strip() if g_exs and atual_idx < len(g_exs) else "exercício"

        if stripped == "1" or stripped_lower in {"sim", "agora", "vou fazer agora"}:
            if not g_exs or not g_ordem:
                return _persistir_jump("Treino concluído 💪", None)
            if alvo_idx in g_ordem:
                g_ordem.remove(alvo_idx)
                g_ordem.insert(0, alvo_idx)
            return _persistir_jump(
                "Bora! 💪\n\n" + _anunciar_exercicio_guiado(g_exs, g_ordem[0]),
                {**guiado, "ordem": g_ordem},
            )
        elif stripped == "2" or stripped_lower in {"nao", "não", "ordem", "seguir", "seguir a ordem"}:
            return _persistir_jump(
                f"Beleza, seguindo a ordem. Você está no *{atual_nome}* — manda a série.",
                guiado,
            )
        elif _eh_comando_reservado(stripped_lower):
            conversa.estado_pendente = None
            db.add(conversa)
            db.flush()
        else:
            return _persistir_jump(
                "Responda *1* (SIM, vou fazer agora) ou *2* (NÃO, sigo a ordem).",
                estado,
            )

    _m = re.match(r'^treinar(?:\s+(.+))?$', stripped_lower)
    if _m:
        nome_capturado = _m.group(1)
        if nome_capturado:
            nome_busca = stripped[len("treinar"):].strip()
            treinos_lista = treino_service.listar_treinos(user.id, db)
            matches_dia = []
            for plano in treinos_lista:
                dia = _casar_dia(nome_busca, _dias_do_plano(plano))
                if dia:
                    matches_dia.append((plano, dia))
            matches_plano = [
                p for p in treinos_lista
                if nome_busca.lower() in _nome_display_treino(p).lower()
                or _nome_display_treino(p).lower() in nome_busca.lower()
            ]
            if len(matches_dia) == 1:
                plano, dia = matches_dia[0]
                reply = _apresentar_ou_iniciar(dia, plano.id)
            elif len(matches_dia) >= 2:
                plano_lista = [p for p, _ in matches_dia]
                plano_labels = [_nome_display_treino(p) for p in plano_lista]
                linhas = [f"Você tem *{nome_busca}* em mais de um plano. Qual deles?\n"]
                for i, lb in enumerate(plano_labels, 1):
                    linhas.append(f"*{i}.* {lb}")
                linhas.append("\nResponda com o *número* ou o *nome* (ou *cancelar*).")
                reply = "\n".join(linhas)
                conversa.estado_pendente = {
                    "tipo": "escolhendo_plano",
                    "plano_ids": [p.id for p in plano_lista],
                    "plano_labels": plano_labels,
                    "criado_em": datetime.utcnow().isoformat(),
                }
            elif len(matches_plano) == 1:
                reply = _mostrar_dias_plano(matches_plano[0])
            elif len(matches_plano) >= 2:
                plano_lista = matches_plano[:10]
                plano_labels = [_nome_display_treino(p) for p in plano_lista]
                linhas = ["Achei mais de um plano com esse nome. Qual deles?\n"]
                for i, lb in enumerate(plano_labels, 1):
                    linhas.append(f"*{i}.* {lb}")
                linhas.append("\nResponda com o *número* ou o *nome* (ou *cancelar*).")
                reply = "\n".join(linhas)
                conversa.estado_pendente = {
                    "tipo": "escolhendo_plano",
                    "plano_ids": [p.id for p in plano_lista],
                    "plano_labels": plano_labels,
                    "criado_em": datetime.utcnow().isoformat(),
                }
            else:
                conversa.estado_pendente = {
                    "tipo": "treinar_nao_casou",
                    "nome": nome_busca,
                    "criado_em": datetime.utcnow().isoformat(),
                }
                reply = (
                    f"Não achei nenhum treino ou plano chamado *{nome_busca}*. O que você quer fazer?\n\n"
                    "1️⃣ Treinar assim mesmo (eu registro os exercícios que você mandar)\n"
                    "2️⃣ Importar um treino que já tenho\n"
                    "3️⃣ Criar um plano do zero\n"
                    "4️⃣ Cancelar"
                )
        else:
            treinos_lista = treino_service.listar_treinos(user.id, db)
            if treinos_lista:
                if len(treinos_lista) == 1:
                    plano = treinos_lista[0]
                    dias_nomes = _dias_do_plano(plano)
                    if dias_nomes:
                        linhas = [f"Plano: *{_nome_display_treino(plano)}*\n", "Qual treino você vai fazer?\n"]
                        for i, dn in enumerate(dias_nomes, 1):
                            linhas.append(f"*{i}.* {dn}")
                        linhas.append("\nResponda com o *número* ou o *nome* (ou *cancelar*).")
                        reply = "\n".join(linhas)
                        conversa.estado_pendente = {
                            "tipo": "escolhendo_treino",
                            "dias_nomes": dias_nomes,
                            "plano_id": plano.id,
                            "criado_em": datetime.utcnow().isoformat(),
                        }
                    else:
                        reply = (
                            f"O plano *{_nome_display_treino(plano)}* ainda não tem treinos separados por dia.\n"
                            "Me diz o *nome do treino* que você vai fazer hoje (ex: 'Peito A') e eu inicio a sessão. Ou *cancelar*."
                        )
                        conversa.estado_pendente = {
                            "tipo": "escolhendo_treino",
                            "dias_nomes": [],
                            "plano_id": plano.id,
                            "criado_em": datetime.utcnow().isoformat(),
                        }
                else:
                    plano_lista = treinos_lista[:10]
                    plano_labels = [_nome_display_treino(t) for t in plano_lista]
                    linhas = ["Você tem mais de um plano. Qual deles?\n"]
                    for i, lb in enumerate(plano_labels, 1):
                        linhas.append(f"*{i}.* {lb}")
                    linhas.append("\nResponda com o *número* ou o *nome* (ou *cancelar*).")
                    reply = "\n".join(linhas)
                    conversa.estado_pendente = {
                        "tipo": "escolhendo_plano",
                        "plano_ids": [t.id for t in plano_lista],
                        "plano_labels": plano_labels,
                        "criado_em": datetime.utcnow().isoformat(),
                    }
            else:
                # Lista vazia → menu de 3 opções
                conversa.estado_pendente = {
                    "tipo": "lista_vazia_treino",
                    "criado_em": datetime.utcnow().isoformat(),
                }
                reply = (
                    "Você ainda não tem treinos salvos. Vamos criar um?\n\n"
                    "1️⃣ Importar treino que já tenho (do meu personal/PDF/papel)\n"
                    "2️⃣ Criar treino do zero (eu te oriento e monto)\n"
                    "3️⃣ Cancelar"
                )
        mensagens_tmp = list(conversa.mensagens or [])
        mensagens_tmp.append({"role": "user", "content": stripped, "timestamp": datetime.utcnow().isoformat()})
        mensagens_tmp.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens_tmp
        db.add(conversa)
        db.commit()
        return reply

    # 0. /menu command and menu item selection (intercept before everything else)
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

    # 3.5 Fluxo de exclusão de registro — intercepta antes do fluxo geral (não chama a IA)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "apagando_registro":
        reply = await _handle_apagar_registro(conversa, message_text, user, db)
        mensagens.append({"role": "user", "content": stored_text, "timestamp": datetime.utcnow().isoformat()})
        mensagens.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens
        db.add(conversa)
        db.commit()
        return reply

    # 3.6 Fluxo de edição de registro — intercepta antes do fluxo geral (não chama a IA)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "editando_registro":
        reply = await _handle_editar_registro(conversa, message_text, user, db)
        mensagens.append({"role": "user", "content": stored_text, "timestamp": datetime.utcnow().isoformat()})
        mensagens.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens
        db.add(conversa)
        db.commit()
        return reply

    # 3.7 Fluxo de substituição de dieta — intercepta pergunta hoje-vs-plano (não chama a IA)
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "substituicao_dieta":
        reply = _handle_substituicao_dieta(conversa, message_text, user, db)
        mensagens.append({"role": "user", "content": stored_text, "timestamp": datetime.utcnow().isoformat()})
        mensagens.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        conversa.mensagens = mensagens
        db.add(conversa)
        db.commit()
        return reply

    # 3.8 Confirmar registro no histórico corporal após variação grande de peso no perfil
    if conversa.estado_pendente and conversa.estado_pendente.get("tipo") == "confirmar_historico_medida":
        reply = await _handle_confirmar_historico_medida(conversa, message_text, user, db)
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
    ctx_treinos = _treinos_context_str(user.id, db)

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

    partes_ctx = [p for p in [ctx_sessao, ctx_nutricao, ctx_habitos, ctx_treinos, ctx_confirmacao, ctx_coleta] if p]
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
        exclusao_iniciada_msg: str | None = None
        edicao_iniciada_msg: str | None = None
        while response.stop_reason == "tool_use" and tool_iterations < 5:
            tool_iterations += 1
            tool_results = []
            coleta_iniciada_msg = None
            exclusao_iniciada_msg = None
            edicao_iniciada_msg = None

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
                    result = await _process_tool_cadastrar_treino(block.input, user, db)
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
                elif block.name == "iniciar_exclusao_registro":
                    alvo = block.input.get("alvo")
                    if alvo == "treino":
                        exclusao_iniciada_msg = _iniciar_exclusao_treino(user, conversa, db)
                        result = "EXCLUSAO_INICIADA"
                    elif alvo == "dieta":
                        exclusao_iniciada_msg = _iniciar_exclusao_dieta(user, conversa, db)
                        result = "EXCLUSAO_INICIADA"
                    elif alvo == "suplemento":
                        exclusao_iniciada_msg = _iniciar_exclusao_suplemento(user, conversa, db)
                        result = "EXCLUSAO_INICIADA"
                    else:
                        exclusao_iniciada_msg = (
                            "Por enquanto só consigo apagar *treinos*, *dietas* e *suplementos*. "
                            "Exclusão de remédio chega em breve! 🙂"
                        )
                        result = "EXCLUSAO_TIPO_NAO_SUPORTADO"
                elif block.name == "iniciar_edicao_registro":
                    alvo = block.input.get("alvo")
                    if alvo == "suplemento":
                        edicao_iniciada_msg = _iniciar_edicao_suplemento(user, conversa, db)
                        result = "EDICAO_INICIADA"
                    elif alvo == "treino":
                        edicao_iniciada_msg = _iniciar_edicao_treino(user, conversa, db)
                        result = "EDICAO_INICIADA"
                    elif alvo == "dieta":
                        edicao_iniciada_msg = (
                            "Para ajustar sua dieta, é só me dizer qual alimento quer trocar — "
                            "ex: 'troca o arroz por batata'. Eu recalculo as calorias e macros pra você. 🥗"
                        )
                        result = "EDICAO_DIETA_REDIRECIONADO"
                    else:
                        edicao_iniciada_msg = (
                            "Por enquanto só edito *suplementos*, *treinos* e *dieta* "
                            "(essa última trocando alimentos direto na conversa). 🙂"
                        )
                        result = "EDICAO_TIPO_NAO_SUPORTADO"
                elif block.name == "substituir_alimento":
                    origem_pt = block.input.get("origem_pt", "")
                    origem_en = block.input.get("origem_en", "")
                    destino_pt = block.input.get("destino_pt", "")
                    destino_en = block.input.get("destino_en", "")
                    gramas_origem = float(block.input.get("gramas_origem", 100))
                    origem_obj, _ = await _resolver_alimento(origem_pt, origem_en, db)
                    if origem_obj is None:
                        result = (
                            f"ERRO_ALIMENTO_NAO_ENCONTRADO: origem '{origem_pt}' / '{origem_en}' "
                            "nao encontrada em nenhuma base"
                        )
                    else:
                        destino_obj, _ = await _resolver_alimento(destino_pt, destino_en, db)
                        if destino_obj is None:
                            result = (
                                f"ERRO_ALIMENTO_NAO_ENCONTRADO: destino '{destino_pt}' / '{destino_en}' "
                                "nao encontrado em nenhuma base"
                            )
                        else:
                            res = _calcular_substituicao_normed(
                                _normar_alimento(origem_obj), gramas_origem, _normar_alimento(destino_obj)
                            )
                            if res["erro"]:
                                result = f"ERRO: {res['erro']}"
                            else:
                                resumo = _fmt_substituicao(res)
                                descricao = (
                                    f"{res['origem']['nome']} {res['origem']['gramas']}g"
                                    f" -> {res['destino']['nome']} {res['destino']['gramas']}g"
                                )
                                conversa.estado_pendente = {
                                    "tipo": "substituicao_dieta",
                                    "etapa": "aguardando_escopo",
                                    "descricao": descricao,
                                    "resumo_macros": resumo,
                                }
                                result = (
                                    f"SUBSTITUICAO_CALCULADA: apresente os números abaixo ao usuário "
                                    f"e PERGUNTE se a troca é só para hoje ou para salvar no plano alimentar. "
                                    f"Números: {resumo}"
                                )
                elif block.name == "consultar_historico_treino":
                    hist = exercicio_service.get_historico_recente(user.id, db, semanas=4)
                    result = _fmt_historico_treino(hist)
                elif block.name == "editar_perfil":
                    args = block.input or {}
                    peso_novo = args.get("peso_kg")
                    nivel_novo = args.get("nivel_experiencia")
                    if peso_novo is None and nivel_novo is None:
                        result = "Nada para atualizar — informe peso_kg ou nivel_experiencia."
                    else:
                        partes_result = []
                        if peso_novo is not None:
                            if peso_novo < 30 or peso_novo > 300:
                                partes_result.append(f"Peso fora do intervalo (30-300kg): {peso_novo}")
                            else:
                                info = perfil_service.atualizar_peso_perfil(user.id, float(peso_novo), db)
                                partes_result.append(f"Peso atualizado: {info['anterior']}kg → {info['novo']}kg")
                                if info["diff"] is not None and info["diff"] >= 5.0:
                                    conversa.estado_pendente = {
                                        "tipo": "confirmar_historico_medida",
                                        "peso_kg": float(peso_novo),
                                        "anterior": info["anterior"],
                                        "criado_em": datetime.utcnow().isoformat(),
                                    }
                                    db.add(conversa)
                                    partes_result.append(
                                        f"VARIACAO_GRANDE: {info['diff']:.1f}kg de diferença. "
                                        f"PERGUNTE ao usuário se quer registrar como nova medição no histórico corporal (sim/não)."
                                    )
                        if nivel_novo is not None:
                            info_n = perfil_service.atualizar_nivel_perfil(user.id, nivel_novo, db)
                            if "erro" in info_n:
                                partes_result.append(info_n["erro"])
                            else:
                                partes_result.append(f"Nível atualizado: {info_n['anterior']} → {info_n['novo']}")
                        result = " | ".join(partes_result)
                else:
                    result = "Ferramenta desconhecida."
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            # Se a coleta, exclusão ou edição foi iniciada, usa a mensagem pré-formatada sem chamar Claude novamente
            if coleta_iniciada_msg or exclusao_iniciada_msg or edicao_iniciada_msg:
                reply = coleta_iniciada_msg or exclusao_iniciada_msg or edicao_iniciada_msg
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

        if not (coleta_iniciada_msg or exclusao_iniciada_msg or edicao_iniciada_msg):
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

    if _contains_keywords(reply, DIETA_KEYWORDS):
        db.add(Dieta(user_id=user.id, conteudo={"texto": reply, "gerado_em": datetime.utcnow().isoformat()}))

    db.commit()
    return reply
