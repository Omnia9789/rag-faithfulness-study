"""
generate_answers.py
-------------------
Calls an LLM API to generate both baseline and RAG-style answers.
Saves results to data/baseline_answers.csv and data/rag_answers.csv.

Supports:
  - OpenAI (GPT-4o, GPT-3.5-turbo, etc.)
  - Anthropic (claude-3-5-sonnet, etc.)  ← set PROVIDER = "anthropic"

Set your API key via environment variable:
    export OPENAI_API_KEY="sk-..."
    export ANTHROPIC_API_KEY="sk-ant-..."

Or hard-code it below (not recommended for shared repos).
"""

import os
import csv
import time
from pathlib import Path

# ── config ─────────────────────────────────────────────────────────────────────
PROVIDER   = "openai"                     # "openai" | "anthropic"
MODEL      = "gpt-4o-mini"               # or "claude-3-5-haiku-20241022"
SLEEP_SEC  = 1.5                         # pause between API calls (rate limits)

ROOT       = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "data"

QUESTIONS_FILE  = DATA_DIR / "questions.csv"
PASSAGES_FILE   = DATA_DIR / "passages.csv"
BASELINE_OUT    = DATA_DIR / "baseline_answers.csv"
RAG_OUT         = DATA_DIR / "rag_answers.csv"

BASELINE_SYSTEM = (
    "You are a knowledgeable assistant. Answer the question clearly and accurately "
    "in 4–6 sentences. Do not ask for clarification."
)

RAG_SYSTEM = (
    "You are a knowledgeable assistant. You will be given a reference passage and a question. "
    "Answer the question using only information from the passage. "
    "Be precise and complete. Do not add information not present in the passage."
)

RAG_USER_TEMPLATE = (
    "Reference passage:\n\"\"\"\n{passage}\n\"\"\"\n\nQuestion: {question}"
)


# ── helpers ────────────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(rows: list[dict], path: Path, fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved → {path}")


# ── API callers ────────────────────────────────────────────────────────────────

def call_openai(system: str, user: str, model: str) -> str:
    try:
        from openai import OpenAI  # pip install openai
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.3,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()


def call_anthropic(system: str, user: str, model: str) -> str:
    try:
        import anthropic  # pip install anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    msg = client.messages.create(
        model=model,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


def call_llm(system: str, user: str) -> str:
    if PROVIDER == "openai":
        return call_openai(system, user, MODEL)
    elif PROVIDER == "anthropic":
        return call_anthropic(system, user, MODEL)
    else:
        raise ValueError(f"Unknown PROVIDER: {PROVIDER!r}")


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    questions = load_csv(QUESTIONS_FILE)
    passages  = {p["question_id"]: p["passage"] for p in load_csv(PASSAGES_FILE)}

    baseline_rows: list[dict] = []
    rag_rows: list[dict]      = []

    for i, q in enumerate(questions, 1):
        qid      = q["id"]
        question = q["question"]

        print(f"[{i}/{len(questions)}] {qid}: {question[:60]}...")

        # — baseline answer —
        print("  → Generating baseline answer …")
        baseline_text = call_llm(BASELINE_SYSTEM, f"Question: {question}")
        baseline_rows.append({
            "id":          f"A{i:02d}",
            "question_id": qid,
            "answer_type": "baseline",
            "answer":      baseline_text,
        })
        time.sleep(SLEEP_SEC)

        # — RAG answer —
        passage = passages.get(qid, "")
        if not passage:
            print(f"  ⚠  No passage found for {qid}, skipping RAG answer.")
            continue

        print("  → Generating RAG answer …")
        rag_user  = RAG_USER_TEMPLATE.format(passage=passage, question=question)
        rag_text  = call_llm(RAG_SYSTEM, rag_user)
        rag_rows.append({
            "id":          f"B{i:02d}",
            "question_id": qid,
            "answer_type": "rag",
            "answer":      rag_text,
        })
        time.sleep(SLEEP_SEC)

    fieldnames = ["id", "question_id", "answer_type", "answer"]
    save_csv(baseline_rows, BASELINE_OUT, fieldnames)
    save_csv(rag_rows,      RAG_OUT,      fieldnames)
    print("\n✓ Answer generation complete.")


if __name__ == "__main__":
    main()
