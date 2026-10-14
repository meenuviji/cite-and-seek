"""`cite-and-seek eval check`: load the golden set and incidents, normalize paths, report counts.

Output is counts and question IDs only (L7). Any unmapped scored path stops
the run (decision 13).
"""

import sys

from cite_and_seek.eval import CORPUS_ROOT
from cite_and_seek.eval.golden import load_golden
from cite_and_seek.eval.incidents import load_incidents
from cite_and_seek.eval.paths import PathNormalizer, normalize_all


def run_check(final: bool) -> None:
    questions = load_golden(final=final)
    answerable = [q for q in questions if q.answerable]
    unanswerable = [q for q in questions if not q.answerable]
    split_name = "held-out (--final)" if final else "tuning"
    print(f"split: {split_name}, {len(questions)} questions "
          f"({len(answerable)} answerable, {len(unanswerable)} unanswerable)")

    normalizer = PathNormalizer(CORPUS_ROOT)
    # Only answerable questions' sources are scored (recall@k); unanswerable ones are not.
    _, golden_report = normalize_all(
        normalizer, {q.id: q.expected_sources for q in answerable}
    )
    no_sources = sorted(q.id for q in answerable if not q.expected_sources)
    print(f"golden expected_sources (answerable, scored): {golden_report.paths} paths, "
          f"{golden_report.normalized} normalized, {len(golden_report.unmapped_ids)} questions unmapped")
    print(f"golden expected_sources (unanswerable, not scored): "
          f"{sum(len(q.expected_sources) for q in unanswerable)} paths")

    incidents = load_incidents()
    _, incident_report = normalize_all(normalizer, {i.id: i.real_files for i in incidents})
    print(f"incidents: {len(incidents)}, real_file: {incident_report.paths} paths, "
          f"{incident_report.normalized} normalized, {len(incident_report.unmapped_ids)} unmapped")

    problems = []
    if golden_report.unmapped_ids:
        problems.append(f"golden questions with unmapped sources: {list(golden_report.unmapped_ids)}")
    if no_sources:
        problems.append(f"answerable questions with no expected_sources: {no_sources}")
    if incident_report.unmapped_ids:
        problems.append(f"incidents with unmapped real_file: {list(incident_report.unmapped_ids)}")
    if problems:
        sys.exit("STOP (decision 13):\n  " + "\n  ".join(problems))
    print("OK: every scored path maps to a corpus file")
