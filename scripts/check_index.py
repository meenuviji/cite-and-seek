"""Plumbing check for embedding and search, using corpus text only (no queries).

Checks vector shape and unit norms, then searches each chunk's own text and
expects that chunk back at rank 1.
"""

import sys
from pathlib import Path

import numpy as np

from cite_and_seek.corpus import load_corpus, load_tokenizer
from cite_and_seek.embedding import MiniLMEmbedder
from cite_and_seek.retrieval import DenseRetriever, NumpyIndex

CORPUS_ROOT = Path(__file__).resolve().parent.parent / "corpus"
NORM_TOLERANCE = 1e-5


def main() -> None:
    chunks = load_corpus(CORPUS_ROOT, load_tokenizer())
    embedder = MiniLMEmbedder()
    index = NumpyIndex(embedder.dim)
    retriever = DenseRetriever(embedder, index, chunks)

    norms = np.linalg.norm(index.matrix, axis=1)
    norms_ok = bool(np.all(np.abs(norms - 1) <= NORM_TOLERANCE))
    print(f"vectors: {index.matrix.shape}, norms {norms.min():.6f}-{norms.max():.6f}")

    failures = 0
    min_score = 1.0
    for chunk in chunks:
        top = retriever.search(chunk.text, k=1)[0]
        min_score = min(min_score, top.score)
        if top.chunk != chunk:
            failures += 1
            print(f"MISS: {chunk.corpus_path}:{chunk.start_line}-{chunk.end_line} "
                  f"-> {top.chunk.corpus_path}:{top.chunk.start_line}-{top.chunk.end_line}")
    print(f"self-retrieval: {len(chunks) - failures}/{len(chunks)} at rank 1, "
          f"min rank-1 score {min_score:.6f}")

    if not norms_ok or failures:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
