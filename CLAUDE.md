# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Dev server (porta 3000, reload automático)
python -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload

# Aplicar migrations
python -m alembic upgrade head

# Criar nova migration após alterar models
python -m alembic revision --autogenerate -m "descricao"

# Dependências
pip install -r requirements.txt
```

O arquivo `.env` é obrigatório na raiz. Use `.env.example` como referência.

## Arquitetura

SaaS de fitness no WhatsApp: usuários interagem com o bot "Evo" via WhatsApp → Evolution API captura as mensagens e entrega via webhook → FastAPI processa → Claude responde → Evolution API envia de volta.

### Fluxo principal (mensagem recebida)

```
WhatsApp → Evolution API → POST /webhook/whatsapp
  → subscription_service.get_or_create_user()   # identifica por telefone (só dígitos)
  → subscription_service.check_active_subscription()  # filtra status='ativo' AND data_fim >= hoje
  → claude_service.process_message()            # chama Claude, persiste histórico
  → whatsapp_service.send_message()             # POST na Evolution API
```

Se o usuário não tiver assinatura ativa, recebe os links de pagamento e o fluxo encerra. Todos os handlers retornam HTTP 200 mesmo em erro para evitar retentativas do Evolution API.

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

- Modelo: `claude-sonnet-4-6`
- Histórico da conversa armazenado em `Conversa.mensagens` (coluna JSON, máximo 20 mensagens passadas para a API)
- `Conversa` é 1:1 com `Usuario` — toda a thread numa única linha
- Quando a resposta contém palavras-chave de treino ou dieta, um registro `Treino`/`Dieta` é criado automaticamente (persistência para consulta no admin)

### Modelos de dados

| Tabela | Chave de negócio | Observação |
|--------|-----------------|------------|
| `usuarios` | `telefone` (único, só dígitos) | nome/email preenchidos na primeira compra |
| `assinaturas` | `hotmart_transaction_id` | plano: `trimestral` (90d) / `anual` (365d) |
| `conversas` | `user_id` (único) | JSON array de `{role, content, timestamp}` |
| `treinos` / `dietas` | `user_id` | auto-gerados pelo `claude_service` por keywords |

### Roteamento

| Prefixo | Arquivo | Descrição |
|---------|---------|-----------|
| `GET /` | `main.py` | health check |
| `POST /webhook/whatsapp` | `app/routers/whatsapp.py` | recebe eventos do Evolution API |
| `POST /webhook/hotmart` | `app/routers/hotmart.py` | recebe compras aprovadas |
| `GET /admin/users` | `app/routers/admin.py` | lista usuários (sem autenticação) |
| `GET /admin/users/{id}/treinos\|dietas\|conversa` | `app/routers/admin.py` | histórico por usuário |

### Infraestrutura

A Evolution API roda como processo separado (Node.js, porta 8080) e compartilha o mesmo banco PostgreSQL. Localmente, inicie com `start-evolution.bat` em `C:\Users\Igor Hanate\evolution-api\`. Em produção, precisa de hospedagem própria com URL pública configurada em `EVOLUTION_API_URL`.

Deploy da FastAPI: Render (free tier, Docker). Build e migrations (`alembic upgrade head`) ocorrem automaticamente no startup via `CMD` do Dockerfile. Cada push no `master` dispara deploy automático.
