#!/usr/bin/env bash
set -e

cleanup() {
  echo "Shutting down..."
  kill $backend_pid $frontend_pid 2>/dev/null
  wait
}
trap cleanup EXIT INT TERM

cd "$(dirname "$0")/.."

echo "Starting backend..."
cd backend
.venv/bin/uvicorn binocular.main:app --host 0.0.0.0 --port 8000 --reload &
backend_pid=$!
cd ..

echo "Starting frontend..."
cd frontend
npm run dev &
frontend_pid=$!
cd ..

wait
