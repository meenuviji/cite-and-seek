"""Corpus loading and baseline chunking (decision 6, leakage control L1)."""

from dataclasses import dataclass
from pathlib import Path

from transformers import AutoTokenizer, PreTrainedTokenizerBase

from cite_and_seek.path_map import to_source_path

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Excludes [CLS]/[SEP]. Set by the model's 256-token input limit, not tuned.
CHUNK_TOKENS = 200


@dataclass(frozen=True)
class Chunk:
    corpus_path: str  # relative to corpus/
    source_path: str  # upstream repo path, used for citations
    start_line: int  # 1-indexed, inclusive
    end_line: int  # inclusive
    text: str


def load_tokenizer() -> PreTrainedTokenizerBase:
    return AutoTokenizer.from_pretrained(MODEL_NAME)


def iter_corpus_files(root: Path) -> list[tuple[str, str]]:
    """Return (corpus_path, text) for every non-hidden file under root, sorted."""
    root = root.resolve()
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts) or not path.is_file():
            continue
        # L1: only files under corpus/ are indexed, including symlink targets.
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"path resolves outside corpus: {path}")
        files.append((relative.as_posix(), path.read_text(encoding="utf-8")))
    return files


def chunk_text(corpus_path: str, text: str, tokenizer: PreTrainedTokenizerBase) -> list[Chunk]:
    """Pack whole lines into chunks of at most CHUNK_TOKENS tokens, no overlap."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    counts = [len(ids) for ids in tokenizer(lines, add_special_tokens=False)["input_ids"]]
    source_path = to_source_path(corpus_path)

    chunks = []

    def flush(start: int, end: int) -> None:
        body = "".join(lines[start:end])
        if body.strip():
            chunks.append(Chunk(corpus_path, source_path, start + 1, end, body))

    start, total = 0, 0
    for i, count in enumerate(counts):
        if count > CHUNK_TOKENS:
            raise ValueError(f"{corpus_path}:{i + 1} exceeds {CHUNK_TOKENS} tokens")
        if total + count > CHUNK_TOKENS:
            flush(start, i)
            start, total = i, 0
        total += count
    flush(start, len(lines))
    return chunks


def load_corpus(root: Path, tokenizer: PreTrainedTokenizerBase) -> list[Chunk]:
    return [
        chunk
        for corpus_path, text in iter_corpus_files(root)
        for chunk in chunk_text(corpus_path, text, tokenizer)
    ]
