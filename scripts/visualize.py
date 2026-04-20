"""
visualize.py
------------
Generates all charts for the RAG Faithfulness Study.
Saves PNG files to results/.

Charts produced:
  1.  bar_metrics_comparison.png   — grouped bar: all 4 metrics side-by-side
  2.  hallucination_rate.png       — bar comparison of hallucination rates
  3.  per_question_correctness.png — per-question correctness (baseline vs RAG)
  4.  per_question_faithfulness.png— per-question faithfulness
  5.  radar_summary.png            — radar / spider chart of aggregate metrics
  6.  category_heatmap.png         — heatmap of faithfulness by category
  7.  improvement_delta.png        — delta bar chart (RAG − Baseline per question)
"""

import json
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT    = Path(__file__).resolve().parent.parent
RES_DIR = ROOT / "results"
RES_DIR.mkdir(exist_ok=True)

# ── palette ────────────────────────────────────────────────────────────────────
C_BASE  = "#E07B54"   # warm terracotta for baseline
C_RAG   = "#3A7CA5"   # steel blue for RAG
C_DELTA = "#5BAD72"   # green for improvement
BG      = "#F9F6F0"
GRID    = "#E0DDD8"

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.facecolor":    BG,
    "figure.facecolor":  BG,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.color":        GRID,
    "grid.linewidth":    0.8,
})


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def savefig(name: str) -> None:
    path = RES_DIR / name
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved → {path}")


# ── 1. Grouped bar — all metrics ───────────────────────────────────────────────
def chart_metrics_comparison(summary: list[dict]) -> None:
    b = next(s for s in summary if s["answer_type"] == "baseline")
    r = next(s for s in summary if s["answer_type"] == "rag")

    metrics = ["Correctness", "Faithfulness", "Completeness"]
    bv = [float(b["avg_correctness"]), float(b["avg_faithfulness"]), float(b["avg_completeness"])]
    rv = [float(r["avg_correctness"]), float(r["avg_faithfulness"]), float(r["avg_completeness"])]

    x   = np.arange(len(metrics))
    w   = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))

    bars_b = ax.bar(x - w/2, bv, w, label="Baseline", color=C_BASE, zorder=3)
    bars_r = ax.bar(x + w/2, rv, w, label="RAG",      color=C_RAG,  zorder=3)

    for bar in list(bars_b) + list(bars_r):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=11)
    ax.set_ylim(0, 6); ax.set_ylabel("Score (out of 5)", fontsize=10)
    ax.set_title("Average Answer Quality Metrics\nBaseline vs RAG", fontsize=13, pad=12)
    ax.legend(fontsize=10)
    savefig("bar_metrics_comparison.png")


# ── 2. Hallucination rate ──────────────────────────────────────────────────────
def chart_hallucination(summary: list[dict]) -> None:
    b = next(s for s in summary if s["answer_type"] == "baseline")
    r = next(s for s in summary if s["answer_type"] == "rag")

    fig, ax = plt.subplots(figsize=(6, 4))
    labels  = ["Baseline", "RAG"]
    vals    = [float(b["avg_hallucination_rate"]), float(r["avg_hallucination_rate"])]
    colors  = [C_BASE, C_RAG]
    bars    = ax.bar(labels, vals, color=colors, width=0.45, zorder=3)

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{val:.1%}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylim(0, 0.55)
    ax.set_ylabel("Hallucination Rate (per answer)", fontsize=10)
    ax.set_title("Hallucination Rate\nBaseline vs RAG", fontsize=13, pad=12)
    savefig("hallucination_rate.png")


# ── 3 & 4. Per-question line charts ───────────────────────────────────────────
def chart_per_question(comparison: list[dict], metric: str, title: str, fname: str) -> None:
    qids   = [r["question_id"] for r in comparison]
    bv     = [float(r.get(f"baseline_{metric}", 0)) for r in comparison]
    rv     = [float(r.get(f"rag_{metric}",      0)) for r in comparison]
    x      = np.arange(len(qids))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(x, bv, "o-", color=C_BASE, linewidth=2, markersize=7, label="Baseline")
    ax.plot(x, rv, "s-", color=C_RAG,  linewidth=2, markersize=7, label="RAG")
    ax.fill_between(x, bv, rv, alpha=0.12, color=C_RAG)

    ax.set_xticks(x); ax.set_xticklabels(qids, rotation=45, ha="right", fontsize=9)
    ax.set_ylim(0, 5.5); ax.set_ylabel("Score (out of 5)", fontsize=10)
    ax.set_title(title, fontsize=13, pad=12)
    ax.legend(fontsize=10)
    savefig(fname)


# ── 5. Radar chart ────────────────────────────────────────────────────────────
def chart_radar(summary: list[dict]) -> None:
    b = next(s for s in summary if s["answer_type"] == "baseline")
    r = next(s for s in summary if s["answer_type"] == "rag")

    labels   = ["Correctness", "Faithfulness", "Completeness", "Non-hallucination"]
    bv = [float(b["avg_correctness"]), float(b["avg_faithfulness"]),
          float(b["avg_completeness"]), (1 - float(b["avg_hallucination_rate"])) * 5]
    rv = [float(r["avg_correctness"]), float(r["avg_faithfulness"]),
          float(r["avg_completeness"]), (1 - float(r["avg_hallucination_rate"])) * 5]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    bv += bv[:1]; rv += rv[:1]; angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_facecolor(BG)
    ax.plot(angles, bv, color=C_BASE, linewidth=2, label="Baseline")
    ax.fill(angles, bv, color=C_BASE, alpha=0.25)
    ax.plot(angles, rv, color=C_RAG,  linewidth=2, label="RAG")
    ax.fill(angles, rv, color=C_RAG,  alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 5)
    ax.set_title("Aggregate Quality Profile\nBaseline vs RAG", fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
    savefig("radar_summary.png")


# ── 6. Category heatmap ───────────────────────────────────────────────────────
def chart_category_heatmap(cat_data: list[dict]) -> None:
    categories = sorted({r["category"] for r in cat_data})
    types      = ["baseline", "rag"]
    matrix     = np.zeros((len(categories), 2))

    for r in cat_data:
        ci = categories.index(r["category"])
        ti = types.index(r["answer_type"])
        matrix[ci, ti] = float(r["avg_faithfulness"])

    fig, ax = plt.subplots(figsize=(6, max(4, len(categories) * 0.65)))
    im = ax.imshow(matrix, cmap="YlGnBu", vmin=1, vmax=5, aspect="auto")
    plt.colorbar(im, ax=ax, label="Avg Faithfulness (1–5)")

    ax.set_xticks([0, 1]); ax.set_xticklabels(["Baseline", "RAG"], fontsize=11)
    ax.set_yticks(range(len(categories))); ax.set_yticklabels(categories, fontsize=10)
    ax.set_title("Faithfulness by Category", fontsize=13, pad=12)

    for ci in range(len(categories)):
        for ti in range(2):
            val = matrix[ci, ti]
            ax.text(ti, ci, f"{val:.1f}", ha="center", va="center",
                    fontsize=11, color="black" if val < 3.5 else "white")

    savefig("category_heatmap.png")


# ── 7. Delta bar ──────────────────────────────────────────────────────────────
def chart_delta(comparison: list[dict]) -> None:
    qids   = [r["question_id"] for r in comparison]
    deltas = [float(r.get("rag_faithfulness", 0)) - float(r.get("baseline_faithfulness", 0))
              for r in comparison]
    colors = [C_DELTA if d >= 0 else C_BASE for d in deltas]
    x      = np.arange(len(qids))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(x, deltas, color=colors, zorder=3)
    ax.axhline(0, color="#888", linewidth=1)

    ax.set_xticks(x); ax.set_xticklabels(qids, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Faithfulness Δ (RAG − Baseline)", fontsize=10)
    ax.set_title("Faithfulness Improvement per Question\n(RAG vs Baseline)", fontsize=13, pad=12)

    patch_gain = mpatches.Patch(color=C_DELTA, label="RAG improved")
    patch_loss = mpatches.Patch(color=C_BASE,  label="RAG worse / equal")
    ax.legend(handles=[patch_gain, patch_loss], fontsize=10)
    savefig("improvement_delta.png")


# ── main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    with open(RES_DIR / "summary_stats.json") as f:
        summary = json.load(f)

    comparison = load_csv(RES_DIR / "per_question_comparison.csv")
    cat_data   = load_csv(RES_DIR / "category_breakdown.csv")

    chart_metrics_comparison(summary)
    chart_hallucination(summary)
    chart_per_question(comparison, "correctness",  "Per-Question Correctness\nBaseline vs RAG",  "per_question_correctness.png")
    chart_per_question(comparison, "faithfulness", "Per-Question Faithfulness\nBaseline vs RAG", "per_question_faithfulness.png")
    chart_radar(summary)
    chart_category_heatmap(cat_data)
    chart_delta(comparison)

    print("\n✓ All charts saved to results/")


if __name__ == "__main__":
    main()
