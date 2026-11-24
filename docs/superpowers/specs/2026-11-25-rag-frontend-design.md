# RAG Frontend — Design

**Date:** 2026-11-25
**Status:** Proposed (awaiting approval)

## Intent and why

The RAG pipeline works end-to-end from the terminal, but the user wants to use it
"as a common man" — open an app, type a question, get an answer, upload a new PDF,
without ever running a command. The front end must therefore hide the CLI and the
Python machinery behind a familiar, ChatGPT-like chat interface.

## Goals

- A local web app a non-technical person can use daily: ask a question, read an
  answer, expand the sources behind it.
- Let the user upload a PDF and index it from the UI.
- Keep all existing RAG code unchanged; the UI only calls into it.
- Look and feel like a modern chat app (familiar layout, clear states).

## Non-goals

- Authentication, multiple users, cloud deployment, sharing links.
- Streaming tokens, conversation memory, model selection UI, document deletion,
  chat history persistence (all possible later).
- Rewriting any module under `src/simple_rag/`.

## Anti-goals (things that would make this a failure)

- Exposing the freellmapi key or any backend detail to the browser.
- Moving embedding or pgvector work into JavaScript.
- A UI that needs a terminal to be used day-to-day after the first setup.

## Constraints

- Python 3.14 project managed by `uv`; Node 24.22.1 and npm 11.6.2 are installed.
- freellmapi desktop router runs locally at `http://127.0.0.1:31415/v1`.
- Local `BAAI/bge-m3` weights are cached; embedded pgvector data lives in
  `data/pgdata/` (gitignored).
- Everything stays free/open source.

## Approaches considered

1. **React SPA + small FastAPI backend (chosen).** Vite + React + TypeScript +
   Tailwind for the UI; FastAPI wraps `pipeline` functions. Best fit for "proper
   React app with good UI/UX" and keeps all RAG Python code intact. Trades off
   two processes to run locally (solved by one launcher).
2. **Gradio chat UI.** Fastest to build and chat-native, but limited layout
   control and weak for side-by-side source inspection. rejected.
3. **Streamlit page.** Simplest Python-only path, but does not satisfy the
   explicit React requirement and reads as a data app rather than a product.
   Rejected.

## Decided how

- **Frontend:** Vite + React + TypeScript (strict), Tailwind CSS, plain `useState`
  (no Redux/Zustand). Lives in `frontend/`.
- **Backend:** FastAPI in `backend/`, launched with `uv run uvicorn`. It imports
  `simple_rag.pipeline` and calls existing functions; it does not reimplement RAG.
- **API (v1):**
  - `GET /api/health` — server status and number of indexed chunks.
  - `POST /api/index` (multipart PDF) — save under `data/raw/` with a sanitized
    filename, call `index_pdf()`, return `IndexStats` as JSON.
  - `POST /api/ask` (`{question, top_k, max_tokens}`) — call `retrieve()`,
    `build_context()`, and `generate_answer()`; return `{answer, sources}` where
    each source is `{content, source, chunk_index, similarity}`.
- **Vite dev proxy:** `/api` → `http://127.0.0.1:8000` so the browser never deals
  with CORS or ports.
- **Launcher:** `start.bat` (Windows) starts the backend and the Vite dev server,
  then opens `http://localhost:5173` in the default browser. Double-click only.

### UI shape (ChatGPT-like)

```
┌──────────────┬────────────────────────────────────────────┐
│              │                                            │
│  + New chat  │   You: According to the text, what is...   │
│              │                                            │
│              │   Assistant: The rules of heredity...      │
│              │   Sources: [chunk 3 ▾] [chunk 0 ▾]         │
│              │                                            │
│  Upload PDF  │                                            │
│              │   ┌──────────────────────────────────────┐  │
│  ● online    │   │ Ask anything about your documents... │  │
│              │   │                              [ ↑ ]  │  │
│              │   └──────────────────────────────────────┘  │
└──────────────┴────────────────────────────────────────────┘
```

- Dark narrow sidebar, light main chat area, rounded composer at the bottom.
- Assistant messages show an expandable **Sources** row (click a chip to read the
  chunk, with source filename and similarity score).
- Clear states: empty screen with suggested questions, "thinking" indicator,
  inline error banner, upload progress, and online/offline badge.
- Responsive: sidebar collapses on narrow screens.

## Calls made by the builder (not user decisions)

- **Online/offline badge** means the FastAPI backend is reachable. If the
  freellmapi router is down, the ask request returns a clear inline error rather
  than a second status badge. This keeps `/api/health` a cheap local check.
- **`top_k` and `max_tokens` are fixed defaults** sent by the client in v1;
  there is no settings UI. `max_tokens` is the *context-building* budget passed
  to `context_for()` (default 2000), not an LLM completion limit.
- **Empty-state suggested questions are static** (e.g. "What is heredity?"),
  derived from no document content. No extra endpoint is needed.
- **Conversation model (user decision):** a single in-memory thread. "New chat"
  clears the current messages; there is no conversation list and no persistence.
  The sidebar therefore has no "Recent" section in v1.

## What is left to the builder

- Component breakdown and exact styling tokens.
- Request/response TypeScript types matching the API shapes above.
- Error handling details and the launcher script contents.
- Tests: backend endpoint smoke test; frontend build (`npm run build`) check.
