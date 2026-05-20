import io
import logging
import os
from datetime import date, datetime

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
    ax_h.text(0.0, 0.80, "EVOLUTION FIT IA",
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

        # Marca o último ponto
        ax.plot(xs[-1], ys[-1], "o", color=_WHITE, markersize=7, zorder=5)
        y_range = max(ys) - min(ys) if len(ys) > 1 else 20
        ax.annotate(
            f"  {ys[-1]:.0f} kg",
            xy=(xs[-1], ys[-1]),
            xytext=(xs[-1], ys[-1] + y_range * 0.14 + 3),
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
    ax_f.axvline(x=0.66, ymin=0.1, ymax=0.9, color=_GRID, linewidth=0.8,
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
