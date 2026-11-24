@echo off
cd /d "%~dp0"

if not exist .env (
  echo Missing .env - copy .env.example to .env and add your freellmapi key, then run start.bat again.
  pause
  exit /b 1
)

if not exist frontend\node_modules (
  echo Installing frontend dependencies (one time)...
  call npm install --prefix frontend
  if errorlevel 1 (
    echo npm install failed - check your Node installation.
    pause
    exit /b 1
  )
)

start "simple-rag API" cmd /k "uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000"
start "simple-rag UI" cmd /k "npm run dev --prefix frontend"

timeout /t 5 /nobreak >nul
start "" http://localhost:5173
