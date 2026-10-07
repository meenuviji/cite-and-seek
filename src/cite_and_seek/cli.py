"""Command-line interface: search (retrieval only) and ask (retrieval plus generation)."""

import argparse
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from cite_and_seek.corpus import load_corpus, load_tokenizer
from cite_and_seek.embedding import MiniLMEmbedder
from cite_and_seek.generation import GenerationError, HaikuGenerator
from cite_and_seek.retrieval import DenseRetriever, Hit, NumpyIndex

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = REPO_ROOT / "corpus"
# Chosen by convention, not tuned.
DEFAULT_K = 5


def build_retriever(corpus_root: Path = CORPUS_ROOT) -> DenseRetriever:
    chunks = load_corpus(corpus_root, load_tokenizer())
    embedder = MiniLMEmbedder()
    return DenseRetriever(embedder, NumpyIndex(embedder.dim), chunks)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("k must be at least 1")
    return number


def citation(hit: Hit) -> str:
    return f"{hit.chunk.source_path}:{hit.chunk.start_line}-{hit.chunk.end_line}"


def search(question: str, k: int) -> None:
    for rank, hit in enumerate(build_retriever().search(question, k), start=1):
        print(f"[{rank}] {hit.score:.4f}  {citation(hit)}")
        for line in hit.chunk.text.rstrip("\n").splitlines():
            print(f"    {line}")
        print()


def ask(question: str, k: int) -> None:
    # The API key is loaded into the environment at runtime only; it is never printed.
    load_dotenv(REPO_ROOT / ".env")
    hits = build_retriever().search(question, k)
    start = time.perf_counter()
    try:
        answer = HaikuGenerator().generate(question, hits)
    except GenerationError as error:
        sys.exit(f"generation stopped early: {error}")
    except anthropic.APIStatusError as error:
        request_id = error.response.headers.get("request-id")
        sys.exit(f"API error: {type(error).__name__} (status {error.status_code}, request {request_id})")
    except anthropic.APIConnectionError as error:
        sys.exit(f"API connection error: {type(error).__name__}")
    except anthropic.AnthropicError as error:
        sys.exit(f"API client error: {type(error).__name__}")
    latency = time.perf_counter() - start

    print(answer.text)
    print("\nRetrieved:")
    for rank, hit in enumerate(hits, start=1):
        print(f"  [{rank}] {hit.score:.4f}  {citation(hit)}")
    print(f"\n{answer.model} | abstained={answer.abstained} | in {answer.input_tokens} "
          f"/ out {answer.output_tokens} tokens | {latency:.2f}s | request {answer.request_id}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="cite-and-seek")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("search", "print the top-k chunks for a question"),
        ("ask", "answer a question from the top-k chunks, with citations"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("question")
        command.add_argument("-k", type=positive_int, default=DEFAULT_K,
                             help=f"number of chunks to retrieve (default {DEFAULT_K})")
    args = parser.parse_args()
    if args.command == "search":
        search(args.question, args.k)
    elif args.command == "ask":
        ask(args.question, args.k)
