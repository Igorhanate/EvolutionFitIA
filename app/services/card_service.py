import io
import logging
import os
from datetime import date, datetime

import httpx

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.registro_exercicio import RegistroExercicio

logger = logging.getLogger(__name__)

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "LOGO EVOLUTION FIT.jpeg")

# Paleta dark estilo Strava
_BG = "#1C1C1E"
_BG_CHART = "#2C2C2E"
_ACCENT = "#FF6B35"
_WHITE = "#FFFFFF"
_GRAY = "#8E8E93"
_GRID = "#3A3A3C"


def get_last_session_stats(user_id: int, db: Session) -> dict:
    ultima_sessao: date | None = (
        db.query(func.max(RegistroExercicio.sessao_data))
        .filter(RegistroExercicio.user_id == user_id)
        .scalar()
    )
    total_sessoes: int = (
        db.query(func.count(func.distinct(RegistroExercicio.sessao_data)))
        .filter(RegistroExercicio.user_id == user_id)
        .scalar()
        or 0
    )

    if not ultima_sessao:
        return {"duracao": "—", "exercicios": 0, "sessoes": total_sessoes}

    row = (
        db.query(
            func.min(RegistroExercicio.criado_em),
            func.max(RegistroExercicio.criado_em),
            func.count(RegistroExercicio.id),
        )
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.sessao_data == ultima_sessao,
        )
        .first()
    )
    min_t: datetime | None
    max_t: datetime | None
    n: int
    min_t, max_t, n = row

    if min_t and max_t and min_t != max_t:
        delta = int((max_t - min_t).total_seconds() / 60) + 8
        duracao = f"{max(delta, 15)} min"
    else:
        duracao = "~45 min" if (n or 0) > 3 else "~30 min"

    return {"duracao": duracao, "exercicios": int(n or 0), "sessoes": total_sessoes}


def gerar_card_evolucao(
    user_nome: str | None,
    evolucao: list[dict],
    stats: dict,
) -> bytes:
    """
    Gera PNG do card de evolução estilo Strava.

    evolucao: lista de {'data': 'YYYY-MM-DD', 'soma_rm': float}
    stats: {'duracao': str, 'exercicios': int, 'sessoes': int}
    """
    fig = plt.figure(figsize=(10, 5.5), facecolor=_BG, dpi=100)

    gs = gridspec.GridSpec(
        3, 1,
        figure=fig,
        height_ratios=[0.16, 0.57, 0.27],
        hspace=0.0,
        left=0.08, right=0.94, top=0.97, bottom=0.03,
    )

    # ── Header ──────────────────────────────────────────────────────────────
    ax_h = fig.add_subplot(gs[0])
    ax_h.set_facecolor(_BG)
    ax_h.axis("off")

    primeiro = (user_nome or "").split()[0] if user_nome else "Atleta"
    ax_h.text(0.0, 0.80, "EVOLUTION FIT AI",
              transform=ax_h.transAxes, fontsize=15, fontweight="bold",
              color=_ACCENT, va="center", ha="left")
    ax_h.text(0.0, 0.18, f"Evolução de Desempenho — {primeiro}",
              transform=ax_h.transAxes, fontsize=9, color=_GRAY,
              va="center", ha="left")
    ax_h.text(1.0, 0.50, date.today().strftime("%d/%m/%Y"),
              transform=ax_h.transAxes, fontsize=9, color=_GRAY,
              va="center", ha="right")

    # ── Gráfico ─────────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1])
    ax.set_facecolor(_BG_CHART)
    for spine in ax.spines.values():
        spine.set_edgecolor(_GRID)

    if evolucao:
        xs = list(range(len(evolucao)))
        ys = [float(e["soma_rm"]) for e in evolucao]
        labels = [e["data"][5:].replace("-", "/") for e in evolucao]  # MM/DD

        ax.plot(xs, ys, color=_ACCENT, linewidth=2.5, zorder=3,
                marker="o", markersize=3.5, markerfacecolor=_ACCENT, markeredgewidth=0)
        ax.fill_between(xs, ys, alpha=0.18, color=_ACCENT)

        step = max(1, len(xs) // 7)
        ax.set_xticks(xs[::step])
        ax.set_xticklabels([labels[i] for i in xs[::step]], fontsize=7.5, color=_GRAY)
        ax.set_xlim(-0.5, len(xs) - 0.5)

        # Y-axis: zoom na faixa dos dados com margem de 15%
        y_range = max(ys) - min(ys) if len(ys) > 1 else 20
        y_pad = max(y_range * 0.25, 15)
        ax.set_ylim(max(0, min(ys) - y_pad), max(ys) + y_pad * 1.6)

        # Marca o último ponto
        ax.plot(xs[-1], ys[-1], "o", color=_WHITE, markersize=7, zorder=5)
        ax.annotate(
            f"  {ys[-1]:.0f} kg",
            xy=(xs[-1], ys[-1]),
            xytext=(xs[-1], ys[-1] + y_pad * 0.5),
            fontsize=8.5, color=_WHITE, fontweight="bold",
        )
    else:
        ax.text(0.5, 0.5, "Sem dados de treino ainda\nRegistre exercícios para gerar o gráfico",
                transform=ax.transAxes, ha="center", va="center",
                color=_GRAY, fontsize=11, linespacing=1.6)

    ax.set_ylabel("Soma 1RM (kg)", fontsize=8, color=_GRAY, labelpad=5)
    ax.tick_params(axis="y", colors=_GRAY, labelsize=7.5)
    ax.tick_params(axis="x", colors=_GRAY, length=3)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    ax.grid(True, color=_GRID, linewidth=0.5, alpha=0.7, axis="y")

    # ── Footer: stats + logo ─────────────────────────────────────────────────
    ax_f = fig.add_subplot(gs[2])
    ax_f.set_facecolor(_BG)
    ax_f.axis("off")

    stats_display = [
        (stats.get("duracao", "—"), "DURAÇÃO"),
        (str(stats.get("exercicios", 0)), "EXERCÍCIOS"),
        (str(stats.get("sessoes", 0)), "SESSÕES"),
    ]
    for (val, label), x in zip(stats_display, [0.10, 0.30, 0.50]):
        ax_f.text(x, 0.72, val, transform=ax_f.transAxes,
                  fontsize=19, fontweight="bold", color=_WHITE,
                  va="center", ha="center")
        ax_f.text(x, 0.18, label, transform=ax_f.transAxes,
                  fontsize=7, color=_GRAY, va="center", ha="center",
                  fontweight="bold")

    # Divisor vertical antes do logo
    ax_f.plot([0.66, 0.66], [0.1, 0.9], color=_GRID, linewidth=0.8,
              transform=ax_f.transAxes)

    # Logo (lado direito do footer)
    try:
        logo = plt.imread(_LOGO_PATH)
        ax_logo = fig.add_axes([0.72, 0.015, 0.20, 0.24])
        ax_logo.imshow(logo, aspect="auto")
        ax_logo.axis("off")
    except Exception as e:
        logger.warning("logo_not_found", extra={"error": str(e)})
        ax_f.text(0.83, 0.50, "EVO IA", transform=ax_f.transAxes,
                  fontsize=12, color=_ACCENT, fontweight="bold",
                  va="center", ha="center")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                facecolor=_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def get_volume_ultima_sessao(user_id: int, db: Session) -> float:
    """Volume total da ultima sessao = soma de (carga_kg * series * repeticoes)."""
    ultima_sessao = (
        db.query(func.max(RegistroExercicio.sessao_data))
        .filter(RegistroExercicio.user_id == user_id)
        .scalar()
    )
    if not ultima_sessao:
        return 0.0
    registros = (
        db.query(RegistroExercicio)
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.sessao_data == ultima_sessao,
        )
        .all()
    )
    total = 0.0
    for r in registros:
        total += float(r.carga_kg or 0) * int(r.series or 0) * int(r.repeticoes or 0)
    return total


def gerar_card_treino(user_nome: str | None, stats: dict, volume_kg: float) -> bytes:
    """Card simples de fim de treino: duracao, exercicios, volume total, sessoes.

    stats: {'duracao': str, 'exercicios': int, 'sessoes': int}
    volume_kg: volume total levantado na sessao (kg)
    """
    fig = plt.figure(figsize=(10, 5.5), facecolor=_BG, dpi=100)
    ax = fig.add_subplot(111)
    ax.set_facecolor(_BG)
    ax.axis("off")

    primeiro = (user_nome or "").split()[0] if user_nome else "Atleta"

    # Header
    ax.text(0.06, 0.88, "EVOLUTION FIT AI", fontsize=17, fontweight="bold",
            color=_ACCENT, va="center", ha="left", transform=ax.transAxes)
    ax.text(0.06, 0.78, f"Resumo do Treino — {primeiro}", fontsize=11, color=_GRAY,
            va="center", ha="left", transform=ax.transAxes)
    ax.text(0.94, 0.88, date.today().strftime("%d/%m/%Y"), fontsize=10, color=_GRAY,
            va="center", ha="right", transform=ax.transAxes)

    # Volume em destaque (centro)
    if volume_kg >= 1000:
        vol_txt = f"{volume_kg/1000:.1f}t"
    else:
        vol_txt = f"{volume_kg:.0f} kg"
    ax.text(0.5, 0.55, vol_txt, fontsize=52, fontweight="bold", color=_ACCENT,
            va="center", ha="center", transform=ax.transAxes)
    ax.text(0.5, 0.42, "VOLUME TOTAL LEVANTADO", fontsize=10, color=_GRAY,
            va="center", ha="center", transform=ax.transAxes, fontweight="bold")

    # Stats na base (3 colunas)
    base = [
        (str(stats.get("duracao", "—")), "DURAÇÃO"),
        (str(stats.get("exercicios", 0)), "EXERCÍCIOS"),
        (str(stats.get("sessoes", 0)), "SESSÕES TOTAIS"),
    ]
    for (val, label), x in zip(base, [0.22, 0.50, 0.78]):
        ax.text(x, 0.20, val, fontsize=22, fontweight="bold", color=_WHITE,
                va="center", ha="center", transform=ax.transAxes)
        ax.text(x, 0.10, label, fontsize=8, color=_GRAY, fontweight="bold",
                va="center", ha="center", transform=ax.transAxes)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=_BG, edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Card de fim de treino "Clássico" (gerado pela rota /api/card do site) ──

_CARD_SITE_URL = os.getenv("CARD_SITE_URL", "https://evolutionfit-site.vercel.app")


def _fmt_kg_br(volume_kg: float) -> str:
    """3250.0 -> '3.250 kg' (separador de milhar BR)."""
    inteiro = int(round(volume_kg or 0))
    s = f"{inteiro:,}".replace(",", ".")
    return f"{s} kg"


def get_reps_nome_ultima_sessao(user_id: int, db: Session) -> tuple[int, str]:
    """Soma de repetições (series*reps) e nome do treino da última sessão."""
    ultima_sessao = (
        db.query(func.max(RegistroExercicio.sessao_data))
        .filter(RegistroExercicio.user_id == user_id)
        .scalar()
    )
    if not ultima_sessao:
        return 0, ""
    registros = (
        db.query(RegistroExercicio)
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.sessao_data == ultima_sessao,
        )
        .all()
    )
    total_reps = 0
    nome = ""
    for r in registros:
        total_reps += int(r.series or 0) * int(r.repeticoes or 0)
        if not nome and r.treino_nome:
            nome = r.treino_nome
    return total_reps, nome


async def gerar_card_treino_classico(
    user_nome: str | None,
    stats: dict,
    volume_kg: float,
    reps_total: int,
    treino_nome: str,
) -> bytes:
    """Card de fim de treino no estilo Clássico (rota /api/card do site, PNG transparente)."""
    params = {
        "modalidade": "musculacao",
        "tempo": str(stats.get("duracao", "")),
        "kgLevantados": _fmt_kg_br(volume_kg),
        "repeticoes": str(reps_total),
    }
    if treino_nome:
        params["nomeTreino"] = treino_nome
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{_CARD_SITE_URL}/api/card", params=params)
        r.raise_for_status()
        return r.content


def get_rm_max_ultima_sessao(user_id: int, db: Session) -> float:
    """Maior 1RM estimado da última sessão (0.0 se não houver)."""
    ultima_sessao = (
        db.query(func.max(RegistroExercicio.sessao_data))
        .filter(RegistroExercicio.user_id == user_id)
        .scalar()
    )
    if not ultima_sessao:
        return 0.0
    rm = (
        db.query(func.max(RegistroExercicio.rm_estimado))
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.sessao_data == ultima_sessao,
        )
        .scalar()
    )
    return float(rm or 0)


async def gerar_card_evolucao_classico(
    evolucao: list[dict],
    rm_max_kg: float,
    treino_nome: str,
) -> bytes:
    """Card de evolução no estilo do studio (template=evolucao da rota /api/card).

    evolucao: lista de {'data','soma_rm'} — usa os últimos 4 pontos (3 anteriores + atual).
    Lança ValueError se houver menos de 2 pontos (caller decide o fallback).
    """
    pontos = [float(e["soma_rm"]) for e in evolucao][-4:]
    if len(pontos) < 2:
        raise ValueError("evolucao insuficiente para o grafico (min 2 sessoes)")
    anterior, atual = pontos[-2], pontos[-1]
    pct = ((atual - anterior) / anterior * 100) if anterior else 0.0
    pct_txt = f"{pct:.1f}".replace(".", ",")
    params = {
        "template": "evolucao",
        "pontos": ",".join(f"{p:.0f}" for p in pontos),
        "percentEvolucao": pct_txt,
    }
    if rm_max_kg > 0:
        params["rm"] = f"{rm_max_kg:.0f} kg"
    if treino_nome:
        params["nomeTreino"] = treino_nome
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{_CARD_SITE_URL}/api/card", params=params)
        r.raise_for_status()
        return r.content
