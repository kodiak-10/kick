#!/bin/zsh
set -euo pipefail

cd /Users/tim/coach.py

if [ -f /Users/tim/coach.py/.env ]; then
  set -a
  source /Users/tim/coach.py/.env
  set +a
fi

exec /opt/anaconda3/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
