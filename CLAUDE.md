# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Dev server (porta 8001, reload automático)
uvicorn main:app --port 8001 --reload

# Aplicar migrations
alembic upgrade head

# Criar nova migration após alterar models
alembic revision --autogenerate -m "descricao"

# Ativar assinatura de teste localmente (nunca usar em produção)
DATABASE_URL=<url> python scripts/activate_test.py <telefone> [anual|trimestral]

# Dependências
pip install -r requirements.txt
```

O arquivo `.env` é obrigatório na raiz. Use `.env.example` como referência. Variáveis obrigatórias: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `EVOLUTION_API_URL`, `EVOLUTION_API_TOKEN`, `EVOLUTION_API_INSTANCE`, `ADMIN_API_KEY`.

## Arquitetura

SaaS de fitness no WhatsApp: usuários interagem com o bot "Evo" via WhatsApp → Evolution API captura as mensagens e entrega via webhook → FastAPI processa → Claude responde → Evolution API envia de volta.

### Fluxo principal (mensagem recebida)

```
WhatsApp → Evolution API → POST /webhook/whatsapp
  → subscription_service.get_or_create_user()        # identifica por telefone (só dígitos)
  → deduplicação: user.ultima_mensagem_id == message_id → retorna "duplicate"
  → subscription_service.check_active_subscription() # filtra status='ativo' AND data_fim >= hoje
  → persiste ultima_mensagem_id antes de processar    # garante dedup mesmo se send falhar
  → claude_service.process_message()                 # chama Claude com prompt caching
  → whatsapp_service.send_message()                  # POST na Evolution API (retry 3x, backoff 1s/2s/4s)
```

Se o usuário não tiver assinatura ativa, recebe os links de pagamento e o fluxo encerra. Todos os handlers retornam HTTP 200 mesmo em erro para evitar retentativas do Evolution API.

### WhatsApp LID Addressing

Alguns usuários do WhatsApp multi-device enviam mensagens com `remoteJid` no formato `700146790417@lid` e `addressingMode: "lid"`. Nesses casos, o número real está em `remoteJidAlt` (`5511999328525@s.whatsapp.net`). O `get_phone()` em `app/schemas/whatsapp.py` já trata isso automaticamente.

### Fluxo Hotmart (compra aprovada)

```
Hotmart → POST /webhook/hotmart
  → valida HMAC-SHA256(body, HOTMART_WEBHOOK_SECRET)
  → apenas event = "PURCHASE_APPROVED" é processado
  → subscription_service.activate_subscription()  # upsert usuário + cria Assinatura
  → whatsapp_service.send_welcome_message()
```

Deduplicação por `hotmart_transaction_id` — reprocessar a mesma transação é no-op.

### Claude AI (`app/services/claude_service.py`)

- Modelo: configurado via `settings.CLAUDE_MODEL` (default `claude-sonnet-4-6`)
- **Prompt caching:** system prompt enviado com `cache_control: {"type": "ephemeral"}` — reduz ~90% dos tokens do system prompt (TTL 5 min na Anthropic)
- Histórico da conversa armazenado em `Conversa.mensagens` (coluna JSON, máximo 20 mensagens passadas para a API)
- `Conversa` é 1:1 com `Usuario` — toda a thread numa única linha
- Quando a resposta contém palavras-chave de treino ou dieta, um registro `Treino`/`Dieta` é criado automaticamente

### Autenticação admin

Todos os endpoints `GET /admin/*` exigem header `X-Admin-Key: <ADMIN_API_KEY>`. A dependency `require_admin_key` em `app/middleware/auth.py` retorna 403 se ausente ou incorreto.

### Logs

Todos os logs são JSON estruturado via `pythonjsonlogger`. Padrão de chamada:
```python
logger.info("event_name", extra={"user_id": ..., "key": "value"})
logger.error("event_name", extra={"error": str(e)}, exc_info=True)
```

### Modelos de dados

| Tabela | Chave de negócio | Observação |
|--------|-----------------|------------|
| `usuarios` | `telefone` (único, só dígitos) | `ultima_mensagem_id` usado para deduplicação de webhooks |
| `assinaturas` | `hotmart_transaction_id` | plano: `trimestral` (90d) / `anual` (365d) |
| `conversas` | `user_id` (único) | JSON array de `{role, content, timestamp}` |
| `treinos` / `dietas` | `user_id` | auto-gerados pelo `claude_service` por keywords |

### Roteamento

| Prefixo | Arquivo | Descrição |
|---------|---------|-----------|
| `GET /` | `main.py` | health check — verifica banco + Evolution API |
| `POST /webhook/whatsapp` | `app/routers/whatsapp.py` | recebe eventos do Evolution API |
| `POST /webhook/hotmart` | `app/routers/hotmart.py` | recebe compras aprovadas |
| `GET /admin/users` | `app/routers/admin.py` | lista usuários — exige `X-Admin-Key` |
| `GET /admin/users/{id}/treinos\|dietas\|conversa` | `app/routers/admin.py` | histórico por usuário — exige `X-Admin-Key` |

### Infraestrutura

- **FastAPI:** Render (free tier, Docker). Build e migrations (`alembic upgrade head`) ocorrem automaticamente no startup. Cada push no `master` dispara deploy automático.
- **Evolution API:** roda como processo separado (Node.js). Localmente, inicie com `start-evolution.bat` em `C:\Users\Igor Hanate\evolution-api\` e exponha via Cloudflare tunnel (`cloudflared tunnel --url http://localhost:8080`). Configure `EVOLUTION_API_URL` no Render com a URL do tunnel.
- **Banco:** PostgreSQL no Render (free tier). Migration chain: `001` (schema inicial) → `002` (ultima_mensagem_id).

### Status atual (v1.0.0-production-ready)

- Deploy live em `https://evolutionfit-api.onrender.com`
- `ADMIN_API_KEY` configurada no Render (valor em `scripts/activate_test.py` docs)
- Hotmart vars (`HOTMART_WEBHOOK_SECRET`, `HOTMART_OFFER_ID_*`, `PAYMENT_LINK_*`) ainda com valor `PENDENTE` — configurar antes de ativar vendas
- Número bot `551153043378` pode ter restrição de envio — aquecer antes de lançar
