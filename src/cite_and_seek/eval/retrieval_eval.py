"""`cite-and-seek eval retrieval`: file-level retrieval metrics (decision 16).

For each answerable question, the top max(K) chunks are retrieved once; k
counts chunks, and a chunk matches when its source_path is one of the
question's canonical expected_sources. Terminal output and results/ hold
aggregates and IDs only; per-question detail goes to reports/ (L7, L15).
"""

import json
import sys

from cite_and_seek.cli import build_retriever, DEFAULT_K
from cite_and_seek.eval import CORPUS_ROOT
from cite_and_seek.eval.golden import load_golden
from cite_and_seek.eval.paths import PathNormalizer, normalize_all
from cite_and_seek.eval.runinfo import (REPORTS_DIR, new_run_id, require_clean_tree,
                                        run_config, write_results)
from cite_and_seek.eval.stats import mean_with_ci, proportion

KS = (1, 3, 5, 10)


def score_ranking(expected: frozenset[str], ranked_sources: list[str], k: int) -> dict:
    """hit, recall, and reciprocal rank for one question at cutoff k."""
    top = ranked_sources[:k]
    found = expected & set(top)
    first = next((rank for rank, source in enumerate(top, start=1) if source in expected), None)
    return {"hit": bool(found), "recall": len(found) / len(expected),
            "rr": 1 / first if first else 0.0}


def aggregate(scores: dict[str, dict[int, dict]]) -> dict:
    by_k = {}
    for k in KS:
        rows = [per_k[k] for per_k in scores.values()]
        by_k[str(k)] = {
            "hit": proportion(sum(r["hit"] for r in rows), len(rows)),
            "recall": mean_with_ci([r["recall"] for r in rows]),
            "mrr": mean_with_ci([r["rr"] for r in rows]),
        }
    return by_k


def run_retrieval(final: bool) -> None:
    require_clean_tree()
    questions = [q for q in load_golden(final=final) if q.answerable]
    expected, report = normalize_all(PathNormalizer(CORPUS_ROOT),
                                     {q.id: q.expected_sources for q in questions})
    if report.unmapped_ids:
        sys.exit(f"STOP (decision 13): unmapped sources for {list(report.unmapped_ids)}")

    retriever = build_retriever()
    run_id = new_run_id("retrieval")
    scores, details = {}, []
    for q in questions:
        ranked = [hit.chunk.source_path for hit in retriever.search(q.question, max(KS))]
        scores[q.id] = {k: score_ranking(expected[q.id], ranked, k) for k in KS}
        details.append({"id": q.id, "expected": sorted(expected[q.id]), "retrieved": ranked})

    detail_dir = REPORTS_DIR / run_id
    detail_dir.mkdir(parents=True, exist_ok=True)
    with (detail_dir / "retrieval.jsonl").open("w", encoding="utf-8") as handle:
        for row in details:
            handle.write(json.dumps(row) + "\n")

    metrics = aggregate(scores)
    payload = {
        "run_id": run_id,
        "stage": "retrieval",
        "split": "held_out" if final else "tuning",
        "config": run_config(ks=list(KS), chunk_count=len(retriever.chunks),
                             matching="file-level, source_path after decision-13 normalization"),
        "n_questions": len(questions),
        "n_expected_paths": report.paths,
        "metrics": metrics,
        "ids_missed_at_10": sorted(i for i, per_k in scores.items() if not per_k[10]["hit"]),
        # IDs only (L15); used for diagnostics such as false abstentions despite a hit.
        "ids_missed_at_k": {str(k): sorted(i for i, per_k in scores.items() if not per_k[k]["hit"])
                            for k in KS},
    }
    path = write_results(run_id, payload)

    print(f"run {run_id}: {len(questions)} answerable questions "
          f"({payload['split']}), {report.paths} expected paths")
    print(f"{'k':>3}  {'hit@k':>22}  {'recall@k':>22}  {'MRR@k':>22}")
    for k in KS:
        m = metrics[str(k)]
        hit, rec, mrr = m["hit"], m["recall"], m["mrr"]
        marker = "  <- pipeline k" if k == DEFAULT_K else ""
        print(f"{k:>3}  {hit['count']:>2}/{hit['n']} {hit['rate']:.3f} "
              f"[{hit['ci95'][0]:.2f},{hit['ci95'][1]:.2f}]  "
              f"{rec['mean']:>8.3f} [{rec['ci95'][0]:.2f},{rec['ci95'][1]:.2f}]  "
              f"{mrr['mean']:>8.3f} [{mrr['ci95'][0]:.2f},{mrr['ci95'][1]:.2f}]{marker}")
    print(f"missed at k=10: {payload['ids_missed_at_10']}")
    print(f"wrote {path}; per-question detail in reports/runs/{run_id}/")
