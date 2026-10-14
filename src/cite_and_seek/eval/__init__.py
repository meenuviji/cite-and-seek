"""Evaluation harness (v0.2).

Only this package reads the golden set and the incident originals (L6). Its
terminal output is aggregates and question IDs only (L7); errors name fields
and IDs, never values.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = REPO_ROOT / "corpus"
