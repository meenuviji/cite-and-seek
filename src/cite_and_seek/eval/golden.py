"""Golden-set loader (decision 17, L6, L10).

Serves tuning-split questions unless final=True, which serves the held-out
split (used once, at v1.0). The golden file must match the hash recorded in
the split, so a changed golden set cannot be scored against a stale split.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from cite_and_seek.eval import REPO_ROOT

GOLDEN_PATH = REPO_ROOT / "evaluation" / "questions" / "golden_set.json"
SPLIT_PATH = REPO_ROOT / "evaluation" / "splits" / "golden_split.json"

FIELD_TYPES: dict[str, type] = {
    "id": str,
    "question": str,
    "category": str,
    "difficulty": str,
    "answerable": bool,
    "expected_sources": list,
    "source_type": str,
    "expected_facts": list,
    "ground_truth_answer": str,
    "verified_by": str,
    "verification_status": str,
}
STATUS_FOR_ANSWERABLE = {True: "verified", False: "verified_absent"}


class GoldenSetError(ValueError):
    """Schema or integrity problem. Messages name fields and IDs, never values."""


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    question: str
    category: str
    difficulty: str
    answerable: bool
    expected_sources: tuple[str, ...]
    source_type: str
    expected_facts: tuple[str, ...]
    ground_truth_answer: str


def _validate(index: int, item: object) -> GoldenQuestion:
    if not isinstance(item, dict):
        raise GoldenSetError(f"entry {index} is not an object")
    label = item.get("id") if isinstance(item.get("id"), str) else f"entry {index}"
    for field, kind in FIELD_TYPES.items():
        if not isinstance(item.get(field), kind):
            raise GoldenSetError(f"{label}: field '{field}' missing or not {kind.__name__}")
    for field in ("expected_sources", "expected_facts"):
        if not all(isinstance(value, str) for value in item[field]):
            raise GoldenSetError(f"{label}: field '{field}' has a non-string item")
    if item["verification_status"] != STATUS_FOR_ANSWERABLE[item["answerable"]]:
        raise GoldenSetError(f"{label}: 'answerable' and 'verification_status' disagree")
    return GoldenQuestion(
        id=item["id"],
        question=item["question"],
        category=item["category"],
        difficulty=item["difficulty"],
        answerable=item["answerable"],
        expected_sources=tuple(item["expected_sources"]),
        source_type=item["source_type"],
        expected_facts=tuple(item["expected_facts"]),
        ground_truth_answer=item["ground_truth_answer"],
    )


def load_golden(
    final: bool = False, golden_path: Path = GOLDEN_PATH, split_path: Path = SPLIT_PATH
) -> list[GoldenQuestion]:
    raw = golden_path.read_bytes()
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != split["golden_sha256"]:
        raise GoldenSetError("golden_set.json does not match the hash recorded in the split")

    data = json.loads(raw)
    if not isinstance(data, list):
        raise GoldenSetError("golden_set.json top level is not a list")
    questions = [_validate(i, item) for i, item in enumerate(data)]
    by_id = {q.id: q for q in questions}
    if len(by_id) != len(questions):
        raise GoldenSetError("duplicate question ids")

    tuning, held_out = set(split["tuning"]), set(split["held_out"])
    if tuning & held_out:
        raise GoldenSetError(f"ids in both splits: {sorted(tuning & held_out)}")
    if tuning | held_out != by_id.keys():
        raise GoldenSetError("split ids do not match golden ids")

    selected = held_out if final else tuning
    return [by_id[i] for i in sorted(selected)]
