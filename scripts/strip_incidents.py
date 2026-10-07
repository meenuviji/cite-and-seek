"""Generate stripped incident copies for the corpus (decision 2, leakage control L2).

Reads evaluation/synthetic_incidents/SCN-*.md and writes copies to
corpus/incidents/ that keep only the scenario, hypothetical_situation, and
label keys. Kept lines are copied byte for byte. All checks run before any
file is written.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = (REPO_ROOT / "evaluation" / "synthetic_incidents").resolve()
DST_DIR = (REPO_ROOT / "corpus" / "incidents").resolve()

EXPECTED_KEYS = {
    "scenario",
    "real_file",
    "real_function",
    "real_observable_behavior",
    "hypothetical_situation",
    "expected_evidence",
    "expected_answer",
    "label",
}
KEEP_KEYS = {"scenario", "hypothetical_situation", "label"}
STRIP_KEYS = EXPECTED_KEYS - KEEP_KEYS

KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")

# Connecting words in multi-word real_function values; not location terms.
STOP_WORDS = {"a", "an", "and", "the", "in", "of", "on", "to", "for", "with", "from", "or", "via", "by"}


def parse_blocks(text: str, name: str) -> list[tuple[str, list[str]]]:
    """Split a file into (key, lines) blocks, one per top-level key."""
    blocks: list[tuple[str, list[str]]] = []
    for line in text.splitlines(keepends=True):
        match = KEY_LINE.match(line)
        if match:
            blocks.append((match.group(1), [line]))
        elif line[:1] in (" ", "\t") or not line.strip():
            if not blocks:
                sys.exit(f"{name}: continuation line before first key")
            blocks[-1][1].append(line)
        else:
            sys.exit(f"{name}: unparseable top-level line: {line[:40]!r}")
    return blocks


def inline_value(block_lines: list[str]) -> str:
    """Value of a one-line key, with surrounding quotes removed."""
    return KEY_LINE.match(block_lines[0]).group(2).strip().strip("\"'")


def leak_terms(blocks: dict[str, list[str]]) -> set[tuple[str, str]]:
    """(source field, term) pairs that point at the root-cause location."""
    terms = {
        ("real_function", name)
        for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", inline_value(blocks["real_function"]))
        if name.lower() not in STOP_WORDS
    }
    for path in re.findall(r"[\w./-]+\.\w+", inline_value(blocks["real_file"])):
        terms.add(("real_file basename", Path(path).name))
    return terms


def assert_inside(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root):
        sys.exit(f"refusing path outside {root}: {path}")


def main() -> None:
    sources = sorted(SRC_DIR.glob("SCN-*.md"))
    if not sources:
        sys.exit(f"no SCN-*.md files in {SRC_DIR}")

    outputs: list[tuple[Path, str]] = []
    warnings: list[str] = []
    for src in sources:
        assert_inside(src, SRC_DIR)
        name = src.name
        blocks_list = parse_blocks(src.read_text(encoding="utf-8"), name)
        keys = [key for key, _ in blocks_list]
        if len(keys) != len(set(keys)) or set(keys) != EXPECTED_KEYS:
            sys.exit(f"{name}: unexpected key set {sorted(keys)}")
        blocks = dict(blocks_list)

        stripped = "".join("".join(lines) for key, lines in blocks_list if key in KEEP_KEYS)

        out_keys = {key for key, _ in parse_blocks(stripped, name)}
        if out_keys != KEEP_KEYS:
            sys.exit(f"{name}: stripped copy has keys {sorted(out_keys)}")
        for key in STRIP_KEYS:
            if key in stripped:
                sys.exit(f"{name}: stripped key name {key!r} still present")

        # Warn only: the term itself is ground truth, so name just its source field.
        for field, term in sorted(leak_terms(blocks)):
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", stripped):
                warnings.append(f"{name}: kept text mentions a {field} value")

        dst = DST_DIR / name
        assert_inside(dst, DST_DIR)
        outputs.append((dst, stripped))

    DST_DIR.mkdir(parents=True, exist_ok=True)
    for dst, stripped in outputs:
        dst.write_text(stripped, encoding="utf-8")
        print(f"wrote {dst.relative_to(REPO_ROOT)} ({len(KEEP_KEYS)} keys)")

    for warning in warnings:
        print(f"WARNING: {warning}")
    print(f"{len(outputs)} files written, {len(warnings)} warnings")


if __name__ == "__main__":
    main()
