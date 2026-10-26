"""LLM judge (decision 14): Gemini Flash, temperature 0, JSON-schema response.

The judge compares a candidate answer with the reference answer and its
expected facts. It measures agreement with the reference, not faithfulness to
retrieved chunks (decision 18). It is uncalibrated in v0.2 (sprint deviation):
every number it produces is labeled as such.
"""

import json
import random
import sys
import time
from dataclasses import dataclass
from typing import Protocol

import httpx
from google import genai
from google.genai import errors, types

JUDGE_MODEL_ID = "gemini-3.6-flash"  # 3.8 and 3.7 were unavailable (503) on 2026-10-26; decision 19
JUDGE_TEMPERATURE = 0.0
LABELS = ("correct", "partial", "incorrect")
MAX_ATTEMPTS = 6
BASE_DELAY_S = 2.0
# Without a timeout a stalled request waits forever; a timed-out request is retried.
REQUEST_TIMEOUT_MS = 60_000

JUDGE_SYSTEM_PROMPT = """\
You grade a candidate answer to a question about a software codebase against a reference answer and a list of expected facts, written by an expert who verified them by reading the code. Judge only whether the candidate's factual content agrees with the reference.

Check the candidate against each expected fact in turn: is the fact stated in the candidate, missing from it, or contradicted by it?

Labels:
- correct: states every expected fact and nothing that contradicts the reference.
- partial: states some expected facts and misses others, with no contradictions.
- incorrect: contradicts the reference or an expected fact, or states none of the expected facts.

Extra details not in the reference do not lower the grade unless they contradict it. Ignore style, length, and citations.
Respond with JSON only: {"label": "correct" | "partial" | "incorrect", "reason": "<one sentence>"}"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": list(LABELS)},
        "reason": {"type": "string"},
    },
    "required": ["label", "reason"],
}


@dataclass(frozen=True)
class Verdict:
    label: str
    reason: str


class JudgeError(RuntimeError):
    """The judge returned something other than a valid verdict."""


class Judge(Protocol):
    def grade(self, question: str, reference: str, facts: tuple[str, ...],
              candidate: str) -> Verdict: ...


def build_judge_message(question: str, reference: str, facts: tuple[str, ...],
                        candidate: str) -> str:
    fact_lines = "\n".join(f"- {fact}" for fact in facts) or "- (none listed)"
    return (f"<question>\n{question}\n</question>\n\n"
            f"<reference_answer>\n{reference}\n</reference_answer>\n\n"
            f"<expected_facts>\n{fact_lines}\n</expected_facts>\n\n"
            f"<candidate_answer>\n{candidate}\n</candidate_answer>")


def is_retryable(error: errors.APIError) -> bool:
    return error.code == 429 or (error.code is not None and error.code >= 500)


class GeminiJudge:
    def __init__(self, client: genai.Client | None = None, model: str = JUDGE_MODEL_ID) -> None:
        self.client = client or genai.Client(
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
        self.model = model
        self.config = types.GenerateContentConfig(
            temperature=JUDGE_TEMPERATURE,
            system_instruction=JUDGE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        )

    def grade(self, question: str, reference: str, facts: tuple[str, ...],
              candidate: str) -> Verdict:
        contents = build_judge_message(question, reference, facts, candidate)
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=contents, config=self.config)
                return parse_verdict(response.text)
            except (errors.APIError, httpx.TimeoutException) as error:
                retryable = isinstance(error, httpx.TimeoutException) or is_retryable(error)
                if not retryable or attempt == MAX_ATTEMPTS - 1:
                    raise
                # Exponential backoff with jitter, for free-tier rate limits (decision 14).
                delay = BASE_DELAY_S * 2 ** attempt + random.uniform(0, 1)
                code = getattr(error, "code", "timeout")
                print(f"    judge: {code}, retry {attempt + 1}/{MAX_ATTEMPTS - 1} in {delay:.0f}s",
                      file=sys.stderr, flush=True)
                time.sleep(delay)
        raise JudgeError("unreachable")


def parse_verdict(text: str | None) -> Verdict:
    try:
        data = json.loads(text or "")
    except json.JSONDecodeError as error:
        raise JudgeError("judge response is not JSON") from error
    if data.get("label") not in LABELS or not isinstance(data.get("reason"), str):
        raise JudgeError("judge response has no valid label and reason")
    return Verdict(data["label"], data["reason"])
