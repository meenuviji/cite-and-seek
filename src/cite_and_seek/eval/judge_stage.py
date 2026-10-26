"""`cite-and-seek eval judge`: grade a saved run's answers with the LLM judge (decisions 14, 18).

Reads reports/runs/<source_run>/answers.jsonl; never regenerates answers.
Only answerable questions are graded. Abstentions and generation errors are
counted as outcomes, not judged. Every judge-based number is uncalibrated in
v0.2 (sprint deviation). Judge reasons go to reports/ only (L7, L15).
"""

import json
import sys
from pathlib import Path

from cite_and_seek.eval.golden import load_golden
from cite_and_seek.eval.judge import (JUDGE_MODEL_ID, JUDGE_SYSTEM_PROMPT, JUDGE_TEMPERATURE,
                                      LABELS, GeminiJudge, JudgeError)
from cite_and_seek.eval.run_stage import require_env_key
from cite_and_seek.eval.runinfo import (REPORTS_DIR, RESULTS_DIR, new_run_id, require_clean_tree,
                                        run_config, sha256_text, write_results)
from cite_and_seek.eval.stats import mean_with_ci, proportion

CALIBRATION = "uncalibrated"
OUTCOMES = (*LABELS, "abstained", "generation_error", "judge_error")


def latest_run_id(stage: str) -> str:
    runs = sorted(RESULTS_DIR.glob(f"*-{stage}-*.json"))
    if not runs:
        sys.exit(f"no results/*-{stage}-*.json to judge")
    return json.loads(runs[-1].read_text(encoding="utf-8"))["run_id"]


def run_judge(source_run: str | None, closed_book: bool, final: bool) -> None:
    require_clean_tree()
    require_env_key("GEMINI_API_KEY")
    source_run = source_run or latest_run_id("closedbook" if closed_book else "run")
    answers_path = REPORTS_DIR / source_run / "answers.jsonl"
    if not answers_path.is_file():
        sys.exit(f"no answers for {source_run} in reports/runs/")
    rows = [json.loads(line) for line in answers_path.read_text(encoding="utf-8").splitlines()]
    golden = {q.id: q for q in load_golden(final=final)}
    if {r["id"] for r in rows} != golden.keys():
        sys.exit(f"{source_run} does not cover exactly the selected split")

    n_answerable = sum(q.answerable for q in golden.values())
    judge = GeminiJudge()
    run_id = new_run_id("judge")
    detail_dir = REPORTS_DIR / run_id
    detail_dir.mkdir(parents=True, exist_ok=True)
    outcomes: dict[str, str] = {}
    with (detail_dir / "judgments.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            q = golden[row["id"]]
            if not q.answerable:
                continue
            reason = None
            if row["error"]:
                outcome = "generation_error"
            elif row["abstained"]:
                outcome = "abstained"
            else:
                try:
                    verdict = judge.grade(q.question, q.ground_truth_answer, q.expected_facts,
                                          row["text"])
                    outcome, reason = verdict.label, verdict.reason
                except JudgeError as error:
                    outcome, reason = "judge_error", str(error)
            outcomes[q.id] = outcome
            handle.write(json.dumps({"id": q.id, "outcome": outcome, "reason": reason}) + "\n")
            handle.flush()
            # Progress: ID and label only (L7).
            print(f"  [{len(outcomes)}/{n_answerable}] {q.id}: {outcome}", flush=True)

    n = len(outcomes)
    judged = [o for o in outcomes.values() if o in LABELS]
    payload = {
        "run_id": run_id,
        "stage": "judge",
        "source_run_id": source_run,
        "source_closed_book": closed_book,
        "split": "held_out" if final else "tuning",
        "calibration": CALIBRATION,
        "config": run_config(judge={"model": JUDGE_MODEL_ID, "temperature": JUDGE_TEMPERATURE,
                                    "response": "json_schema",
                                    "system_prompt_sha256": sha256_text(JUDGE_SYSTEM_PROMPT),
                                    "inputs": "question, ground_truth_answer, expected_facts, candidate"}),
        "n_answerable": n,
        "metrics": {
            # End to end: every answerable question counts; abstentions and errors are not correct.
            "correct_over_answerable": proportion(sum(o == "correct" for o in outcomes.values()), n),
            "correct_or_partial_over_answerable": proportion(
                sum(o in ("correct", "partial") for o in outcomes.values()), n),
            # Among answers the judge actually graded.
            "label_share_of_judged": {label: proportion(judged.count(label), len(judged))
                                      for label in LABELS},
        },
        "outcome_counts": {o: sum(v == o for v in outcomes.values()) for o in OUTCOMES},
        "ids_by_outcome": {o: sorted(i for i, v in outcomes.items() if v == o) for o in OUTCOMES},
    }
    path = write_results(run_id, payload)
    print_summary(payload)
    print(f"wrote {path}; judge reasons in reports/runs/{run_id}/judgments.jsonl")


def fmt(metric: dict) -> str:
    rate = "n/a" if metric["rate"] is None else f"{metric['rate']:.3f}"
    return f"{metric['count']}/{metric['n']} = {rate} [{metric['ci95'][0]:.2f}, {metric['ci95'][1]:.2f}]"


def print_summary(payload: dict) -> None:
    m = payload["metrics"]
    print(f"run {payload['run_id']} ({payload['calibration']} judge {JUDGE_MODEL_ID}) "
          f"on {payload['source_run_id']}: {payload['n_answerable']} answerable questions")
    print(f"correct (of all answerable):            {fmt(m['correct_over_answerable'])}")
    print(f"correct or partial (of all answerable): {fmt(m['correct_or_partial_over_answerable'])}")
    for label in LABELS:
        print(f"  {label:9} share of judged:           {fmt(m['label_share_of_judged'][label])}")
    print(f"outcomes: {payload['outcome_counts']}")
    for outcome in ("incorrect", "judge_error", "generation_error"):
        if payload["ids_by_outcome"][outcome]:
            print(f"  {outcome} ids: {payload['ids_by_outcome'][outcome]}")


def rag_gain(rag_judge: dict, closed_judge: dict) -> dict:
    """Paired comparison on the same answerable questions (L13)."""
    def correct_ids(payload: dict) -> set[str]:
        return set(payload["ids_by_outcome"]["correct"])

    ids = sorted({i for ids in rag_judge["ids_by_outcome"].values() for i in ids})
    rag, closed = correct_ids(rag_judge), correct_ids(closed_judge)
    differences = [float(i in rag) - float(i in closed) for i in ids]
    return {
        "n": len(ids),
        "rag_correct": len(rag),
        "closed_book_correct": len(closed),
        "difference": mean_with_ci(differences),
        "only_rag_correct": len(rag - closed),
        "only_closed_book_correct": len(closed - rag),
        "calibration": CALIBRATION,
    }


def load_results(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
