"""Query stage: convert a user's question into an embedding vector.

This reuses `embed_query()` from the embeddings module, which already applies
the BGE query instruction and returns a normalized unit vector. Keeping that
logic in one place means documents and queries are embedded consistently.
"""

from __future__ import annotations

from dataclasses import dataclass

from simple_rag.config import get_settings
from simple_rag.embeddings.embedder import embed_query
from simple_rag.query.ask import Question


@dataclass(frozen=True)
class QueryEmbedding:
    """A question plus the vector that represents it for retrieval."""

    question: str
    vector: tuple[float, ...]

    @property
    def dim(self) -> int:
        return len(self.vector)


def embed_question(question: Question) -> QueryEmbedding:
    """Turn a validated Question into a vector ready for pgvector search."""
    vector = embed_query(question.text)

    expected_dim = get_settings().embedding_dim
    if len(vector) != expected_dim:
        raise RuntimeError(
            f"Question embedding has {len(vector)} dims, expected {expected_dim}. "
            "Check EMBEDDING_MODEL / EMBEDDING_DIM in .env."
        )

    return QueryEmbedding(question=question.text, vector=tuple(vector))


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.query.embed_question
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    result = embed_question(Question("What is heredity?"))
    print(f"question    : {result.question}")
    print(f"dimensions  : {result.dim}")
    print(f"first 5     : {[round(v, 4) for v in result.vector[:5]]}")
    print(f"norm        : {sum(v * v for v in result.vector):.4f}")
