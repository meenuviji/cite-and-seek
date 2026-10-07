"""Vector index and retriever interfaces with brute-force numpy implementations (decision 5)."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from cite_and_seek.corpus import Chunk
from cite_and_seek.embedding import Embedder


class VectorIndex(Protocol):
    def add(self, vectors: np.ndarray) -> None:
        """Append (n, dim) vectors; ids continue from the current size."""
        ...

    def search(self, query_vector: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (ids, scores) of the top-k vectors, best first."""
        ...


class NumpyIndex:
    """Exact cosine search over unit vectors: a dot product against every row."""

    def __init__(self, dim: int) -> None:
        self.matrix = np.empty((0, dim), dtype=np.float32)

    def add(self, vectors: np.ndarray) -> None:
        self.matrix = np.vstack([self.matrix, vectors.astype(np.float32, copy=False)])

    def search(self, query_vector: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        scores = self.matrix @ query_vector
        # Stable sort keeps tied scores in id order, so results repeat run to run.
        ids = np.argsort(-scores, kind="stable")[: min(k, len(scores))]
        return ids, scores[ids]


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


class Retriever(Protocol):
    def search(self, query: str, k: int) -> list[Hit]: ...


class DenseRetriever:
    def __init__(self, embedder: Embedder, index: VectorIndex, chunks: list[Chunk]) -> None:
        self.embedder = embedder
        self.index = index
        self.chunks = chunks
        index.add(embedder.embed([chunk.text for chunk in chunks]))

    def search(self, query: str, k: int) -> list[Hit]:
        ids, scores = self.index.search(self.embedder.embed([query])[0], k)
        return [Hit(self.chunks[i], float(s)) for i, s in zip(ids, scores)]
