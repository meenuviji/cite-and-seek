"""Embedder interface and the MiniLM baseline (decision 4)."""

from typing import Protocol

import numpy as np
from sentence_transformers import SentenceTransformer

from cite_and_seek.corpus import MODEL_NAME


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, dim) float32 array of L2-normalized vectors."""
        ...


class MiniLMEmbedder:
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        # MiniLM is symmetric: queries and chunks are encoded the same way.
        vectors = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vectors.astype(np.float32, copy=False)
