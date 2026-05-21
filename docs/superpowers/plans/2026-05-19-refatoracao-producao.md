# Refatoração para Produção — EvolutionFitIA

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar o EvolutionFitIA seguro, confiável e econômico para receber os primeiros usuários pagantes.

**Architecture:** Segurança via API Key no admin, deduplicação de mensagens no banco, retry no Evolution API, prompt caching na Claude API, logs JSON para Render, CORS restrito.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Anthropic SDK, httpx, python-json-logger, Render free tier.

---

## Mapa de arquivos

| Arquivo | Ação |
|---|---|
| `app/config.py` | Adiciona `ADMIN_API_KEY`, `CLAUDE_MODEL`, `ALLOWED_ORIGINS` |
| `app/middleware/auth.py` | **Novo** — dependency `require_admin_key` |
| `app/models/usuario.py` | Adiciona campo `ultima_mensagem_id` |
| `alembic/versions/002_add_ultima_mensagem_id.py` | **Nova migration** |
| `app/routers/admin.py` | Remove `activate-test`, aplica auth |
| `app/routers/whatsapp.py` | Reativa subscription, deduplicação |
| `app/routers/hotmart.py` | Aplica auth ao endpoint |
| `app/services/whatsapp_service.py` | Retry + logs JSON |
| `app/services/claude_service.py` | Prompt caching + model via settings |
| `main.py` | Logging JSON, CORS restrito, health check robusto |
| `requirements.txt` | Adiciona `python-json-logger` |
| `Dockerfile` | Remove `ARG CACHE_BUST`, adiciona `HEALTHCHECK` |
| `.dockerignore` | Completo |
| `render.yaml` | Novos env vars |
| `.env.example` | Atualizado |
| `scripts/activate_test.py` | **Novo** — script local de ativação de teste |

---

## Task 1: Settings e dependências

**Files:**
- Modify: `app/config.py`
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Passo 1: Atualizar `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str

    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    EVOLUTION_API_URL: str
    EVOLUTION_API_TOKEN: str
    EVOLUTION_API_INSTANCE: str

    ADMIN_API_KEY: str

    HOTMART_WEBHOOK_SECRET: str
    HOTMART_OFFER_ID_TRIMESTRAL: str
    HOTMART_OFFER_ID_ANUAL: str

    PAYMENT_LINK_TRIMESTRAL: str
    PAYMENT_LINK_ANUAL: str

    ALLOWED_ORIGINS: str = "https://evolutionfit-api.onrender.com"


settings = Settings()
```

- [ ] **Passo 2: Adicionar `python-json-logger` ao `requirements.txt`**

Adicionar após `pydantic[email]==2.10.3`:
```
python-json-logger==2.0.7
```

- [ ] **Passo 3: Atualizar `.env.example`**

```ini
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/evolutionfit

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6

# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_TOKEN=evfit_secret_key_2026
EVOLUTION_API_INSTANCE=evolutionfit

# Admin
ADMIN_API_KEY=troque-por-uma-chave-secreta-forte

# Hotmart
HOTMART_WEBHOOK_SECRET=seu-secret-hotmart
HOTMART_OFFER_ID_TRIMESTRAL=CODIGO_OFERTA_TRIMESTRAL
HOTMART_OFFER_ID_ANUAL=CODIGO_OFERTA_ANUAL

# Links de pagamento
PAYMENT_LINK_TRIMESTRAL=https://pay.hotmart.com/SEU_PRODUTO?off=OFERTA_TRIMESTRAL
PAYMENT_LINK_ANUAL=https://pay.hotmart.com/SEU_PRODUTO?off=OFERTA_ANUAL

# CORS (separado por vírgula)
ALLOWED_ORIGINS=https://evolutionfit-api.onrender.com
```

- [ ] **Passo 4: Adicionar `ADMIN_API_KEY` ao `.env` local** (só para desenvolvimento)

No arquivo `.env`, adicionar:
```
ADMIN_API_KEY=dev-admin-key-local
```

- [ ] **Passo 5: Commit**

```bash
git add app/config.py requirements.txt .env.example
git commit -m "feat: adiciona ADMIN_API_KEY, CLAUDE_MODEL e ALLOWED_ORIGINS ao settings"
```

---

## Task 2: Middleware de autenticação admin

**Files:**
- Create: `app/middleware/auth.py`
- Modify: `app/routers/admin.py`

- [ ] **Passo 1: Criar `app/middleware/auth.py`**

```python
from fastapi import Header, HTTPException
from app.config import settings


async def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Acesso negado")
```

- [ ] **Passo 2: Atualizar `app/routers/admin.py`** (remove `activate-test`, aplica auth)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin_key
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services.subscription_service import check_active_subscription

router = APIRouter(tags=["Admin"], dependencies=[Depends(require_admin_key)])


@router.get("/users", response_model=list[dict])
def list_users(db: Session = Depends(get_db)):
    users = db.query(Usuario).order_by(Usuario.created_at.desc()).all()
    result = []
    for user in users:
        assinatura = check_active_subscription(user.id, db)
        result.append({
            "id": user.id,
            "telefone": user.telefone,
            "nome": user.nome,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "assinatura_ativa": assinatura is not None,
            "plano": assinatura.plano if assinatura else None,
            "data_fim": assinatura.data_fim.isoformat() if assinatura else None,
        })
    return result


@router.get("/users/{user_id}/treinos")
def get_treinos(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    treinos = db.query(Treino).filter(Treino.user_id == user_id).order_by(Treino.criado_em.desc()).all()
    return [{"id": t.id, "conteudo": t.conteudo, "criado_em": t.criado_em.isoformat()} for t in treinos]


@router.get("/users/{user_id}/dietas")
def get_dietas(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    dietas = db.query(Dieta).filter(Dieta.user_id == user_id).order_by(Dieta.criado_em.desc()).all()
    return [{"id": d.id, "conteudo": d.conteudo, "criado_em": d.criado_em.isoformat()} for d in dietas]


@router.get("/users/{user_id}/conversa")
def get_conversa(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    conversa = db.query(Conversa).filter(Conversa.user_id == user_id).first()
    if not conversa:
        return {"mensagens": []}
    return {"mensagens": conversa.mensagens, "atualizado_em": conversa.atualizado_em.isoformat()}


def _get_user_or_404(user_id: int, db: Session) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user
```

- [ ] **Passo 3: Verificar que `/admin/users` retorna 403 sem header**

```bash
curl -s https://evolutionfit-api.onrender.com/admin/users
# Esperado: {"detail":"Acesso negado"}
```

- [ ] **Passo 4: Commit**

```bash
git add app/middleware/ app/routers/admin.py
git commit -m "feat: auth por API Key em todos os endpoints /admin"
```

---

## Task 3: Logging JSON estruturado

**Files:**
- Modify: `main.py`

- [ ] **Passo 1: Atualizar `main.py` com logging JSON, CORS restrito e health check robusto**

```python
import logging
import logging.config

import httpx
import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.config import settings
from app.database import engine
from app.routers import admin, hotmart, whatsapp


def _setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("SELECT 1"))
    yield


app = FastAPI(
    title="Evolution Fit AI",
    description="SaaS fitness no WhatsApp com IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router, prefix="/webhook")
app.include_router(hotmart.router, prefix="/webhook")
app.include_router(admin.router, prefix="/admin")


@app.get("/")
async def health():
    details: dict = {}

    # Verifica banco
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        details["database"] = "ok"
    except Exception as e:
        details["database"] = str(e)

    # Verifica Evolution API
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.EVOLUTION_API_URL}/instance/fetchInstances",
                headers={"apikey": settings.EVOLUTION_API_TOKEN},
            )
            details["evolution_api"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as e:
        details["evolution_api"] = str(e)

    status = "ok" if all(v == "ok" for v in details.values()) else "degraded"
    return {"status": status, "details": details}
```

- [ ] **Passo 2: Verificar que o servidor inicia sem erros localmente**

```bash
cd "C:\Users\Igor Hanate\Desktop\EvolutionFitIA"
pip install python-json-logger==2.0.7
uvicorn main:app --port 8001 --reload
# Esperado: INFO logs em formato JSON no terminal, sem erros
```

- [ ] **Passo 3: Commit**

```bash
git add main.py requirements.txt
git commit -m "feat: logging JSON, CORS restrito e health check robusto"
```

---

## Task 4: Migration e model — deduplicação

**Files:**
- Modify: `app/models/usuario.py`
- Create: `alembic/versions/002_add_ultima_mensagem_id.py`

- [ ] **Passo 1: Adicionar campo `ultima_mensagem_id` ao model `Usuario`**

```python
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telefone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nome: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ultima_mensagem_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assinaturas: Mapped[list["Assinatura"]] = relationship(back_populates="usuario")
    treinos: Mapped[list["Treino"]] = relationship(back_populates="usuario")
    dietas: Mapped[list["Dieta"]] = relationship(back_populates="usuario")
    conversa: Mapped["Conversa | None"] = relationship(back_populates="usuario", uselist=False)
```

- [ ] **Passo 2: Criar migration `alembic/versions/002_add_ultima_mensagem_id.py`**

```python
"""add ultima_mensagem_id to usuarios

Revision ID: 002
Revises: 001
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("ultima_mensagem_id", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "ultima_mensagem_id")
```

- [ ] **Passo 3: Verificar revision ID da migration anterior**

```bash
cd "C:\Users\Igor Hanate\Desktop\EvolutionFitIA"
grep "^revision" alembic/versions/001_initial_schema.py
# Esperado: revision = "001" (ou o valor real — ajuste down_revision na 002 se for diferente)
```

- [ ] **Passo 4: Commit**

```bash
git add app/models/usuario.py alembic/versions/002_add_ultima_mensagem_id.py
git commit -m "feat: campo ultima_mensagem_id para deduplicação de mensagens"
```

---

## Task 5: Webhook — subscription check + deduplicação

**Files:**
- Modify: `app/routers/whatsapp.py`

- [ ] **Passo 1: Reescrever `app/routers/whatsapp.py`**

```python
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.whatsapp import EvolutionWebhookPayload
from app.services import claude_service, subscription_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        payload = EvolutionWebhookPayload(**body)

        if payload.is_from_me():
            return {"status": "ignored"}

        if payload.event not in ("messages.upsert", "MESSAGES_UPSERT"):
            return {"status": "ignored"}

        phone = payload.get_phone()
        text = payload.get_text()
        message_id = payload.get_message_id()

        if not phone or not text:
            return {"status": "ignored"}

        user = subscription_service.get_or_create_user(phone, db)

        if payload.data and payload.data.pushName and not user.nome:
            user.nome = payload.data.pushName
            db.commit()

        # Deduplicação: ignora mensagem já processada
        if message_id and user.ultima_mensagem_id == message_id:
            logger.info({"event": "duplicate_message", "user_id": user.id, "message_id": message_id})
            return {"status": "duplicate"}

        assinatura = subscription_service.check_active_subscription(user.id, db)

        if not assinatura:
            await whatsapp_service.send_no_subscription_message(phone)
            return {"status": "no_subscription"}

        reply = await claude_service.process_message(user, text, db)
        await whatsapp_service.send_message(phone, reply)

        # Atualiza ID da última mensagem processada
        if message_id:
            user.ultima_mensagem_id = message_id
            db.commit()

    except Exception as e:
        logger.error({"event": "webhook_error", "error": str(e)})

    return {"status": "ok"}
```

- [ ] **Passo 2: Adicionar método `get_message_id()` ao schema `EvolutionWebhookPayload`**

Abrir `app/schemas/whatsapp.py` e adicionar o método na classe `EvolutionWebhookPayload`:

```python
    def get_message_id(self) -> str | None:
        if self.data and self.data.key:
            return self.data.key.id
        return None
```

O arquivo completo `app/schemas/whatsapp.py` deve ficar:

```python
from pydantic import BaseModel


class EvolutionMessageKey(BaseModel):
    remoteJid: str
    fromMe: bool
    id: str
    remoteJidAlt: str | None = None
    addressingMode: str | None = None


class EvolutionMessageData(BaseModel):
    key: EvolutionMessageKey
    message: dict | None = None
    messageType: str | None = None
    messageTimestamp: int | None = None
    pushName: str | None = None


class EvolutionWebhookPayload(BaseModel):
    event: str
    instance: str | None = None
    data: EvolutionMessageData | None = None

    def get_phone(self) -> str | None:
        if not self.data or not self.data.key:
            return None
        key = self.data.key
        if key.addressingMode == "lid" and key.remoteJidAlt:
            jid = key.remoteJidAlt
        else:
            jid = key.remoteJid
        return "".join(filter(str.isdigit, jid.split("@")[0]))

    def get_text(self) -> str | None:
        if not self.data or not self.data.message:
            return None
        msg = self.data.message
        return (
            msg.get("conversation")
            or msg.get("extendedTextMessage", {}).get("text")
            or msg.get("imageMessage", {}).get("caption")
        )

    def get_message_id(self) -> str | None:
        if self.data and self.data.key:
            return self.data.key.id
        return None

    def is_from_me(self) -> bool:
        return bool(self.data and self.data.key and self.data.key.fromMe)
```

- [ ] **Passo 3: Commit**

```bash
git add app/routers/whatsapp.py app/schemas/whatsapp.py
git commit -m "feat: reativa subscription check e adiciona deduplicação de mensagens"
```

---

## Task 6: WhatsApp service — retry com backoff

**Files:**
- Modify: `app/services/whatsapp_service.py`

- [ ] **Passo 1: Reescrever `app/services/whatsapp_service.py`**

```python
import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INSTANCE = settings.EVOLUTION_API_INSTANCE
_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 2, 4]  # segundos


def _base_url() -> str:
    return settings.EVOLUTION_API_URL.rstrip("/")


def _headers() -> dict:
    return {
        "apikey": settings.EVOLUTION_API_TOKEN,
        "Content-Type": "application/json",
    }


async def send_message(phone: str, text: str) -> None:
    url = f"{_base_url()}/message/sendText/{INSTANCE}"
    payload = {"number": phone, "text": text}
    last_error: Exception | None = None

    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=payload, headers=_headers())
                response.raise_for_status()
                return
        except httpx.HTTPError as e:
            last_error = e
            logger.warning({
                "event": "send_retry",
                "attempt": attempt,
                "max": _MAX_RETRIES,
                "phone": phone,
                "error": str(e),
            })
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)

    logger.error({
        "event": "send_failed",
        "phone": phone,
        "text_preview": text[:50],
        "error": str(last_error),
    })
    raise last_error


async def send_no_subscription_message(phone: str) -> None:
    text = (
        "Olá! Para acessar o *Evolution Fit AI*, você precisa de uma assinatura ativa.\n\n"
        "Escolha seu plano:\n\n"
        f"*Trimestral* — R$ 39,99 (3 meses)\n{settings.PAYMENT_LINK_TRIMESTRAL}\n\n"
        f"*Anual* — R$ 29,99/mês (12 meses)\n{settings.PAYMENT_LINK_ANUAL}\n\n"
        "Após o pagamento, sua conta será ativada automaticamente em instantes!"
    )
    await send_message(phone, text)


async def send_welcome_message(phone: str, nome: str | None) -> None:
    primeiro_nome = (nome or "").split()[0] if nome else "você"
    text = (
        f"Olá, *{primeiro_nome}*! Bem-vindo(a) ao *Evolution Fit AI*! 💪\n\n"
        "Sua assinatura foi ativada com sucesso.\n\n"
        "Sou o *Evo*, seu personal trainer e nutricionista virtual.\n\n"
        "Me conta: qual é o seu *objetivo principal*?\n"
        "• Perda de gordura\n"
        "• Ganho de massa muscular\n"
        "• Condicionamento físico\n"
        "• Outro\n\n"
        "A partir daí crio seu treino e dieta 100% personalizados!"
    )
    await send_message(phone, text)
```

- [ ] **Passo 2: Commit**

```bash
git add app/services/whatsapp_service.py
git commit -m "feat: retry com backoff exponencial no Evolution API"
```

---

## Task 7: Claude service — prompt caching + model via settings

**Files:**
- Modify: `app/services/claude_service.py`

- [ ] **Passo 1: Reescrever `app/services/claude_service.py`**

```python
import logging
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é "Evo", personal trainer e nutricionista profissional com 10 anos de experiência, especializado em treino funcional e nutrição esportiva. Comunica-se exclusivamente em português brasileiro, com tom motivador, direto e amigável.

REGRAS:
- Sempre chame o usuário pelo primeiro nome quando souber
- Antes de gerar treino ou dieta, faça perguntas essenciais (nível de condicionamento, equipamentos disponíveis, objetivo, lesões, dias disponíveis por semana)
- Treinos: estruture por Dia 1 / Dia 2 etc., inclua séries/repetições e tempos de descanso
- Dietas: inclua café da manhã, almoço, lanche e jantar; pergunte sobre restrições alimentares
- Mensagens curtas para WhatsApp: parágrafos curtos, bullet points, sem paredes de texto
- Nunca saia do personagem. Fale apenas sobre fitness e nutrição.
- Se o usuário mencionar lesão, oriente a consultar um médico antes de qualquer plano."""

MAX_HISTORY = 20

TREINO_KEYWORDS = {"treino", "exercício", "exercicio", "musculação", "musculacao", "academia", "workout", "treinar"}
DIETA_KEYWORDS = {"dieta", "alimentação", "alimentacao", "nutrição", "nutricao", "comer", "refeição", "refeicao", "cardapio", "cardápio"}


def _get_or_create_conversa(user_id: int, db: Session) -> Conversa:
    conversa = db.query(Conversa).filter(Conversa.user_id == user_id).first()
    if not conversa:
        conversa = Conversa(user_id=user_id, mensagens=[])
        db.add(conversa)
        db.flush()
    return conversa


def _contains_keywords(text: str, keywords: set[str]) -> bool:
    return any(kw in text.lower() for kw in keywords)


async def process_message(user: Usuario, message_text: str, db: Session) -> str:
    conversa = _get_or_create_conversa(user.id, db)

    mensagens: list[dict] = list(conversa.mensagens or [])
    mensagens.append({
        "role": "user",
        "content": message_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Monta histórico para a API (sem timestamps)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in mensagens[-MAX_HISTORY:]
    ]

    # Prompt caching: system prompt com cache_control
    system_with_cache = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT + (f"\n\nNome do usuário: {user.nome.split()[0]}" if user.nome else ""),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            system=system_with_cache,
            messages=history,
        )
        reply = response.content[0].text
    except anthropic.APIError as e:
        logger.error({"event": "claude_error", "user_id": user.id, "error": str(e)})
        reply = "Ops, tive um problema técnico agora. Pode repetir sua mensagem?"

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
```

- [ ] **Passo 2: Commit**

```bash
git add app/services/claude_service.py
git commit -m "feat: prompt caching na Claude API e model via settings"
```

---

## Task 8: Dockerfile e .dockerignore

**Files:**
- Modify: `Dockerfile`
- Modify: `.dockerignore`

- [ ] **Passo 1: Reescrever `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s CMD curl -f http://localhost:${PORT:-8080}/ || exit 1

CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
```

- [ ] **Passo 2: Reescrever `.dockerignore`**

```
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.env.*
!.env.example
.git/
.gitignore
.pytest_cache/
docs/
scripts/
*.md
```

- [ ] **Passo 3: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "fix: Dockerfile limpo com HEALTHCHECK, .dockerignore completo"
```

---

## Task 9: render.yaml e script local de ativação

**Files:**
- Modify: `render.yaml`
- Create: `scripts/activate_test.py`

- [ ] **Passo 1: Atualizar `render.yaml`**

```yaml
services:
  - type: web
    name: evolutionfit-api
    env: docker
    plan: free
    healthCheckPath: /
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: evolutionfit-db
          property: connectionString
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: CLAUDE_MODEL
        value: claude-sonnet-4-6
      - key: EVOLUTION_API_URL
        sync: false
      - key: EVOLUTION_API_TOKEN
        sync: false
      - key: EVOLUTION_API_INSTANCE
        sync: false
      - key: ADMIN_API_KEY
        sync: false
      - key: HOTMART_WEBHOOK_SECRET
        sync: false
      - key: HOTMART_OFFER_ID_TRIMESTRAL
        sync: false
      - key: HOTMART_OFFER_ID_ANUAL
        sync: false
      - key: PAYMENT_LINK_TRIMESTRAL
        sync: false
      - key: PAYMENT_LINK_ANUAL
        sync: false
      - key: ALLOWED_ORIGINS
        value: https://evolutionfit-api.onrender.com

databases:
  - name: evolutionfit-db
    databaseName: evolutionfit
    plan: free
```

- [ ] **Passo 2: Criar `scripts/activate_test.py`**

```python
"""
Script local para ativar assinatura de teste.
Uso: DATABASE_URL=<url> python scripts/activate_test.py <telefone> [plano]

Exemplo:
  DATABASE_URL=postgresql://... python scripts/activate_test.py 5511999328525 anual
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.usuario import Usuario
from app.models.assinatura import Assinatura

PLAN_DURATIONS = {"trimestral": 90, "anual": 365}


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/activate_test.py <telefone> [anual|trimestral]")
        sys.exit(1)

    phone = "".join(filter(str.isdigit, sys.argv[1]))
    plano = sys.argv[2] if len(sys.argv) > 2 else "anual"
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("Erro: variável DATABASE_URL não definida")
        sys.exit(1)

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = db.query(Usuario).filter(Usuario.telefone == phone).first()
    if not user:
        user = Usuario(telefone=phone, nome="Teste")
        db.add(user)
        db.flush()
        print(f"Usuário criado: id={user.id}")
    else:
        print(f"Usuário existente: id={user.id}")

    hoje = date.today()
    duracao = PLAN_DURATIONS.get(plano, 365)
    transaction_id = f"TEST-{phone}"

    existing = db.query(Assinatura).filter(Assinatura.hotmart_transaction_id == transaction_id).first()
    if existing:
        existing.data_fim = hoje + timedelta(days=duracao)
        existing.status = "ativo"
        print(f"Assinatura atualizada: id={existing.id}, plano={plano}, válida até {existing.data_fim}")
    else:
        assinatura = Assinatura(
            user_id=user.id,
            plano=plano,
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=duracao),
            status="ativo",
            hotmart_transaction_id=transaction_id,
        )
        db.add(assinatura)
        print(f"Assinatura criada: plano={plano}, válida até {hoje + timedelta(days=duracao)}")

    db.commit()
    db.close()
    print("Concluído.")


if __name__ == "__main__":
    main()
```

- [ ] **Passo 3: Commit**

```bash
git add render.yaml scripts/activate_test.py
git commit -m "feat: render.yaml com novos env vars e script local de ativação de teste"
```

---

## Task 10: Deploy no Render

- [ ] **Passo 1: Adicionar `ADMIN_API_KEY` no Render via API**

```bash
curl -s -X PUT "https://api.render.com/v1/services/srv-d85nfrjtqb8s73bsdbug/env-vars" \
  -H "Authorization: Bearer rnd_oCCdNtdKyNPS5HC1uOQcUcU68I3F" \
  -H "Content-Type: application/json" \
  -d '[
    {"key":"DATABASE_URL","value":"postgresql://evolutionfit:JT7KP6b4KpRua446o6rkQpwgYNydIufc@dpg-d85nei0jo89c73dj2eb0-a/evolutionfit"},
    {"key":"ANTHROPIC_API_KEY","value":"<valor-do-env-ANTHROPIC_API_KEY>"},
    {"key":"CLAUDE_MODEL","value":"claude-sonnet-4-6"},
    {"key":"EVOLUTION_API_URL","value":"https://specific-habitat-optimum-stock.trycloudflare.com"},
    {"key":"EVOLUTION_API_TOKEN","value":"evfit_secret_key_2026"},
    {"key":"EVOLUTION_API_INSTANCE","value":"evolutionfit"},
    {"key":"ADMIN_API_KEY","value":"evfit-admin-2026"},
    {"key":"HOTMART_WEBHOOK_SECRET","value":"PENDENTE"},
    {"key":"HOTMART_OFFER_ID_TRIMESTRAL","value":"PENDENTE"},
    {"key":"HOTMART_OFFER_ID_ANUAL","value":"PENDENTE"},
    {"key":"PAYMENT_LINK_TRIMESTRAL","value":"PENDENTE"},
    {"key":"PAYMENT_LINK_ANUAL","value":"PENDENTE"},
    {"key":"ALLOWED_ORIGINS","value":"https://evolutionfit-api.onrender.com"}
  ]'
```

- [ ] **Passo 2: Push tudo para o GitHub**

```bash
git push
```

- [ ] **Passo 3: Disparar redeploy no Render**

```bash
curl -s -X POST "https://api.render.com/v1/services/srv-d85nfrjtqb8s73bsdbug/deploys" \
  -H "Authorization: Bearer rnd_oCCdNtdKyNPS5HC1uOQcUcU68I3F" \
  -H "Content-Type: application/json" \
  -d '{"clearCache":"clear"}'
```

- [ ] **Passo 4: Aguardar deploy ficar `live`**

```bash
# Repetir até status=live
curl -s "https://api.render.com/v1/services/srv-d85nfrjtqb8s73bsdbug/deploys?limit=1" \
  -H "Authorization: Bearer rnd_oCCdNtdKyNPS5HC1uOQcUcU68I3F" | grep -o '"status":"[^"]*"'
```

- [ ] **Passo 5: Verificar health check**

```bash
curl -s https://evolutionfit-api.onrender.com/
# Esperado: {"status":"ok","details":{"database":"ok","evolution_api":"ok"}}
# ou {"status":"degraded",...} se Evolution API local não estiver acessível
```

- [ ] **Passo 6: Verificar auth admin**

```bash
# Sem key — deve retornar 403
curl -s https://evolutionfit-api.onrender.com/admin/users
# Esperado: {"detail":"Acesso negado"}

# Com key — deve retornar lista (vazia ou com usuários)
curl -s https://evolutionfit-api.onrender.com/admin/users \
  -H "X-Admin-Key: evfit-admin-2026"
# Esperado: [] ou lista de usuários
```

- [ ] **Passo 7: Commit final de verificação**

```bash
git tag v1.0.0-production-ready
git push --tags
```
