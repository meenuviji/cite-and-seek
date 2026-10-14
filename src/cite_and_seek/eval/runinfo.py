"""Run IDs and the run configuration recorded with every result (L11, L15)."""

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version

from cite_and_seek.cli import DEFAULT_K
from cite_and_seek.corpus import CHUNK_TOKENS, MODEL_NAME
from cite_and_seek.eval import REPO_ROOT
from cite_and_seek.eval.golden import SPLIT_PATH
from cite_and_seek.generation import MAX_TOKENS, MODEL_ID, SYSTEM_PROMPT, TEMPERATURE

RESULTS_DIR = REPO_ROOT / "results"
REPORTS_DIR = REPO_ROOT / "reports" / "runs"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def new_run_id(stage: str) -> str:
    return f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{stage}-{_git('rev-parse', '--short', 'HEAD')}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_config(**extra) -> dict:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    return {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "split": {"seed": split["seed"], "file_sha256": hashlib.sha256(SPLIT_PATH.read_bytes()).hexdigest(),
                  "golden_sha256": split["golden_sha256"]},
        "embedding_model": MODEL_NAME,
        "chunk_tokens": CHUNK_TOKENS,
        "retriever": "dense, numpy brute-force cosine",
        "pipeline_k": DEFAULT_K,
        "generation": {"model": MODEL_ID, "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
                       "system_prompt_sha256": sha256_text(SYSTEM_PROMPT)},
        "versions": {"python": platform.python_version(),
                     **{name: version(name) for name in
                        ("sentence-transformers", "numpy", "torch", "anthropic")}},
        **extra,
    }


def write_results(run_id: str, payload: dict) -> str:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{run_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(REPO_ROOT))
