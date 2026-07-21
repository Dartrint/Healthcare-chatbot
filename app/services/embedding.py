from __future__ import annotations

import hashlib
import numpy as np
from pathlib import Path

from app.config import EMBEDDING_MODEL

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None


class EmbeddingService:
    _cached_model = None
    _cached_model_name = None

    def __init__(self) -> None:
        self.model_name = EMBEDDING_MODEL
        self.model = self.__class__._cached_model
        self.dim = 384

        if SentenceTransformer and (
            self.model is None or self.__class__._cached_model_name != self.model_name
        ):
            try:
                self.model = SentenceTransformer(self.model_name)
                # Use new API if available, fallback to deprecated method
                if hasattr(self.model, 'get_embedding_dimension'):
                    self.dim = int(self.model.get_embedding_dimension())
                else:
                    self.dim = int(self.model.get_sentence_embedding_dimension())
                self.__class__._cached_model = self.model
                self.__class__._cached_model_name = self.model_name
            except Exception:
                self.model = None

    def embed_text(self, text: str) -> np.ndarray:
        if self.model is not None:
            vector = self.model.encode(text, normalize_embeddings=True)
            return np.asarray(vector, dtype=np.float32)

        return self._stable_random_embedding(text)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if self.model is not None:
            return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)

        return np.vstack([self._stable_random_embedding(text) for text in texts])

    def _stable_random_embedding(self, text: str) -> np.ndarray:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
        rng = np.random.default_rng(seed)
        vec = rng.random(384, dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
