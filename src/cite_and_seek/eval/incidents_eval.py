"""`cite-and-seek eval incidents`: incident retrieval with leave-one-out by file (decisions 3, 11).

Each incident's own corpus file is excluded entirely: the grader asks for k
plus that file's chunk count and drops those chunks, so the retriever
interface stays search(question, k) (L8). Reported as a separate set, never
used to choose configurations. Answer scoring for incidents is out of scope in
v0.2 (sprint deviation: retrieval only).
"""

import json
import sys

from cite_and_seek.cli import build_retriever
from cite_and_seek.eval import CORPUS_ROOT
from cite_and_seek.eval.incidents import load_incidents
from cite_and_seek.eval.paths import PathNormalizer, normalize_all
from cite_and_seek.eval.retrieval_eval import KS, aggregate, score_ranking
from cite_and_seek.eval.runinfo import (REPORTS_DIR, new_run_id, require_clean_tree,
                                        run_config, write_results)


def run_incidents() -> None:
    require_clean_tree()
    incidents = load_incidents()
    expected, report = normalize_all(PathNormalizer(CORPUS_ROOT),
                                     {i.id: i.real_files for i in incidents})
    if report.unmapped_ids:
        sys.exit(f"STOP (decision 13): unmapped real_file for {list(report.unmapped_ids)}")

    retriever = build_retriever()
    run_id = new_run_id("incidents")
    scores, details = {}, []
    for incident in incidents:
        own = sum(c.corpus_path == incident.corpus_path for c in retriever.chunks)
        hits = retriever.search(incident.query, max(KS) + own)
        kept = [h for h in hits if h.chunk.corpus_path != incident.corpus_path][:max(KS)]
        ranked = [h.chunk.source_path for h in kept]
        scores[incident.id] = {k: score_ranking(expected[incident.id], ranked, k) for k in KS}
        details.append({"id": incident.id, "excluded_chunks": own, "retrieved": ranked})

    detail_dir = REPORTS_DIR / run_id
    detail_dir.mkdir(parents=True, exist_ok=True)
    with (detail_dir / "incidents.jsonl").open("w", encoding="utf-8") as handle:
        for row in details:
            handle.write(json.dumps(row) + "\n")

    metrics = aggregate(scores)
    payload = {
        "run_id": run_id,
        "stage": "incidents",
        "set": "incidents (separate; never used to choose configurations)",
        "config": run_config(ks=list(KS), leave_one_out="exclude every chunk of the incident's own file",
                             query="scenario + hypothetical_situation"),
        "n_incidents": len(incidents),
        "n_expected_paths": report.paths,
        "metrics": metrics,
        "ids_missed_at_10": sorted(i for i, per_k in scores.items() if not per_k[10]["hit"]),
        "answer_scoring": "not run in v0.2 (retrieval only)",
    }
    path = write_results(run_id, payload)
    print(f"run {run_id}: {len(incidents)} incidents, {report.paths} expected paths, leave-one-out by file")
    for k in KS:
        m = metrics[str(k)]
        print(f"  k={k:<2} hit {m['hit']['count']}/{m['hit']['n']} "
              f"[{m['hit']['ci95'][0]:.2f},{m['hit']['ci95'][1]:.2f}]  "
              f"recall {m['recall']['mean']:.3f}  MRR {m['mrr']['mean']:.3f}")
    print(f"missed at k=10: {payload['ids_missed_at_10']}")
    print(f"wrote {path}")
