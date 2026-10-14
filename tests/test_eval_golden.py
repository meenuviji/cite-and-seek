"""Golden loader on synthetic fixtures only; the real golden set is never read here."""

import hashlib
import json

import pytest

from cite_and_seek.eval.golden import GoldenSetError, load_golden


def make_item(qid: str, answerable: bool = True, **overrides) -> dict:
    item = {
        "id": qid,
        "question": f"synthetic question {qid}",
        "category": "synthetic",
        "difficulty": "easy",
        "answerable": answerable,
        "expected_sources": ["code/models.py"] if answerable else [],
        "source_type": "code",
        "expected_facts": ["synthetic fact"],
        "ground_truth_answer": "synthetic answer",
        "verified_by": "fixture",
        "verification_status": "verified" if answerable else "verified_absent",
    }
    item.update(overrides)
    return item


def write_fixture(tmp_path, items, tuning, held_out, sha=None):
    golden = tmp_path / "golden_set.json"
    golden.write_text(json.dumps(items), encoding="utf-8")
    digest = sha or hashlib.sha256(golden.read_bytes()).hexdigest()
    split = tmp_path / "golden_split.json"
    split.write_text(json.dumps(
        {"golden_sha256": digest, "tuning": tuning, "held_out": held_out}), encoding="utf-8")
    return golden, split


def test_serves_tuning_by_default_and_held_out_with_final(tmp_path):
    items = [make_item("q1"), make_item("q2"), make_item("q3", answerable=False)]
    golden, split = write_fixture(tmp_path, items, ["q1", "q3"], ["q2"])
    assert [q.id for q in load_golden(golden_path=golden, split_path=split)] == ["q1", "q3"]
    assert [q.id for q in load_golden(True, golden, split)] == ["q2"]


def test_rejects_hash_mismatch(tmp_path):
    golden, split = write_fixture(tmp_path, [make_item("q1")], ["q1"], [], sha="0" * 64)
    with pytest.raises(GoldenSetError, match="hash"):
        load_golden(golden_path=golden, split_path=split)


def test_rejects_split_that_does_not_cover_golden(tmp_path):
    golden, split = write_fixture(tmp_path, [make_item("q1"), make_item("q2")], ["q1"], [])
    with pytest.raises(GoldenSetError, match="do not match"):
        load_golden(golden_path=golden, split_path=split)


def test_rejects_status_disagreement(tmp_path):
    items = [make_item("q1", verification_status="verified_absent")]
    golden, split = write_fixture(tmp_path, items, ["q1"], [])
    with pytest.raises(GoldenSetError, match="disagree"):
        load_golden(golden_path=golden, split_path=split)


def test_error_names_field_not_value(tmp_path):
    items = [make_item("q1", question=12345)]
    golden, split = write_fixture(tmp_path, items, ["q1"], [])
    with pytest.raises(GoldenSetError) as error:
        load_golden(golden_path=golden, split_path=split)
    assert "question" in str(error.value)
    assert "12345" not in str(error.value)
