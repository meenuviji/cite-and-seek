"""`cite-and-seek eval run`: generate answers for the split with the v0.1 pipeline.

Answers are saved to reports/runs/<run_id>/answers.jsonl, where the judge
(Commit F) and calibration read them; they are never regenerated. results/
gets aggregates and IDs only (L7, L15).
"""

import json
import os
import statistics
import sys
import time

from dotenv import load_dotenv

from cite_and_seek.cli import DEFAULT_K, build_retriever
from cite_and_seek.eval import REPO_ROOT
from cite_and_seek.eval.answer_checks import abstention_violations, check_citations
from cite_and_seek.eval.golden import load_golden
from cite_and_seek.eval.runinfo import (REPORTS_DIR, new_run_id, require_clean_tree,
                                        run_config, sha256_text, write_results)
from cite_and_seek.eval.stats import proportion
from cite_and_seek.generation import (CLOSED_BOOK_SYSTEM_PROMPT, ClosedBookHaikuGenerator,
                                      GenerationError, HaikuGenerator)

# Anthropic list price for claude-haiku-4-5, USD per million tokens, as of 2026-10.
PRICE_PER_MTOK = {"input": 1.00, "output": 5.00}


def require_env_key(name: str) -> None:
    """Fail before any work if an API key is missing; never prints the value."""
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get(name):
        sys.exit(f"{name} is not set (expected in .env at the repository root)")


def run_generation(final: bool, closed_book: bool = False) -> None:
    require_clean_tree()
    require_env_key("ANTHROPIC_API_KEY")
    questions = load_golden(final=final)
    # Closed-book (L13) retrieves nothing; the RAG run uses the v0.1 pipeline.
    retriever = None if closed_book else build_retriever()
    generator = ClosedBookHaikuGenerator() if closed_book else HaikuGenerator()
    run_id = new_run_id("closedbook" if closed_book else "run")
    detail_dir = REPORTS_DIR / run_id
    detail_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with (detail_dir / "answers.jsonl").open("w", encoding="utf-8") as handle:
        for q in questions:
            hits = [] if closed_book else retriever.search(q.question, DEFAULT_K)
            start = time.perf_counter()
            try:
                answer = generator.generate(q.question, hits)
                error = None
            except GenerationError as exc:
                answer, error = None, str(exc)
            latency = time.perf_counter() - start
            retrieved = [(h.chunk.source_path, h.chunk.start_line, h.chunk.end_line) for h in hits]
            row = {
                "id": q.id,
                "answerable": q.answerable,
                "retrieved": retrieved,
                "latency_s": latency,
                "error": error,
            }
            if answer:
                row.update(text=answer.text, abstained=answer.abstained, model=answer.model,
                           input_tokens=answer.input_tokens, output_tokens=answer.output_tokens,
                           request_id=answer.request_id)
            rows.append(row)
            handle.write(json.dumps(row) + "\n")

    extra = ({"closed_book": True, "k": 0,
              "closed_book_system_prompt_sha256": sha256_text(CLOSED_BOOK_SYSTEM_PROMPT)}
             if closed_book else {"closed_book": False, "k": DEFAULT_K})
    payload = {"run_id": run_id, "stage": "closedbook" if closed_book else "run",
               "split": "held_out" if final else "tuning",
               "config": run_config(price_per_mtok_usd=PRICE_PER_MTOK, **extra),
               **summarize(rows)}
    path = write_results(run_id, payload)
    print_summary(payload)
    print(f"wrote {path}; answers in reports/runs/{run_id}/answers.jsonl")


def summarize(rows: list[dict]) -> dict:
    done = [r for r in rows if not r["error"]]
    answerable = [r for r in done if r["answerable"]]
    unanswerable = [r for r in done if not r["answerable"]]

    violation_counts: dict[str, int] = {}
    violating_ids = []
    citations_total = citations_valid = 0
    uncited_ids, invalid_citation_ids = [], []
    for r in done:
        problems = abstention_violations(r["text"])
        for problem in problems:
            violation_counts[problem] = violation_counts.get(problem, 0) + 1
        if problems:
            violating_ids.append(r["id"])
        if not r["abstained"]:
            check = check_citations(r["text"], {tuple(c) for c in r["retrieved"]})
            citations_total += check.total
            citations_valid += check.valid
            if check.total == 0:
                uncited_ids.append(r["id"])
            if check.invalid:
                invalid_citation_ids.append(r["id"])

    abstentions = [r for r in done if r["abstained"]]
    answered = [r for r in done if not r["abstained"]]
    tokens_in = sum(r["input_tokens"] for r in done)
    tokens_out = sum(r["output_tokens"] for r in done)
    latencies = sorted(r["latency_s"] for r in done)
    return {
        "n_questions": len(rows),
        "errors": {"count": len(rows) - len(done),
                   "ids": sorted(r["id"] for r in rows if r["error"])},
        "metrics": {
            "correct_abstention": proportion(sum(r["abstained"] for r in unanswerable), len(unanswerable)),
            "false_abstention": proportion(sum(r["abstained"] for r in answerable), len(answerable)),
            "abstention_format_violation": {
                **proportion(sum(bool(abstention_violations(r["text"])) for r in abstentions),
                             len(abstentions)),
                "by_type": violation_counts,
            },
            "citation_validity": proportion(citations_valid, citations_total),
            "answers_without_citations": proportion(len(uncited_ids), len(answered)),
            "answers_with_invalid_citation": proportion(len(invalid_citation_ids), len(answered)),
        },
        "ids": {
            "false_abstention": sorted(r["id"] for r in answerable if r["abstained"]),
            "missed_abstention": sorted(r["id"] for r in unanswerable if not r["abstained"]),
            "format_violation": sorted(violating_ids),
            "without_citations": sorted(uncited_ids),
            "invalid_citation": sorted(invalid_citation_ids),
        },
        "usage": {
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "cost_usd": round(tokens_in / 1e6 * PRICE_PER_MTOK["input"]
                              + tokens_out / 1e6 * PRICE_PER_MTOK["output"], 6),
        },
        "latency_s": {
            "mean": statistics.mean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p90": latencies[int(0.9 * (len(latencies) - 1))] if latencies else None,
            "scope": "generation call only, per question",
        },
    }


def fmt(metric: dict) -> str:
    rate = "n/a" if metric["rate"] is None else f"{metric['rate']:.3f}"
    return f"{metric['count']}/{metric['n']} = {rate} [{metric['ci95'][0]:.2f}, {metric['ci95'][1]:.2f}]"


def print_summary(payload: dict) -> None:
    m, ids = payload["metrics"], payload["ids"]
    print(f"run {payload['run_id']}: {payload['n_questions']} questions ({payload['split']}), "
          f"{payload['errors']['count']} errors {payload['errors']['ids']}")
    print(f"correct abstention (unanswerable): {fmt(m['correct_abstention'])}  missed: {ids['missed_abstention']}")
    print(f"false abstention (answerable):     {fmt(m['false_abstention'])}  ids: {ids['false_abstention']}")
    print(f"abstention format violations:      {fmt(m['abstention_format_violation'])}  "
          f"by type: {m['abstention_format_violation']['by_type']}")
    print(f"citation validity (citations):     {fmt(m['citation_validity'])}")
    print(f"answers with an invalid citation:  {fmt(m['answers_with_invalid_citation'])}  ids: {ids['invalid_citation']}")
    print(f"answers with no citation:          {fmt(m['answers_without_citations'])}  ids: {ids['without_citations']}")
    u, lat = payload["usage"], payload["latency_s"]
    print(f"tokens: in {u['input_tokens']} / out {u['output_tokens']}; cost ${u['cost_usd']:.4f}")
    print(f"latency (generation): mean {lat['mean']:.2f}s, median {lat['median']:.2f}s, p90 {lat['p90']:.2f}s")
