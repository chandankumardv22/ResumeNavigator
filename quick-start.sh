#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

if [ ! -d "$BACKEND/venv" ]; then
  echo "[setup] Creating Python venv..."
  python -m venv "$BACKEND/venv"
  "$BACKEND/venv/Scripts/pip" install -q -r "$BACKEND/requirements.txt"
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "[setup] Installing frontend packages (one-time)..."
  (cd "$FRONTEND" && npm install)
fi

if [ ! -f "$BACKEND/.env" ]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

if [ ! -d "$FRONTEND/build" ]; then
  echo "[setup] Building frontend (one-time, ~1 min)..."
  (cd "$FRONTEND" && npm run build:quick)
fi

echo "[start] Backend  -> http://127.0.0.1:8000"
(cd "$BACKEND" && source venv/Scripts/activate && python -m uvicorn main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

echo "[start] Frontend -> http://localhost:3000"
(cd "$FRONTEND" && npm run start:quick) &
FRONTEND_PID=$!

echo ""
echo "ResumeAIX is running (quick mode)."
echo "  App:  http://localhost:3000"
echo "  API:  http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to stop both servers."
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
