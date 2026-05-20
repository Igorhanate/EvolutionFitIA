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

O arquivo `.env` é obrigatório na raiz. Use `.env.example` como referência. Variáveis obrigatórias: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `EVOLUTION_API_URL`, `EVOLUTION_API_TOKEN`, `EVOLUTION_API_INSTANCE`, `ADMIN_API_KEY`.

**NUNCA** use Docker ou PowerShell — use apenas Bash. **NUNCA** desconecte a instância WhatsApp `evolutionfit`.

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

Se imagem recebida: `media_service.get_media_bytes()` baixa via Evolution API antes de chamar Claude.

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
- **`estado_pendente`** (JSON): máquina de estados para fluxos multi-turno:
  - `{"tipo": "confirmar_exercicio", ...}` — aguarda confirmação de carga anormal (variação >20%)
  - `{"tipo": "confirmar_refeicao", "analise": {...}}` — aguarda confirmação de registro de refeição
  - `{"tipo": "coleta_fotos", "fotos": [...], "angulos_restantes": [...]}` — coleta 3 fotos para análise de composição corporal
  - `{"tipo": "aguardando_menu"}` — usuário chamou /menu, aguarda seleção de item

#### Ferramentas Claude (TOOLS)

| Tool | Ação |
|------|------|
| `registrar_exercicio` | Salva carga/séries/reps; calcula 1RM; detecta variação >20% |
| `registrar_medidas` | Salva medidas corporais (peso, cintura, quadril, etc.) |
| `registrar_analise_foto` | Persiste resultado de análise de composição corporal (% gordura) |
| `analisar_refeicao` | Extrai macros de foto de alimento; verifica limite 6/dia; inicia confirmação |
| `cadastrar_dieta_propria` | Cadastra dieta externa como MetaNutricional |
| `cadastrar_treino_proprio` | Cadastra treino externo como Treino com `origem: "proprio"` |
| `iniciar_coleta_fotos_corpo` | Inicia coleta de 3 fotos (frente/costas/lado) para análise corporal |

`TOOLS_ANALISE_CORPO` = subset com apenas `registrar_analise_foto`, usado na chamada de análise das 3 fotos.

#### /menu command

Usuário digita `/menu` → recebe lista numerada de 11 funcionalidades → digita o número → ação executada.  
Item 6 ("Ver minha evolução") gera PNG via `card_service.gerar_card_evolucao()`, envia via `whatsapp_service.send_image()` e retorna texto com stats.

#### Fluxo de imagens

- **Foto de alimento** → Claude usa `analisar_refeicao` → tabela nutricional + confirmação de registro
- **Foto de corpo (1ª)** → Claude usa `iniciar_coleta_fotos_corpo` → Python armazena no `estado_pendente`
- **Foto de corpo (2ª)** → Python intercepta via `_handle_coleta_fotos` sem chamar Claude
- **Foto de corpo (3ª)** → Python intercepta, acumula as 3 fotos, chama `_analisar_tres_fotos` (Claude Vision com `TOOLS_ANALISE_CORPO`)

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
| `usuarios` | `telefone` (único, só dígitos) | `ultima_mensagem_id` para dedup de webhooks |
| `assinaturas` | `hotmart_transaction_id` | plano: `trimestral` (90d) / `anual` (365d) |
| `conversas` | `user_id` (único) | JSON array `{role, content, timestamp}` + `estado_pendente` |
| `treinos` / `dietas` | `user_id` | auto-gerados por keywords; `origem: "proprio"` se cadastro externo |
| `registros_exercicio` | `user_id + sessao_data + posicao_sessao` | 1RM estimado por Epley/Brzycki/Lander |
| `medidas_corporais` | `user_id + data_medicao` | peso + circunferências (todos nullable) |
| `fotos_composicao` | `user_id` | apenas `gordura_estimada_pct` e `analise_texto` — fotos não armazenadas |
| `registros_refeicao` | `user_id + data_refeicao` | macros confirmados; limite 6/dia |
| `metas_nutricionais` | `user_id` (ativa=True) | ao criar nova meta, anteriores desativadas |

### Migrations Alembic

Chain atual: `001` (schema inicial) → `002` (ultima_mensagem_id) → `003` (registros_exercicio) → `004` (medidas_corporais + fotos_composicao) → `005` (registros_refeicao) → `006` (metas_nutricionais) — **HEAD = 006**

### Roteamento

| Prefixo | Arquivo | Descrição |
|---------|---------|-----------|
| `GET /` | `main.py` | health check — verifica banco + Evolution API |
| `POST /webhook/whatsapp` | `app/routers/whatsapp.py` | recebe eventos do Evolution API |
| `POST /webhook/hotmart` | `app/routers/hotmart.py` | recebe compras aprovadas |
| `GET /admin/users` | `app/routers/admin.py` | lista usuários — exige `X-Admin-Key` |
| `GET /admin/users/{id}/treinos\|dietas\|conversa` | `app/routers/admin.py` | histórico por usuário |
| `GET /admin/users/{id}/evolucao/sessao` | `app/routers/admin.py` | soma 1RMs por sessão |
| `GET /admin/users/{id}/evolucao/exercicio?exercicio=` | `app/routers/admin.py` | 1RM de exercício específico |
| `GET /admin/users/{id}/exercicios` | `app/routers/admin.py` | exercícios únicos do usuário |
| `GET /admin/users/{id}/medidas` | `app/routers/admin.py` | histórico de medidas corporais |
| `GET /admin/users/{id}/fotos` | `app/routers/admin.py` | histórico de análises de composição |
| `GET /admin/users/{id}/refeicoes` | `app/routers/admin.py` | histórico de refeições |
| `GET /admin/users/{id}/meta-nutricional` | `app/routers/admin.py` | metas nutricionais |

### Evolution API

- Versão: v2.3.7 — instância `evolutionfit`
- `POST /message/sendText/{instance}` — enviar texto
- `POST /message/sendMedia/{instance}` — enviar imagem (base64, campo `media`)
- `POST /chat/getBase64FromMediaMessage/{instance}` — baixar mídia recebida

### Card PNG de evolução

`app/services/card_service.py` — matplotlib com backend `Agg` (não-interativo).
- `get_last_session_stats(user_id, db)` → `{"duracao": str, "exercicios": int, "sessoes": int}`
- `gerar_card_evolucao(user_nome, evolucao, stats)` → `bytes` (PNG)
- Logo: `LOGO EVOLUTION FIT.jpeg` na raiz do projeto (note o espaço no nome)
- Paleta dark: BG `#1C1C1E`, accent `#FF6B35`, white `#FFFFFF`, gray `#8E8E93`

### Infraestrutura

- **FastAPI:** Render (free tier, Docker). Build e migrations (`alembic upgrade head`) ocorrem automaticamente no startup. Cada push no `master` dispara deploy automático.
- **Evolution API:** roda como processo separado (Node.js). Localmente, inicie com `node dist/main.js` em `C:\Users\Igor Hanate\evolution-api\` e exponha via Cloudflare tunnel (`cloudflared tunnel --url http://localhost:8080`). Configure `EVOLUTION_API_URL` no Render com a URL do tunnel.
- **Banco:** PostgreSQL no Render (free tier).

### Status atual

- Deploy live em `https://evolutionfit-api.onrender.com`
- `ADMIN_API_KEY` configurada no Render
- Hotmart vars (`HOTMART_WEBHOOK_SECRET`, `HOTMART_OFFER_ID_*`, `PAYMENT_LINK_*`) ainda com valor `PENDENTE` — configurar antes de ativar vendas
- Número bot `551153043378` — não desconectar a instância `evolutionfit`
