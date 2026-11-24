"""Embedding stage: turn text into vectors with a LOCAL model.

No API key, no network, no freellmapi involved. The model named in .env
(BAAI/bge-m3) is loaded once and then reused for every call.

Two entry points:
    embed_texts([...])  -> vectors for storing chunks
    embed_query("...")  -> one vector for searching later
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from simple_rag.config import get_settings

# BGE models expect this instruction on SEARCH QUERIES, not on documents.
# It noticeably improves retrieval quality.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load the model once (cached), using the name from .env."""
    return SentenceTransformer(get_settings().embedding_model)


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed document chunks so they can be stored in a vector store.

    Args:
        texts: Chunk strings to embed.
        batch_size: How many texts the model processes at once.

    Returns:
        One vector (list of floats) per input text.

    Raises:
        ValueError: Empty input or invalid batch_size.
        RuntimeError: The model returns a different dimension than configured.
    """
    if not texts:
        return []
    if any(not isinstance(text, str) for text in texts):
        raise TypeError("every item in texts must be a string")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    vectors = _get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,  # unit vectors -> dot product = cosine similarity
        show_progress_bar=False,
    )

    expected_dim = get_settings().embedding_dim
    for vector in vectors:
        if len(vector) != expected_dim:
            raise RuntimeError(
                f"Model returned {len(vector)} dimensions, expected {expected_dim}. "
                "Check EMBEDDING_MODEL and EMBEDDING_DIM in your .env file."
            )

    return [[float(value) for value in vector] for vector in vectors]


def embed_query(text: str) -> list[float]:
    """Embed a user question for retrieval (adds the BGE query instruction)."""
    if not text or not text.strip():
        raise ValueError("query text must not be empty")

    return embed_texts([QUERY_PREFIX + text.strip()])[0]


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.embeddings.embedder
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    samples = [
        "RAG retrieves relevant documents before generating an answer.",
        "Chunking splits clean text into token-sized pieces.",
    ]
    vectors = embed_texts(samples)

    print(f"embedded texts : {len(vectors)}")
    print(f"dimensions     : {len(vectors[0])}")
    print(f"first 5 values : {[round(v, 4) for v in vectors[0][:5]]}")

    query_vector = embed_query("How does RAG work?")
    print(f"query vector   : {len(query_vector)} dims")

    # Unit vectors -> a dot product is cosine similarity
    dot = sum(a * b for a, b in zip(vectors[0], vectors[1]))
    print(f"cosine between samples: {dot:.4f}")
