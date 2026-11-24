# simple-rag

A small, step-by-step learning project for Retrieval-Augmented Generation (RAG),
built toward a production agentic RAG system.

## Architecture

This project deliberately uses **two different approaches** for embeddings and
generation:

| Stage | Tool | Runs where | Needs API key? |
|-------|------|-----------|----------------|
| Embeddings | `sentence-transformers` with `BAAI/bge-m3` | Locally, on this machine | No |
| Generation | freellmapi → free cloud LLM providers | Local router, cloud inference | Yes (unified freellmapi key) |

- **Embeddings are local.** No embedding API is used. `BAAI/bge-m3` is MIT-licensed,
  1024-dimensional, supports 8192-token inputs and 100+ languages, and is deterministic.
  The weights are downloaded once and cached; after that it works offline.
- **Generation uses freellmapi.** freellmapi is a router running on this laptop. It
  holds the free-tier provider keys and exposes one OpenAI-compatible endpoint at
  `http://127.0.0.1:31415/v1` (desktop app port). Only the `LLM_*` settings apply to it.
- **Why split them:** retrieval quality should not depend on which LLM is answering.
  Swapping the chat model later never forces a vector-store rebuild — but changing
  the embedding model does, which is why it is pinned in `.env`.

## Setup

1. Install Python 3.14+ and [uv](https://docs.astral.sh/uv/).
2. Run `uv sync` to install dependencies.
3. Copy `.env.example` to `.env`. Add your freellmapi URL + key for generation;
   leave the embedding values as-is (they are local).
4. Run `uv run python -m simple_rag.config` to verify settings.

> The embedding model weights (~2.2 GB) are downloaded on first use and then cached.

### Check freellmapi manually

```powershell
# 1. Confirm the desktop app is listening on port 31415
Get-NetTCPConnection -State Listen | Where-Object LocalPort -eq 31415

# 2. See which process owns it
Get-Process FreeLLMAPI | Select-Object Id, Path

# 3. Is the API reachable? 200 = yes, 401 = reachable but needs a key
curl.exe -s -o NUL -w "%{http_code}`n" http://127.0.0.1:31415/v1/docs

# 4. Open the interactive API viewer in your browser
Start-Process "http://127.0.0.1:31415/v1/docs"

# 5. List available models (paste your real unified key)
curl.exe -H "Authorization: Bearer freellmapi-YOUR_KEY" http://127.0.0.1:31415/v1/models
```

## Structure

- `src/simple_rag/ingestion/` — load PDFs and clean extracted text
- `src/simple_rag/chunking/` — split clean text into token-sized chunks
- `src/simple_rag/embeddings/` — local `sentence-transformers` model (no API)
- `src/simple_rag/vectorstore/` — store + search vectors
- `src/simple_rag/generation/` — freellmapi-backed LLM answers from context
- `src/simple_rag/prompts/` — prompt templates
- `src/simple_rag/config.py` — settings from `.env`
- `src/simple_rag/pipeline.py` — ties stages together

## Progress

- [x] config
- [x] ingestion
- [x] text cleaning
- [x] chunking
- [ ] embeddings
- [ ] vectorstore
- [ ] generation
