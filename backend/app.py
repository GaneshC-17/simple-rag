"""FastAPI backend: wraps the existing simple_rag pipeline for the web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from simple_rag.config import get_settings
from simple_rag.generation.generator import generate_answer
from simple_rag.pipeline import index_pdf, retrieve
from simple_rag.prompts.context import build_context
from simple_rag.vectorstore.pg_store import PgVectorStore

app = FastAPI(title="simple-rag API")

RAW_DIR = get_settings().raw_data_dir


class AskRequest(BaseModel):
    question: str
    top_k: int = 3
    max_tokens: int = 2000


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


@app.post("/api/ask")
def ask(request: AskRequest) -> dict:
    """Answer a question and return the chunks the answer is based on."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    results = retrieve(request.question, top_k=request.top_k)
    context = build_context(results, max_tokens=request.max_tokens)

    try:
        answer = generate_answer(request.question, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sources = [
        {
            "content": result.content,
            "source": result.source,
            "chunk_index": result.chunk_index,
            "similarity": result.similarity,
        }
        for result in results
    ]
    return {"answer": answer, "sources": sources}


@app.post("/api/index")
def index(file: UploadFile = File(...)) -> dict:
    """Save an uploaded PDF and index it into the vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    safe_name = Path(file.filename).name
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / safe_name
    target.write_bytes(file.file.read())

    try:
        stats = index_pdf(str(target))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "source": stats.source,
        "pages": stats.pages,
        "chunks": stats.chunks,
        "tokens": stats.tokens,
    }
