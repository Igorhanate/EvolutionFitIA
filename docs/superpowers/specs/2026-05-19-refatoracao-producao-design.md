# Design: Refatoração para Produção — EvolutionFitIA

**Data:** 2026-05-19  
**Status:** Aprovado  
**Escopo:** Segurança + Confiabilidade + Custo + Qualidade — pronto para primeiros usuários pagantes

---

## Contexto

Sistema de chatbot fitness no WhatsApp. Stack: FastAPI + SQLAlchemy + Claude API + Evolution API + Render (free tier). Ainda em desenvolvimento — sem usuários pagantes. Próximo ciclo (pós-lançamento) fará refatoração modular completa.

**Restrição:** Sem plataformas pagas. Todas as soluções devem usar serviços gratuitos ou open-source.

---

## 1. Segurança

### 1.1 Admin API Key
- Novo arquivo `app/middleware/auth.py` com FastAPI dependency `require_admin_key`
- Lê `ADMIN_API_KEY` de `settings` (env var obrigatória)
- Todos os endpoints `GET/POST /admin/*` passam a exigir header `X-Admin-Key: <valor>`
- Retorna `403 Forbidden` se ausente ou incorreto

### 1.2 Remoção do endpoint de teste
- `POST /admin/activate-test` é **removido** do router
- Para criar assinatura de teste: script local `scripts/activate_test.py` que conecta diretamente ao banco via `DATABASE_URL` — não exposto na API

### 1.3 Reativação da checagem de assinatura
- Código comentado em `app/routers/whatsapp.py` é **descomentado e limpo**
- Sem TODOs, sem comentários de debug

### 1.4 CORS restrito
- `allow_origins=["*"]` substituído por `settings.ALLOWED_ORIGINS` (lista separada por vírgula)
- Default: `https://evolutionfit-api.onrender.com`
- Adicionado ao `render.yaml` como env var

---

## 2. Confiabilidade

### 2.1 Deduplicação de mensagens
- Novo campo `ultima_mensagem_id: str | None` na tabela `usuarios`
- Nova migration Alembic: `002_add_ultima_mensagem_id.py`
- No webhook: antes de chamar Claude, compara `data.key.id` com `user.ultima_mensagem_id`
  - Se igual: retorna `{"status": "duplicate"}` sem processar
  - Se diferente: processa e atualiza o campo após resposta enviada com sucesso
- Previne resposta dupla quando Evolution API reenvia webhook por timeout

### 2.2 Retry no Evolution API
- `whatsapp_service.send_message()` tenta até **3 vezes** com backoff exponencial: 1s → 2s → 4s
- Usa `asyncio.sleep` — sem dependência externa
- Se falhar após 3 tentativas: loga `{"event": "send_failed", "phone": ..., "text_preview": ...}` (primeiros 50 chars)
- Função `send_message` levanta exceção após esgotar tentativas para que o caller decida

### 2.3 Logs estruturados (JSON)
- `main.py` configura `logging` com formatter JSON via `python-json-logger` (gratuito, adicionar ao `requirements.txt`)
- Todos os `logger.error/warning/info` passam a logar dicts com campos: `event`, `user_id` (quando disponível), `error`, `timestamp`
- Render captura stdout gratuitamente — sem custo adicional

### 2.4 Health check robusto
- `GET /` verifica: (1) conexão com banco, (2) resposta do Evolution API `GET /instance/fetchInstances`
- Retorna `{"status": "ok"}` se tudo saudável, `{"status": "degraded", "details": {...}}` se algum falhar
- HTTP 200 em ambos os casos (para não derrubar UptimeRobot/Render health check)

---

## 3. Custo (Claude API)

### 3.1 Prompt caching
- `SYSTEM_PROMPT` recebe `cache_control: {"type": "ephemeral"}` via parâmetro `system` da API
- As primeiras mensagens mais antigas do histórico também recebem cache quando possível
- Implementação usa `anthropic.types.TextBlockParam` com `cache_control`
- TTL de 5 min da Anthropic — reutiliza cache em conversas ativas
- Reduz custo em ~90% nos tokens do system prompt (estimativa Anthropic)

### 3.2 Model via settings
- `settings.CLAUDE_MODEL` com default `"claude-sonnet-4-6"`
- Adicionado ao `render.yaml` e `.env.example`

---

## 4. Qualidade e Produção-Readiness

### 4.1 Dockerfile limpo
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8080/ || exit 1
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
```
- Remove `ARG CACHE_BUST=1`
- Adiciona `HEALTHCHECK` nativo

### 4.2 .dockerignore completo
```
__pycache__/
*.pyc
*.pyo
.env
.git/
.pytest_cache/
docs/
*.md
```

### 4.3 Settings atualizadas
Novos campos em `app/config.py`:
- `ADMIN_API_KEY: str`
- `CLAUDE_MODEL: str = "claude-sonnet-4-6"`
- `ALLOWED_ORIGINS: str = "https://evolutionfit-api.onrender.com"`

### 4.4 render.yaml atualizado
Novos `sync: false` para `ADMIN_API_KEY`, `CLAUDE_MODEL`, `ALLOWED_ORIGINS`.

### 4.5 Script de ativação de teste
`scripts/activate_test.py` — conecta ao banco via `DATABASE_URL` local, cria usuário + assinatura. Usado apenas em desenvolvimento, nunca deployado.

---

## Arquivos modificados

| Arquivo | Tipo de mudança |
|---|---|
| `app/middleware/auth.py` | **Novo** |
| `app/routers/admin.py` | Remove `activate-test`, adiciona auth |
| `app/routers/whatsapp.py` | Reativa subscription check, deduplicação |
| `app/routers/hotmart.py` | Adiciona auth ao endpoint (proteção extra) |
| `app/services/whatsapp_service.py` | Retry + logs estruturados |
| `app/services/claude_service.py` | Prompt caching + model via settings |
| `app/models/usuario.py` | Campo `ultima_mensagem_id` |
| `app/config.py` | Novos campos |
| `main.py` | Logging JSON, CORS restrito, health check robusto |
| `Dockerfile` | Limpo + HEALTHCHECK |
| `.dockerignore` | Completo |
| `render.yaml` | Novos env vars |
| `requirements.txt` | Adiciona `python-json-logger` |
| `alembic/versions/002_add_ultima_mensagem_id.py` | **Nova migration** |
| `scripts/activate_test.py` | **Novo** (local only) |

---

## O que NÃO está neste escopo

- Refatoração modular da arquitetura (próximo ciclo pós-lançamento)
- Testes unitários (próximo ciclo)
- Fila de mensagens / Redis (próximo ciclo)
- Histórico de conversa compactado (próximo ciclo)
- Resolução do número do bot (`551153043378`) — depende de ação manual do usuário
