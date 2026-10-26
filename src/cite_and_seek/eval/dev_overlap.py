"""`cite-and-seek eval dev-overlap`: dev-query similarity to golden questions (L12).

For each owner-written dev query, the highest cosine similarity to any
tuning-split golden question. Scores and dev-query text only; no golden text
and no nearest-question IDs are reported.
"""

from cite_and_seek.eval import REPO_ROOT
from cite_and_seek.eval.golden import load_golden
from cite_and_seek.eval.runinfo import new_run_id, require_clean_tree, run_config, write_results
from cite_and_seek.embedding import MiniLMEmbedder

DEV_QUERIES = REPO_ROOT / "dev" / "dev_queries.txt"


def run_dev_overlap() -> None:
    require_clean_tree()
    queries = [line.strip() for line in DEV_QUERIES.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    golden = load_golden()
    embedder = MiniLMEmbedder()
    similarity = embedder.embed(queries) @ embedder.embed([q.question for q in golden]).T
    best = similarity.max(axis=1)

    run_id = new_run_id("devoverlap")
    payload = {
        "run_id": run_id,
        "stage": "dev_overlap",
        "config": run_config(compared_against="tuning-split golden questions",
                             similarity="cosine, all-MiniLM-L6-v2"),
        "n_dev_queries": len(queries),
        "n_golden_questions": len(golden),
        "max_similarity": [{"dev_query": q, "max_cosine": round(float(s), 4)}
                           for q, s in zip(queries, best)],
    }
    path = write_results(run_id, payload)
    print(f"run {run_id}: {len(queries)} dev queries vs {len(golden)} tuning golden questions")
    for row in payload["max_similarity"]:
        print(f"  {row['max_cosine']:.4f}  {row['dev_query']}")
    print(f"wrote {path}")
