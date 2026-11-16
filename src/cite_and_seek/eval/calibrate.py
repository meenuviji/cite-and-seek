"""`cite-and-seek eval calibrate`: blind owner grading for judge calibration (decision 15).

grade: shows the owner one generated answer at a time and records the owner's
label. The sample comes from the official generation run, not from judge
results, so grading never waits for the judge and never sees its labels. It is
the one command that prints golden content, for the owner in their own
terminal (exception to L7). Labels go to reports/ only.

score: once the judge run is finished, compares the judge's labels with the
owner's on the IDs the owner labeled. Prints and commits aggregates and IDs
only (L7, L15).
"""

import json
import random
import sys
from pathlib import Path

from cite_and_seek.eval.golden import load_golden
from cite_and_seek.eval.judge import LABELS
from cite_and_seek.eval.judge_stage import latest_run_id
from cite_and_seek.eval.runinfo import (REPORTS_DIR, RESULTS_DIR, new_run_id, require_clean_tree,
                                        run_config, write_results)
from cite_and_seek.eval.stats import proportion

SEED = 2026
TARGET = 15
KEYS = {"c": "correct", "p": "partial", "i": "incorrect", "s": "skipped"}
CALIBRATION_DIR = REPORTS_DIR.parent / "calibration"


def sample_order(eligible_ids: list[str], seed: int = SEED) -> list[str]:
    """Fixed ordering over eligible IDs: sorted, then shuffled with the seed."""
    order = sorted(eligible_ids)
    random.Random(seed).shuffle(order)
    return order


def labels_path(source_run: str) -> Path:
    return CALIBRATION_DIR / source_run / "owner_labels.jsonl"


def read_labels(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return {row["id"]: row["owner_label"]
            for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def eligible_rows(source_run: str) -> dict[str, dict]:
    """Answerable questions with a non-abstained, error-free answer in the source run."""
    answers_path = REPORTS_DIR / source_run / "answers.jsonl"
    if not answers_path.is_file():
        sys.exit(f"no answers for {source_run} in reports/runs/")
    rows = {r["id"]: r for r in map(json.loads, answers_path.read_text(encoding="utf-8").splitlines())}
    answerable = {q.id for q in load_golden() if q.answerable}
    return {i: r for i, r in rows.items() if i in answerable and not r["error"] and not r["abstained"]}


def run_grade(source_run: str | None) -> None:
    source_run = source_run or latest_run_id("run")
    rows = eligible_rows(source_run)
    golden = {q.id: q for q in load_golden()}
    path = labels_path(source_run)
    path.parent.mkdir(parents=True, exist_ok=True)
    done = read_labels(path)
    order = sample_order(list(rows))
    print(f"calibration on {source_run}: {len(order)} eligible answers, target {TARGET} labels.")
    print("Keys: c correct, p partial, i incorrect, s skip, q quit (progress is saved).\n")
    with path.open("a", encoding="utf-8") as handle:
        for qid in order:
            labeled = sum(v != "skipped" for v in done.values())
            if labeled >= TARGET:
                break
            if qid in done:
                continue
            q, answer = golden[qid], rows[qid]["text"]
            facts = "\n".join(f"  - {f}" for f in q.expected_facts) or "  - (none listed)"
            print(f"===== [{labeled + 1}/{TARGET}] {qid} =====")
            print(f"QUESTION:\n{q.question}\n\nREFERENCE ANSWER:\n{q.ground_truth_answer}\n")
            print(f"EXPECTED FACTS:\n{facts}\n\nCANDIDATE ANSWER:\n{answer}\n")
            key = ""
            while key not in KEYS and key != "q":
                key = input("label [c/p/i/s/q]: ").strip().lower()
            if key == "q":
                break
            done[qid] = KEYS[key]
            handle.write(json.dumps({"id": qid, "owner_label": KEYS[key]}) + "\n")
            handle.flush()
            print()
    labeled = sum(v != "skipped" for v in done.values())
    print(f"{labeled}/{TARGET} labeled, {len(done) - labeled} skipped; saved to {path}")


def confusion(judge: dict[str, str], owner: dict[str, str]) -> dict:
    """Percent agreement and judge-by-owner counts on IDs both labeled."""
    ids = sorted(i for i, label in owner.items() if label in LABELS and judge.get(i) in LABELS)
    matrix = {j: {o: 0 for o in LABELS} for j in LABELS}
    for i in ids:
        matrix[judge[i]][owner[i]] += 1
    agree = sum(judge[i] == owner[i] for i in ids)
    return {"n": len(ids), "agree": agree, "matrix": matrix,
            "disagreement_ids": [i for i in ids if judge[i] != owner[i]]}


def run_score(judge_run: str) -> None:
    require_clean_tree()
    result_path = RESULTS_DIR / f"{judge_run}.json"
    if not result_path.is_file():
        sys.exit(f"judge run {judge_run} is not finished: no {result_path.name} in results/")
    judge_payload = json.loads(result_path.read_text(encoding="utf-8"))
    source_run = judge_payload["source_run_id"]
    owner = read_labels(labels_path(source_run))
    if not owner:
        sys.exit(f"no owner labels for {source_run}; run `eval calibrate grade` first")
    judge = {i: outcome for outcome, ids in judge_payload["ids_by_outcome"].items() for i in ids}
    owner_labeled = [i for i, v in owner.items() if v in LABELS]
    not_judged = sorted(i for i in owner_labeled if judge.get(i) not in LABELS)
    result = confusion(judge, owner)
    run_id = new_run_id("calibration")
    payload = {
        "run_id": run_id,
        "stage": "calibration",
        "judge_run_id": judge_run,
        "source_run_id": source_run,
        "config": run_config(judge_model=judge_payload["config"]["judge"]["model"],
                             sampling=f"seed {SEED} shuffle of sorted answerable, non-abstained IDs; "
                                      f"target {TARGET} labels"),
        "owner_labeled": len(owner_labeled),
        "owner_skipped": sum(v == "skipped" for v in owner.values()),
        "excluded_not_judged_ids": not_judged,
        "agreement": proportion(result["agree"], result["n"]),
        "confusion_judge_by_owner": result["matrix"],
        "disagreement_ids": result["disagreement_ids"],
    }
    path = write_results(run_id, payload)
    a = payload["agreement"]
    rate = "n/a" if a["rate"] is None else f"{a['rate']:.3f}"
    print(f"calibration of {judge_run} ({judge_payload['config']['judge']['model']}) on {source_run}")
    print(f"agreement: {a['count']}/{a['n']} = {rate} [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}]")
    print("judge / owner".rjust(14) + "  " + "  ".join(f"{o:>9}" for o in LABELS))
    for j in LABELS:
        print(f"{j:>14}  " + "  ".join(f"{result['matrix'][j][o]:>9}" for o in LABELS))
    print(f"disagreement ids: {result['disagreement_ids']}")
    if not_judged:
        print(f"excluded (owner-labeled, no judge label): {not_judged}")
    print(f"wrote {path}")
