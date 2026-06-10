@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\venv" (
  echo [setup] Creating Python venv...
  python -m venv backend\venv
  backend\venv\Scripts\pip install -q -r backend\requirements.txt
)

if not exist "frontend\node_modules" (
  echo [setup] Installing frontend packages (one-time)...
  cd frontend && call npm install && cd ..
)

if not exist "backend\.env" (
  copy backend\.env.example backend\.env >nul
)

if not exist "frontend\build" (
  echo [setup] Building frontend (one-time, ~1 min)...
  cd frontend && call npm run build:quick && cd ..
)

echo [start] Backend  -^> http://127.0.0.1:8000
start "ResumeAIX Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo [start] Frontend -^> http://localhost:3000
start "ResumeAIX Frontend" cmd /k "cd /d %~dp0frontend && npm run start:quick"

echo.
echo ResumeAIX is running (quick mode).
echo   App:  http://localhost:3000
echo   API:  http://127.0.0.1:8000/docs
echo Close the two terminal windows to stop.
echo.
pause
