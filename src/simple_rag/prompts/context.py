"""Build the context block that will be given to the LLM.

Retrieved chunks arrive as a list of SearchResult objects. The LLM needs one
string that clearly labels where each piece came from, and that fits inside a
reasonable token budget so we don't overflow the model's context window.
"""

from __future__ import annotations

from dataclasses import dataclass

from simple_rag.chunking.splitter import count_tokens
from simple_rag.vectorstore.pg_store import SearchResult


@dataclass(frozen=True)
class Context:
    """The assembled context block plus stats, useful for debugging."""

    text: str
    chunk_count: int
    token_count: int


def build_context(
    results: list[SearchResult],
    *,
    max_tokens: int = 2000,
) -> Context:
    """Join the most relevant chunks into one labeled string.

    Chunks are added in the order returned by the vector search (best match
    first). As soon as the next chunk would exceed the budget, we stop rather
    than truncate it mid-sentence.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")

    blocks: list[str] = []
    used_tokens = 0

    for result in results:
        block = (
            f"[Source: {result.source}, chunk {result.chunk_index}]\n"
            f"{result.content}"
        )
        block_tokens = count_tokens(block)
        if used_tokens + block_tokens > max_tokens:
            break
        blocks.append(block)
        used_tokens += block_tokens

    return Context(
        text="\n\n---\n\n".join(blocks),
        chunk_count=len(blocks),
        token_count=used_tokens,
    )


if __name__ == "__main__":
    # Quick test: uv run python -m simple_rag.prompts.context
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from simple_rag.pipeline import retrieve

    results = retrieve("What is heredity?", top_k=3)
    context = build_context(results, max_tokens=2000)
    print(f"chunks used : {context.chunk_count}")
    print(f"tokens used : {context.token_count}")
    print("-" * 60)
    print(context.text[:1500])
