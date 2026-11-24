"""Central configuration for the RAG project.

WHY THIS FILE EXISTS
--------------------
Every setting the app needs is read once, in one place. Other modules import
`settings` from here instead of calling os.getenv() themselves. That means:
  - one place to look when something is misconfigured
  - no missing values discovered halfway through a pipeline run

HOW TO CHANGE A VALUE
---------------------
Edit `.env` (never hardcode a key or a model name in Python code).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# config.py lives at <root>/src/simple_rag/config.py
# parents[0] = simple_rag, [1] = src, [2] = project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env into os.environ. Values already set in the shell win.
load_dotenv(PROJECT_ROOT / ".env")


def _required(name: str) -> str:
    """Read a required setting, or fail early with a helpful message."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing setting {name!r}. Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    """A typed, read-only snapshot of the project configuration."""

    # freellmapi connection
    llm_base_url: str
    llm_api_key: str
    llm_model: str

    # Embeddings: one family + dimension per vector store
    embedding_model: str
    embedding_dim: int

    # Data locations (derived from the project root, not hardcoded)
    raw_data_dir: Path
    processed_data_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the environment variables in .env."""
        return cls(
            llm_base_url=_required("LLM_BASE_URL"),
            llm_api_key=_required("LLM_API_KEY"),
            llm_model=_required("LLM_MODEL"),
            embedding_model=_required("EMBEDDING_MODEL"),
            embedding_dim=int(_required("EMBEDDING_DIM")),
            raw_data_dir=PROJECT_ROOT / "data" / "raw",
            processed_data_dir=PROJECT_ROOT / "data" / "processed",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the shared settings object (the .env file is read only once)."""
    return Settings.from_env()


if __name__ == "__main__":
    # Quick self-check: `uv run python -m simple_rag.config`
    s = get_settings()
    print(f"endpoint   : {s.llm_base_url}")
    print(f"api key    : {s.llm_api_key[:12]}... (masked)")
    print(f"chat model : {s.llm_model}")
    print(f"embedding  : {s.embedding_model} ({s.embedding_dim} dims)")
    print(f"raw data   : {s.raw_data_dir}")
