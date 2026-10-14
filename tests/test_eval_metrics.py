"""Interval estimates and per-question retrieval scoring, on synthetic inputs."""

import pytest

from cite_and_seek.eval.retrieval_eval import score_ranking
from cite_and_seek.eval.stats import bootstrap_mean, proportion, wilson


@pytest.mark.parametrize("successes, n, low, high", [
    (5, 10, 0.2366, 0.7634),
    (0, 10, 0.0, 0.2775),
    (10, 10, 0.7225, 1.0),
])
def test_wilson_known_values(successes, n, low, high):
    lo, hi = wilson(successes, n)
    assert lo == pytest.approx(low, abs=1e-4)
    assert hi == pytest.approx(high, abs=1e-4)


def test_proportion_reports_counts():
    result = proportion(3, 4)
    assert (result["count"], result["n"], result["rate"]) == (3, 4, 0.75)


def test_bootstrap_is_deterministic_and_brackets_mean():
    values = [0.0, 0.5, 1.0, 1.0, 0.25]
    first, second = bootstrap_mean(values), bootstrap_mean(values)
    assert first == second
    assert first[0] <= sum(values) / len(values) <= first[1]


def test_bootstrap_constant_values():
    assert bootstrap_mean([1.0, 1.0, 1.0]) == (1.0, 1.0)


RANKED = ["a.py", "b.py", "a.py", "c.py", "d.py"]


def test_single_expected_file():
    expected = frozenset({"c.py"})
    assert score_ranking(expected, RANKED, 3) == {"hit": False, "recall": 0.0, "rr": 0.0}
    assert score_ranking(expected, RANKED, 5) == {"hit": True, "recall": 1.0, "rr": 0.25}


def test_multiple_expected_files_partial_recall():
    expected = frozenset({"b.py", "z.py"})
    assert score_ranking(expected, RANKED, 5) == {"hit": True, "recall": 0.5, "rr": 0.5}


def test_duplicate_chunks_from_one_file_count_once():
    expected = frozenset({"a.py", "b.py"})
    assert score_ranking(expected, RANKED, 1) == {"hit": True, "recall": 0.5, "rr": 1.0}
