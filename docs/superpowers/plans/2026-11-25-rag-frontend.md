# RAG Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, ChatGPT-style React web app that lets a non-technical user upload PDFs and ask questions against the existing RAG pipeline.

**Architecture:** A small FastAPI backend wraps the already-working `simple_rag.pipeline` functions and exposes three JSON endpoints. A Vite + React + TypeScript frontend calls those endpoints through a dev proxy and renders a single-thread chat UI. No module under `src/simple_rag/` is modified.

**Tech Stack:** Python 3.14 / uv / FastAPI / uvicorn / pytest; Node 24 / npm 11 / Vite / React / TypeScript (strict) / Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-11-25-rag-frontend-design.md`

## Global Constraints

- Do not modify any file under `src/simple_rag/` — the backend only imports it.
- Python 3.14, packages installed with `uv`; Node 24.22.1, npm 11.6.2.
- All dependencies free/open source.
- Fixed v1 values: `top_k=3`, `max_tokens=2000` (context budget, not completion limit). No settings UI.
- Single in-memory chat thread; "New chat" clears messages. No history list, no persistence, no auth.
- The browser never sees the freellmapi key or backend internals.
- Backend on `127.0.0.1:8000`, frontend dev server on `localhost:5173`, `/api` proxied by Vite.

## Review Focus

- Non-PDF upload → expect HTTP 400 with a readable message, not a server crash (tested in Task 3).
- Empty question → expect HTTP 400 before any model call (tested in Task 2).
- freellmapi unreachable / key rejected → expect HTTP 502 with the error detail, and the UI shows an inline error banner (tested in Task 2, rendered in Task 5).
- No documents indexed → expect a grounded "I don't know" answer with an empty `sources` list, not a crash (tested in Task 2).
- Filename with spaces or path traversal (`../../x.pdf`) → sanitized to a basename under `data/raw/`, never written outside it (tested in Task 3).

---

### Task 1: Backend skeleton and health endpoint

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/app.py`
- Create: `tests/test_backend.py`
- Modify: `pyproject.toml`, `uv.lock` (via uv commands)

**Interfaces:**
- Consumes: `simple_rag.vectorstore.pg_store.PgVectorStore` (context manager, `.count()`).
- Produces: `backend.app.app` (FastAPI instance), `backend.app.get_chunk_count() -> int` (monkeypatch seam), `GET /api/health` returning `{"status": "ok", "chunks": <int>}`.

- [ ] **Step 1: Add dependencies**

Run: `uv add fastapi uvicorn` then `uv add --dev pytest`
Expected: both resolve on Python 3.14; `pyproject.toml` and `uv.lock` updated.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_backend.py
from fastapi.testclient import TestClient
from backend.app import app

def test_health_reports_status_and_chunk_count(monkeypatch):
    monkeypatch.setattr("backend.app.get_chunk_count", lambda: 7)
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "chunks": 7}
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/test_backend.py::test_health_reports_status_and_chunk_count -v`
Expected: FAIL (module `backend.app` not found).

- [ ] **Step 4: Implement `backend/app.py`**

Exactly: `app = FastAPI()`; `def get_chunk_count() -> int` opens `PgVectorStore()` in a `with` block and returns `.count()`; `GET /api/health` returns `{"status": "ok", "chunks": get_chunk_count()}`. Wrap the DB call in `try/except Exception` and return `{"status": "ok", "chunks": 0}` on failure — health must never make the badge go red just because the DB has not been initialized yet.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_backend.py::test_health_reports_status_and_chunk_count -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend pyproject.toml uv.lock tests/test_backend.py
git commit -m "feat(backend): add FastAPI app skeleton and health endpoint"
```

---

### Task 2: Ask endpoint

**Files:**
- Modify: `backend/app.py`
- Modify: `tests/test_backend.py`

**Interfaces:**
- Consumes: `simple_rag.pipeline.retrieve(query, *, top_k=3) -> list[SearchResult]`, `simple_rag.prompts.context.build_context(results, *, max_tokens=2000) -> Context`, `simple_rag.generation.generator.generate_answer(question, context) -> str`.
- Produces: `POST /api/ask` with JSON body `{question: str, top_k: int = 3, max_tokens: int = 2000}` and response `{answer: str, sources: [{content, source, chunk_index, similarity}]}`.

- [ ] **Step 1: Write the failing tests**

```python
def test_ask_returns_answer_and_sources(monkeypatch):
    from simple_rag.vectorstore.pg_store import SearchResult
    from simple_rag.prompts.context import Context

    result = SearchResult("The rules of heredity...", "notes.pdf", 3, 0.56)
    monkeypatch.setattr("backend.app.retrieve", lambda q, top_k: [result])
    monkeypatch.setattr("backend.app.build_context", lambda r, max_tokens: Context("The rules of heredity...", 1, 10))
    monkeypatch.setattr("backend.app.generate_answer", lambda q, c: "The rules of heredity determine inheritance.")

    response = TestClient(app).post("/api/ask", json={"question": "What is heredity?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The rules of heredity determine inheritance."
    assert body["sources"][0] == {
        "content": "The rules of heredity...", "source": "notes.pdf",
        "chunk_index": 3, "similarity": 0.56,
    }

def test_ask_rejects_empty_question():
    assert TestClient(app).post("/api/ask", json={"question": "   "}).status_code == 400

def test_ask_returns_502_when_llm_fails(monkeypatch):
    def boom(q, c): raise RuntimeError("Cannot reach freellmapi")
    monkeypatch.setattr("backend.app.retrieve", lambda q, top_k: [])
    monkeypatch.setattr("backend.app.build_context", lambda r, max_tokens: Context("", 0, 0))
    monkeypatch.setattr("backend.app.generate_answer", boom)
    response = TestClient(app).post("/api/ask", json={"question": "anything"})
    assert response.status_code == 502
    assert "freellmapi" in response.json()["detail"]

def test_ask_with_no_documents_returns_grounded_answer(monkeypatch):
    monkeypatch.setattr("backend.app.retrieve", lambda q, top_k: [])
    monkeypatch.setattr("backend.app.build_context", lambda r, max_tokens: Context("", 0, 0))
    monkeypatch.setattr("backend.app.generate_answer", lambda q, c: "I don't know based on the provided documents.")
    body = TestClient(app).post("/api/ask", json={"question": "anything"}).json()
    assert body["sources"] == []
    assert "I don't know" in body["answer"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_backend.py -v`
Expected: the four new tests FAIL (endpoint missing).

- [ ] **Step 3: Implement `POST /api/ask` in `backend/app.py`**

Use a Pydantic model `AskRequest(question: str, top_k: int = 3, max_tokens: int = 2000)`. Reject blank `question` with `HTTPException(400)`. Call the three consumed functions in order, map each `SearchResult` to the source dict with exact keys above, and catch `RuntimeError` from `generate_answer` → `HTTPException(502, detail=str(exc))`. Import the three functions at module level so the monkeypatch seams resolve.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_backend.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py tests/test_backend.py
git commit -m "feat(backend): add grounded ask endpoint with sources"
```

---

### Task 3: PDF upload / index endpoint

**Files:**
- Modify: `backend/app.py`
- Modify: `tests/test_backend.py`

**Interfaces:**
- Consumes: `simple_rag.pipeline.index_pdf(path: str, *, chunk_size=300, overlap=60) -> IndexStats(source, pages, chunks, tokens)`, `simple_rag.config.get_settings().raw_data_dir`.
- Produces: `POST /api/index` (multipart field `file`) returning `{source, pages, chunks, tokens}`.

- [ ] **Step 1: Write the failing tests**

```python
def test_index_accepts_pdf_and_saves_sanitized_name(monkeypatch, tmp_path):
    from simple_rag.pipeline import IndexStats
    saved = {}
    monkeypatch.setattr("backend.app.RAW_DIR", tmp_path)
    monkeypatch.setattr("backend.app.index_pdf", lambda path: (saved.update(path=path), IndexStats("my doc.pdf", 2, 3, 100))[1])

    client = TestClient(app)
    response = client.post("/api/index", files={"file": ("../../my doc.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert response.status_code == 200
    assert response.json() == {"source": "my doc.pdf", "pages": 2, "chunks": 3, "tokens": 100}
    assert saved["path"].endswith("my doc.pdf")
    assert (tmp_path / "my doc.pdf").exists()

def test_index_rejects_non_pdf():
    response = TestClient(app).post("/api/index", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_backend.py -v`
Expected: the two new tests FAIL.

- [ ] **Step 3: Implement `POST /api/index` in `backend/app.py`**

Exactly: module-level `RAW_DIR = get_settings().raw_data_dir` (monkeypatch seam). Take `file: UploadFile = File(...)`; reject if `not file.filename.lower().endswith(".pdf")` → `HTTPException(400, "Only PDF files are supported")`. Sanitize with `Path(file.filename).name`, write bytes to `RAW_DIR / safe_name` (create dir if needed), call `index_pdf(str(target))`, return the `IndexStats` dict. Catch `Exception` from indexing → `HTTPException(500, detail=str(exc))` so the UI gets a readable error.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_backend.py -v`
Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py tests/test_backend.py
git commit -m "feat(backend): add PDF upload and indexing endpoint"
```

---

### Task 4: Frontend scaffold, types, and API client

**Files:**
- Create: `frontend/` (Vite scaffold), `frontend/src/types.ts`, `frontend/src/api.ts`
- Modify: `frontend/vite.config.ts`, `frontend/src/index.css`

**Interfaces:**
- Consumes: the three API contracts from Tasks 1–3.
- Produces: TypeScript types `Source`, `AskResponse`, `IndexResponse`, `HealthResponse`; functions `askQuestion(question: string): Promise<AskResponse>`, `indexPdf(file: File): Promise<IndexResponse>`, `getHealth(): Promise<HealthResponse>`. Each throws `Error` with the backend `detail` message on non-2xx responses.

- [ ] **Step 1: Scaffold and install**

Run:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install && npm install -D tailwindcss @tailwindcss/vite
```
Expected: `frontend/` created with a TypeScript React app.

- [ ] **Step 2: Configure Tailwind and the dev proxy**

Edit `frontend/vite.config.ts` to import `@tailwindcss/vite`, add the plugin, and add `server.proxy = { "/api": "http://127.0.0.1:8000" }`. Replace `frontend/src/index.css` with a single `@import "tailwindcss";` line. Verify with `cd frontend && npm run build` — expect a successful build.

- [ ] **Step 3: Write `frontend/src/types.ts`**

Define exactly: `Source` with `content: string; source: string; chunk_index: number; similarity: number`; `AskResponse` with `answer: string; sources: Source[]`; `IndexResponse` with `source: string; pages: number; chunks: number; tokens: number`; `HealthResponse` with `status: string; chunks: number`.

- [ ] **Step 4: Write `frontend/src/api.ts`**

Implement the three functions using `fetch` against relative `/api/...` URLs. `askQuestion` posts JSON `{question, top_k: 3, max_tokens: 2000}`. `indexPdf` posts `FormData` with field `file`. On a non-OK response, parse JSON and `throw new Error(body.detail ?? "Request failed")`.

- [ ] **Step 5: Verify and commit**

Run: `cd frontend && npm run build` — expect PASS.
```bash
git add frontend
git commit -m "feat(frontend): scaffold React app with typed API client"
```

---

### Task 5: Chat UI (single thread)

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`, `frontend/src/components/MessageList.tsx`, `frontend/src/components/Composer.tsx`, `frontend/src/components/SourceChip.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/index.css`

**Interfaces:**
- Consumes: `askQuestion`, `indexPdf`, `getHealth` and all four types from Task 4.
- Produces: a `ChatMessage` view model `{role: "user" | "assistant"; answer?: string; sources?: Source[]}` held in `App` state; "New chat" clears it.

- [ ] **Step 1: Build the components**

- `Sidebar`: dark fixed-width panel; shows "New chat" button, "Upload PDF" file input button, and an online/offline badge from `getHealth()` polled once on mount.
- `MessageList`: empty state with static suggestions ("What is heredity?", "What determines inheritance?"); otherwise renders user bubbles right-aligned and assistant answers left-aligned; shows a "thinking" indicator while awaiting.
- `SourceChip`: collapsed chip labeled `chunk {chunk_index}`; expanding reveals `source`, `similarity`, and `content`.
- `Composer`: textarea plus send button; Enter sends, Shift+Enter newlines; disabled while loading or empty.

Use Tailwind utility classes only; no component library.

- [ ] **Step 2: Wire `App.tsx`**

State: `messages: ChatMessage[]`, `pending: boolean`, `error: string | null`, `uploading: boolean`. On send: append user message, set pending, call `askQuestion`, append assistant message with answer + sources; on error set `error` and render an inline banner. On upload: call `indexPdf`, show a short success line with chunk count. "New chat" sets `messages` to `[]` and clears `error`.

- [ ] **Step 3: Verify build and commit**

Run: `cd frontend && npm run build` — expect PASS.
```bash
git add frontend/src
git commit -m "feat(frontend): add ChatGPT-style chat interface with sources"
```

---

### Task 6: One-click launcher and documentation

**Files:**
- Create: `start.bat`
- Modify: `README.md`

**Interfaces:**
- Consumes: `backend/app.py` (uvicorn target `backend.app:app`) and `frontend/` npm scripts.

- [ ] **Step 1: Write `start.bat`**

It must: `cd` to the script directory, start `uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000` in one window, start `npm run dev --prefix frontend` in a second window, wait a few seconds, then `start "" http://localhost:5173`. Use `start` so two windows remain open.

- [ ] **Step 2: Update `README.md`**

Add a "Web app" section with: double-click `start.bat`, wait for the browser at `localhost:5173`, use Upload PDF then ask a question. Keep the CLI commands as an alternative. Mention the backend/frontend ports.

- [ ] **Step 3: Verify and commit**

Run: `Get-Content start.bat` and confirm the three commands and URL are present. Manual smoke: double-click `start.bat`, confirm both server windows open and the page loads.
```bash
git add start.bat README.md
git commit -m "docs: add one-click launcher and web app instructions"
```
