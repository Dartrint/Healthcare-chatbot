from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory_store"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

PLANS_FILE = MEMORY_DIR / "plans.json"
RAG_INDEX_FILE = MEMORY_DIR / "rag.index"
RAG_META_FILE = MEMORY_DIR / "rag_meta.json"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant").strip()
LOCAL_LLM_PATH = os.getenv("LOCAL_LLM_PATH", "").strip()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
RAG_SOURCE_DIR = Path(os.getenv("RAG_SOURCE_DIR", BASE_DIR / "data"))

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "400"))
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.25"))
