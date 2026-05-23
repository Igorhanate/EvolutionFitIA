# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### Ferramentas Claude (TOOLS — 13 tools)

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
| `treinos` / `dietas` | `user_id` | auto-gerados por keywords; `origem:"proprio"` se externo |
| `registros_exercicio` | `user_id + sessao_data + posicao_sessao` | 1RM por Epley/Brzycki/Lander |
| `medidas_corporais` | `user_id + data_medicao` | peso + circunferências (nullable) |
| `fotos_composicao` | `user_id` | só `gordura_estimada_pct` + texto; foto não armazenada |
| `registros_refeicao` | `user_id + data_refeicao` | macros confirmados; limite 6/dia |
| `metas_nutricionais` | `user_id` (`ativa=True`) | nova meta desativa anteriores |
| `habitos_dia` | `user_id + data` (unique) | `agua_ml`, `fumou`, `bebeu_alcool`, `suplementos_tomados` |
| `perfis_habitos` | `user_id` (único) | lista de suplementos + datas início de streak |

### Migrations Alembic

`001` → `002` → `003` → `004` → `005` → `006` → `007` — **HEAD = 007**

| # | O que cria |
|---|------------|
| 001 | Schema inicial (usuarios, assinaturas, conversas, treinos, dietas) |
| 002 | `ultima_mensagem_id` em usuarios |
| 003 | `registros_exercicio` |
| 004 | `medidas_corporais` + `fotos_composicao` |
| 005 | `registros_refeicao` |
| 006 | `metas_nutricionais` |
| 007 | `habitos_dia` + `perfis_habitos` |

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

## Variáveis de ambiente no Render

| Variável | Status |
|----------|--------|
| `DATABASE_URL` | ✅ configurada (fromDatabase) |
| `ANTHROPIC_API_KEY` | ✅ configurada |
| `META_PHONE_NUMBER_ID` | ✅ `1191798997340349` — número definitivo +55 11 5304-3378 |
| `META_ACCESS_TOKEN` | ✅ token permanente configurado |
| `META_WEBHOOK_VERIFY_TOKEN` | ✅ configurada (`evfit-webhook-verify-2026`) |
| `META_APP_SECRET` | ✅ configurada |
| `ADMIN_API_KEY` | ✅ configurada |
| `OPENAI_API_KEY` | ⚠️ pendente — necessário para reativar transcrição de áudio |
| `HOTMART_WEBHOOK_SECRET` | ⚠️ pendente — substituir por Kiwify |
| `HOTMART_OFFER_ID_*` | ⚠️ pendente — substituir por Kiwify |
| `PAYMENT_LINK_*` | ⚠️ pendente — atualizar com links reais da Kiwify |

## Logs

JSON estruturado via `pythonjsonlogger`:
```python
logger.info("event_name", extra={"user_id": ..., "key": "value"})
logger.error("event_name", extra={"error": str(e)}, exc_info=True)
```

---

## PENDÊNCIAS / ROADMAP (melhorias a fazer)

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
