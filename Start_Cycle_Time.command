#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if lsof -i :8765 >/dev/null 2>&1; then
    if ! curl -fsS "http://127.0.0.1:8765/api/health" 2>/dev/null | grep -q '"service": "cycle-time"'; then
        osascript -e 'display alert "Cycle Time เปิดไม่ได้" message "พอร์ต 8765 ถูกใช้งานโดยโปรแกรมอื่น กรุณาปิดโปรแกรมนั้นแล้วลองใหม่" as critical'
        exit 1
    fi
else
    PY_BIN="$DIR/.venv/bin/python3"
    if [ ! -f "$PY_BIN" ]; then
        PY_BIN="python3"
    fi
    nohup "$PY_BIN" "$DIR/app_server.py" >/dev/null 2>&1 &
    sleep 1.5
fi

open "http://localhost:8765/index.html"
exit 0
