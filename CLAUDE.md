# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# CONTEXTO DO PROJETO — Evolution Fit AI (atualizado em 26/05/2026)

## O QUE É

SaaS de fitness via WhatsApp com IA. O usuário envia mensagens para o número **+55 11 5304-3378**; o bot responde como personal trainer + nutricionista ("Evo"), gerenciando treinos, dietas, medidas, hábitos e evolução físicos. Receita por assinatura recorrente (trimestral/anual), ativada automaticamente via webhook de compra.

**Planos:** Trimestral R$ 29,99/mês · Anual R$ 19,99/mês

---

## STACK REAL

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 (Dockerfile) |
| Framework | FastAPI 0.115.5 + Uvicorn |
| ORM / Migrations | SQLAlchemy 2.0.36 + Alembic 1.14.0 (HEAD = migration 012) |
| Banco | PostgreSQL — **produção: Render free tier** (DB local no `.env` é cópia parada) |
| WhatsApp | **Meta Cloud API** (graph.facebook.com v19.0) |
| Pagamento | **Kiwify** — integração implementada em `kiwify.py`; router Hotmart removido (27/05) |
| Hospedagem | **Render free tier**, Docker, deploy automático no push `master` |
| IA | **claude-sonnet-4-6** (padrão em `config.py`; sobreposto por env `CLAUDE_MODEL`) |
| SDK Anthropic | 0.40.0, com prompt caching ephemeral (TTL 5 min) |
| Áudio | OpenAI Whisper (`whisper-1`) — **DESATIVADO**, aguardando `OPENAI_API_KEY` |
| Scheduler | APScheduler 3.10.4 in-process (lembrete das 20h **comentado/desativado** desde 25/05) |
| Geração de imagem | matplotlib + Pillow (card de evolução PNG, item 10 do menu) |
| Parsing de arquivos | pandas + openpyxl (Excel) / pypdf (PDF) |

---

## TAMANHO ATUAL

**58 arquivos `.py`** · **~5.700 linhas de código**

Estrutura: `main.py` + `app/` (routers, services, models, schemas, middleware) + `alembic/versions/` (12 migrations) + `alembic/seeds/` (seed TACO) + `scripts/`.

---

## FUNCIONALIDADES PRONTAS E FUNCIONANDO

**Infraestrutura / plataforma**
- Webhook WhatsApp recebe texto, imagem, documento (Excel/PDF) e áudio (áudio: recebido, porém responde "só texto/fotos" até `OPENAI_API_KEY` ser configurada)
- Dedup atômico de mensagens (tabela `mensagens_processadas`, migration 010)
- Resposta HTTP 200 imediata + processamento em BackgroundTask (evita reenvio da Meta)
- Assinatura HMAC-SHA256 do webhook (`META_APP_SECRET`)
- Webhook Kiwify: compra aprovada → ativa assinatura + envia boas-vindas; cancelamento → desativa
- Ativação manual de assinatura via `POST /admin/subscriptions/grant`
- Landing page servida em `/landing` (`static/landing/index.html`)
- API Admin completa (usuários, histórico, evolução, medidas, refeições, metas)

**Menu e fluxo de conversa**
- `/menu` com 12 opções em 4 categorias (Treino, Nutrição, Medidas & Corpo, Hábitos Diários)
- Máquina de estados multi-turno (`estado_pendente` em `Conversa`)
- Perfil persistente do usuário (`perfis_fitness`, migrations 008–009)

**Treino**
- Item 1: criação personalizada com coleta estruturada (9 perguntas → 1 chamada Claude → salva)
- Item 2: cadastro de treino externo (personal/PDF/Excel → `cadastrar_treino_proprio`)
- Item 3: registro de cargas/séries por sessão, cálculo de 1RM (Epley/Brzycki/Lander)
- Item 4: evolução de força (1RM por exercício, gráfico histórico)
- Contexto de treinos injetado no prompt (resumo do treino mais recente + títulos anteriores)
- Apagar treinos via chat (lista numerada, múltiplos, "todos", confirmação)
- Editar treino via chat

**Nutrição**
- Item 5: criação de dieta personalizada (protocolo Mifflin-St Jeor, déficit/superávit/manutenção, plano 7 dias)
- Item 6: cadastro de dieta externa (nutricionista/PDF/Excel → `cadastrar_dieta_propria`)
- Item 7: análise de refeição por foto (macros estimados + balanço do dia; limite 6/dia)
- Apagar dietas via chat
- Dados corporais opcionais mas ativamente solicitados na criação de dieta

**Medidas & Corpo**
- Item 8: registro de peso e medidas corporais (histórico comparativo)
- Item 9: análise de composição corporal (fluxo de 3 fotos + Claude Vision → % gordura estimada)
- Item 10: painel de evolução em PNG (card dark-theme com logo)

**Hábitos Diários**
- Item 11: registro de água (ml acumulado) e suplementos (marcar como tomados)
- Item 12: acompanhamento de dias sem álcool / sem fumar (streaks)
- Cadastro e edição de lista de suplementos
- Apagar suplementos da lista via chat
- Rodapé do menu exibe contadores do dia (água, streaks, suplementos)
- Lembrete automático das 20h: **DESATIVADO** (código comentado) — motivo: Render free dorme + regra de opt-in estrito

---

## PENDÊNCIAS PRINCIPAIS

**Imediatas (pré-lançamento)**
1. **Kiwify** — configurar produto na plataforma, obter tokens de webhook e preencher `KIWIFY_WEBHOOK_TOKEN_ANUAL/TRIMESTRAL` + `PAYMENT_LINK_*` no Render
2. **OpenAI API Key** — necessário para reativar transcrição de áudio (Whisper)
3. **Edição de dieta** via chat — ✅ CONCLUÍDA 26/05. Edição inteligente via tool `substituir_alimento` — busca TACO→USDA (fallback), equivalência calórica, fórmula Atwater quando falta kcal, desambiguação de corte (ex: "frango" → pergunta qual corte), e pergunta "só hoje vs salvar no plano" (anexa ao `texto_original`). ⚠️ Resíduo cosmético: aviso "dieta em breve" em `iniciar_edicao_registro` tool description — ✅ Resíduo cosmético removido 27/05: descrição e dispatch de `iniciar_edicao_registro` corrigidos — dieta redireciona para `substituir_alimento` sem mensagem "em breve".
4. **Limpeza Hotmart ✅ CONCLUÍDA 27/05** — removidos `app/routers/hotmart.py`, `app/schemas/hotmart.py`, `OFFER_PLAN_MAP`, `map_offer_to_plan()`, `validate_hotmart_webhook()`, import+include em `main.py`, vars `HOTMART_*` de `config.py` e `render.yaml`. Adicionado `extra="ignore"` no Settings (tolera vars órfãs no `.env`/Render). NÃO removida a coluna `hotmart_transaction_id` (reaproveitada pelo Kiwify para dedup). Em produção.

**Próximo ciclo de desenvolvimento**
5. **Base nutricional TACO** — model `AlimentoTACO` + migration + script de importação (`scripts/importar_taco.py`) — plano detalhado adiante neste arquivo
6. **Coleta estruturada para dieta** (análogo ao fluxo de treino)
7. **Reaproveitamento de perfil** no 2º treino em diante (não repetir 9 perguntas)
8. **Sistema de lembretes opt-in** — bloqueado: requer scheduler confiável (Render pago ou cron externo); entidade Remédio também depende disso

**Operacional / lançamento**
9. Render free "dorme" (~50s na 1ª mensagem) — avaliar upgrade antes do lançamento público
10. Teste de compra ponta-a-ponta com número que nunca comprou
11. Configurar alerta de saldo baixo na Anthropic (bot parou uma vez por créditos zerados)
12. Usuária de teste **Maria** — confirmada ativa (usando normalmente)

---

## VARIÁVEIS DE AMBIENTE — STATUS

| Variável | Status |
|---|---|
| `DATABASE_URL`, `ANTHROPIC_API_KEY`, todas as `META_*`, `ADMIN_API_KEY` | ✅ configuradas no Render (`ADMIN_API_KEY` rotacionada 28/05) |
| `OPENAI_API_KEY` | ⚠️ pendente (áudio desativado) |
| `KIWIFY_WEBHOOK_TOKEN_*`, `PAYMENT_LINK_*` | ⚠️ pendente (produto não configurado na Kiwify ainda) |
| `HOTMART_*` | ✅ removidas do código (27/05) — ✅ apagadas do painel Render (28/05) — ✅ apagadas do `.env` local (28/05) |

---

## Commands

```bash
# Dev server (porta 8001) — NÃO use --reload no Windows (deadlock de workers)
uvicorn main:app --port 8001

# Matar servidor (Windows — use Python, não kill nem taskkill)
python -c "import os; os.kill(<PID>, 9)"

# Aplicar migrations
alembic upgrade head

# Criar nova migration após alterar models
alembic revision --autogenerate -m "descricao"

# Ativar assinatura de teste localmente (nunca usar em produção)
DATABASE_URL=<url> python scripts/activate_test.py <telefone> [anual|trimestral]

# Dependências
pip install -r requirements.txt
```

O arquivo `.env` é obrigatório na raiz. Variáveis obrigatórias: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `META_PHONE_NUMBER_ID`, `META_ACCESS_TOKEN`, `META_WEBHOOK_VERIFY_TOKEN`, `ADMIN_API_KEY`. Opcionais: `OPENAI_API_KEY` (Whisper), `META_APP_SECRET` (validação de assinatura, recomendado em produção), `CLAUDE_MODEL` (default `claude-sonnet-4-6`).

**NUNCA** use Docker ou PowerShell — use apenas Bash.

---

## Arquitetura geral

SaaS de fitness no WhatsApp: usuário → WhatsApp → Meta Cloud API → webhook → FastAPI → Claude → resposta via Meta Cloud API.

### Fluxo principal (mensagem recebida)

```
GET  /webhook/whatsapp  → verificação do webhook Meta (hub.challenge)
POST /webhook/whatsapp
  → validar X-Hub-Signature-256 (HMAC-SHA256 com META_APP_SECRET)
  → dedup (ultima_mensagem_id)
  → check_active_subscription()
  → [se áudio] responde "só texto e fotos por enquanto" e retorna (transcrição desativada)
  → [se imagem] media_service.get_media_bytes(media_id) → image_b64
  → [se documento Excel/PDF] media_service.get_media_bytes(media_id) → file_reader.extrair_texto() → injeta em text com prefixo "[Arquivo recebido: NOME]"
  → claude_service.process_message()
  → whatsapp_service.send_message()
```

Todos os handlers retornam HTTP 200 mesmo em erro (sem retentativas da Meta).

### Payload Meta Cloud API (mensagem recebida)

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "contacts": [{"profile": {"name": "Nome"}, "wa_id": "5511999999999"}],
        "messages": [{
          "from": "5511999999999",
          "id": "wamid.xxx",
          "type": "text",
          "text": {"body": "mensagem"}
        }]
      }
    }]
  }]
}
```

Tipos suportados: `text`, `image`, `audio`, `document`. Status updates (sem `messages[]`) são ignorados via `is_message_event()`.

### Fluxo Hotmart (compra aprovada)

```
POST /webhook/hotmart
  → HMAC-SHA256(body, HOTMART_WEBHOOK_SECRET)
  → event = "PURCHASE_APPROVED"
  → subscription_service.activate_subscription()
  → whatsapp_service.send_welcome_message()
```

Deduplicação por `hotmart_transaction_id`.

---

## Claude AI (`app/services/claude_service.py`)

- Modelo: `settings.CLAUDE_MODEL` (default `claude-sonnet-4-6`)
- **Prompt caching:** system prompt com `cache_control: {"type": "ephemeral"}` — TTL 5 min
- Histórico em `Conversa.mensagens` (JSON, máximo 20 mensagens por chamada)
- **`estado_pendente`** (JSON) — máquina de estados multi-turno:

| Tipo | Quando ativo |
|------|-------------|
| `confirmar_exercicio` | Variação de carga >20% aguarda confirmação |
| `confirmar_refeicao` | Análise de foto de alimento aguarda "sim/não" |
| `coleta_fotos` | Coleta de 3 fotos para análise corporal em andamento |
| `aguardando_menu` | Usuário chamou /menu, aguarda número 1–12 |
| `criando_treino` | Coleta estruturada de 9 perguntas para criar treino personalizado |

### Ferramentas Claude (TOOLS — 15 tools)

| Tool | Ação |
|------|------|
| `registrar_exercicio` | Salva série/reps/carga; calcula 1RM; detecta variação >20% |
| `registrar_medidas` | Salva medidas corporais |
| `registrar_analise_foto` | Persiste resultado de análise corporal (% gordura) |
| `analisar_refeicao` | Extrai macros de foto de alimento; inicia confirmação |
| `cadastrar_dieta_propria` | Salva dieta externa como MetaNutricional |
| `cadastrar_treino_proprio` | Salva treino externo como Treino (`origem: "proprio"`) |
| `iniciar_coleta_fotos_corpo` | Inicia fluxo de coleta de 3 fotos |
| `registrar_agua` | Acumula consumo de água do dia (ml) |
| `registrar_habito_fumar` | Registra fumou/não-fumou; mantém contador de dias sem fumar |
| `registrar_habito_alcool` | Registra bebeu/não-bebeu álcool; mantém contador de dias sem beber |
| `registrar_tomei_suplementos` | Marca suplementos como tomados no dia |
| `registrar_suplementos_usuario` | Salva lista de suplementos para personalizar lembretes |
| `substituir_alimento` | Calcula equivalência calórica entre dois alimentos via TACO (só leitura — não persiste) |
| `consultar_historico_treino` | Retorna histórico real das últimas 4 semanas por exercício (3 últimas execuções + carga/reps/1RM); lista WhatsApp |
| `TOOLS_ANALISE_CORPO` | Subset com só `registrar_analise_foto` — usado na chamada de 3 fotos |

### /menu command

`/menu` → lista 12 opções em 4 categorias (Treino, Nutrição, Medidas & Corpo, Hábitos Diários) → usuário responde número → ação. Item 10 gera PNG e envia via `send_image`.  
O menu mostra contadores de hábitos do dia no rodapé quando há dados (água, dias sem fumar/beber, suplementos).

**Opções do menu:**
- **Treino:** 1 Criar treino personalizado · 2 Cadastrar treino do personal · 3 Registrar cargas/séries · 4 Evolução de força (1RM)
- **Nutrição:** 5 Criar dieta personalizada · 6 Cadastrar dieta do nutricionista · 7 Analisar refeição por foto
- **Medidas & Corpo:** 8 Registrar peso e medidas · 9 Análise de composição corporal (fotos) · 10 Painel de evolução 📊
- **Hábitos Diários:** 11 Registrar água e suplementos · 12 Acompanhar dias sem álcool / sem fumar

**Tipos de treino suportados (item 1 e `cadastrar_treino_proprio`):** musculação/academia, calistenia, yoga, pilates, corrida/endurance, treino híbrido, treino funcional, CrossFit, mobilidade — adapta exercícios e equipamentos ao tipo e local informados (nem todo treino é em academia).

### Fluxo de imagens

- **Foto de alimento** → `analisar_refeicao` → tabela nutricional → confirmar registro
- **Foto de corpo (1ª)** → `iniciar_coleta_fotos_corpo` → armazena em `estado_pendente`
- **Foto de corpo (2ª)** → interceptada por `_handle_coleta_fotos` sem chamar Claude
- **Foto de corpo (3ª)** → `_analisar_tres_fotos` (Claude Vision + `TOOLS_ANALISE_CORPO`)

### Fluxo de áudio

- `payload.is_audio()` detecta `type == "audio"` no payload Meta
- Download via `media_service.get_media_bytes(media_id)` — dois GETs à Graph API
- Transcrição via OpenAI Whisper (`whisper-1`, `language="pt"`)
- Suporte a: OGG (padrão WhatsApp), MP3, MP4, WAV, WebM
- Bot envia `🎤 _Áudio transcrito:_ "..."` antes de responder
- Texto transcrito entra no fluxo normal (tools, menu, confirmações, etc.)
- `OPENAI_API_KEY` vazia → áudio ignorado silenciosamente

### Fluxo de documentos (Excel / PDF)

- `payload.is_document()` detecta `type == "document"` no payload Meta
- Download via `media_service.get_media_bytes(media_id)` (mesmo mecanismo das imagens)
- Extração de texto: `file_reader.extrair_texto(bytes, mimetype, filename)` — roteia para `ler_excel` ou `ler_pdf`
  - **Excel (.xlsx / .xls):** `pandas.ExcelFile` com engine `openpyxl`; itera abas, serializa como texto tabular
  - **PDF:** `pypdf.PdfReader`; extrai texto página a página
  - **Imagens enviadas como documento:** não extraídas aqui — devem ser enviadas como tipo `image` para usar Claude Vision
- Texto extraído é injetado em `text` com prefixo `[Arquivo recebido: NOME]\n\n<conteúdo>`
- O fluxo normal de `process_message` processa o texto: Claude detecta treino/dieta externa e chama `cadastrar_treino_proprio` / `cadastrar_dieta_propria`
- Formato não suportado → mensagem orientando o usuário a usar PDF ou Excel

### Criação de dieta — dados de composição corporal

Ao criar dieta (item 5 ou via chat), o Evo solicita ativamente medidas corporais (cintura, quadril, braço, coxa) e análise de composição corporal estimada por foto (% gordura). Esses dados são **opcionais**, mas aumentam a precisão do cálculo de calorias e macros — o peso isolado não distingue massa magra de gordura. Se o usuário já tiver medidas ou fotos de composição no contexto, o Evo usa esses valores automaticamente.

### Integração USDA FoodData Central

- **Arquivo:** `app/services/usda_service.py`
- **Função:** `buscar_alimento_usda(termo, api_key) -> list[dict]` — async, `httpx.AsyncClient(timeout=15)`, `dataType=["Foundation","SR Legacy"]`, `pageSize=5`
- **Macros:** retorna por 100g (mesmo padrão TACO); campos `None` quando nutriente não disponível
- **Atwater fallback:** se `kcal` vier `None` mas `proteina_g`, `carboidrato_g` e `lipideos_g` estiverem presentes, calcula `round(p*4 + c*4 + l*9, 1)` e sinaliza `kcal_estimado: True`; se faltar algum macro, mantém `kcal: None`
- **Guard de chave vazia:** `USDA_API_KEY` vazia → retorna `[]` sem chamar a API
- **Cascata:** `_resolver_alimento(termo_pt, termo_en, db)` em `claude_service.py` — busca TACO em PT primeiro; se não encontrar, busca USDA em EN; retorna `(obj, fonte)` ou `(None, None)`
- **Config:** `USDA_API_KEY: str = ""` em `app/config.py` (opcional, mesmo padrão de `OPENAI_API_KEY`); ✅ **configurada no Render (28/05)**

---

## Scheduler (`app/services/scheduler_service.py`)

APScheduler (`AsyncIOScheduler`, timezone `America/Sao_Paulo`) integrado ao lifespan do FastAPI.

**Job:** `lembretes_suplemento` — CronTrigger `hour=20, minute=0`  
- Percorre todos os assinantes ativos
- Envia lembrete só para quem não registrou `suplementos_tomados=True` naquele dia
- Se o usuário tem suplementos cadastrados (`perfis_habitos.suplementos`), o lembrete é personalizado; senão, genérico
- `misfire_grace_time=600` — tolera até 10 min de atraso (ex: restart do serviço)

---

## Modelos de dados

| Tabela | Chave de negócio | Observação |
|--------|-----------------|------------|
| `usuarios` | `telefone` (único, só dígitos) | `ultima_mensagem_id` para dedup |
| `assinaturas` | `hotmart_transaction_id` | plano: `trimestral` (90d) / `anual` (365d) |
| `conversas` | `user_id` (único) | JSON `{role, content, timestamp}` + `estado_pendente` |
| `treinos` / `dietas` | `user_id` | gerados pelo fluxo de coleta (opção 1) ou por keywords; `origem:"proprio"` se externo |
| `perfis_fitness` | `user_id` (único) | perfil persistente; valores canônicos curtos (ex: "intermediario", "musculacao") |
| `mensagens_processadas` | `message_id` (PRIMARY KEY) | dedup atômico de webhooks; substitui `ultima_mensagem_id` |
| `registros_exercicio` | `user_id + sessao_data + posicao_sessao` | 1RM por Epley/Brzycki/Lander |
| `medidas_corporais` | `user_id + data_medicao` | peso + circunferências (nullable) |
| `fotos_composicao` | `user_id` | só `gordura_estimada_pct` + texto; foto não armazenada |
| `registros_refeicao` | `user_id + data_refeicao` | macros confirmados; limite 6/dia |
| `metas_nutricionais` | `user_id` (`ativa=True`) | nova meta desativa anteriores |
| `habitos_dia` | `user_id + data` (unique) | `agua_ml`, `fumou`, `bebeu_alcool`, `suplementos_tomados` |
| `perfis_habitos` | `user_id` (único) | lista de suplementos + datas início de streak |
| `alimentos_taco` | `taco_id` (index) | tabela de referência global, somente-leitura; 597 alimentos TACO 4ª Ed. |

### Migrations Alembic

`001` → `002` → `003` → `004` → `005` → `006` → `007` → `008` → `009` → `010` → `011` → `012` — **HEAD = 012**

| # | O que cria |
|---|------------|
| 001 | Schema inicial (usuarios, assinaturas, conversas, treinos, dietas) |
| 002 | `ultima_mensagem_id` em usuarios |
| 003 | `registros_exercicio` |
| 004 | `medidas_corporais` + `fotos_composicao` |
| 005 | `registros_refeicao` |
| 006 | `metas_nutricionais` |
| 007 | `habitos_dia` + `perfis_habitos` |
| 008 | `perfis_fitness` (perfil persistente do cliente) |
| 009 | `dias_semana_padrao` + `tempo_sessao_padrao` em `perfis_fitness` |
| 010 | `mensagens_processadas` (dedup atômico de webhooks) |
| 011 | `alimentos_taco` — tabela vazia (índices em taco_id, nome, categoria) |
| 012 | popula `alimentos_taco` com 597 alimentos do seed `alembic/seeds/taco_seed.json` |

**ATENÇÃO — autogenerate é INVIÁVEL neste projeto:** o banco PostgreSQL do Render é compartilhado com outra aplicação (Evolution API), que possui ~30 tabelas próprias (`Session`, `Contact`, `Instance`, `Message`, etc.). `alembic revision --autogenerate` geraria `drop_table` para todas elas. **Todas as migrações devem ser escritas manualmente**, seguindo o padrão das 001–012.

---

## Roteamento

| Endpoint | Arquivo | Descrição |
|----------|---------|-----------|
| `GET /` | `main.py` | Health check (banco) |
| `GET /webhook/whatsapp` | `app/routers/whatsapp.py` | Verificação do webhook Meta (hub.challenge) |
| `POST /webhook/whatsapp` | `app/routers/whatsapp.py` | Mensagens WhatsApp (texto, imagem, áudio, documento Excel/PDF) |
| `POST /webhook/hotmart` | `app/routers/hotmart.py` | Compras aprovadas |
| `GET /admin/users` | `app/routers/admin.py` | Lista usuários — `X-Admin-Key` |
| `GET /admin/users/{id}/treinos\|dietas\|conversa` | admin | Histórico |
| `GET /admin/users/{id}/evolucao/sessao` | admin | Soma 1RMs por sessão |
| `GET /admin/users/{id}/evolucao/exercicio?exercicio=` | admin | 1RM de exercício |
| `GET /admin/users/{id}/exercicios` | admin | Exercícios únicos do usuário |
| `GET /admin/users/{id}/medidas` | admin | Histórico de medidas |
| `GET /admin/users/{id}/fotos` | admin | Análises de composição corporal |
| `GET /admin/users/{id}/refeicoes` | admin | Refeições registradas |
| `GET /admin/users/{id}/meta-nutricional` | admin | Metas nutricionais |

---

## Serviços

| Arquivo | Responsabilidade |
|---------|-----------------|
| `claude_service.py` | Orquestração Claude, tools, contexto, menu, fluxos multi-turno |
| `exercicio_service.py` | 1RM, posição de sessão, evolução por exercício |
| `nutricao_service.py` | Medidas, fotos, refeições, metas, contexto nutricional |
| `usda_service.py` | Consulta USDA FoodData Central (Foundation + SR Legacy); fallback Atwater para kcal; camada 2 após TACO na substituição de alimentos |
| `habito_service.py` | Água, streaks fumar/álcool, suplementos, contexto de hábitos |
| `scheduler_service.py` | APScheduler — lembrete de suplementação às 20h |
| `audio_service.py` | Transcrição via OpenAI Whisper |
| `file_reader.py` | Extração de texto de Excel (.xlsx/.xls) e PDF enviados pelo usuário |
| `media_service.py` | Download de mídia via Meta Cloud API (GET graph.facebook.com/{media_id}) |
| `card_service.py` | Geração de PNG dark-theme (matplotlib) para item 6 do menu |
| `whatsapp_service.py` | Envio de texto e imagem via Meta Cloud API (retry 3x) |
| `subscription_service.py` | get_or_create_user, check_active_subscription, activate_subscription |

---

## Meta Cloud API

- Endpoint de envio: `POST https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages`
- Autenticação: `Authorization: Bearer {META_ACCESS_TOKEN}`
- Upload de mídia: `POST https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/media` (multipart)
- Download de mídia: `GET https://graph.facebook.com/v19.0/{media_id}` → resolve URL → GET com Bearer
- Webhook: `GET /webhook/whatsapp` (verificação) + `POST /webhook/whatsapp` (mensagens)
- Assinatura: `X-Hub-Signature-256: sha256=<HMAC-SHA256(body, META_APP_SECRET)>`

## Card PNG de evolução (item 6 do menu)

`app/services/card_service.py` — matplotlib backend `Agg`.
- `get_last_session_stats(user_id, db)` → `{"duracao": str, "exercicios": int, "sessoes": int}`
- `gerar_card_evolucao(user_nome, evolucao, stats)` → `bytes` PNG
- Logo: `LOGO EVOLUTION FIT.jpeg` na raiz (atenção: espaço no nome)
- Paleta: BG `#1C1C1E`, accent `#FF6B35`

---

## Status atual (2026-05-21)

### ✅ Concluído
- Bot **respondendo no WhatsApp via Meta Cloud API** — funcionando em produção
- Número definitivo **+55 11 5304-3378** (ID `1191798997340349`) conectado e funcionando
- Webhook configurado e assinado: `POST /webhook/whatsapp` recebe eventos da Meta corretamente
- App Meta: **Evolution Fit AI** (ID `2038319580456035`)
- WABA ID: `1518787246362458` — subscrita ao app
- Webhook URL: `https://evolutionfit-api.onrender.com/webhook/whatsapp`
- Token de verificação: `evfit-webhook-verify-2026`
- Token Meta **permanente** configurado no Render (`META_ACCESS_TOKEN`) — token de usuário do sistema, não expira
- Integração Kiwify implementada: `POST /webhook/kiwify?plano=anual|trimestral` — ativa assinatura e envia boas-vindas automaticamente
- Landing page no ar: `https://evolutionfit-api.onrender.com/landing`
- Nome do produto atualizado para **Evolution Fit AI** em todos os arquivos
- Endpoint admin `POST /admin/subscriptions/grant` para ativar assinaturas manualmente
- **Áudio desativado temporariamente** — responde que só processa texto e fotos; reativar quando `OPENAI_API_KEY` for configurada
- **Twilio:** conta a ser cancelada — não será mais utilizada (substituída pela Meta Cloud API)

### ⚠️ Pendente
1. **Plataforma de vendas (Kiwify):** configurar produto na Kiwify e webhook de pagamento; substituir vars `HOTMART_*` por equivalentes Kiwify no Render
2. **Links de pagamento:** atualizar `PAYMENT_LINK_TRIMESTRAL` e `PAYMENT_LINK_ANUAL` com links reais da Kiwify
3. **OpenAI API Key:** necessário para reativar transcrição de áudio

---

## Infraestrutura

- **FastAPI:** Render (free tier, Docker). `alembic upgrade head` no startup. Push em `master` dispara deploy automático.
- **WhatsApp:** Meta Cloud API (WhatsApp Business Platform). Webhook configurado no painel Meta for Developers apontando para `https://evolutionfit-api.onrender.com/webhook/whatsapp`.
- **Banco:** PostgreSQL no Render (free tier).
- **Scheduler:** APScheduler in-process (sem Redis). No Render free tier pode ter cold start — o lembrete de 20h pode ser perdido se o serviço estiver dormindo.

**Nota sobre migrations:** `alembic/env.py` e `app/database.py` leem `DATABASE_URL` diretamente de `os.environ` (via `load_dotenv`) sem importar o `Settings` completo. Isso permite que `alembic upgrade head` rode no startup sem exigir todas as variáveis da aplicação.

**Nota sobre o .dockerignore:** `scripts/` está listado no `.dockerignore` e **não entra na imagem Docker**. Qualquer arquivo que precise existir em produção (ex: seed de dados consumido por migration) NÃO pode ficar em `scripts/`. Dados consumidos por migrações ficam em `alembic/seeds/` (que entra na imagem via `COPY . .`).

## Variáveis de ambiente no Render

| Variável | Status |
|----------|--------|
| `DATABASE_URL` | ✅ configurada (fromDatabase) |
| `ANTHROPIC_API_KEY` | ✅ configurada |
| `META_PHONE_NUMBER_ID` | ✅ `1191798997340349` — número definitivo +55 11 5304-3378 |
| `META_ACCESS_TOKEN` | ✅ token permanente configurado |
| `META_WEBHOOK_VERIFY_TOKEN` | ✅ configurada (`evfit-webhook-verify-2026`) |
| `META_APP_SECRET` | ✅ configurada |
| `ADMIN_API_KEY` | ✅ configurada (rotacionada 28/05) |
| `OPENAI_API_KEY` | ⚠️ pendente — necessário para reativar transcrição de áudio |
| `USDA_API_KEY` | ✅ configurada no Render (28/05) |
| `HOTMART_WEBHOOK_SECRET` | ✅ removida do código (27/05) — ✅ apagada do painel Render (28/05) |
| `HOTMART_OFFER_ID_*` | ✅ removidas do código (27/05) — ✅ apagadas do painel Render (28/05) |
| `PAYMENT_LINK_*` | ⚠️ pendente — atualizar com links reais da Kiwify |

## Logs

JSON estruturado via `pythonjsonlogger`:
```python
logger.info("event_name", extra={"user_id": ..., "key": "value"})
logger.error("event_name", extra={"error": str(e)}, exc_info=True)
```

---

## HISTÓRICO DE MUDANÇAS (sessão de 28/05/2026 — limpeza de segurança e confirmações)

### Segurança
- **`ADMIN_API_KEY` rotacionada** — nova chave gerada e atualizada no Render. Chave anterior descartada. Prática de segurança: nunca ecoar/logar a chave.

### Limpeza confirmada
- **`HOTMART_*` vars** — apagadas do painel Render (estavam órfãs pós-migração para Kiwify) e confirmadas ausentes do `.env` local (grep retornou 0 linhas).
- **`USDA_API_KEY`** — confirmada ativa no Render; testada em produção com busca real.
- **Salvamento por keyword (`Lugar C`)** — confirmado removido do código. Banco tem apenas 5 treinos reais (todos `origem="proprio"`): Peito A (133), Peito 3 (131), PEITO 3 (129), PEITO 1 (128), PERNA 2025 (125). Pendências L647-L648 marcadas como concluídas.
- **`static/landing/motion.html`** — arquivo de 68KB não commitado, deletado. `static/landing/index.html` revertido (tinha botão "Assistir Motion 🎬" não finalizado). `LOGO PNG COM BORDA.PNG` (1.4MB) adicionado ao `.gitignore`.

---

## HISTÓRICO DE MUDANÇAS (sessão de 27/05/2026 — tool consultar_historico_treino + planejamento épico)

### Implementado
- **Tool `consultar_historico_treino` ✅** — IA agora enxerga o histórico real de execuções (cargas/séries/reps/1RM) das últimas 4 semanas, agrupado por exercício (3 últimas execuções cada). Funções: `exercicio_service.get_historico_recente` + helper `_fmt_historico_treino` (lista WhatsApp, sem tabela). Removida a comparação de "1RM médio por sessão" porque misturava treinos diferentes — só evolução POR EXERCÍCIO (comparação válida).

### ÉPICO: Estrutura de treino (séries individuais + comparação por treino) — planejado, não iniciado

**CONTEXTO DA DECISÃO (27/05):** Discutido em detalhe com o Igor. Duas comparações desejadas:
- (#1) Mesmo exercício entre treinos diferentes (supino do "peito A" vs "peito B") — ✅ JÁ FUNCIONA via `consultar_historico_treino` (agrupa por nome de exercício, ignora o treino). Testado e confirmado.
- (#2) Mesmo treino em dias diferentes (peito A de hoje vs peito A da semana passada) — ❌ FALTA. Precisa vincular a sessão de registros ao treino.

**DECISÃO de como marcar o treino da sessão:** o usuário diz qual treino ao começar — manda "treinar [nome]" (ex: "treinar peito A"). Isso marca todos os registros daquela sessão com o nome/tipo do treino. (NÃO usar `treino_id` da instância do plano — quebra ao recriar plano. Usar o nome/tipo, que é estável.)

**AS 3 PARTES DO ÉPICO (incrementais):**

**PARTE 1 — Vínculo sessão→treino (resolve comparação #2):**
- Adicionar campo `treino_nome: str` no `RegistroExercicio` para o nome/tipo do treino da sessão.
- Fluxo "treinar [nome]": ao iniciar, captura o nome do treino e marca a sessão. Os registros seguintes herdam esse nome até a sessão acabar/trocar.
- `get_historico_recente` passa a permitir filtrar/agrupar por `treino_nome` → comparar "peito A" entre datas.

**PARTE 2 — Séries individuais + aquecimento:**
- `RegistroExercicio` hoje guarda `series/reps/carga` AGREGADOS. Criar estrutura para guardar cada SÉRIE individual com carga/reps próprias + flag `is_aquecimento` (bool).
- Decisão pendente: tabela nova (`registros_series`) vinculada ao `RegistroExercicio`, OU coluna JSON `series_detalhe` no model existente. Avaliar na sessão dedicada.
- Mudança no fluxo `registrar_exercicio` (hoje recebe `series/reps/carga`; passaria a receber séries individuais).

**PARTE 3 — Fluxo de apresentação (formato WhatsApp):**
- Ao SOLICITAR treino: lista simples "Exercício A - X aquecimentos e Y séries válidas com N repetições" + "Envie 'treinar [nome]' para iniciar".
- Ao mandar "treinar [nome]": mostrar por exercício "No seu último treino você fez: aquecimento com X, séries válidas: 1ª série X peso N reps, 2ª série...". Depende das Partes 1 e 2.

**REQUER:** migração(ões) nova(s) — todas MANUAIS (autogenerate inviável, banco compartilhado). Mudança em `registrar_exercicio`, no contexto, na exibição, e no parsing do "treinar".

**ORDEM SUGERIDA:** Parte 1 (mais isolada, destrava #2) → Parte 2 (estrutura de séries) → Parte 3 (apresentação, depende das duas). Fazer em sessão(ões) dedicada(s) com cabeça fresca.

---

## HISTÓRICO DE MUDANÇAS (sessão de 27/05/2026 — limpeza de resíduo "dieta em breve")

### Corrigido
- **`claude_service.py` — description da tool `iniciar_edicao_registro`:** removida a frase `'Suplemento' e 'treino' implementados; 'dieta' em breve.`. Substituída por instrução explícita: dieta NÃO usa esta ferramenta — deve ser editada via `substituir_alimento` (trocar alimentos específicos na conversa). Claude passa a saber o caminho correto em vez de prometer funcionalidade futura.
- **`claude_service.py` — dispatch `elif block.name == "iniciar_edicao_registro"`:** ramo `else` (que capturava dieta e remédio) dividido em dois:
  - `elif alvo == "dieta"`: retorna mensagem orientando o usuário a trocar alimentos na conversa (`result = "EDICAO_DIETA_REDIRECIONADO"`).
  - `else` (remédio/outro): mensagem genérica de não-suportado sem mencionar "dieta em breve" (`result = "EDICAO_TIPO_NAO_SUPORTADO"`).
  - Ramos `suplemento` e `treino` intocados.

### Pendente
- Nenhuma pendência nova desta sessão. Ver histórico anterior para pendências em aberto.

---

## HISTÓRICO DE MUDANÇAS (sessão de 26/05/2026 — parte 4: USDA fallback na substituição de alimentos)

### Implementado
- **`app/config.py`:** `USDA_API_KEY: str = ""` adicionado logo após `OPENAI_API_KEY` (mesmo padrão opcional). Chave real configurada no `.env` local; **pendente configurar no Render**.
- **`app/services/usda_service.py` (novo):** `buscar_alimento_usda(termo, api_key) -> list[dict]` — async, `httpx.AsyncClient(timeout=15)`, guard para `api_key` vazio, `dataType=["Foundation","SR Legacy"]`, `pageSize=5`. Mapeia `nutrientNumber` como str ou int; aceita `value` ou `amount`. Fallback de Atwater: se `kcal` vier `None` mas `proteina_g`, `carboidrato_g` e `lipideos_g` estiverem todos presentes, calcula `round(p*4 + c*4 + l*9, 1)` e sinaliza `kcal_estimado: True`. Se faltar algum macro, mantém `kcal: None` e `kcal_estimado: False`. Erros de rede → `[]` + log.
- **`claude_service.py` — tool `substituir_alimento` reformulada:** `origem`/`destino` (strings únicas) substituídos por `origem_pt`, `origem_en`, `destino_pt`, `destino_en`. Claude sempre fornece os dois idiomas; `required` atualizado. Description atualizada para descrever a cascata PT→EN e a regra de perguntar o corte quando o alimento for genérico.
- **`claude_service.py` — helpers novos:**
  - `_normar_alimento(obj) -> dict`: extrai `{nome, kcal, proteina_g, lipideos_g, carboidrato_g, fibra_g}` de um `AlimentoTACO` (via `hasattr(obj, "kcal")`) ou dict USDA — formato comum para o cálculo.
  - `_calcular_substituicao_normed(normed_o, gramas_origem, normed_d) -> dict`: mesma matemática de `substituir_por_equivalencia_calorica` mas sobre dicts normalizados; retorna mesmo formato consumido por `_fmt_substituicao`; guards kcal=None e kcal=0 preservados.
  - `_resolver_alimento(termo_pt, termo_en, db) -> (obj, fonte) | (None, None)`: cascata TACO → USDA; TACO busca em PT, USDA em EN; retorna primeiro resultado de cada base.
- **`claude_service.py` — dispatch `substituir_alimento` refatorado:** usa `await _resolver_alimento(...)` nos dois lados; normaliza com `_normar_alimento`; calcula com `_calcular_substituicao_normed`. Mensagem de erro inclui tanto o termo PT quanto EN. Fluxo `substituicao_dieta` (hoje-vs-plano) e `_fmt_substituicao` inalterados.
- **`claude_service.py` — description da tool:** frase adicionada: Claude deve perguntar o corte/tipo específico antes de chamar a ferramenta quando o alimento for genérico (ex: "frango", "peixe", "carne"). Não assume o corte sozinho.
- **`scripts/test_usda.py` (novo):** script standalone de teste das 5 situações (dict cru, tilápia, rice, xyzabc, chave vazia). Não entra na imagem Docker (`scripts/` está no `.dockerignore`).

### Validado antes de commitar
- Tilápia USDA: `kcal=96`, `proteina_g=20.1`, `lipideos_g=1.7` — bate com referência nutricional.
- Frango peito cru: kcal ausente na USDA → Atwater calcula `107.4 kcal` (`22.5×4 + 0×4 + 1.93×9`), `kcal_estimado=True`.

### Pendente
- [x] **Configurar `USDA_API_KEY` no Render** — ✅ configurada (28/05).
- [ ] **Teste end-to-end em produção**: pedir substituição de alimento presente só na USDA (ex: tilápia) via WhatsApp.
- [x] **Edição de dieta** — ✅ CONCLUÍDA 26/05. Implementada como edição inteligente via substituição de alimentos (TACO→USDA, equivalência calórica, hoje-vs-plano).

---

## HISTÓRICO DE MUDANÇAS (sessão de 26/05/2026 — parte 3: hoje-vs-plano + contexto de dieta)

### Implementado
- **`nutricao_service.py` — `anexar_troca_ao_plano(user_id, descricao_troca, db) -> bool`:** pega `get_meta_ativa`; se None → False; caso contrário anexa `"\n[ajuste] " + descricao_troca` ao `texto_original` (ou cria se vazio); `db.flush()`; retorna True.
- **`claude_service.py` — dispatch `substituir_alimento` reformulado:** em vez de devolver `SUBSTITUICAO_OK` diretamente, arma `conversa.estado_pendente = {tipo: "substituicao_dieta", etapa: "aguardando_escopo", descricao, resumo_macros}` e retorna `SUBSTITUICAO_CALCULADA: apresente os números ... e PERGUNTE se é só para hoje ou para salvar no plano`. Loop de tool-use NÃO é interrompido — Claude ainda responde com os números e a pergunta; `estado_pendente` é persistido no `db.commit()` final.
- **`claude_service.py` — constantes `_ESCOPO_PLANO_KEYWORDS` / `_ESCOPO_HOJE_KEYWORDS`:** plano = {"plano","salva","salvar","sempre","fixo","permanente","todo dia"}; hoje = {"hoje","agora","só essa","uma vez","dessa vez","só hoje"}.
- **`claude_service.py` — `_handle_substituicao_dieta`:** handler síncrono que detecta plano → chama `anexar_troca_ao_plano` (confirma ou informa "sem plano salvo"); hoje → responde sem persistir; ambíguo → repergunta mantendo estado.
- **`claude_service.py` — step 3.7 em `process_message`:** intercepta `tipo == "substituicao_dieta"` antes do fluxo geral; mesmo padrão dos steps 3.5/3.6 (commit + return imediato sem chamar Claude).
- **`nutricao_service.py` — `build_nutricao_context`:** após a linha de macros da meta ativa, injeta `"Cardápio/ajustes do plano: <texto_original>"` truncado a 500 chars com `"..."`. Só adiciona se `meta.texto_original` tiver conteúdo. Isso inclui ajustes acumulados via `[ajuste]`.

### Diagnóstico confirmado (sem alteração de código)
- `estado_pendente` setado no dispatch de tool sobrevive até o próximo turno: nenhum reset entre o dispatch e o `db.commit()` final de `process_message`. Único ponto que zera é `/menu` (intencional). Padrão análogo ao de `iniciar_exclusao_registro` (que também seta `estado_pendente` dentro do loop de tools).

### Pendente (próxima sessão)
- [x] **Edição de dieta** — ✅ CONCLUÍDA 26/05 (não via Opção B, mas via edição inteligente por substituição de alimentos com TACO→USDA e pergunta hoje-vs-plano).
- [x] Aviso "dieta em breve" em `iniciar_edicao_registro` tool description — ✅ RESOLVIDO 27/05: descrição e dispatch corrigidos; edição de dieta redireciona para `substituir_alimento` sem mensagem "em breve".

---

## HISTÓRICO DE MUDANÇAS (sessão de 26/05/2026 — parte 2: camada de serviço TACO + tool)

### Implementado
- **Camada 1 — `nutricao_service.py`:** `buscar_alimento(termo, db)` — ilike palavra-a-palavra (nomes TACO usam vírgulas, ex: "Arroz, integral, cozido"; substring única falha); resultados "começa com" antes de "contém"; limite 10. `macros_por_porcao(alimento, gramas)` — proporção por 100g; campos `None` do TACO permanecem `None` (nunca inventar).
- **Camada 2 — `nutricao_service.py`:** `substituir_por_equivalencia_calorica(origem, gramas, destino, db)` — calcula gramas equivalentes caloricamente; guards para kcal=None e kcal=0; retorna dict `{origem, destino, erro}`.
- **Camada 3 — `claude_service.py`:** tool `substituir_alimento` adicionada ao array `TOOLS` (14 tools no total). Dispatch `elif block.name == "substituir_alimento"` no loop de tool-use: busca ambos os alimentos, pega o 1º de cada lista, chama `substituir_por_equivalencia_calorica`, monta string `SUBSTITUICAO_OK | ORIGEM: ... | DESTINO: ...`. Helper `_fmt_substituicao` formata macros com `n/d` para `None`. **Não interrompe o loop** (não seta `edicao_iniciada_msg`). **Não persiste nada** — só calcula e devolve ao Claude.

### Diagnóstico (investigação sem alteração de código)
- **Tilápia:** NÃO existe na base TACO 4ª edição. `SELECT nome FROM alimentos_taco WHERE nome ILIKE '%tila%'` → 0 resultados. Busca com e sem acento: 0.
- **Persistência de dieta:** `substituir_alimento` é somente-leitura — nenhum `db.add`/`db.flush`; a dieta do usuário não é alterada pela substituição. `build_nutricao_context` envia ao Claude apenas o resumo de macros da meta ativa, não o `texto_original` completo.
- **Padrão `aguardando_confirmacao`** reconhecido para reusar na pergunta "só hoje vs no plano": `_normalizar_confirmacao` + `estado_pendente = None` ao final em qualquer desfecho.

### Pendente (próxima sessão)
- [x] **Edição de dieta** — ✅ CONCLUÍDA 26/05 via substituição inteligente (ver histórico partes 3 e 4).
- [x] Pergunta "só hoje ou atualizar o plano?" — ✅ implementado (hoje-vs-plano com `_handle_substituicao_dieta`).

---

## HISTÓRICO DE MUDANÇAS (sessão de 26/05/2026)

### Implementado
- NOVO: usuário pode **editar treino** via chat. `_iniciar_edicao_treino` lista treinos reais (reusa `treino_service.listar_treinos`); `_handle_editar_registro` recebeu `elif alvo == "treino"` nas duas etapas (`aguardando_escolha` e `aguardando_novo_valor`). Fluxo seguro: aceita só 1 número → bot pede texto novo → salva novo via `treino_service.cadastrar_treino_proprio` PRIMEIRO → só apaga o antigo se o save não lançou exceção → confirma. Dispatch de `iniciar_edicao_registro` plugado para `alvo="treino"`. Tool description atualizada: suplemento e treino implementados, dieta em breve.
- REFATORAÇÃO: lógica de persistência de treino extraída para `treino_service.cadastrar_treino_proprio(user_id, nome, texto, db, exercicios="") → Treino`. Reusada em `_process_tool_cadastrar_treino` (sem mudança de comportamento) e no novo fluxo de edição.
- `dryrun*.json` adicionado ao `.gitignore` (padrão glob, cobre futuros). `*.xlsx` e `*.xls` adicionados ao `.gitignore` (cobre `Taco-4a-Edicao.xlsx` e futuros).

### Investigado e implementado
- Base nutricional TACO **IMPORTADA**: model `AlimentoTACO`, migrations 011 (cria tabela) e 012 (popula 597 alimentos). Seed em `alembic/seeds/taco_seed.json`. Validação cruzada 56/56 campos OK. Descoberta infra: banco compartilhado com Evolution API → autogenerate inviável; `scripts/` no .dockerignore → seed movido para `alembic/seeds/`.

### Decidido
- **Edição de dieta**: Opção B aprovada, mas implementada de forma diferente e superior — edição inteligente via tool `substituir_alimento` (TACO→USDA, equivalência calórica, Atwater fallback, desambiguação de corte, hoje-vs-plano). ✅ CONCLUÍDA 26/05.
- **TBCA**: NÃO usar por ora — restrição de uso comercial exige autorização formal da USP/UNICAMP.

### Pendente (próxima sessão)
- [x] **Edição de dieta** — ✅ CONCLUÍDA 26/05 (ver histórico sessão 26/05 partes 2, 3 e 4).
- [x] ~~Implementar **model + tabela + script de importação** da base TACO~~ — CONCLUÍDO 26/05.

---

## HISTÓRICO DE MUDANÇAS (sessão de 25/05/2026 — continuação)
- NOVO: usuário pode apagar as próprias DIETAS via chat. Fundação genérica de exclusão parametrizada por `alvo`: `_EXCLUSAO_CONFIG` mapeia tipo → (singular, plural, apagar_fn); `_handle_apagar_registro` agora serve treino e dieta sem duplicação. Adicionado `listar_dietas` + `apagar_dietas` em nutricao_service (hard-delete em `metas_nutricionais`, guarda user_id). A tabela `dietas` (keyword-lixo) é ignorada — só `MetaNutricional` é exposta. Dispatch da tool `iniciar_exclusao_registro` plugado para `alvo="dieta"`. Comportamento de treino preservado identicamente.
- NOVO: usuário pode remover suplementos da lista via chat. `_iniciar_exclusao_suplemento` lê `PerfilHabitos.suplementos` (lista JSON, sem IDs de banco), exibe numerada. `_handle_apagar_registro` bifurca por `alvo=="suplemento"`: calcula `lista_restante` por posição (correto mesmo com nomes duplicados), regrava via `registrar_suplementos_usuario(user_id, lista_restante, db)`. Apagar todos → `[]` gravado corretamente. Treino e dieta preservados identicamente.
- [x] Apagar DIETAS pelo usuário via chat — FEITO 25/05.
- [x] Apagar SUPLEMENTOS pelo usuário via chat — FEITO 25/05.

## HISTÓRICO DE MUDANÇAS (sessão de 25/05/2026)
- Segunda limpeza de produção concluída: apagados +28 treinos-lixo do user 1 (menus, coaching, confirmações com real preservado, 3 cópias redundantes de Perna). Banco do user 1 com 10 treinos reais e únicos. Limpeza do histórico 100% concluída.
- Lembrete automático das 20h DESATIVADO (bloco add_job comentado em scheduler_service.py; função _enviar_lembretes_suplemento preservada). Será substituído por sistema de lembretes opt-in (contínuo/pontual/horário) quando a confiabilidade do disparo for resolvida (Render free dorme → scheduler in-process não dispara confiável; precisa Render pago ou cron externo).
- Criado app/services/treino_service.py (listar_treinos com filtro real + apagar_treinos com guarda user_id+id). Rota admin /admin/treinos/delete refatorada para reusar apagar_treinos (guarda centralizada).
- NOVO: usuário pode apagar os próprios treinos via chat. Tool iniciar_exclusao_registro(alvo) + estado "apagando_registro" + _handle_apagar_registro (step 3.5 em process_message). Fluxo seguro: lista numerada → escolha → confirmação → hard-delete. Suporta múltiplos ("1, 3, 4") e "todos" (com confirmação reforçada de irreversibilidade). Travas: só itens do próprio user, só apaga com "sim" explícito, cancelar/seleção inválida aborta (tudo-ou-nada). Testado em produção.

## HISTÓRICO DE MUDANÇAS (sessão de 24/05/2026)
- Removido o salvamento de treino por keyword (gerava registros falsos). Dieta mantém keyword até a Etapa 3.
- Bug A (salvamento) confirmado resolvido: treino gerado com sucesso é salvo; adicionada guarda contra reply vazio. Confirmado em produção.
- Descoberto que o .env local aponta para banco LOCAL (cópia parada); produção é o banco do Render. Toda verificação real deve ser feita em produção (via rota admin).
- Criada rota admin POST /admin/treinos/delete com dry-run (padrão) + backup antes de apagar + restrição por user_id + lista explícita de ids.
- Limpeza de produção: apagados 75 treinos-lixo do user 1 (perguntas, confirmações, deflexões salvas por engano pelo antigo keyword). Backup salvo. Sobraram ~27 reais + 10 do grupo D a revisar.
- ADMIN_API_KEY rotacionada (a anterior havia sido exposta).
- .gitignore agora ignora dumps (treinos.json, backups).
- Bug B RESOLVIDO: criado _treinos_context_str que injeta um resumo dos treinos salvos no contexto da IA (treino mais recente com excerpt do corpo + até 3 títulos anteriores), com filtro anti-lixo (origem=="proprio" ou len>=400), nota honesta no caso vazio, e moldura para a IA só falar de treino quando perguntada. Testado em produção: "qual meu treino?" agora responde com o treino real; conversa normal não puxa treino espontaneamente; criação de treino segue funcionando. FLUXO DE TREINO COMPLETO (criar → salvar → consultar).
- .gitignore ampliado para dryrun.json, delecao_resultado.json, *_resultado.json.
- Segunda limpeza de produção: apagados +28 treinos-lixo do user 1 (8 menus, 9 coaching/resumos, 8 confirmações com real preservado, 3 cópias redundantes de Perna). Backup em delecao2_resultado.json. Banco do user 1 agora com 10 treinos reais e únicos. Limpeza do histórico 100% concluída.

## HISTÓRICO DE MUDANÇAS (sessão de 23/05/2026)
- Coleta estruturada de criação de treino (etapa 2a): bot conduz as 9 perguntas via estado "criando_treino", salva no perfil e gera o treino com 1 chamada à IA.
- Perfil persistente do cliente: tabela perfis_fitness (migração 008) + campos dias/tempo (migração 009). Salva valores canônicos curtos (ex: "intermediario", "musculacao") para reaproveitar depois.
- Webhook assíncrono: responde HTTP 200 imediatamente e processa em BackgroundTask (corrige a demora de até 3 min que causava reenvio da Meta e fluxo errático).
- Dedup atômico de webhook: tabela mensagens_processadas (migração 010) com message_id PRIMARY KEY (substitui o ultima_mensagem_id que tinha race condition).
- Correção: salvamento do perfil estourava VARCHAR(20) com textos longos; agora salva códigos curtos + trunca texto livre.

---

## PENDÊNCIAS / ROADMAP (melhorias a fazer)

### Treino — pendências imediatas (continuação da etapa 2)
- [x] Remover o salvamento de treino por palavra-chave (Lugar C em process_message) — ✅ CONCLUÍDO (verificado 30/05). Zero ocorrências de "Lugar C" no código; `TREINO_KEYWORDS` definida mas não usada em salvamento; `Treino` só é criado em `_gerar_treino_de_dados` (coleta estruturada) e `treino_service.cadastrar_treino_proprio` (tools). Bloco final de `process_message` salva apenas `Dieta` por keyword, não `Treino`.
- [x] Limpar os ~50 treinos falsos já existentes no banco — ✅ CONCLUÍDO (verificado 30/05). Produção (user_id=1) tem apenas 5 treinos, todos com `origem="proprio"` (Peito A, Peito 3, PEITO 3, PEITO 1, PERNA 2025) — nenhum lixo.
- [x] Etapa 2b ✅ CONCLUÍDA 27/05 — no 2º treino em diante, `_iniciar_coleta_treino` detecta perfil salvo (`dias_semana_padrao != None`), mostra resumo legível do perfil e pergunta "manter ou mudar?". Se manter: pré-preenche 7 campos e pergunta só `tipo_treino` + `dor_desconforto`. Se mudar: refaz coleta completa do zero. Estado usa chave `fase` (`confirmando_perfil` / `coletando`). Em produção.
- [ ] Etapa 3: replicar a coleta estruturada para DIETA (fluxo separado), reaproveitando o perfil.

### Treino — pendências (continuação)
- [x] Bug B: RESOLVIDO em 24/05 — IA enxerga os treinos via _treinos_context_str.
- [x] Limpeza completa (grupo D + lixo restante) — RESOLVIDO em 24/05, banco com 10 treinos reais.
- [x] Etapa 2b ✅ CONCLUÍDA 27/05 — ver descrição detalhada acima.
- [ ] Etapa 3: coleta estruturada de DIETA + remover keyword de dieta.

### Exclusão e edição de registros pelo usuário
- [x] Apagar TREINOS pelo usuário via chat (lista numerada, múltiplos, "todos", confirmação) — FEITO 25/05.
- [x] Apagar DIETAS pelo usuário via chat — FEITO 25/05.
- [x] Apagar SUPLEMENTOS pelo usuário via chat — FEITO 25/05.
- [ ] Replicar exclusão para REMÉDIO (não existe ainda como entidade no banco — bloqueado até implementar o modelo).
- [ ] CADASTRAR REMÉDIOS (entidade nova — não existe model/tabela hoje): criar o modelo de remédio com uso PONTUAL (com data fim) ou RECORRENTE/contínuo, horário(s). Projeto próprio, MAIOR, porque se conecta ao sistema de LEMBRETES opt-in (que depende de disparo confiável — Render pago ou cron externo). Tratar depois do "editar".
- [x] EDITAR SUPLEMENTO pelo usuário via chat — FEITO 25/05. Tool `iniciar_edicao_registro(alvo)` + estado `editando_registro` + `_handle_editar_registro` (etapas: aguardando_escolha → aguardando_novo_valor). Troca por posição (seguro com nomes duplicados). Fundação genérica pronta para treino e dieta.
- [ ] EDITAR TREINO e DIETA (fundação genérica pronta; treino = cadastrar novo via serviço direto + apagar antigo; dieta = idem via nutricao_service.cadastrar_meta ou Claude bridge para extração de calorias).
- [ ] Dados corporais (peso, idade, sexo): EDITÁVEIS, não apagáveis (decisão do dono).

### Lembretes (sistema novo opt-in) — depende de disparo confiável
- [ ] Lembretes opt-in: usuário ativa, informa o quê + se é contínuo ou pontual (remédio com data fim) + horário. Tabela de lembretes no banco. Lembrete pontual para sozinho ao fim do período. PRÉ-REQUISITO: disparo confiável (Render pago ou cron externo) — o scheduler in-process não dispara no free tier.

**REGRAS OBRIGATÓRIAS do sistema de lembretes (válidas quando o sistema opt-in for construído):**
- [ ] **OPT-IN ESTRITO:** lembrete só é enviado para quem PEDIU explicitamente para recebê-lo. NUNCA enviar lembrete automático/não solicitado a nenhum usuário. (O antigo job das 20h foi desativado em 25/05 justamente por violar isso.)
- [ ] **Lembrete de suplemento só faz sentido se o usuário TEM suplemento cadastrado:** se a lista de suplementos estiver vazia, NÃO enviar lembrete de suplemento.
- Ao ativar um lembrete, o usuário informa: o quê, se é uso CONTÍNUO ou PONTUAL (ex: remédio por X dias com data fim), e o HORÁRIO desejado. Lembrete pontual deve parar sozinho ao fim do período.
- PRÉ-REQUISITO técnico: disparo confiável (Render pago ou cron externo) — o scheduler in-process não dispara no free tier (serviço dorme).

### Experiência de uso (prioridade)
- [ ] Bot repetitivo: faz a mesma pergunta várias vezes ao criar treino e dieta. Corrigir para não repetir.

### Refinos de funcionalidade
- [ ] Lembrete de suplementos/vitaminas junto à refeição que os inclui (ex: creatina no café, vitamina D no jantar). NÃO criar lembrete exclusivo de remédio temporário.
- [ ] Dietas: mostrar medidas sempre em 2 unidades — gramas E colheres de sopa.

### Rápidos
- [ ] Remover o limite de 6 análises de refeição por foto por dia.

### Grandes (sessão dedicada)
- [ ] Treino guiado ao vivo: treino completo -> cliente "estou pronto" -> bot manda exercício a exercício -> cliente reporta carga/reps -> bot indica descanso (aquecimento 1 min, válidas caso a caso) e próxima série.
- [ ] Integração com wearables (Garmin/Apple Watch/Samsung/Xiaomi/Amazfit/Huawei): projeto à parte. Avaliar focar 1 plataforma (Garmin) ou usar leitura de arquivo exportado do relógio.

### Lançamento
- [ ] Render plano Free "dorme" com inatividade (1a mensagem lenta ~50s). Avaliar plano pago antes do lançamento.
- [ ] Teste de compra nova de ponta a ponta com número que nunca comprou.
- [ ] Validar valor pago no webhook Kiwify (segurança extra).
- [ ] Migrar memória de dor/desconforto para o banco de dados (hoje é só por conversa).

### Limpeza / acompanhamento
- [ ] Confirmar com a Maria que está usando normalmente.
- [ ] Possível registro duplicado da Maria no banco (conta antiga, telefone 12 dígitos) — limpar via rota admin.
- [ ] Lembrete: assinatura anual do criador expira ~maio/2027.

### Treino — novos refinos
- [ ] Ao criar treino, perguntar o sexo da pessoa.
- [ ] Variação grande de peso/séries vs histórico: questionar o usuário ("registrei X, seu último foi Y, está certo?") e seguir só se confirmado.
- [ ] Registro de carga POR EXERCÍCIO (não só por treino): considerar dados do mesmo exercício entre treinos diferentes APENAS quando ele for o 1º exercício da sessão em ambos os treinos.

### Mídia / biblioteca (exigem hospedar arquivos)
- [ ] Banco de GIFs de execução de cada exercício; cliente pergunta "como é esse exercício?" e recebe o GIF (e a máquina, se usar).
- [ ] Banco de fotos realistas de aparelhos; cliente pergunta qual é o aparelho e recebe a foto.
- [ ] Fotos de corpos estilo manequim para o cliente escolher o objetivo de corpo ideal.

### Grande (viabilidade a discutir)
- [ ] Análise de vídeo de execução: cliente grava o exercício e a IA aponta o que melhorar (definir formato do feedback — escrito? anotando o vídeo?). Projeto complexo, avaliar viabilidade antes.

### Skills de domínio (qualidade do conteúdo gerado)
- [ ] Skill de NUTRIÇÃO especialista (referência: mcpmarket nutritional-specialist + ISSN Position Stand) para melhorar dietas geradas.
- [ ] Skill de TREINOS especialista (referências: Schoenfeld, Israetel, Krieger; volume/descanso/progressão do protocolo Igor Hanate) para melhorar treinos gerados.

### Base nutricional TACO — ✅ CONCLUÍDA (26/05/2026)

**Arquivos:**
- Model: `app/models/alimento_taco.py` → classe `AlimentoTACO`, tabela `alimentos_taco`
- Script de parsing: `scripts/importar_taco.py` (standalone, só pandas — lê o Excel, grava seed)
- Seed versionado: `alembic/seeds/taco_seed.json` (597 registros, UTF-8)
- Migration 011: cria tabela `alimentos_taco` (índices em `taco_id`, `nome`, `categoria`)
- Migration 012: popula com os 597 alimentos do seed

**Estatísticas validadas contra o Excel (56/56 campos OK):**
- 597 alimentos · 15 categorias
- `"Tr"` → `0.0`: proteina_g=6, lipideos_g=30, fibra_g=7
- `"*"` → `NULL`: kcal=4, proteina_g=4, lipideos_g=4, carboidrato_g=4, fibra_g=8
- Carboidrato negativo → `0.0`: 4 alimentos (taco_id 288, 322, 337, 400; máx −0.045g)
- 6 alimentos com kcal=NULL (4 via `"*"` + 2 sais via NaN — sal não tem calorias)
- 235 alimentos sem fibra_g (39,4%)
- 2 nomes com espaço no início (taco_id 224 e 227) — corrigidos por `.strip()`

**Nota estrutural do Excel:** a categoria está na **col 0** das linhas-separador (não na col 1 como estava documentado). Col 13 é duplicata de layout — ignorada. Heurística de separador: col0 não-numérico, não-nan, não em `{'legenda','alimento'}`, não começa com `'número'`, não formado só por símbolos `*†‡§`.

**Para que serve:**
- Fundação para edição inteligente de dieta (recalcular macros ao trocar itens)
- Suporte à análise de refeição por foto (validação/complemento dos valores da IA)
- Futura skill de nutrição especialista

**TBCA:** NÃO usar por ora — tem restrição de uso comercial (exige autorização formal dos coordenadores da USP/UNICAMP). Avaliar somente com autorização em mãos.

### Segurança / operação
- [ ] Configurar alerta de saldo baixo / recarga automática de créditos no Console da Anthropic (o bot parou hoje porque os créditos zeraram).
