"""FastAPI 서버 — REST + WebSocket + 정적 파일 서빙."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.gui import review
from src.gui.bus import event_bus
from src.gui.events import OfficeEvent, OfficePayload
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
    from src.gui.dispatch import WRITER_IDS

    roster = load_roster()
    for a in roster:  # 프론트 멘션 목록에서 '쓰기 가능'을 표시하려면 필요하다
        a["writer"] = a.get("agent_id") in WRITER_IDS
    return roster


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
        return {"busy": False, "queued": crew_runner.queued}
    return {
        "busy": crew_runner.is_busy,
        "queued": crew_runner.queued,
        "crew": s.crew,
        "status": s.status.value,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "error": s.error,
    }


@app.post("/api/run/{crew_name}")
def run_crew(crew_name: str) -> dict[str, str]:
    from main import COMMANDS
    if crew_name not in COMMANDS:
        return {"error": f"알 수 없는 크루: {crew_name}"}
    _, func = COMMANDS[crew_name]
    crew_runner.run(crew_name, func)
    return {"status": "started", "crew": crew_name}


# ── 지시 채팅 (07 §8) ──

def _emit(type_: str, **payload: Any) -> None:
    """서버 스레드에서 OfficeEvent 브로드캐스트. 리스너와 같은 포맷을 쓴다."""
    text = payload.pop("text", None)
    event_bus.broadcast_threadsafe(
        OfficeEvent(type=type_, run_id=payload.pop("run_id", None),
                    payload=OfficePayload(text=text if text is not None
                                          else json.dumps(payload, ensure_ascii=False)))
    )


@app.post("/api/message")
def post_message(text: str = Body(..., embed=True)) -> dict[str, Any]:
    """메시지 → 라우팅 → 큐 투입. 라우터 판정 불가 시 실행하지 않고 되묻는다."""
    from src.gui.dispatch import dispatch

    text = (text or "").strip()
    if not text:
        return {"ask": "지시 내용을 입력해 주세요."}

    _emit("user.message", text=text)
    d = dispatch(text, on_event=lambda t, p: _emit(t, **p))
    if d.get("ask"):
        _emit("router.decided", text=d["ask"])
        return {"ask": d["ask"]}

    mode = "회의" if len(d["agents"]) >= 2 else "작업"
    _emit("router.decided", run_id=d["run_id"],
          text=f"[{mode}] {d['agenda']} — {', '.join(d['agents'])}")
    crew_runner.run(d["agenda"], d["run"], run_id=d["run_id"])
    return {"run_id": d["run_id"], "agents": d["agents"], "agenda": d["agenda"], "mode": mode}


# ── 확인함 (07 §7) ──

@app.get("/api/review")
def review_list() -> list[dict[str, Any]]:
    return review.pending()


@app.get("/api/review/{run_id}")
def review_preview(run_id: str) -> dict[str, Any]:
    return review.preview(run_id)


@app.post("/api/review/{run_id}/approve")
def review_approve(run_id: str) -> dict[str, Any]:
    return review.approve(run_id)


@app.post("/api/review/{run_id}/reject")
def review_reject(run_id: str) -> dict[str, Any]:
    return review.reject(run_id)


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
