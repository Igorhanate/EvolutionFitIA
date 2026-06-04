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
- Item 7: análise de refeição por foto (macros estimados + balanço do dia; sem limite diário)
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

## HISTÓRICO DE MUDANÇAS (sessão de 31/05/2026 — épico Parte 1 completo + refinos)

### Implementado
- **Épico Parte 1 passo 2 — Comando A ✅** — comando `'treinar [nome]'` inicia sessão na tabela `sessoes_treino`; se vier sem nome, bot pergunta. Registros de exercício durante sessão ativa herdam o `treino_nome`.
- **B1.a ✅** — quando `'treinar'` sem nome E há treinos salvos, bot mostra lista numerada (até 10 mais recentes); aceita número OU nome livre.
- **B1.b.1 ✅** — item 1 do menu agora pede o **NOME DO PLANO** antes de gravar `Treino` (fase `nomeando_treino`). Validação: não-vazio, ≤60 chars, comandos reservados cancelam.
- **B1.b.2 ✅** — quando `'treinar'` sem nome E lista vazia, bot mostra menu de 3 opções (importar/criar do zero/cancelar). Opção 1 dispara item 2 do menu, opção 2 dispara item 1.
- **Fix ✅** — textos ajustados de "treino" para "plano" (1 plano semanal = 1 `Treino` no banco). `SYSTEM_PROMPT` proíbe RPE/RPE alvo no output de treinos gerados pela IA.

### Cancelado / Adiado
- **B2 (registro retroativo / pergunta de vincular) CANCELADO** — versão proposta (mostrar lista de todos os treinos sempre que cair exercício sem sessão) seria confusa. O comportamento desejado pelo Igor depende de saber "esse exercício está nesse treino?", que só é possível com Parte 2 (estrutura nova). Adiado para Parte 3 (apresentação) com base na Parte 2.

---

## HISTÓRICO DE MUDANÇAS (sessão de 31/05/2026 — continuação tarde: Parte 2 Etapas 1 e 2)

### Implementado
- **Etapa 1 da Parte 2 ✅** — migration 014: coluna `series_detalhe` JSON nullable em `registros_exercicio`. Testada upgrade/downgrade/upgrade local antes do push. Em produção, deploy aplicou migration sem erro.
- **Etapa 2 da Parte 2 ✅** — tool `salvar_treino_estruturado` + função async `extrair_estrutura_treino` (2 tentativas, degradação graciosa) + integração em `_gerar_treino_de_dados` (item 1 do menu). Ao salvar o plano, `Treino.conteudo["dias"]` passa a conter a lista estruturada de dias/exercícios extraída por 2ª chamada Claude.
- **Fix Etapa 2 ✅** — primeira versão (`max_tokens=2000`) falhava em planos grandes (Claude retornava só `nome_plano` sem `dias`). Corrigido com: `max_tokens=4000`, prompt reforçado com 5 regras numeradas, retry agressivo na 2ª tentativa (instrução de "sua resposta anterior estava INCOMPLETA"), log expandido com `stop_reason` e `usage`.
- **Validação em produção ✅** — plano novo (id=140, "salve como teste 2.0") criado após o fix retornou estrutura COMPLETA: 6 dias, todos com `numero`/`nome`/`foco`/`exercicios` populados, cada exercício com `series_validas`/`aquecimento`/`reps`/`descanso_seg`.
- **Etapa 3 da Parte 2 ✅** — `_process_tool_cadastrar_treino` (item 2 do menu — cadastrar treino do personal) virou async e passou a chamar `extrair_estrutura_treino` após salvar. Atualiza `Treino.conteudo['dias']` com a estrutura extraída via 2ª chamada Claude. Degradação graciosa se falhar. Dispatch em `process_message` agora usa `await`. Validado em produção (id=141, treino do Personal João — 3 dias estruturados com 4 exercícios cada, todos com `nome`/`series_validas`/`aquecimento`/`reps`/`descanso_seg`).

### Estado da Parte 2 (final de 01/06 madrugada)
- ✅ Etapa 1: migration 014 (`series_detalhe` em `registros_exercicio`)
- ✅ Etapa 2: extração estruturada item 1 (criar plano do zero)
- ✅ Etapa 3: extração estruturada item 2 (cadastrar plano do personal)
- ✅ Etapa 4: séries individuais + aquecimento na tool `registrar_exercicio`
- ❌ Etapa 5 original CANCELADA — escopo replanejado abaixo

---

## HISTÓRICO DE MUDANÇAS (sessão de 01/06/2026 madrugada — Etapa 4 + replanejamento terminologia)

### Implementado
- **Etapa 4 da Parte 2 ✅** — tool `registrar_exercicio` agora aceita campo opcional `series_detalhe` (lista de séries individuais com `is_aquecimento`). Helper `_derivar_agregados_de_series` calcula agregados a partir das séries válidas (count, max carga, reps da série de maior carga). Compatível com ambos os formatos: simples (3 agregados como antes) ou detalhado (lista). 1RM continua usando agregados. `_handle_confirmacao` (variação anormal) propaga `series_detalhe` corretamente. Validado em produção via rota admin nova `/admin/users/{id}/registros-exercicio`.
- **Rota admin nova ✅** — GET `/admin/users/{user_id}/registros-exercicio?limit=N` retorna últimos registros com todos os campos (incluindo `series_detalhe`). Usado pra validar Etapa 4 em produção.

### Decidido (replanejamento de terminologia — Parte 2 Etapa 5 + Parte 3)
- **Glossário consolidado:** PLANO = `Treino` no banco (1 linha) / TREINO = item dentro de `conteudo["dias"]` (ex: "Peito A", "Push") / EXERCÍCIO = item dentro de `dias[i].exercicios`.
- **Problema descoberto:** todo o sistema atual trata o nome do PLANO como `treino_nome` em sessões e registros. Isso impede comparações por TREINO (dia) e a apresentação de "treino do dia" no formato que o Igor pediu.
- **Solução acordada:** `treino_nome` em `SessaoTreino` e `RegistroExercicio` passa a guardar nome do TREINO (dia), não do PLANO. Sem migration nova — só muda semântica.
- **Registros antigos serão APAGADOS** (5 registros de teste, todos com `treino_nome` = nome do plano, semanticamente errados). Recomeço limpo.
- **Etapa 5 original (detecção exercício fora) CANCELADA** — substituída por replanejamento maior.

### REPLANEJAMENTO Parte 2/3 (alinhamento terminológico — 01/06)

**Fluxo-alvo do usuário:**
1. Usuário manda `treinar` (sem nome).
2. Se 0 planos → lista vazia (já implementado em B1.b.2). Se 1 plano → vai direto pros TREINOS. Se 2+ → pergunta o PLANO primeiro.
3. Bot mostra lista numerada de TREINOS (dias do plano escolhido).
4. Usuário escolhe (número ou nome).
5. Bot APRESENTA o treino do dia: `Segue seu treino de *X*:` / `- Supino: 2 aquecimentos + 3 séries válidas de 8-10 reps` / `...` / `Envie *treinar* para iniciar.`
6. Usuário manda `treinar` (confirmação) → sessão abre com `treino_nome = nome do TREINO`.
7. Ao registrar exercício, bot compara contra `dias[X].exercicios`. Se fora → pergunta "adicionar ao treino ou pontual?". Se dentro → registra + mostra histórico série a série.

**Etapas redesenhadas (5):**
- 🟡 **E1:** Apagar registros antigos (5 de teste, todos com `treino_nome` semanticamente errado).
- 🟡 **E2:** Refatorar `treinar [nome]` + B1.a + B1.b.1 pra exigir nome de TREINO (não PLANO). Lista numerada mostra treinos dos planos. Se 1 plano vai direto; se 2+ pergunta plano antes.
- 🟡 **E3:** Apresentação do treino antes de iniciar — bot mostra exercícios estruturados + pede confirmação (`treinar`) pra abrir sessão.
- 🟡 **E4:** Detecção de exercício fora do treino (match parcial case-insensitive). Pergunta "adicionar ou pontual?". Adicionar → atualiza `Treino.conteudo["dias"][X].exercicios`. Pontual → só registra.
- 🟡 **E5:** Apresentação de histórico série a série ao registrar (lê `series_detalhe` dos últimos registros).

**Não entra nesse replanejamento:** comando `finalizar` + estatísticas, auto-expiração 20min, B3 (confirmar troca de sessão). Ficam pra depois.

**Estimativa:** 5 commits + testes entre cada. Provavelmente 1-2 sessões adicionais.

---

## HISTÓRICO DE MUDANÇAS (sessão de 30/05/2026 — cadastro de perfil obrigatório Etapas 1 e 1.5)

### Implementado
- **Cadastro de perfil obrigatório — Etapa 1 ✅** — guard 0.5 inserido no início de `process_message` (antes de `/menu`): verifica `perfil_minimo_completo`; se False, força fluxo de 6 etapas: confirmar nome → sexo → data de nascimento → altura → peso → nível de experiência. Grava em `PerfilFitness`. Bloqueia qualquer uso do bot até completar. `perfil_service` ganhou `perfil_minimo_completo()` e `calcular_idade()`. Boas-vindas Kiwify ajustada para direcionar ao cadastro em vez do `/menu`.
- **Cadastro de perfil — Etapa 1.5 ✅** — após gravar os 5 campos, em vez de liberar direto, exibe oferta opcional: `1️⃣ Registrar medidas / 2️⃣ Enviar fotos pra análise / 3️⃣ Pular por agora`. Opção 1 redireciona para o fluxo oportunista de `registrar_medidas`; opção 2 copia a instrução do item 9 do menu (frente/costas/lado); opção 3 libera com `/menu`. Helper `faltam_medidas_ou_fotos()` adicionado em `perfil_service`. Item 5 do menu (dieta) prefixa aviso dinâmico se faltar medidas e/ou fotos — não bloqueia, só informa.
- **Cadastro de perfil — Etapa 2 ✅** — tool `editar_perfil` adicionada (atualiza `peso_kg` e/ou `nivel_experiencia` no `PerfilFitness` quando o usuário pedir explicitamente). Guardrail de 5kg: variação grande aciona `estado_pendente = confirmar_historico_medida` e pergunta se quer registrar também no histórico corporal (guard 3.8 em `process_message`). `atualizar_peso_perfil` + `atualizar_nivel_perfil` em `perfil_service`. Rota admin `GET /admin/users/{id}/perfil` criada para debug de campos do perfil.
- 🔍 Observação a verificar: usuário (Igor) reportou que dados do cadastro "sumiram" após primeira sessão. Investigação não conclusiva (não havia rota /admin/perfil — criada agora mas não consultada). Sinais indicam perfil persistido (estado_pendente=None + 808 msgs históricas). Verificar na próxima sessão com a rota nova `GET /admin/users/{id}/perfil`.
- **Pendência "Perguntar sexo ao criar treino" ✅** — superada: sexo agora coletado obrigatoriamente na Etapa 1 do cadastro.
- **Limite de 6 análises de refeição/dia removido** — usuário pode registrar quantas refeições quiser. Custo da API mitigado pelo fato de só refeições CONFIRMADAS contarem (análise sem confirmar não persiste).
- **Épico Parte 1 — passo 1 de 2 ✅** — migration 013 criada (tabela `sessoes_treino` + coluna `treino_nome` em `registros_exercicio`). Model `SessaoTreino` novo. Testada localmente (upgrade/downgrade/upgrade OK). Em produção via deploy auto.
- **Épico Parte 1 — passo 2 de 2 ✅ (31/05)** — fluxo "treinar [nome]" implementado. Novo serviço `app/services/sessao_treino_service.py` (`get_sessao_ativa` + `iniciar_sessao` — fecha sessão anterior automaticamente). Guard 0.8 em `process_message`: regex `^treinar(?:\s+(.+))?$` captura nome ou pergunta qual treino (`aguardando_nome_treino`); handler do estado trata "cancelar", comandos reservados (/menu, treinar X) passam adiante sem bloquear, texto vazio permanece aguardando. `_process_tool_registrar` consulta `get_sessao_ativa` antes de salvar e passa `treino_nome` para `exercicio_service.registrar`; avisa se não há sessão ativa (não bloqueia o registro). `exercicio_service.registrar` ganhou parâmetro `treino_nome: str | None = None`. Commit `0decbe3` em produção.
- **Maria id=6 confirmada ativa ✅** — duplicata id=5 mantida como lixo silencioso (documentado em Limpeza/acompanhamento).

### Segurança
- **`ADMIN_API_KEY` rotacionada** — nova chave gerada e atualizada no Render. Chave anterior descartada. 🔐 Incidente registrado: chave vazou inline em `curl -H` no chat. Regra: NUNCA colar valores de chave em comandos — usar variável de shell extraída silenciosamente.

### Limpeza confirmada
- **`HOTMART_*` vars** — apagadas do painel Render (estavam órfãs pós-migração para Kiwify) e confirmadas ausentes do `.env` local (grep retornou 0 linhas).
- **`USDA_API_KEY`** — confirmada ativa no Render; testada em produção com busca real.
- **Salvamento por keyword (`Lugar C`)** — confirmado removido do código. Banco tem apenas 5 treinos reais (todos `origem="proprio"`): Peito A (133), Peito 3 (131), PEITO 3 (129), PEITO 1 (128), PERNA 2025 (125). Pendências L647-L648 marcadas como concluídas.
- **`static/landing/motion.html`** — arquivo de 68KB não commitado, deletado. `static/landing/index.html` revertido (tinha botão "Assistir Motion 🎬" não finalizado). `LOGO PNG COM BORDA.PNG` (1.4MB) adicionado ao `.gitignore`.
- **Persistência PerfilFitness verificada** — PerfilFitness nunca é deletado em nenhuma trilha de código (zero `db.delete` em produção); cancelamento de assinatura só muda status; sem CASCADE; perfil sobrevive a cancelamento/renovação. Documentado.

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

**PARTE 2 — Séries individuais + aquecimento + estrutura de exercícios (BLOCO COESO — não fatiar):**
- **Problema de representação atual:** plano semanal hoje é 1 `Treino` com texto livre. Para "peito A de hoje vs peito A da semana passada" funcionar, cada dia precisa ser separado — N `Treinos` individuais OU lista estruturada de treinos-do-dia dentro do plano (decisão a tomar na sessão dedicada).
- **Lista estruturada de exercícios:** quando um plano é salvo, guardar `conteudo['exercicios_estruturados']` (JSON) — não só texto livre. Sem isso, detectar "esse exercício está nesse treino?" requer parse regex sobre texto gerado pelo Claude (~30% de falsos positivos).
- **Detecção de exercício fora do plano:** ao registrar exercício em sessão ativa, comparar contra `exercicios_estruturados`. Se **não** estiver, perguntar: *"esse exercício não estava no treino — quer adicionar ao treino ou salvar só como pontual?"*. "Adicionar" → grava no treino E registra execução. "Pontual" → registra execução com `treino_nome` vinculado, sem mexer no treino.
- **Séries individuais + aquecimento:** `RegistroExercicio` hoje guarda `series/reps/carga` AGREGADOS. Criar estrutura para guardar cada SÉRIE individual com carga/reps próprias + flag `is_aquecimento` (bool). Decisão pendente: tabela nova (`registros_series`) vinculada ao `RegistroExercicio`, OU coluna JSON `series_detalhe` no model existente.
- **Tool `registrar_exercicio`** passa a aceitar séries individuais (não só agregado) — mudança no input_schema e no `_process_tool_registrar`.
- **Parte 3 (apresentação) e B3 (confirmar troca de sessão)** entram na mesma sessão da Parte 2 OU logo depois — serão pequenos com a estrutura já pronta.

**PARTE 3 — Fluxo de apresentação (formato WhatsApp):**
- Ao SOLICITAR treino: lista simples "Exercício A - X aquecimentos e Y séries válidas com N repetições" + "Envie 'treinar [nome]' para iniciar".
- Ao mandar "treinar [nome]": mostrar por exercício "No seu último treino você fez: aquecimento com X, séries válidas: 1ª série X peso N reps, 2ª série...". Depende das Partes 1 e 2.

⭐ **FEEDBACK DO IGOR (31/05):** hoje, ao mandar `'treinar [nome do plano]'`, o bot só responde "Sessão iniciada" e fica esperando os registros. Isso **NÃO ATENDE** à expectativa. Ao iniciar a sessão, o bot deve:
1. Identificar **QUAL DIA** do plano semanal é (Dia 1, Dia 2... do plano salvo).
2. Mostrar o treino do dia no formato:
   `'Exercício A - X aquecimentos e Y séries válidas com N repetições'`
   `'Exercício B - X aquecimentos e Y séries válidas com N repetições'`
   `'Envie [comando] para iniciar'`
3. Após confirmação (`'treinar'` ou comando equivalente), por exercício mostrar:
   `'No seu último treino você fez: aquecimento com X, séries válidas: 1ª X reps N peso, 2ª...'`

Isso confirma que a Parte 3 depende essencialmente das Partes 1 (vínculo sessão→treino) + 2 (séries individuais + aquecimento + parsing do dia atual a partir do texto do plano). **Atacar essa apresentação como o foco principal da Parte 3.**

**REQUER:** migração(ões) nova(s) — todas MANUAIS (autogenerate inviável, banco compartilhado). Mudança em `registrar_exercicio`, no contexto, na exibição, e no parsing do "treinar".

**ORDEM ATUALIZADA (01/06 madrugada):** Parte 1 ✅ + Parte 2 Etapas 1-4 ✅. Etapa 5 original ❌ CANCELADA. Próximas = E1-E5 do REPLANEJAMENTO (alinhamento terminológico PLANO/TREINO/EXERCÍCIO + apresentação no formato que o Igor pediu). Depois disso = finalizar + auto-expira + B3.

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
- [x] **Épico Parte 1 PASSO 2 — Comando A ✅ CONCLUÍDO (31/05):** fluxo "treinar [nome]" — parser guard 0.8, herança do `treino_nome` em `registrar_exercicio`, bot pergunta se vier sem nome, handler de `aguardando_nome_treino` com tratamento de cancelar/comandos reservados. NÃO implementado (ficam pra Parte 1 estendida ou Parte 2): comando "finalizar" e auto-expiração 20min.
- [x] **Épico Parte 1 PASSO 2 — Comando B1.a ✅ CONCLUÍDO (31/05):** ao mandar "treinar" sem nome, se houver treinos salvos mostra lista numerada (até 10, mais recentes primeiro) com estado `escolhendo_treino`. Handler aceita número válido, número fora de range (repete pergunta sem limpar estado), nome livre, cancelar, e comandos reservados (limpa estado, deixa guards seguintes processar). Lista vazia → fallback `aguardando_nome_treino` (B1.b). Dois helpers locais em `process_message`: `_nome_display_treino` (prefere `conteudo["nome"]`, fallback `_titulo_treino`) e `_eh_comando_reservado` (reusado em ambos os handlers).
- [x] **Épico Parte 1 PASSO 2 — Comando B1.b.2 ✅ CONCLUÍDO (31/05):** "treinar" sem nome + lista vazia → menu de 3 opções (`lista_vazia_treino`): 1️⃣ Importar treino → `_handle_menu_item(2)` (cadastrar próprio); 2️⃣ Criar do zero → `_iniciar_coleta_treino` (9 perguntas); 3️⃣ Cancelar → limpa estado. Resposta inválida repete menu sem limpar estado. Comandos reservados (`/menu`, `treinar`) limpam estado e passam adiante. Emojis verificados byte-a-byte (U+FE0F + U+20E3, espaço após cada).
- [x] **Épico Parte 1 PASSO 2 — Comando B1.b.1 ✅ CONCLUÍDO (31/05):** item 1 do menu (criar treino personalizado) agora pede nome antes de gravar. `_gerar_treino_de_dados` não persiste mais `Treino` diretamente — seta `estado_pendente = {"tipo": "criando_treino", "fase": "nomeando_treino", "texto_gerado": reply}` e retorna o treino + pergunta de nome. `_handle_coleta_treino` ganhou fase `"nomeando_treino"` (antes de `confirmando_perfil`): valida nome (vazio / >60 chars / cancelar), grava `Treino(conteudo={"texto", "nome", "gerado_em"})`, limpa estado, retorna confirmação com sugestão de `'treinar {nome}'`. Nota: 1 chamada Claude gera plano semanal completo (Dia 1/Dia 2/...) salvo como 1 linha no banco — texto de pergunta e confirmação usa "plano" em vez de "treino" para refletir isso. SYSTEM_PROMPT proíbe RPE no output de treinos gerados.
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
- [ ] Verificar via `/admin/users/{id}/perfil` se o cadastro de perfil do Igor persistiu mesmo após reclamação de "dados perdidos" (30/05).
- ✅ CONCLUÍDO 30/05 — limite de 6 análises de refeição/dia removido. Constante LIMITE_FOTOS_DIA removida de nutricao_service.py; guard em claude_service.py removido; menções no SYSTEM_PROMPT e no menu item 7 removidas. Agora usuário pode analisar quantas refeições quiser/dia.

### Grandes (sessão dedicada)
- [ ] Treino guiado ao vivo: treino completo -> cliente "estou pronto" -> bot manda exercício a exercício -> cliente reporta carga/reps -> bot indica descanso (aquecimento 1 min, válidas caso a caso) e próxima série.
- [ ] Integração com wearables (Garmin/Apple Watch/Samsung/Xiaomi/Amazfit/Huawei): projeto à parte. Avaliar focar 1 plataforma (Garmin) ou usar leitura de arquivo exportado do relógio.

### Lançamento
- [ ] Render plano Free "dorme" com inatividade (1a mensagem lenta ~50s). Avaliar plano pago antes do lançamento.
- [ ] Teste de compra nova de ponta a ponta com número que nunca comprou.
- [ ] Validar valor pago no webhook Kiwify (segurança extra).
- [ ] Migrar memória de dor/desconforto para o banco de dados (hoje é só por conversa).
- [ ] Configurar alerta de saldo baixo / recarga automática de créditos no Console da Anthropic (o bot parou uma vez por créditos zerados).

### Limpeza / acompanhamento
- ✅ CONFIRMADO 30/05: id=6 (Maria Eduarda, telefone 13 dígitos, assinatura anual ATIVA até 2027-05-22) está usando o bot ativamente com conversas registradas.
- ⚠️ MANTIDA: id=5 (12 dígitos, sem assinatura, sem conversas) deixada como lixo silencioso — nunca recebe mensagens porque o normalize_phone do subscription_service.py converte 12→13 dígitos. Causa raiz documentada: id=5 foi criado antes da normalização ser aplicada; id=6 é o canônico.
- [ ] Lembrete: assinatura anual do criador expira ~maio/2027.

### Treino — novos refinos
- [x] Ao criar treino, perguntar o sexo da pessoa. — ✅ CONCLUÍDO 30/05: sexo coletado obrigatoriamente na Etapa 1 do cadastro de perfil antes de qualquer uso do bot.
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

---

## PRÓXIMA SESSÃO (retomada após /clear)

**Foco:** E1 do REPLANEJAMENTO — apagar registros antigos e começar alinhamento terminológico PLANO/TREINO/EXERCÍCIO.

**Decisões já tomadas (não reperguntar):**
1. ✅ Plano semanal: 1 `Treino` com `conteudo["dias"]` estruturado (JSON) — implementado na Etapa 2.
2. ✅ Séries individuais: coluna JSON `series_detalhe` no `RegistroExercicio` existente — migration 014 aplicada.
3. ✅ Extração estruturada: `extrair_estrutura_treino` (2ª chamada Claude com tool) — itens 1 e 2 do menu funcionando.
4. ✅ Etapa 4: tool `registrar_exercicio` aceita `series_detalhe` opcional — validado em produção.
5. Match parcial case-insensitive para detecção de exercício fora do treino.
6. Sempre perguntar (a cada exercício fora do treino) — não auto-adicionar.
7. Se 1 plano → vai direto pra lista de TREINOS (dias). Se 2+ planos → pergunta PLANO primeiro.
8. Registros antigos (5 de teste, `treino_nome` com nome do plano) serão APAGADOS — recomeço limpo.

**Reconhecimento obrigatório no início:**
- `git status` + `git log --oneline -8`
- `alembic current` (deve estar em 014)
- Ler seção REPLANEJAMENTO Parte 2/3 acima para entender glossário e fluxo-alvo completo.

**Cuidados:**
- Render free SEM backup automático — testar upgrade/downgrade/upgrade local se houver nova migration.
- Auto-migrate roda no Dockerfile: commit + push = migration aplicada em produção automaticamente.
- Banco compartilhado com Evolution API — autogenerate inviável, migrations sempre MANUAIS.

**Status do produto:** migration 014 em produção. Extração estruturada funcionando nos dois fluxos (id=140 e id=141). Tool registrar_exercicio aceita series_detalhe (validado em produção). PRÓXIMA SESSÃO: alinhamento de terminologia PLANO/TREINO/EXERCÍCIO.


=================================================================
ATUALIZACAO 01/06/2026 (MAIS RECENTE - substitui qualquer "estado/proximo passo" anterior deste arquivo)
=================================================================

METODO (lembrete que se provou essencial): Claude Code COLAPSA outputs > ~18 linhas. Recon de codigo SEMPRE por janelas pequenas (awk 'NR>=X && NR<=Y {printf "%d|%s\n",NR,$0}'), nunca confiar no RESUMO do Claude Code. Mudanca em fluxo central: revisar DIFF LITERAL (copiar p/ Desktop e anexar no chat) antes de qualquer push. py_compile e gate de sintaxe, nao de logica.

GLOSSARIO: PLANO = Treino no banco (1 linha). TREINO = dia em conteudo["dias"][i] (ex "Peito A"). EXERCICIO = item em dias[i].exercicios[j]. treino_nome (SessaoTreino/RegistroExercicio) = nome do TREINO (dia).

EPICO DE TREINOS - estado:
[OK] E1 - registros antigos apagados (recomeco limpo).
[OK] E2 - "treinar" oferece os TREINOS (dias), nao os PLANOS. Commit 028e774, VALIDADO em producao 01/06.
     - escolhendo_treino agora carrega dias_nomes + plano_id (era ids/labels).
     - NOVO estado escolhendo_plano: 2+ planos -> pergunta o plano primeiro; 1 plano -> direto pros dias; 0 -> menu lista_vazia (inalterado).
     - Q1: nome de dia digitado casa contra os dias do plano (case-insensitive, parcial) -> nome canonico; 0/ambiguo -> repergunta.
     - Q2: plano sem "dias" -> aceita nome de dia livre.
     - Helpers _dias_do_plano e _casar_dia (inline em process_message, ~apos _eh_comando_reservado).

[ATIVO] E3 - APRESENTACAO DO TREINO ANTES DE INICIAR  <- PROXIMO PASSO
     - Apos escolher o TREINO (dia), o bot NAO abre sessao na hora. Apresenta os exercicios estruturados:
         "Segue seu treino de *Peito A*:
          - Supino reto: 2 aquecimentos + 3 series de 8-10
          - Crucifixo: 3 series de 12-15
          Envie *treinar* para iniciar."
     - Le conteudo["dias"][i].exercicios (campos: nome, series_validas, aquecimento, reps, descanso_seg, observacoes).
     - NOVO estado "aguardando_inicio_treino" (carrega nome do dia + plano_id + dia escolhido).
     - So quando o usuario manda "treinar" (confirmacao) e que iniciar_sessao abre a SessaoTreino. Sem confirmacao, sessao NAO abre.
     - HOJE a msg "Sessao iniciada... manda os exercicios" e o comportamento antigo; E3 troca por apresentar->confirmar.
     - RECON antes de codar: campos de exercicio em dias[i].exercicios; TODOS os call-sites atuais de iniciar_sessao (escolhendo_treino numero/nome; transicao do escolhendo_plano; "treinar [nome]" direto ~2944-2950) -> DECIDIR se "treinar [nome]" direto tambem apresenta+confirma.

[PENDENTE] E4 - deteccao de exercicio fora do treino (match parcial case-insensitive; perguntar adicionar/pontual). plano_id da sessao provavelmente precisara ser persistido (migration?).
[PENDENTE] E5 - historico serie a serie ao registrar (le series_detalhe dos ultimos registros do mesmo exercicio + treino_nome).

PENDENCIAS NOVAS (mini-epico "gestao de planos" - DEPOIS de E3/E4/E5; pedido Igor 01/06):
  P1 - Adesao de 90 dias: a partir da criacao do 1o plano, o bot NAO fica oferecendo criar novos; em vez disso reforca manter o mesmo plano por >=90 dias (pra ver resultados e refinar), permitindo editar 1 exercicio ou outro. Se o cliente insistir em criar novo apos o aviso, PERMITIR.
       A DEFINIR: ancora = data de criacao do 1o Treino (verificar se Treino tem created_at); reforco dispara so ao pedir plano novo na janela ou tambem proativo?; ONDE o bot hoje oferece criar (provavel /menu).
  P2 - 1 plano por MODALIDADE por usuario (anti-compartilhamento de conta). PROVAVEL MIGRATION: coluna "modalidade" no Treino.
       A DEFINIR: o que e "modalidade" (opcoes do menu de criacao? musculacao/hibrido/funcional?); ao criar 2o da mesma modalidade -> BLOQUEAR ou SUBSTITUIR.
  CONFLITO P1xP2: se so pode 1 por modalidade e o cliente insiste em criar outro da mesma -> vira SUBSTITUIR o atual, nao coexistir. ALINHAR.

LANCAMENTO (inalterado): Kiwify (tokens/links), OPENAI_API_KEY (Whisper/audio), upgrade Render (free dorme 50s), teste compra ponta-a-ponta, alerta de saldo baixo Anthropic.

=================================================================
ATUALIZACAO 01/06/2026 #2 (MAIS RECENTE - substitui blocos de estado anteriores)
=================================================================

EPICO DE TREINOS:
[OK] E1, E2 (commit 028e774, validado em producao).
[~] E3 COMMIT 1 - CAMINHO DO MENU: apresenta os exercicios do dia + exige confirmacao "treinar" antes de abrir a sessao.
    - 4 edits em claude_service.py, diff revisado e APROVADO; py_compile OK (+90/-12).
    - Helpers novos: _exercicios_do_dia, _apresentar_treino, _apresentar_ou_iniciar. Estado novo: aguardando_inicio_treino.
    - Fluxo: escolhe dia -> _apresentar_ou_iniciar -> se o dia tem exercicios estruturados, APRESENTA + seta estado aguardando_inicio_treino; senao (plano sem dias / Q2) inicia direto. Confirmacao com treinar/sim/iniciar/bora/comecar/vamos abre a sessao.
    - CONFIRMAR NO INICIO DA PROXIMA SESSAO: (1) commit/push foi feito? rodar git log --oneline -3 (msg "feat(treino): E3 commit 1..."); (2) VALIDAR em producao no WhatsApp: treinar -> escolhe plano -> escolhe dia -> deve aparecer "Segue seu treino de *X*: ... Envie *treinar* para iniciar" -> treinar -> "Sessao iniciada".
    - NAO tocados: atalho "treinar [nome]" direto (~L3066) e handler legado aguardando_nome_treino (~L3046) continuam abrindo sessao direto.

[PENDENTE] E3 COMMIT 2 - ATALHO "treinar [nome]" direto (Igor: opcao B expandida). Spec:
    - [nome] casa com um TREINO (dia): apresenta aquele dia + confirma. Mesmo nome em 2+ planos -> perguntar qual plano.
    - [nome] casa com um PLANO: mostra os dias daquele plano (como escolher o plano no menu).
    - [nome] NAO casa nada: perguntar -> (a) PONTUAL (one-off com o nome, sem vinculo a plano); (b) ADICIONAR a um treino (criar [nome] como novo dia num plano existente, definir exercicios); (c) CRIAR um (fluxo criar plano do zero).
    - DEFINIR ANTES DE CODAR (Q1-Q5): semantica exata de "adicionar" e "criar". ATENCAO: interage com a regra futura "1 plano por modalidade" (Igor lembrou) -> criar/adicionar tem que respeitar esse limite.

[PENDENTE] E4 - deteccao de exercicio fora do treino (match parcial case-insensitive; perguntar adicionar/pontual). plano_id da sessao provavelmente precisara ser persistido (migration?).
[PENDENTE] E5 - historico serie a serie ao registrar (le series_detalhe do mesmo exercicio + treino_nome).

PENDENCIAS NOVAS (mini-epico "gestao de planos", DEPOIS de E3/E4/E5):
  P1 - Adesao 90 dias: a partir do 1o plano, NAO oferecer criar novos; reforcar manter o plano >=90 dias (permite editar 1 exercicio ou outro); se insistir apos o aviso, permitir. Definir: ancora (created_at do 1o Treino?), gatilho (so ao pedir novo, ou proativo?), onde o bot hoje oferece criar.
  P2 - 1 plano por MODALIDADE por usuario (anti-compartilhamento de conta). Provavel migration (coluna "modalidade" no Treino). Definir: o que e "modalidade"; 2o da mesma modalidade -> bloquear ou substituir.
  CONFLITO P1xP2: insistir em criar outro da mesma modalidade -> SUBSTITUIR, nao coexistir. Alinhar.

METODO (manter sempre): recon por janelas pequenas (Claude Code COLAPSA outputs >~18 linhas e o RESUMO dele NAO e confiavel - ja errou linha 3177 vs 1516); para mudanca em fluxo central: dump do diff -> copiar pro Desktop -> ANEXAR no chat -> revisar literal ANTES do push. py_compile e gate de sintaxe, nao de logica.

LANCAMENTO (inalterado): Kiwify, OPENAI_API_KEY (Whisper/audio), upgrade Render, teste compra ponta-a-ponta, alerta saldo Anthropic.

=================================================================
ATUALIZACAO 01/06/2026 #3 (MAIS RECENTE)
=================================================================
SESSAO GUIADA - EM ANDAMENTO (vira a proxima entrega; "E3 commit 2 / atalho treinar [nome]" segue pendente DEPOIS).
Decisao Igor (Opcao 1): ao confirmar "treinar", o bot CONDUZ exercicio a exercicio.

APRESENTACAO (antes do treinar) - novo formato:
  "Segue seu treino de *X*:" + por exercicio "<nome> - A aquecimentos e V series validas com R repeticoes" (omite aquecimentos se 0) + "Envie *treinar* para iniciarmos o treino".

GUIADO (apos treinar):
  - Anuncia "Exercicio n/total - *nome*: prescricao".
  - Set no formato REPS x PESO (ex: 8 x80 = 8 reps com 80kg). Aquecimento: prefixo "aquecimento" ou "aq" (ex: aquecimento 12 x40). Rotulo automatico: sem prefixo, e aquecimento ate bater o prescrito, depois validas.
  - AUTO-AVANCO: ao atingir o nº de validas prescrito, registra e passa pro proximo sozinho. "proximo" forca avanco (menos validas); "pular" pula sem registrar; "cancelar" encerra; fim -> finalizada_em + "Treino concluido".
  - Registro: reusa _derivar_agregados_de_series + exercicio_service.registrar (series_detalhe = lista de {carga_kg, repeticoes, is_aquecimento}). Variacao anormal (>20%) NAO entra no guiado no G1.

G1 = sem historico (so prescricao). G2 = historico serie a serie ("no seu ultimo treino voce fez...", le series_detalhe da ultima execucao; cuidado: historico hoje casa por exercicio+posicao, pular desloca posicao - resolver no G2).

PENDENCIA NOVA (Igor pediu pra NAO esquecer): SERIES EXTRAS - hoje o auto-avanco dispara exatamente no nº de validas prescrito; permitir series validas ALEM do prescrito (drop set / extra) fica pra depois.
=================================================================

=================================================================
ATUALIZACAO 02/06/2026 #4 (MAIS RECENTE - substitui blocos de estado anteriores)
=================================================================

EPICO DE TREINOS - estado consolidado:
[OK] E1, E2 (028e774), E3 commit 1 (42f7092) - validados em producao.
[OK] G1 - SESSAO GUIADA: ao confirmar "treinar", o bot conduz exercicio a exercicio. VALIDADO em producao.
     - Apresentacao: "Segue seu treino de *X*:" + por exercicio "*nome* - A aquecimentos e V series validas com R repeticoes" (nome em NEGRITO, linha em branco entre exercicios) + "Envie *treinar* para iniciarmos o treino". (commit 9ab4ea6 = formatacao negrito/espacamento, validado)
     - Guiado: "Bora!" + "Exercicio n/total - *nome*: prescricao". Set REPS x PESO (ex: 8 x80). Aquecimento: prefixo "aquecimento"/"aq". Rotulo hibrido (sem prefixo = aquecimento ate bater o prescrito, depois validas; prefixo forca aquecimento). AUTO-AVANCO ao atingir as validas prescritas. "proximo" forca avanco; "pular" pula sem registrar; fim -> finalizada_em + "Treino concluido".
     - Helpers: _prescricao_str, _parse_set, _anunciar_exercicio_guiado, _registrar_guiado. Estado novo: sessao_guiada.
[OK] FINALIZAR (commit 1589669) - CODIGO NO AR, VALIDAR: comando "finalizar"/"finalizar treino"/"encerrar"/"encerrar treino" SALVA o exercicio em andamento (buffer parcial) e fecha a sessao. "cancelar" virou elif (descarta sem salvar). Opcao *finalizar* aparece no anuncio e na msg de "nao entendi".
[OK] G2 - HISTORICO no anuncio guiado (cobre o antigo E5) - CODIGO NO AR, VALIDAR:
     - Cada exercicio mostra "Sem historico ainda - bora marcar a primeira!" OU "Ultimo: aquec 12x40kg ... validas 8x80kg ...", lendo series_detalhe da ultima execucao.
     - Casa por exercicio + treino_nome (NAO por posicao) - resolve o "pular" deslocar posicoes. Nova funcao exercicio_service.get_ultima_execucao. Helper _historico_exercicio_str (self-fetch do treino_nome via get_sessao_ativa).
     - Commit 1589669 tambem REMOVEU excluir_data=sessao_data -> historico considera o MESMO dia (testavel hoje).
     - VALIDAR: treinar o MESMO dia ja feito -> "Ultimo:" tem que vir DETALHADO (prova que series_detalhe gravou). Se vier so agregado, investigar o write. Admin: GET /admin/users/1/registros-exercicio?limit=8.

PENDENTE DE VALIDACAO (proxima sessao): (1) historico detalhado no WhatsApp; (2) finalizar no meio de um exercicio salva parcial + fecha.

EPICO DE TREINOS - restante:
[PENDENTE] E3 COMMIT 2 - atalho "treinar [nome]" direto (Igor: opcao B expandida).
    - [nome] casa um TREINO (dia): apresenta + confirma; mesmo nome em 2+ planos -> pergunta qual plano.
    - [nome] casa um PLANO: mostra os dias.
    - [nome] NAO casa: pergunta -> (a) PONTUAL; (b) ADICIONAR como novo dia num plano existente; (c) CRIAR plano do zero.
    - Definir semantica de "adicionar"/"criar". Interage com a regra futura "1 plano por modalidade".
[PENDENTE] E4 - deteccao de exercicio fora do treino durante a sessao (match parcial case-insensitive; perguntar adicionar/pontual). plano_id da sessao provavelmente precisara ser persistido (migration?).
[PENDENTE] SERIES EXTRAS - hoje o auto-avanco dispara EXATAMENTE no nº de validas prescrito; permitir validas ALEM do prescrito (drop set/extra) fica pra depois.

MINI-EPICO "gestao de planos" (DEPOIS do epico de treino):
  P1 - Adesao 90 dias: a partir do 1o plano, NAO oferecer criar novos; reforcar manter o plano >=90 dias (permite editar 1 exercicio ou outro); se insistir apos o aviso, permitir. Definir: ancora (created_at do 1o Treino?), gatilho (so ao pedir novo, ou proativo?), onde o bot hoje oferece criar.
  P2 - 1 plano por MODALIDADE por usuario (anti-compartilhamento). Provavel migration (coluna "modalidade" no Treino). Definir: o que e "modalidade"; 2o da mesma -> bloquear ou substituir.
  CONFLITO P1xP2: insistir em criar outro da mesma modalidade -> SUBSTITUIR, nao coexistir.

METODO (manter sempre): Claude Code COLAPSA outputs >~18 linhas e o RESUMO dele NAO e confiavel. Recon por janelas pequenas (awk). Mudanca em fluxo central: dump do diff -> Desktop -> ANEXAR no chat -> revisar LITERAL antes do push. py_compile = gate de sintaxe, nao de logica. Uma coisa de cada vez, validar em producao entre etapas.

LANCAMENTO (inalterado): Kiwify (tokens/links), OPENAI_API_KEY (Whisper/audio), upgrade Render (free dorme ~50s), teste compra ponta-a-ponta, alerta saldo baixo Anthropic.
=================================================================

=================================================================
ATUALIZACAO 02/06/2026 #5 (MAIS RECENTE)
=================================================================
[OK] E3 COMMIT 2 (E3c2) - atalho "treinar [nome]" esperto. VALIDADO em producao.
    - [nome] casa um DIA (em qualquer plano) -> apresenta + confirma (_apresentar_ou_iniciar). Mesmo dia em 2+ planos -> escolhendo_plano.
    - [nome] casa um PLANO -> lista os dias (helper novo _mostrar_dias_plano -> escolhendo_treino).
    - [nome] NAO casa -> estado treinar_nao_casou, menu: 1 pontual (sessao livre) / 2 importar (_handle_menu_item(2)) / 3 criar do zero (_iniciar_coleta_treino) / 4 cancelar.
    - Precedencia: dia -> plano -> nada. NAO toca em modalidade (P2 gateia o "criar" no futuro, num lugar so).

EPICO DE TREINOS FECHADO: E1, E2, E3c1, E3c2, G1, G2, finalizar - todos no ar e validados.

RESTANTE / PROXIMOS:
[PENDENTE] E4 - deteccao de exercicio fora do treino durante a sessao guiada (match parcial; adicionar/pontual). plano_id da sessao provavelmente precisa ser persistido (migration?).
[PENDENTE] SERIES EXTRAS - permitir validas alem do prescrito (drop set); auto-avanco hoje dispara exatamente no prescrito.
[PENDENTE] MINI-EPICO gestao de planos: P1 (adesao 90 dias), P2 (1 plano por modalidade - provavel migration), conflito P1xP2 -> substituir.
=================================================================

[02/06 #6] E4 c1 NO AR (VALIDAR no WhatsApp): no guiado, detecta exercicio fora do treino (nome + NxR + peso opcional), pergunta se registra pontual ou ignora; volta pro exercicio do guiado preservando buffer/idx. Guard anti-falso-positivo: se o nome casar com algum do dia, cai no "nao entendi". c2 (adicionar ao plano) pendente. Series extras: DESCARTADO.

[02/06 #7] E4 COMPLETO + EPICO DE TREINO 100% FECHADO.
- Motor do guiado virou FILA REORDENAVEL: estado sessao_guiada usa "ordem" (fila de indices restantes; atual = ordem[0]) e "buffers" {str(idx): series} (series por exercicio, preservadas ao reordenar). Substituiu idx/buffer unico. Anuncio mostra o n° ORIGINAL do exercicio no plano (ordem[0]+1).
- "ocupado": troca o atual com o proximo (1,2,3,4 na 2 -> 1,3,2,4); repetido empurra mais. Aparece no anuncio.
- E4 pontual (c1): exercicio fora do plano (nome+NxR+peso opc) -> menu registrar pontual / deixa pra la, volta pro atual.
- E4 jump: nomear exercicio DO dia -> pendente: "e o n°X, vai fazer agora? SIM/NAO" (SIM move pro inicio da fila, volta pro interrompido depois); atual: "ja esta nesse"; ja feito: "ja fez". Substituiu o "nao entendi" confuso.
- Aquecimento aceito no inicio E no fim ("10 x 12 aquecimento").
- Detalhes: jump/pontual disparam so com nome+serie (regra nome+carga); a serie digitada pra referenciar e DESCARTADA no SIM do jump (loga normal depois).

RESTAM (fora do epico de treino): mini-epico gestao de planos (P1 adesao 90 dias, P2 1 plano por modalidade - provavel migration) e o bloco de LANCAMENTO (Kiwify tokens/links, OPENAI/Whisper, upgrade Render, teste compra ponta-a-ponta, alerta saldo Anthropic).

[02/06 #8] BACKLOG (anotado).

P1/P2 PLANOS (EM ANDAMENTO - decisoes travadas):
- Ao criar plano, bot PERGUNTA a modalidade (musculacao, corrida, crossfit, yoga...).
- Modalidade nova -> cria normal. Ja tem plano dessa modalidade -> msg de adesao (manter >=90 dias do 1o plano DAQUELA modalidade); se insistir -> SUBSTITUI o existente.
- Ancora 90 dias = 1o plano de cada modalidade. P1 dispara so ao pedir criar plano de modalidade que JA tem.
- 1 por modalidade (varios planos ok, 1 por modalidade). Modalidade provavelmente no Treino.conteudo (JSON) p/ evitar migration.

OUTRAS PENDENCIAS (ordem sugerida A->B->C, D no meio):
A) RAPIDOS (prompt/correcao):
  - Parar de direcionar cliente p/ app/site/plataforma (NAO existe - so WhatsApp).
  - NUNCA indicar remedio/hormonio; se pedirem -> "procure um medico, a Evolution nao faz isso". (seguranca)
  - Historico de refeicoes POR DIA (00:01-23:59), completo. Hoje junta tudo num dia so (bug de data).
B) MEDIOS (fluxo):
  - Dieta UNICA por cliente (criar nova apaga a anterior).
  - Comando "limpar meus dados": apaga tudo registrado, EXCETO itens nao-editaveis do perfil. (destrutivo -> confirmacao dupla)
  - Redesenho /menu: "gerar card" / "treinar" / "ver minhas refeicoes feitas" / "ver meu plano alimentar".
C) GRANDE (imagem/card - sessao propria, pipeline gerar imagem + enviar via Meta):
  - Card de fim de treino (IMAGEM): gasto calorico total, tempo de treino, kg total levantado, % evolucao (ou n° reps se sem evolucao positiva).
  - Submenu "gerar card": 1 ultimo treino, 2 exercicio especifico, 3 treino especifico. (layout a definir)
D) PRODUTO/ANALISE:
  - Definir lista de modalidades disponiveis.
  - Analisar as skills de geracao de treino e dieta.

[04/06 #9] MINI-ÉPICO GESTÃO DE PLANOS (P1/P2) — ENTREGUE, PENDENTE DE TESTE

REGRA: 1 plano por modalidade. Modalidade = musculacao/calistenia/yoga/pilates/
corrida/hibrido/funcional/crossfit/mobilidade (tipo_canon). Estrutura SEMPRE
Plano→Treinos(dias): todos os treinos de uma modalidade ficam num plano só.

COMPORTAMENTO:
- Criar/importar de modalidade NOVA → cria direto.
- Criar/importar de modalidade que JÁ tem plano → bot para e pergunta substituir
  (1 SIM apaga o antigo e salva o novo / 2 NÃO mantém o atual e descarta).
- Aviso 90 dias muda só o TOM: <90 dias reforça "ideal manter"; >90 não cobra.
- Âncora 90 dias = plano mais antigo daquela modalidade (Treino.criado_em).

ONDE FICA: modalidade gravada em Treino.conteudo["modalidade"] (JSON, sem migration).
Planos criados ANTES do 1a ficam sem a tag → invisíveis ao gate (esperado/aceito).

IMPLEMENTAÇÃO:
- treino_service.planos_da_modalidade(user_id, modalidade, db) → planos reais da
  modalidade (usa listar_treinos, checa conteudo["modalidade"]).
- Fonte única de modalidades: MODALIDADE_MAP / MODALIDADE_CANON (claude_service,
  nível de módulo). _gerar_treino_de_dados referencia elas (tipo_map/tipo_canon).
- CRIAR DO ZERO (1a commit 6b09c0e + 1b): _gerar_treino_de_dados ganhou confirmado:bool.
  Gate antes da chamada da IA. Estado criando_treino fase confirmando_substituicao.
  Apaga antigo no save (fase nomeando_treino) se substituir_modalidade setado. Atômico.
- IMPORTAR (Estágio 2, commit 5b0870a): _process_tool_cadastrar_treino NÃO salva na
  hora — extrai dias, faz stash no estado importando_modalidade, devolve instrução
  pra IA perguntar a modalidade (lista numerada, resposta = número). Handlers
  determinísticos importando_modalidade / importando_substituicao em process_message.
  Save real via helper _finalizar_importacao (apaga antigo + cadastrar_treino_proprio
  + patch modalidade/dias, commit único do handler = atômico).

PENDENTE DE TESTE (créditos Anthropic zerados em 04/06 — bot parou; ver lançamento).
Validar no WhatsApp quando recarregar:
1. GERADO: criar musculação → criar outro musculação (aviso + SIM/NÃO) → criar corrida (direto).
2. IMPORTADO: colar plano → bot pergunta modalidade → número → se conflito, substituir SIM/NÃO.
Conferir /admin/users/1/treinos: 1 plano por modalidade, com tag modalidade no conteudo.

PRÓXIMO: backlog A (prompt/correções) → B (fluxo) → C (card imagem) → D (produto);
lançamento (Kiwify, OPENAI_API_KEY/Whisper, upgrade Render, teste compra, alerta saldo Anthropic).
