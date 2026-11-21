#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if ! lsof -i :8000 >/dev/null 2>&1; then
    nohup "$DIR/.venv/bin/python3" "$DIR/app_server.py" >/dev/null 2>&1 &
    sleep 1.5
fi

open "http://localhost:8000/index.html"
exit 0
