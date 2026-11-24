"""Chunking stage: split clean text into token-sized pieces.

Uses tiktoken (MIT) - the tokenizer behind OpenAI's SDKs.

IMPORTANT: freellmapi routes requests to many different providers (Google,
Groq, Mistral...), and each has its own tokenizer. So this token count is an
APPROXIMATION for the model that will eventually embed the chunk. It is still
far more accurate than counting characters, because embedding APIs enforce
TOKEN limits.

Deliberately NOT included yet (the "better version"):
  - sentence / paragraph aware splitting
  - semantic chunking
"""

from __future__ import annotations

import tiktoken

DEFAULT_ENCODING = "cl100k_base"


def count_tokens(text: str, encoding_name: str = DEFAULT_ENCODING) -> int:
    """Count how many tokens a piece of text contains (useful for debugging)."""
    return len(tiktoken.get_encoding(encoding_name).encode(text))


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    encoding_name: str = DEFAULT_ENCODING,
) -> list[str]:
    """Split text into chunks of at most `chunk_size` tokens.

    Args:
        text: Clean text to split.
        chunk_size: Maximum number of TOKENS per chunk.
        overlap: Number of TOKENS repeated at the start of the next chunk.
        encoding_name: tiktoken encoding to use (default: "cl100k_base").

    Returns:
        A list of chunk strings. Empty text returns an empty list.

    Raises:
        ValueError: If chunk_size <= 0, or overlap is negative / too large.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    if not text.strip():
        return []

    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)

    if not tokens:
        return []

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(tokens):
        piece = tokens[start : start + chunk_size]
        chunks.append(encoding.decode(piece))

        if start + chunk_size >= len(tokens):
            break
        start += step

    return chunks


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.chunking.splitter
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sample = "RAG systems retrieve relevant documents before generating an answer. " * 12
    chunks = chunk_text(sample, chunk_size=40, overlap=10)

    print(f"input tokens    : {count_tokens(sample)}")
    print(f"number of chunks: {len(chunks)}")
    for number, chunk in enumerate(chunks, start=1):
        print(f"[{number}] ({count_tokens(chunk)} tokens) {chunk!r}")
