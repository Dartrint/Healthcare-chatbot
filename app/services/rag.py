from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import List

import numpy as np

from app.config import DATA_DIR, RAG_INDEX_FILE, RAG_META_FILE
from app.services.embedding import EmbeddingService

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

try:
    import kagglehub
except ImportError:  # pragma: no cover
    kagglehub = None


class RAGService:
    def __init__(self) -> None:
        self.data_dir = DATA_DIR
        self.index_path = RAG_INDEX_FILE
        self.meta_path = RAG_META_FILE
        self.embedding = EmbeddingService()
        self.docs: List[str] = []
        self.index = None
        self._load_documents()
        self._ensure_index()

    def _find_csv_file(self, folder: Path) -> Path | None:
        for root, _, files in os.walk(folder):
            for filename in files:
                if filename.lower().endswith(".csv"):
                    return Path(root) / filename
        return None

    def _load_documents(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self._find_csv_file(self.data_dir)

        if not csv_path and kagglehub:
            try:
                self.data_dir = Path(kagglehub.dataset_download("prasad22/healthcare-dataset"))
                csv_path = self._find_csv_file(self.data_dir)
            except Exception:
                csv_path = None

        if not csv_path:
            self.docs = ["No healthcare dataset is available. Please add a CSV dataset to the data folder."]
            return

        with csv_path.open("r", encoding="utf-8", errors="ignore") as source:
            reader = csv.DictReader(source)
            self.docs = []
            for row in reader:
                value = next(
                    (row.get(field, "") for field in ["text", "description", "symptoms", "disease"] if row.get(field)),
                    "",
                )
                if value:
                    self.docs.append(value.strip())

        self.docs = self.docs[:5000]

    def _ensure_index(self) -> None:
        if self.index is not None:
            return

        vectors = self.embedding.embed_texts(self.docs)
        vectors = np.atleast_2d(vectors)

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if faiss:
            dim = vectors.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(vectors)
        else:
            self.index = vectors

    def retrieve(self, query: str, k: int = 5) -> List[str]:
        if not self.docs:
            return []

        vector = self.embedding.embed_text(query).reshape(1, -1)
        if faiss and self.index is not None:
            k = min(k, len(self.docs))
            _, indices = self.index.search(vector, k)
            return [self.docs[i] for i in indices[0] if 0 <= i < len(self.docs)]

        embeddings = self.index @ vector.T
        scores = embeddings.flatten()
        order = np.argsort(scores)[::-1][:k]
        return [self.docs[i] for i in order]
