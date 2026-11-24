# simple-rag

A small, step-by-step learning project for Retrieval-Augmented Generation (RAG).

## Setup
1. Install Python 3.14+ and [uv](https://docs.astral.sh/uv/).
2. Run `uv sync` to install dependencies.
3. Copy `.env.example` to `.env` and add your freellmapi URL + key.
4. Run `uv run python main.py`.

## Structure
- `src/simple_rag/ingestion/` — load documents
- `src/simple_rag/chunking/` — split into chunks
- `src/simple_rag/embeddings/` — text to vectors
- `src/simple_rag/vectorstore/` — store + search vectors
- `src/simple_rag/generation/` — LLM answers from context
- `src/simple_rag/prompts/` — prompt templates
- `src/simple_rag/config.py` — settings from .env
- `src/simple_rag/pipeline.py` — ties stages together

## Progress
- [x] config
- [x] ingestion
- [ ] chunking
- [ ] embeddings
- [ ] vectorstore
- [ ] generation