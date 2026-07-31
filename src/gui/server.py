"""FastAPI 서버 — REST + WebSocket + 정적 파일 서빙."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.gui.bus import event_bus
from src.gui.roster import load_roster
from src.gui.runner import crew_runner

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="AI Interview Office", docs_url=None, redoc_url=None)


@app.on_event("startup")
async def _bind_bus() -> None:
    """uvicorn이 만든 이벤트 루프에 bus를 바인딩 + 리스너 연결."""
    from src.gui.listener import gui_listener
    event_bus.bind_loop(asyncio.get_running_loop())
    gui_listener._broadcast = event_bus.broadcast_threadsafe


# ── REST ──

@app.get("/api/agents")
def get_agents() -> list[dict[str, Any]]:
    return load_roster()


@app.get("/api/crews")
def get_crews() -> list[dict[str, str]]:
    # main.py COMMANDS 재사용 (lazy import)
    from main import COMMANDS
    return [{"name": k, "description": v[0]} for k, v in COMMANDS.items()
            if k not in ("gui", "notion")]


@app.get("/api/status")
def get_status() -> dict[str, Any]:
    s = crew_runner.current
    if s is None:
        return {"busy": False}
    return {
        "busy": crew_runner.is_busy,
        "crew": s.crew,
        "status": s.status.value,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "error": s.error,
    }


@app.post("/api/run/{crew_name}")
def run_crew(crew_name: str) -> dict[str, str]:
    if crew_runner.is_busy:
        return {"error": f"이미 실행 중: {crew_runner.current.crew}"}  # type: ignore[union-attr]
    from main import COMMANDS
    if crew_name not in COMMANDS:
        return {"error": f"알 수 없는 크루: {crew_name}"}
    _, func = COMMANDS[crew_name]
    crew_runner.run(crew_name, func)
    return {"status": "started", "crew": crew_name}


# ── WebSocket ──

@app.websocket("/ws/office")
async def ws_office(ws: WebSocket) -> None:
    await ws.accept()
    q = event_bus.subscribe()
    try:
        while True:
            line = await q.get()
            await ws.send_text(line)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        event_bus.unsubscribe(q)


# ── 프론트 서빙 ──

@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def start_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """GUI 서버 기동."""
    import uvicorn
    import webbrowser

    url = f"http://{host}:{port}"
    print(f"\n  Office: {url}\n")
    webbrowser.open(url)

    uvicorn.run(app, host=host, port=port)
