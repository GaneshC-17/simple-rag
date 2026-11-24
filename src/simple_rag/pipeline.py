"""End-to-end RAG plumbing (currently: index a PDF, then retrieve chunks).

This module ties together the stages we have built so far:

    load_pdf -> clean_document -> chunk_text -> embed_texts -> PgVectorStore
    embed_query -> PgVectorStore.search

Generation (the freellmapi LLM call) will be added here as the final step.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from simple_rag.chunking.splitter import chunk_text, count_tokens
from simple_rag.embeddings.embedder import embed_texts
from simple_rag.ingestion.cleaner import clean_document
from simple_rag.ingestion.loader import load_pdf
from simple_rag.query.ask import Question, iter_questions
from simple_rag.query.embed_question import embed_question
from simple_rag.vectorstore.pg_store import PgVectorStore, SearchResult


@dataclass(frozen=True)
class IndexStats:
    """What happened when a PDF was indexed."""

    source: str
    pages: int
    chunks: int
    tokens: int


def index_pdf(
    path: str,
    *,
    chunk_size: int = 300,
    overlap: int = 60,
) -> IndexStats:
    """Read a PDF, clean it, chunk it, embed it, and store it in pgvector."""
    document = clean_document(load_pdf(path))
    chunks = chunk_text(document.text, chunk_size=chunk_size, overlap=overlap)
    vectors = embed_texts(chunks)

    with PgVectorStore() as store:
        store.add(chunks, vectors, source=document.source)

    return IndexStats(
        source=document.source,
        pages=document.page_count,
        chunks=len(chunks),
        tokens=count_tokens(document.text),
    )


def retrieve(query: str, *, top_k: int = 3) -> list[SearchResult]:
    """Embed a question and return the most similar stored chunks."""
    query_embedding = embed_question(Question(query))
    with PgVectorStore() as store:
        return store.search(list(query_embedding.vector), top_k=top_k)


def chat(top_k: int = 3) -> None:
    """Interactive question loop - shows retrieved chunks for each question."""
    print("RAG query mode. Type 'quit', 'exit', or 'q' to stop.")
    for question in iter_questions():
        results = retrieve(question.text, top_k=top_k)
        if not results:
            print("(no chunks found - index a PDF first)")
            continue
        for number, result in enumerate(results, start=1):
            print(
                f"[{number}] similarity={result.similarity:.4f} "
                f"source={result.source} chunk={result.chunk_index}"
            )
            print(result.content)
            print("-" * 60)


def main() -> None:
    """CLI: `uv run python -m simple_rag.pipeline {index,ask,chat}`."""
    parser = argparse.ArgumentParser(description="Simple RAG pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="index a PDF into pgvector")
    index_parser.add_argument("pdf", help="path to the PDF file")

    ask_parser = subparsers.add_parser("ask", help="retrieve chunks for a question")
    ask_parser.add_argument("question", help="the question to search for")
    ask_parser.add_argument("--top-k", type=int, default=3, help="how many chunks")

    chat_parser = subparsers.add_parser("chat", help="ask questions interactively")
    chat_parser.add_argument("--top-k", type=int, default=3, help="how many chunks")

    args = parser.parse_args()

    if args.command == "index":
        stats = index_pdf(args.pdf)
        print(
            f"indexed {stats.source}: {stats.pages} pages, "
            f"{stats.tokens} tokens, {stats.chunks} chunks"
        )
    elif args.command == "ask":
        results = retrieve(args.question, top_k=args.top_k)
        for number, result in enumerate(results, start=1):
            print(
                f"[{number}] similarity={result.similarity:.4f} "
                f"source={result.source} chunk={result.chunk_index}"
            )
            print(result.content)
            print("-" * 60)
    elif args.command == "chat":
        chat(top_k=args.top_k)


if __name__ == "__main__":
    main()
