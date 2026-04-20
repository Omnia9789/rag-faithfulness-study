"""
evaluate.py
-----------
Loads answers and pre-computed evaluation scores, merges them,
computes summary statistics, and writes results to results/.
"""

import os
import csv
import json
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RES_DIR  = ROOT / "results"
RES_DIR.mkdir(exist_ok=True)

SCORES_FILE   = DATA_DIR / "evaluation_scores.csv"
BASELINE_FILE = DATA_DIR / "baseline_answers.csv"
RAG_FILE      = DATA_DIR / "rag_answers.csv"
QUESTIONS_FILE= DATA_DIR / "questions.csv"
PASSAGES_FILE = DATA_DIR / "passages.csv"


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved → {path}")


def avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    scores    = load_csv(SCORES_FILE)
    baseline  = {r["question_id"]: r for r in load_csv(BASELINE_FILE)}
    rag       = {r["question_id"]: r for r in load_csv(RAG_FILE)}
    questions = {r["id"]: r for r in load_csv(QUESTIONS_FILE)}
    passages  = {r["question_id"]: r for r in load_csv(PASSAGES_FILE)}

    # ── 1. Full merged detail table ────────────────────────────────────────────
    detail_rows = []
    for s in scores:
        qid    = s["question_id"]
        ans_type = s["answer_type"]
        src    = baseline if ans_type == "baseline" else rag
        answer = src.get(qid, {}).get("answer", "")
        passage= passages.get(qid, {}).get("passage", "")
        q_text = questions.get(qid, {}).get("question", "")

        detail_rows.append({
            "question_id":       qid,
            "category":          s["category"],
            "answer_type":       ans_type,
            "question":          q_text,
            "passage_available": "yes" if passage else "no",
            "answer":            answer,
            "correctness":       s["correctness"],
            "faithfulness":      s["faithfulness"],
            "completeness":      s["completeness"],
            "hallucination_count": s["hallucination_count"],
            "hallucination_rate":  s["hallucination_rate"],
            "notes":             s.get("evaluator_notes", ""),
        })

    save_csv(detail_rows, RES_DIR / "evaluation_detail.csv")

    # ── 2. Per-question comparison ─────────────────────────────────────────────
    questions_by_id = {r["id"]: r["question"] for r in load_csv(QUESTIONS_FILE)}
    pairs: dict[str, dict] = {}
    for s in scores:
        qid = s["question_id"]
        if qid not in pairs:
            pairs[qid] = {"question_id": qid,
                          "category": s["category"],
                          "question": questions_by_id.get(qid, "")}
        t = s["answer_type"]
        pairs[qid][f"{t}_correctness"]       = s["correctness"]
        pairs[qid][f"{t}_faithfulness"]      = s["faithfulness"]
        pairs[qid][f"{t}_completeness"]      = s["completeness"]
        pairs[qid][f"{t}_hallucination_rate"]= s["hallucination_rate"]

    comparison_rows = list(pairs.values())
    save_csv(comparison_rows, RES_DIR / "per_question_comparison.csv")

    # ── 3. Aggregate summary ───────────────────────────────────────────────────
    def agg(answer_type: str) -> dict:
        subset = [s for s in scores if s["answer_type"] == answer_type]
        return {
            "answer_type":            answer_type,
            "n_questions":            len(subset),
            "avg_correctness":        round(avg([float(s["correctness"])   for s in subset]), 2),
            "avg_faithfulness":       round(avg([float(s["faithfulness"])  for s in subset]), 2),
            "avg_completeness":       round(avg([float(s["completeness"])  for s in subset]), 2),
            "avg_hallucination_rate": round(avg([float(s["hallucination_rate"]) for s in subset]), 3),
            "total_hallucinations":   sum(int(s["hallucination_count"]) for s in subset),
        }

    summary = [agg("baseline"), agg("rag")]
    save_csv(summary, RES_DIR / "summary_stats.csv")

    # also save as JSON for easy consumption by other scripts
    with open(RES_DIR / "summary_stats.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved → {RES_DIR}/summary_stats.json")

    # ── 4. Category breakdown ──────────────────────────────────────────────────
    categories = sorted({s["category"] for s in scores})
    cat_rows = []
    for cat in categories:
        for answer_type in ("baseline", "rag"):
            subset = [s for s in scores
                      if s["category"] == cat and s["answer_type"] == answer_type]
            if not subset:
                continue
            cat_rows.append({
                "category":               cat,
                "answer_type":            answer_type,
                "avg_correctness":        round(avg([float(s["correctness"])  for s in subset]), 2),
                "avg_faithfulness":       round(avg([float(s["faithfulness"]) for s in subset]), 2),
                "avg_hallucination_rate": round(avg([float(s["hallucination_rate"]) for s in subset]), 3),
            })

    save_csv(cat_rows, RES_DIR / "category_breakdown.csv")

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n── Evaluation Summary ──────────────────────────────────────")
    print(f"{'Metric':<30} {'Baseline':>10} {'RAG':>10} {'Δ':>10}")
    print("-" * 62)
    metrics = [
        ("Correctness (avg)",    "avg_correctness"),
        ("Faithfulness (avg)",   "avg_faithfulness"),
        ("Completeness (avg)",   "avg_completeness"),
        ("Hallucination rate",   "avg_hallucination_rate"),
    ]
    b, r = summary[0], summary[1]
    for label, key in metrics:
        bv = float(b[key]); rv = float(r[key])
        delta = rv - bv
        print(f"  {label:<28} {bv:>10.3f} {rv:>10.3f} {delta:>+10.3f}")
    print(f"\n  Total hallucinations: baseline={b['total_hallucinations']}  "
          f"rag={r['total_hallucinations']}")
    print("────────────────────────────────────────────────────────────\n")

    print("✓ Evaluation complete.")


if __name__ == "__main__":
    main()
