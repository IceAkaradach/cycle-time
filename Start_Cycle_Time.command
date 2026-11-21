#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if ! lsof -i :8000 >/dev/null 2>&1; then
    PY_BIN="$DIR/.venv/bin/python3"
    if [ ! -f "$PY_BIN" ]; then
        PY_BIN="python3"
    fi
    nohup "$PY_BIN" "$DIR/app_server.py" >/dev/null 2>&1 &
    sleep 1.5
fi

open "http://localhost:8000/index.html"
exit 0
