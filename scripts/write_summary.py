"""Build results/v0.2-summary.md from the committed results/*.json files only.

Reads aggregates and IDs (L15); never reads the golden set or reports/. Uses
the latest result of each stage. Judge-based rows are labeled uncalibrated
(decision 19) and shown as pending if no judge result exists.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"
OUT = RESULTS / "v0.2-summary.md"


def latest(stage: str, predicate=lambda payload: True) -> dict | None:
    for path in sorted(RESULTS.glob(f"*-{stage}-*.json"), reverse=True):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if predicate(payload):
            return payload
    return None


def prop(m: dict) -> str:
    rate = "n/a" if m["rate"] is None else f"{m['rate']:.3f}"
    return f"{m['count']}/{m['n']} = {rate} [{m['ci95'][0]:.2f}, {m['ci95'][1]:.2f}]"


def mean(m: dict) -> str:
    return f"{m['mean']:.3f} [{m['ci95'][0]:.2f}, {m['ci95'][1]:.2f}] (n={m['n']})"


def table_rows(retrieval, run, judge, closed_judge, gain, incidents) -> list[str]:
    rows = ["| Area | Metric | Value (95% interval) |", "|---|---|---|"]
    for k in ("1", "3", "5", "10"):
        m = retrieval["metrics"][k]
        tag = " (pipeline k)" if k == "5" else ""
        rows.append(f"| Retrieval | hit@{k}{tag} | {prop(m['hit'])} |")
        rows.append(f"| Retrieval | recall@{k}{tag} | {mean(m['recall'])} |")
        rows.append(f"| Retrieval | MRR@{k}{tag} | {mean(m['mrr'])} |")
    m = run["metrics"]
    rows += [
        f"| Abstention | Correct abstention (unanswerable) | {prop(m['correct_abstention'])} |",
        f"| Abstention | False abstention (answerable) | {prop(m['false_abstention'])} |",
        f"| Abstention | Format violations (of abstentions) | {prop(m['abstention_format_violation'])} |",
        f"| Citations | Citation validity (exact match to a retrieved chunk) | {prop(m['citation_validity'])} |",
        f"| Citations | Answers with an invalid citation | {prop(m['answers_with_invalid_citation'])} |",
        f"| Citations | Answers with no citation | {prop(m['answers_without_citations'])} |",
    ]
    if judge:
        jm = judge["metrics"]
        rows += [
            f"| Correctness (uncalibrated judge) | Correct, of all answerable | {prop(jm['correct_over_answerable'])} |",
            f"| Correctness (uncalibrated judge) | Correct or partial, of all answerable | {prop(jm['correct_or_partial_over_answerable'])} |",
        ]
        for label in ("correct", "partial", "incorrect"):
            rows.append(f"| Correctness (uncalibrated judge) | {label.capitalize()}, of judged answers | "
                        f"{prop(jm['label_share_of_judged'][label])} |")
    else:
        rows.append("| Correctness (uncalibrated judge) | Correct, of all answerable | "
                    "pending: judge free-tier quota (decision 19) |")
    if closed_judge and gain:
        cm = closed_judge["metrics"]
        rows += [
            f"| Closed-book (uncalibrated judge) | Correct, of all answerable | {prop(cm['correct_over_answerable'])} |",
            f"| Closed-book (uncalibrated judge) | RAG gain (paired difference in correct rate) | {mean(gain['difference'])} |",
        ]
    else:
        rows.append("| Closed-book | Correctness and RAG gain | pending (decision 19) |")
    u, lat = run["usage"], run["latency_s"]
    rows += [
        f"| Cost | Generation, {run['n_questions']} questions | ${u['cost_usd']:.4f} "
        f"({u['input_tokens']} input / {u['output_tokens']} output tokens) |",
        f"| Latency | Generation call per question | mean {lat['mean']:.2f}s, median {lat['median']:.2f}s, "
        f"p90 {lat['p90']:.2f}s |",
    ]
    for k in ("1", "5", "10"):
        im = incidents["metrics"][k]
        rows.append(f"| Incidents (separate set) | hit@{k}, leave-one-out by file | {prop(im['hit'])} |")
    rows.append(f"| Incidents (separate set) | recall@5 | {mean(incidents['metrics']['5']['recall'])} |")
    return rows


def main() -> None:
    retrieval = latest("retrieval")
    run = latest("run")
    incidents = latest("incidents")
    dev = latest("devoverlap")
    judge = latest("judge", lambda p: p["source_run_id"] == run["run_id"])
    closed = latest("closedbook")
    closed_judge = closed and latest("judge", lambda p: p["source_run_id"] == closed["run_id"])
    gain = None
    if judge and closed_judge:
        import sys
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from cite_and_seek.eval.judge_stage import rag_gain
        gain = rag_gain(judge, closed_judge)

    config = run["config"]
    if judge:
        judge_run = f"`{judge['run_id']}` (git `{judge['config']['git_commit'][:7]}`)"
        judge_model = f"`{judge['config']['judge']['model']}`, temperature 0, JSON schema"
        judge_prompt = f"`{judge['config']['judge']['system_prompt_sha256']}`"
    else:
        judge_run = judge_model = judge_prompt = "pending"
    lines = [
        "# v0.2 baseline results",
        "",
        "Generated by `scripts/write_summary.py` from `results/*.json` (aggregates and IDs only). "
        f"Tuning split: {run['n_questions']} questions "
        f"({run['metrics']['false_abstention']['n']} answerable, {run['metrics']['correct_abstention']['n']} unanswerable). "
        "Proportions: count/n = rate [95% Wilson]. Recall and MRR: mean [95% percentile bootstrap, "
        "seed 2026, 10,000 resamples]. Judge-based numbers are **uncalibrated** (decision 19).",
        "",
        *table_rows(retrieval, run, judge, closed_judge, gain, incidents),
        "",
        "## Question IDs behind the error rates",
        "",
        f"- Retrieval misses at k = 10: {', '.join(retrieval['ids_missed_at_10']) or 'none'}",
        f"- False abstentions: {', '.join(run['ids']['false_abstention']) or 'none'}",
        f"- Missed abstentions: {', '.join(run['ids']['missed_abstention']) or 'none'}",
        f"- Answers with an invalid citation: {', '.join(run['ids']['invalid_citation']) or 'none'}",
        f"- Answers with no citation: {', '.join(run['ids']['without_citations']) or 'none'}",
    ]
    if judge:
        lines.append(f"- Judged incorrect (uncalibrated): {', '.join(judge['ids_by_outcome']['incorrect']) or 'none'}")
        if judge["ids_by_outcome"]["judge_error"]:
            lines.append(f"- Judge errors: {', '.join(judge['ids_by_outcome']['judge_error'])}")
    lines.append(f"- Incident retrieval misses at k = 10: {', '.join(incidents['ids_missed_at_10']) or 'none'}")
    by_type = run["metrics"]["abstention_format_violation"]["by_type"]
    lines += [
        f"- Abstention-format violations by type: "
        + ", ".join(f"{name} {count}" for name, count in sorted(by_type.items()))
        + " (embedded_marker counts non-abstaining answers that contain the marker; "
        "the other types are among abstentions, and one abstention can have several)",
        "",
        "## Dev-query overlap (L12)",
        "",
        "Highest cosine similarity of each owner-written dev query to any tuning-split golden question "
        "(all-MiniLM-L6-v2). Dev queries were used only for smoke tests, never for tuning.",
        "",
        "| Dev query | Max cosine |",
        "|---|---|",
        *[f"| {row['dev_query']} | {row['max_cosine']:.4f} |" for row in dev["max_similarity"]],
        "",
        "## Run configuration",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Retrieval run | `{retrieval['run_id']}` (git `{retrieval['config']['git_commit'][:7]}`) |",
        f"| Generation run | `{run['run_id']}` (git `{config['git_commit'][:7]}`) |",
        f"| Judge run | {judge_run} |",
        f"| Incident run | `{incidents['run_id']}` (git `{incidents['config']['git_commit'][:7]}`) |",
        f"| Clean tree enforced | {all(p['config'].get('clean_tree_enforced') and not p['config']['git_dirty'] for p in filter(None, (retrieval, run, judge, incidents, dev)))} |",
        f"| Embedding model | `{config['embedding_model']}` |",
        f"| Chunk size | {config['chunk_tokens']} tokens, no overlap |",
        f"| Retriever | {config['retriever']}, k = {config['pipeline_k']} |",
        f"| Generation model | `{config['generation']['model']}`, temperature {config['generation']['temperature']}, "
        f"max_tokens {config['generation']['max_tokens']} |",
        f"| Generation prompt SHA-256 | `{config['generation']['system_prompt_sha256']}` |",
        f"| Judge model | {judge_model} |",
        f"| Judge prompt SHA-256 | {judge_prompt} |",
        f"| Split | seed {config['split']['seed']}, split file SHA-256 `{config['split']['file_sha256'][:16]}…`, "
        f"golden SHA-256 `{config['split']['golden_sha256'][:16]}…` |",
        f"| Price basis | ${config['price_per_mtok_usd']['input']:.2f} / ${config['price_per_mtok_usd']['output']:.2f} "
        "per million input / output tokens |",
        "",
        "## Known gaps",
        "",
        f"- **Small sample.** {run['metrics']['correct_abstention']['n']} unanswerable questions in the tuning split: "
        "one abstention moves the abstention rate by about 17 points. Read the intervals, not the point estimates.",
        "- **Public golden set.** Future models may train on it; the closed-book baseline (L13) is the guard, "
        "and it is still pending.",
        "- **No faithfulness metric** (decision 18). The judge measures agreement with the reference answer; "
        "citation validity checks only that each citation points at a retrieved chunk.",
        "- **Answer correctness pending** (decision 19). The judge's free-tier quota (20 requests per model) "
        "stopped the run; `eval judge --resume` completes it with the same judge.",
        "- **Uncalibrated judge** (decision 19). No judge-human agreement has been measured yet.",
        "- **Closed-book baseline not run** (decision 19): the Anthropic API rejected the run "
        "(`organization_on_hold`). RAG gain is pending.",
        "- **Incident answers not scored** (decision 19): incident results are retrieval only.",
        "- **SCN-07 hint** (decision 11). Its situation text hints at its cause, so its retrieval score is likely optimistic.",
        "- **Format heuristic.** The `multi_sentence` abstention check counts sentence-ending punctuation and can "
        "over-count abbreviations.",
        "- **Dev-query overlap.** One dev query has a max cosine of "
        f"{max(r['max_cosine'] for r in dev['max_similarity']):.2f} to a tuning question. Dev queries were not "
        "used for any tuning, so this is recorded, not corrected.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
