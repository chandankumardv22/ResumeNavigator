#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

PY="$BACKEND/venv/bin/python"
[ -x "$PY" ] || PY="$BACKEND/venv/Scripts/python.exe"

if [ ! -x "$PY" ]; then
  echo "[setup] Creating Python venv..."
  python -m venv "$BACKEND/venv"
  PY="$BACKEND/venv/bin/python"
  [ -x "$PY" ] || PY="$BACKEND/venv/Scripts/python.exe"
fi

echo "[setup] Ensuring backend dependencies..."
"$PY" -m pip install -q -r "$BACKEND/requirements.txt"

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "[setup] Installing frontend packages (one-time)..."
  (cd "$FRONTEND" && npm install)
fi

if [ ! -f "$BACKEND/.env" ]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

echo "[models] Training TF-IDF + Logistic Regression if needed..."
(cd "$BACKEND" && "$PY" train_role_model.py)

echo "[start] Backend  -> http://127.0.0.1:8000"
(cd "$BACKEND" && "$PY" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload) &
BACKEND_PID=$!

echo "[start] Frontend -> http://localhost:3000 (live React source)"
(cd "$FRONTEND" && BROWSER=none npm run start:fast) &
FRONTEND_PID=$!

echo ""
echo "ResumeNavigator Smart Analyzer is running."
echo "  App:  http://localhost:3000"
echo "  API:  http://127.0.0.1:8000/docs"
echo "  Look for: Algorithms nav + Five engines panel under upload."
echo "  Hard-refresh (Ctrl+F5) if you still see PathFinder."
echo "Press Ctrl+C to stop both servers."
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
