"""Incident loader on synthetic fixtures only; the real originals are never read here."""

import pytest

from cite_and_seek.eval.incidents import IncidentError, load_incidents

SYNTHETIC = """\
scenario: Synthetic symptom
real_file: app/models.py and app/schemas.py
real_function: synthetic_function
real_observable_behavior: >
  Synthetic behavior.
hypothetical_situation: >
  A synthetic user sees a
  synthetic problem.
expected_evidence:
  - synthetic evidence
expected_answer: >
  Synthetic answer.
label: "SYNTHETIC"
"""


def make_dirs(tmp_path, text=SYNTHETIC, with_copy=True):
    incidents_dir = tmp_path / "incidents_src"
    incidents_dir.mkdir()
    (incidents_dir / "SCN-01.md").write_text(text, encoding="utf-8")
    corpus_root = tmp_path / "corpus"
    (corpus_root / "incidents").mkdir(parents=True)
    if with_copy:
        (corpus_root / "incidents" / "SCN-01.md").write_text("copy", encoding="utf-8")
    return incidents_dir, corpus_root


def test_loads_query_files_and_answer(tmp_path):
    incident = load_incidents(*make_dirs(tmp_path))[0]
    assert incident.id == "SCN-01"
    assert incident.corpus_path == "incidents/SCN-01.md"
    assert incident.query == "Synthetic symptom\n\nA synthetic user sees a synthetic problem."
    assert incident.real_files == ("app/models.py", "app/schemas.py")
    assert incident.expected_answer == "Synthetic answer."


def test_rejects_unexpected_keys(tmp_path):
    with pytest.raises(IncidentError, match="key set"):
        load_incidents(*make_dirs(tmp_path, SYNTHETIC + "extra: field\n"))


def test_requires_stripped_copy(tmp_path):
    with pytest.raises(IncidentError, match="stripped copy"):
        load_incidents(*make_dirs(tmp_path, with_copy=False))
