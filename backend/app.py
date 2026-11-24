"""FastAPI backend: wraps the existing simple_rag pipeline for the web UI."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from simple_rag.config import get_settings
from simple_rag.generation.generator import generate_answer
from simple_rag.pipeline import index_pdf, retrieve
from simple_rag.prompts.context import build_context
from simple_rag.vectorstore.pg_store import PgVectorStore

app = FastAPI(title="simple-rag API")

RAW_DIR = get_settings().raw_data_dir
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=20)
    max_tokens: int = Field(default=2000, ge=1, le=8000)


class HealthResponse(BaseModel):
    status: str
    chunks: int


class SourceOut(BaseModel):
    content: str
    source: str
    chunk_index: int
    similarity: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


class IndexResponse(BaseModel):
    source: str
    pages: int
    chunks: int
    tokens: int


def get_chunk_count() -> int:
    """How many chunks are currently indexed (0 if the DB is not ready)."""
    try:
        with PgVectorStore() as store:
            return store.count()
    except Exception:
        return 0


@app.get("/api/health")
def health() -> HealthResponse:
    """Cheap local check - never fails just because the DB is uninitialized."""
    return HealthResponse(status="ok", chunks=get_chunk_count())


@app.post("/api/ask")
def ask(request: AskRequest) -> AskResponse:
    """Answer a question and return the chunks the answer is based on."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    try:
        results = retrieve(request.question, top_k=request.top_k)
        context = build_context(results, max_tokens=request.max_tokens)
        answer = generate_answer(request.question, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Pipeline failed: {type(exc).__name__}"
        ) from exc

    return AskResponse(
        answer=answer,
        sources=[
            SourceOut(
                content=result.content,
                source=result.source,
                chunk_index=result.chunk_index,
                similarity=result.similarity,
            )
            for result in results
        ],
    )


@app.post("/api/index")
def index(file: UploadFile = File(...)) -> IndexResponse:
    """Save an uploaded PDF and index it into the vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File is too large (max 20 MB)")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File does not look like a PDF")

    # Basename stops path traversal; reserved characters are removed for Windows.
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", Path(file.filename).name)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / safe_name

    try:
        target.write_bytes(data)
        stats = index_pdf(str(target))
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail=f"Indexing failed: {type(exc).__name__}"
        ) from exc

    return IndexResponse(
        source=stats.source,
        pages=stats.pages,
        chunks=stats.chunks,
        tokens=stats.tokens,
    )
