"""Judge parsing, message building, retry policy, RAG gain, closed-book prompt: synthetic only."""

from types import SimpleNamespace

import pytest

from cite_and_seek.eval.judge import (JudgeError, build_judge_message, is_retryable,
                                      parse_verdict)
from cite_and_seek.eval.judge_stage import rag_gain
from cite_and_seek.generation import CLOSED_BOOK_SYSTEM_PROMPT, ClosedBookHaikuGenerator


def test_parse_valid_verdict():
    verdict = parse_verdict('{"label": "partial", "reason": "Misses one fact."}')
    assert (verdict.label, verdict.reason) == ("partial", "Misses one fact.")


@pytest.mark.parametrize("text", ["not json", '{"label": "maybe", "reason": "x"}', '{"label": "correct"}', None])
def test_parse_rejects_invalid(text):
    with pytest.raises(JudgeError):
        parse_verdict(text)


def test_message_lists_each_fact():
    message = build_judge_message("Q?", "Ref.", ("fact one", "fact two"), "Cand.")
    assert "- fact one\n- fact two" in message
    assert message.index("<reference_answer>") < message.index("<expected_facts>") < message.index("<candidate_answer>")


def test_retry_on_rate_limit_and_server_errors_only():
    assert is_retryable(SimpleNamespace(code=429))
    assert is_retryable(SimpleNamespace(code=503))
    assert not is_retryable(SimpleNamespace(code=400))


def test_rag_gain_is_paired():
    rag = {"ids_by_outcome": {"correct": ["a", "b"], "partial": ["c"], "incorrect": [], "abstained": ["d"],
                              "generation_error": [], "judge_error": []}}
    closed = {"ids_by_outcome": {"correct": ["b", "c"], "partial": [], "incorrect": ["a"], "abstained": ["d"],
                                 "generation_error": [], "judge_error": []}}
    gain = rag_gain(rag, closed)
    assert (gain["n"], gain["rag_correct"], gain["closed_book_correct"]) == (4, 2, 2)
    assert (gain["only_rag_correct"], gain["only_closed_book_correct"]) == (1, 1)
    assert gain["difference"]["mean"] == 0.0


def test_closed_book_sends_question_only():
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        return SimpleNamespace(stop_reason="end_turn", model="m", _request_id="r",
                               content=[SimpleNamespace(type="text", text="ABSTAIN: Unknown.")],
                               usage=SimpleNamespace(input_tokens=1, output_tokens=1))

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    answer = ClosedBookHaikuGenerator(client).generate("What is X?", hits=["ignored"])
    assert sent["system"] == CLOSED_BOOK_SYSTEM_PROMPT
    assert sent["messages"][0]["content"] == "<question>\nWhat is X?\n</question>"
    assert sent["extra_body"] == {"temperature": 0.0}
    assert answer.abstained


def test_judge_identity_pins_model_and_prompt():
    from cite_and_seek.eval.judge import JUDGE_MODEL_ID
    from cite_and_seek.eval.judge_stage import judge_identity

    identity = judge_identity("run-x")
    assert identity["source_run_id"] == "run-x"
    assert identity["model"] == JUDGE_MODEL_ID
    assert len(identity["system_prompt_sha256"]) == 64
