"""Deterministic checks on generated answers: abstention format and citation validity.

Both check contracts the generation prompt already states (rules 2 and 3);
neither needs golden data.
"""

import re
from dataclasses import dataclass

from cite_and_seek.generation import ABSTAIN_PREFIX

CITATION = re.compile(r"\[([^\[\]\s:]+):(\d+)-(\d+)\]")
SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def abstention_violations(text: str) -> list[str]:
    """Ways an abstention breaks rule 3 ("exactly one line ... one sentence").

    A non-abstention that contains the marker anywhere is also flagged, since
    rule 3 forbids combining an abstention with a partial answer.
    """
    if not text.startswith(ABSTAIN_PREFIX):
        return ["embedded_marker"] if ABSTAIN_PREFIX in text else []
    problems = []
    if len([line for line in text.splitlines() if line.strip()]) > 1:
        problems.append("multi_line")
    if CITATION.search(text):
        problems.append("has_citation")
    if len(SENTENCE_END.findall(text[len(ABSTAIN_PREFIX):])) > 1:
        problems.append("multi_sentence")
    return problems


@dataclass(frozen=True)
class CitationCheck:
    total: int
    valid: int  # exactly matches a retrieved chunk's source_path and line range
    invalid: tuple[str, ...]


def check_citations(text: str, retrieved: set[tuple[str, int, int]]) -> CitationCheck:
    cited = [(path, int(start), int(end)) for path, start, end in CITATION.findall(text)]
    invalid = tuple(f"{p}:{s}-{e}" for p, s, e in cited if (p, s, e) not in retrieved)
    return CitationCheck(total=len(cited), valid=len(cited) - len(invalid), invalid=invalid)
