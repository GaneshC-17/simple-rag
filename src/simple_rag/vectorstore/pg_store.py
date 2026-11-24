"""Vector store stage: chunks + vectors in PostgreSQL using pgvector.

Uses `embedded-postgres`, which bundles PostgreSQL and the pgvector extension
as a pip package. No external database server, no Docker, no password to set.

The data directory (data/pgdata) is created on first use and persists, so the
vectors survive between runs. It is gitignored.

Use the store as a context manager so the bundled server is started/stopped:
    with PgVectorStore() as store:
        store.add(chunks, vectors, source="notes.pdf")
        results = store.search(query_vector)
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import embedded_postgres
import psycopg

from simple_rag.config import get_settings


@dataclass(frozen=True)
class SearchResult:
    """One retrieved chunk plus how close it was to the query."""

    content: str
    source: str
    chunk_index: int
    similarity: float


def _to_pg_vector(vector: list[float]) -> str:
    """Python list -> pgvector literal, e.g. '[0.1,-0.2,0.3]'."""
    return "[" + ",".join(str(value) for value in vector) + "]"


class PgVectorStore:
    """PostgreSQL + pgvector store for document chunks."""

    def __init__(self, data_dir: Path | None = None) -> None:
        settings = get_settings()
        self.data_dir = data_dir or (settings.processed_data_dir / "pgdata")
        self.expected_dim = settings.embedding_dim
        self._uri: str | None = None
        self._stack: ExitStack | None = None

    def __enter__(self) -> PgVectorStore:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._stack = ExitStack()
        server = self._stack.enter_context(
            embedded_postgres.get_server(str(self.data_dir))
        )
        self._uri = server.get_uri()

        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    embedding vector({self.expected_dim}) NOT NULL
                )
                """
            )
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._stack is not None:
            self._stack.__exit__(*exc_info)

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection]:
        if self._uri is None:
            raise RuntimeError("PgVectorStore must be used inside a 'with' block")
        with psycopg.connect(self._uri) as conn:
            yield conn

    def _check_dim(self, vector: list[float]) -> None:
        if len(vector) != self.expected_dim:
            raise ValueError(
                f"Vector has {len(vector)} dims, expected {self.expected_dim}"
            )

    def add(
        self,
        chunks: list[str],
        vectors: list[list[float]],
        *,
        source: str = "unknown",
    ) -> None:
        """Store chunks and their vectors. Re-adding the same source replaces it."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        for vector in vectors:
            self._check_dim(vector)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE source = %s", (source,))
                for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
                    cur.execute(
                        """
                        INSERT INTO chunks (content, source, chunk_index, embedding)
                        VALUES (%s, %s, %s, %s::vector)
                        """,
                        (chunk, source, index, _to_pg_vector(vector)),
                    )

    def search(self, query_vector: list[float], top_k: int = 3) -> list[SearchResult]:
        """Return the chunks closest to the query vector (cosine similarity)."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        self._check_dim(query_vector)

        literal = _to_pg_vector(query_vector)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content, source, chunk_index,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (literal, literal, top_k),
                )
                rows = cur.fetchall()

        return [
            SearchResult(
                content=row[0], source=row[1], chunk_index=row[2], similarity=float(row[3])
            )
            for row in rows
        ]

    def count(self) -> int:
        """How many chunks are stored (handy for debugging)."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chunks")
                return int(cur.fetchone()[0])
