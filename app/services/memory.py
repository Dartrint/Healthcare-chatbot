from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import numpy as np

from app.config import MEMORY_DIR
from app.services.embedding import EmbeddingService

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None


# =========================
# UTILS
# =========================
def safe_id(user_id: str) -> str:
    normalized = unicodedata.normalize("NFKD", user_id)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_str = re.sub(r"[^a-zA-Z0-9_-]", "_", ascii_str).strip("_")

    if not ascii_str:
        digest = hashlib.md5(user_id.encode("utf-8")).hexdigest()
        return f"user_{digest}"

    return ascii_str


def normalize(vec: np.ndarray) -> np.ndarray:
    """Normalize vector for cosine similarity"""
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


# =========================
# VECTOR MEMORY
# =========================
class VectorMemoryService:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.sid = safe_id(user_id)

        self.index_path: Path = MEMORY_DIR / f"{self.sid}.faiss"
        self.meta_path: Path = MEMORY_DIR / f"{self.sid}.json"

        self.embedding = EmbeddingService()

        self.metadata: List[Dict[str, str]] = []
        self.index = None

        self._load()

    # =========================
    # LOAD / SAVE
    # =========================
    def _load(self) -> None:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        dim = self.embedding.dim  # 🔥 lấy dynamic dimension

        if faiss:
            if self.index_path.exists():
                try:
                    self.index = faiss.read_index(str(self.index_path))
                except Exception:
                    self.index = faiss.IndexFlatIP(dim)
            else:
                self.index = faiss.IndexFlatIP(dim)

        # load metadata
        if self.meta_path.exists():
            try:
                with self.meta_path.open("r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception:
                self.metadata = []

    def _save(self) -> None:
        if faiss and self.index is not None:
            faiss.write_index(self.index, str(self.index_path))

        with self.meta_path.open("w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    # =========================
    # ADD MEMORY
    # =========================
    def add(self, user_input: str, bot_response: str, intent: str = "") -> None:
        entry = {
            "user": user_input,
            "bot": bot_response,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.metadata.append(entry)

        if faiss and self.index is not None:
            vec = self.embedding.embed_text(user_input)

            # 🔥 FIX: normalize vector (cosine similarity)
            vec = normalize(vec).astype("float32").reshape(1, -1)

            try:
                self.index.add(vec)
            except Exception:
                pass

        self._save()

    # backward-compatible alias for older callers
    def save(self, user_input: str, bot_response: str, intent: str = "") -> None:
        self.add(user_input, bot_response, intent)

    # =========================
    # SEARCH MEMORY
    # =========================
    def search(self, query: str, k: int = 3) -> List[Dict[str, str]]:
        if not self.metadata:
            return []

        if faiss and self.index is not None and self.index.ntotal > 0:
            vec = self.embedding.embed_text(query)

            # 🔥 FIX: normalize query
            vec = normalize(vec).astype("float32").reshape(1, -1)

            k = min(k, self.index.ntotal)

            try:
                scores, indices = self.index.search(vec, k)
            except Exception:
                return self.metadata[-k:]

            results = []
            for i in indices[0]:
                if 0 <= i < len(self.metadata):
                    results.append(self.metadata[i])

            return results

        # fallback
        return self.metadata[-k:]

    # =========================
    # UTIL
    # =========================
    def get_all(self) -> List[Dict[str, str]]:
        return self.metadata

    def clear(self) -> None:
        if self.index_path.exists():
            self.index_path.unlink()

        if self.meta_path.exists():
            self.meta_path.unlink()

        self.metadata = []
        self.index = None