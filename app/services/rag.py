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
        """Tìm file CSV trong thư mục"""
        # Ưu tiên real data từ WHO/CDC/NIH APIs
        real_data = folder / "real_healthcare_data.csv"
        if real_data.exists():
            return real_data

        # Fallback: who_healthcare_data.csv (static WHO dataset)
        who_data = folder / "who_healthcare_data.csv"
        if who_data.exists():
            return who_data

        # Tìm CSV khác
        for root, _, files in os.walk(folder):
            for filename in files:
                if filename.lower().endswith(".csv"):
                    return Path(root) / filename
        return None

    def _load_documents(self) -> None:
        """Load medical documents from public API data"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self._find_csv_file(self.data_dir)

        # Nếu không có data, hiển thị thông báo
        if not csv_path or not csv_path.exists():
            self.docs = [
                "Healthcare data is not available. Please ensure a CSV dataset exists in the data/ directory."
            ]
            return

        # Load CSV data
        with csv_path.open("r", encoding="utf-8", errors="ignore") as source:
            reader = csv.DictReader(source)
            self.docs = []
            for row in reader:
                # Ưu tiên field 'text', sau đó các field khác
                text_fields = ["text", "description", "symptoms", "disease", "topic"]
                value = next(
                    (row.get(field, "") for field in text_fields if row.get(field)),
                    "",
                )
                if value:
                    self.docs.append(value.strip())

        if self.docs:
            print(f"[OK] Loaded {len(self.docs)} medical records from {csv_path.name}")
            # Log real data sources from CSV
            try:
                sources = set()
                with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for row in csv.DictReader(f):
                        if "source" in row and row["source"]:
                            sources.add(row["source"])
                if sources:
                    print(f"[DATA] Real data sources: {', '.join(sorted(sources))}")
                else:
                    print(f"[DATA] Data source: {csv_path.name}")
            except:
                print(f"[DATA] Data source: {csv_path.name}")
        else:
            self.docs = ["No valid healthcare data found in the dataset."]

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