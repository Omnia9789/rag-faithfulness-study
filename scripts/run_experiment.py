"""
run_experiment.py
-----------------
Orchestrates the full RAG Faithfulness Study pipeline.

Steps:
  1. Optionally generate answers via an LLM API  (set USE_API=True and add your key)
  2. Produce evaluation scores (automated rubric + saves to results/)
  3. Build all visualisations
  4. Compile the HTML report

Usage:
    python scripts/run_experiment.py
"""

import os
import sys
import argparse
import subprocess

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
RESULTS = os.path.join(ROOT, "results")
REPORTS = os.path.join(ROOT, "reports")

os.makedirs(RESULTS, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

# ── config ─────────────────────────────────────────────────────────────────────
USE_API = False          # flip to True to call the LLM API
API_KEY = os.getenv("OPENAI_API_KEY", "")   # or set your key here


def run(script: str, label: str) -> None:
    print(f"\n{'='*60}\n▶  {label}\n{'='*60}")
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script)],
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"✗  {label} failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"✓  {label} complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG Faithfulness Study pipeline")
    parser.add_argument(
        "--skip-api", action="store_true",
        help="Skip LLM API calls and use pre-generated answers"
    )
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  RAG FAITHFULNESS STUDY — experiment runner")
    print("="*60)

    if USE_API and not args.skip_api:
        if not API_KEY:
            print("⚠  USE_API=True but OPENAI_API_KEY is not set. Falling back to pre-generated data.")
        else:
            run("generate_answers.py", "Step 1 — Generate LLM answers via API")
    else:
        print("\n▶  Step 1 — Skipped (using pre-generated answers in data/)")

    run("evaluate.py",   "Step 2 — Score answers")
    run("visualize.py",  "Step 3 — Build visualisations")
    run("report.py",     "Step 4 — Compile HTML report")

    print(f"\n{'='*60}")
    print("  ✓  Pipeline complete!")
    print(f"  Results  → {RESULTS}/")
    print(f"  Report   → {REPORTS}/report.html")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
