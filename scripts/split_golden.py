"""Generate the fixed tuning / held-out split of golden question IDs (decision 17, L10).

Run once by the owner. Refuses to overwrite an existing split. Prints counts
only, never question content; the split file holds IDs and counts only.

Stratification, fixed before any counts were seen:
- Unanswerable questions are always one stratum.
- Answerable questions are split by category only if every answerable
  category cell has at least MIN_CELL questions (a missing category is its
  own value); otherwise they are one stratum.
- Each stratum holds out round(HOLDOUT_FRACTION * n), rounding half to even.
"""

import hashlib
import json
import platform
import random
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = REPO_ROOT / "evaluation" / "questions" / "golden_set.json"
SPLIT_PATH = REPO_ROOT / "evaluation" / "splits" / "golden_split.json"

SEED = 2026
HOLDOUT_FRACTION = Fraction(1, 5)
MIN_CELL = 5
MISSING_CATEGORY = "<missing>"


def fail(message: str) -> NoReturn:
    # Messages name fields and IDs only, never values from the golden set.
    sys.exit(f"split_golden: {message}")


def load_questions() -> tuple[list[dict], str]:
    raw = GOLDEN_PATH.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, list):
        fail("golden_set.json top level is not a list")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            fail(f"entry {index} is not an object")
        if not isinstance(item.get("id"), str):
            fail(f"entry {index} has no string 'id'")
        if not isinstance(item.get("answerable"), bool):
            fail(f"entry {item['id']} has no boolean 'answerable'")
    ids = [item["id"] for item in data]
    duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
    if duplicates:
        fail(f"duplicate ids: {duplicates}")
    return data, hashlib.sha256(raw).hexdigest()


def category_of(item: dict) -> str:
    value = item.get("category")
    return value if isinstance(value, str) and value else MISSING_CATEGORY


def build_strata(questions: list[dict]) -> tuple[dict[str, list[str]], str, Counter]:
    unanswerable = [q["id"] for q in questions if not q["answerable"]]
    answerable = [q for q in questions if q["answerable"]]
    cells = Counter(category_of(q) for q in answerable)

    strata = {"unanswerable": unanswerable}
    if cells and all(n >= MIN_CELL for n in cells.values()):
        mode = "answerable_by_category"
        for category in sorted(cells):
            strata[f"answerable:{category}"] = [
                q["id"] for q in answerable if category_of(q) == category
            ]
    else:
        mode = "answerable_single_stratum"
        strata["answerable"] = [q["id"] for q in answerable]
    return strata, mode, cells


def main() -> None:
    if SPLIT_PATH.exists():
        fail(f"refusing to overwrite existing {SPLIT_PATH.relative_to(REPO_ROOT)}")

    questions, golden_sha256 = load_questions()
    strata, mode, cells = build_strata(questions)

    rng = random.Random(SEED)
    tuning, held_out, counts = [], [], {}
    # Sorted stratum order and sorted IDs make the shuffle independent of file order.
    for name in sorted(strata):
        ids = sorted(strata[name])
        rng.shuffle(ids)
        n_held = round(HOLDOUT_FRACTION * len(ids))  # Fraction rounds half to even
        held_out.extend(ids[:n_held])
        tuning.extend(ids[n_held:])
        counts[name] = {"n": len(ids), "held_out": n_held, "tuning": len(ids) - n_held}

    # The committed file keeps category names out: strata are counted, not named.
    split = {
        "seed": SEED,
        "holdout_fraction": str(HOLDOUT_FRACTION),
        "min_cell": MIN_CELL,
        "stratification": mode,
        "golden_sha256": golden_sha256,
        "python": platform.python_version(),
        "totals": {"n": len(questions), "tuning": len(tuning), "held_out": len(held_out)},
        "tuning": sorted(tuning),
        "held_out": sorted(held_out),
    }

    SPLIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SPLIT_PATH.open("x", encoding="utf-8") as handle:  # "x" fails if the file exists
        json.dump(split, handle, indent=2)
        handle.write("\n")

    print(f"stratification: {mode}")
    print(f"answerable category cells: {len(cells)} (min size {min(cells.values()) if cells else 0}, "
          f"threshold {MIN_CELL})")
    for name, count in counts.items():
        print(f"  {name:40} n={count['n']:3}  tuning={count['tuning']:3}  held_out={count['held_out']:3}")
    total = split["totals"]
    print(f"total: n={total['n']}  tuning={total['tuning']}  held_out={total['held_out']} "
          f"({total['held_out'] / total['n']:.1%} held out)")
    print(f"wrote {SPLIT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
