"""Print chunk count and token-length stats; fail if any chunk exceeds the model input limit."""

import statistics
import sys
from collections import Counter
from pathlib import Path

from cite_and_seek.corpus import CHUNK_TOKENS, load_corpus, load_tokenizer

MAX_INPUT_TOKENS = 256
CORPUS_ROOT = Path(__file__).resolve().parent.parent / "corpus"


def main() -> None:
    tokenizer = load_tokenizer()
    chunks = load_corpus(CORPUS_ROOT, tokenizer)
    # Re-tokenize each whole chunk with [CLS]/[SEP], as the model will see it.
    lengths = [len(ids) for ids in tokenizer([c.text for c in chunks])["input_ids"]]

    print(f"files:  {len({c.corpus_path for c in chunks})}")
    print(f"chunks: {len(chunks)}")
    per_folder = Counter(c.corpus_path.split("/")[0] for c in chunks)
    for folder, count in sorted(per_folder.items()):
        print(f"  {folder + '/':12} {count}")
    print(
        f"tokens with [CLS]/[SEP]: min {min(lengths)}, median {statistics.median(lengths)}, "
        f"mean {statistics.mean(lengths):.1f}, max {max(lengths)}"
    )
    print(f"packing budget: {CHUNK_TOKENS} + 2 special tokens; model limit: {MAX_INPUT_TOKENS}")

    over = [c for c, n in zip(chunks, lengths) if n > MAX_INPUT_TOKENS]
    for c in over:
        print(f"OVER LIMIT: {c.corpus_path}:{c.start_line}-{c.end_line}")
    if over:
        sys.exit(1)
    print(f"OK: no chunk exceeds {MAX_INPUT_TOKENS} tokens")


if __name__ == "__main__":
    main()
