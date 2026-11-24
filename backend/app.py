"""FastAPI backend: wraps the existing simple_rag pipeline for the web UI."""

from __future__ import annotations

from fastapi import FastAPI

from simple_rag.vectorstore.pg_store import PgVectorStore

app = FastAPI(title="simple-rag API")


def get_chunk_count() -> int:
    """How many chunks are currently indexed (0 if the DB is not ready)."""
    try:
        with PgVectorStore() as store:
            return store.count()
    except Exception:
        return 0


@app.get("/api/health")
def health() -> dict[str, str | int]:
    """Cheap local check - never fails just because the DB is uninitialized."""
    return {"status": "ok", "chunks": get_chunk_count()}
