@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
  echo [setup] Creating Python venv...
  python -m venv backend\venv
)

echo [setup] Ensuring backend dependencies...
backend\venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
  echo [error] Could not install backend requirements. Check Python/pip.
  pause
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo [setup] Installing frontend packages (one-time)...
  cd frontend && call npm install && cd ..
)

if not exist "backend\.env" (
  copy backend\.env.example backend\.env >nul
)

echo [models] Ensuring TF-IDF + Logistic Regression model is trained...
cd backend && call venv\Scripts\python.exe train_role_model.py && cd ..

echo [start] Backend  -^> http://127.0.0.1:8000
start "ResumeNavigator Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [start] Frontend -^> http://localhost:3000  (live React source — not stale build)
start "ResumeNavigator Frontend" cmd /k "cd /d %~dp0frontend && set BROWSER=none&& npm run start:fast"

echo.
echo ResumeNavigator Smart Analyzer is running.
echo   App:  http://localhost:3000
echo   API:  http://127.0.0.1:8000/docs
echo   Look for: Algorithms nav + "Five engines" panel under upload.
echo   Hard-refresh the browser (Ctrl+F5) if you still see PathFinder.
echo Close the two terminal windows to stop.
echo.
pause
