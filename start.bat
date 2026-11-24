@echo off
cd /d "%~dp0"

start "simple-rag API" cmd /k "uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000"
start "simple-rag UI" cmd /k "npm run dev --prefix frontend"

timeout /t 5 /nobreak >nul
start "" http://localhost:5173
