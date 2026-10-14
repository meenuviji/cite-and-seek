"""Incident-scenario loader for scoring (decision 3, L6).

Reads the locked originals, which hold the ground truth (real_file,
expected_answer). The query is built only from the fields the corpus copy
keeps, matching what a real ticket would carry.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from cite_and_seek.eval import CORPUS_ROOT, REPO_ROOT

INCIDENTS_DIR = REPO_ROOT / "evaluation" / "synthetic_incidents"
EXPECTED_KEYS = {
    "scenario",
    "real_file",
    "real_function",
    "real_observable_behavior",
    "hypothetical_situation",
    "expected_evidence",
    "expected_answer",
    "label",
}


# real_file may name more than one file; each path-like token is one file.
PATH_TOKEN = re.compile(r"[\w./-]+\.\w+")


class IncidentError(ValueError):
    """Schema problem. Messages name files and fields, never values."""


@dataclass(frozen=True)
class Incident:
    id: str  # file stem, e.g. SCN-01
    corpus_path: str  # the stripped copy, excluded from retrieval when scoring (decision 11)
    query: str
    real_files: tuple[str, ...]
    expected_answer: str


def load_incidents(
    incidents_dir: Path = INCIDENTS_DIR, corpus_root: Path = CORPUS_ROOT
) -> list[Incident]:
    incidents = []
    for path in sorted(incidents_dir.glob("SCN-*.md")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != EXPECTED_KEYS:
            raise IncidentError(f"{path.name}: unexpected key set")
        for key in ("scenario", "hypothetical_situation", "real_file", "expected_answer"):
            if not isinstance(data[key], str) or not data[key].strip():
                raise IncidentError(f"{path.name}: field '{key}' missing or empty")
        real_files = tuple(PATH_TOKEN.findall(data["real_file"]))
        if not real_files:
            raise IncidentError(f"{path.name}: field 'real_file' names no file path")
        corpus_path = f"incidents/{path.name}"
        if not (corpus_root / corpus_path).is_file():
            raise IncidentError(f"{path.name}: no stripped copy at corpus/{corpus_path}")
        incidents.append(Incident(
            id=path.stem,
            corpus_path=corpus_path,
            query=f"{data['scenario'].strip()}\n\n{data['hypothetical_situation'].strip()}",
            real_files=real_files,
            expected_answer=data["expected_answer"].strip(),
        ))
    if not incidents:
        raise IncidentError(f"no SCN-*.md files in {incidents_dir}")
    return incidents
