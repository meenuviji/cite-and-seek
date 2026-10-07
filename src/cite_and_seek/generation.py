"""Generator interface and the Haiku baseline (decision 9).

Zero-shot: the prompt has no examples (L9 allows them only from the dev set,
and adding them is a separate experiment).
"""

from dataclasses import dataclass
from typing import Protocol

import anthropic

from cite_and_seek.retrieval import Hit

MODEL_ID = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.0
# A ceiling, not a tuned value: hitting it raises instead of returning a truncated answer.
MAX_TOKENS = 4096
ABSTAIN_PREFIX = "ABSTAIN:"

SYSTEM_PROMPT = """\
You answer questions about the source code and documentation of an ecommerce API. The user message contains context chunks retrieved from the codebase, each in a <chunk> tag with a source file path and a line range, followed by a question.

Rules:
1. Use only information stated in the chunks. Do not use outside knowledge about this codebase, the libraries it uses, or how similar systems usually work. If answering would require guessing or filling a gap the chunks leave open, treat the answer as not contained in the chunks.
2. Cite every factual claim with the chunk that supports it, in the form [path:start-end], copying the source and lines attributes exactly. Cite only chunks you used.
3. If the chunks do not contain enough information to answer the question, reply with exactly one line and nothing else:
ABSTAIN: <one sentence stating what information is missing>
Do not combine an abstention with a partial answer.
4. Otherwise, answer directly and concisely."""


@dataclass(frozen=True)
class Answer:
    text: str
    abstained: bool
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    request_id: str | None


class GenerationError(RuntimeError):
    """Raised when the model stops for a reason other than finishing its answer."""


class Generator(Protocol):
    def generate(self, question: str, hits: list[Hit]) -> Answer: ...


def build_user_message(question: str, hits: list[Hit]) -> str:
    """Chunks in retrieval-rank order, then the question."""
    chunks = "\n".join(
        f'<chunk source="{hit.chunk.source_path}" '
        f'lines="{hit.chunk.start_line}-{hit.chunk.end_line}">\n'
        f"{hit.chunk.text.rstrip()}\n</chunk>"
        for hit in hits
    )
    return f"<context>\n{chunks}\n</context>\n\n<question>\n{question}\n</question>"


class HaikuGenerator:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.client = client or anthropic.Anthropic()

    def generate(self, question: str, hits: list[Hit]) -> Answer:
        response = self.client.messages.create(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            # anthropic 1.x dropped temperature from the signature; Haiku 4.5 still
            # honours it in the request body, and decision 9 requires it.
            extra_body={"temperature": TEMPERATURE},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(question, hits)}],
        )
        if response.stop_reason != "end_turn":
            raise GenerationError(
                f"stop_reason={response.stop_reason} (request {response._request_id})"
            )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return Answer(
            text=text,
            abstained=text.startswith(ABSTAIN_PREFIX),
            model=response.model,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_id=response._request_id,
        )
