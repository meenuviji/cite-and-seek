"""Command-line interface: retrieval only, no generation."""

import argparse
from pathlib import Path

from cite_and_seek.corpus import load_corpus, load_tokenizer
from cite_and_seek.embedding import MiniLMEmbedder
from cite_and_seek.retrieval import DenseRetriever, NumpyIndex

CORPUS_ROOT = Path(__file__).resolve().parents[2] / "corpus"
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


def search(question: str, k: int) -> None:
    for rank, hit in enumerate(build_retriever().search(question, k), start=1):
        chunk = hit.chunk
        print(f"[{rank}] {hit.score:.4f}  {chunk.source_path}:{chunk.start_line}-{chunk.end_line}")
        for line in chunk.text.rstrip("\n").splitlines():
            print(f"    {line}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(prog="cite-and-seek")
    commands = parser.add_subparsers(dest="command", required=True)
    search_parser = commands.add_parser("search", help="print the top-k chunks for a question")
    search_parser.add_argument("question")
    search_parser.add_argument("-k", type=positive_int, default=DEFAULT_K,
                               help=f"number of chunks to return (default {DEFAULT_K})")
    args = parser.parse_args()
    if args.command == "search":
        search(args.question, args.k)
