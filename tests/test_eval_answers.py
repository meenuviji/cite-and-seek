"""Abstention-format and citation checks, and run summaries, on synthetic answers."""

from cite_and_seek.eval.answer_checks import abstention_violations, check_citations
from cite_and_seek.eval.run_stage import summarize


def test_clean_abstention():
    assert abstention_violations("ABSTAIN: The chunks do not show the retry policy.") == []


def test_abstention_violations_by_type():
    text = ("ABSTAIN: The chunks do not show it. The function [app/x.py:1-9] only\n"
            "receives the value.")
    assert abstention_violations(text) == ["multi_line", "has_citation", "multi_sentence"]


def test_embedded_marker_in_answer():
    assert abstention_violations("Partly answered.\nABSTAIN: rest is missing.") == ["embedded_marker"]
    assert abstention_violations("A normal answer [app/x.py:1-9].") == []


RETRIEVED = {("app/x.py", 1, 9), ("app/y.py", 10, 20)}


def test_citations_must_match_a_retrieved_chunk_exactly():
    check = check_citations("A [app/x.py:1-9]. B [app/y.py:10-19]. C [app/z.py:1-2].", RETRIEVED)
    assert (check.total, check.valid) == (3, 1)
    assert check.invalid == ("app/y.py:10-19", "app/z.py:1-2")


def test_no_citations():
    assert check_citations("No citations here.", RETRIEVED).total == 0


def row(qid, answerable, text, tokens=(100, 10)):
    return {"id": qid, "answerable": answerable, "retrieved": [list(c) for c in RETRIEVED],
            "latency_s": 1.0, "error": None, "text": text, "abstained": text.startswith("ABSTAIN:"),
            "input_tokens": tokens[0], "output_tokens": tokens[1]}


def test_summarize_counts():
    rows = [
        row("a1", True, "Answer [app/x.py:1-9]."),
        row("a2", True, "ABSTAIN: Missing."),  # false abstention
        row("a3", True, "Answer with no citation."),
        row("u1", False, "ABSTAIN: Missing. Also this."),  # correct, but two sentences
        row("u2", False, "Confident answer [app/q.py:1-2]."),  # missed abstention, invalid citation
        {"id": "e1", "answerable": True, "retrieved": [], "latency_s": 0.5,
         "error": "stop_reason=max_tokens"},
    ]
    s = summarize(rows)
    m, ids = s["metrics"], s["ids"]
    assert s["errors"] == {"count": 1, "ids": ["e1"]}
    assert (m["correct_abstention"]["count"], m["correct_abstention"]["n"]) == (1, 2)
    assert (m["false_abstention"]["count"], m["false_abstention"]["n"]) == (1, 3)
    assert ids["missed_abstention"] == ["u2"] and ids["false_abstention"] == ["a2"]
    assert m["abstention_format_violation"]["by_type"] == {"multi_sentence": 1}
    assert (m["citation_validity"]["count"], m["citation_validity"]["n"]) == (1, 2)
    assert ids["without_citations"] == ["a3"] and ids["invalid_citation"] == ["u2"]
    assert s["usage"]["input_tokens"] == 500
    assert s["usage"]["cost_usd"] == round(500 / 1e6 * 1.0 + 50 / 1e6 * 5.0, 6)
