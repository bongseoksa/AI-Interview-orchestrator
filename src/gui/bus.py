"""EventBus — asyncio 기반 WebSocket fan-out.

GUIEventListener(워커 스레드)에서 call_soon_threadsafe로 이벤트를 넣으면,
연결된 모든 WebSocket 클라이언트에 브로드캐스트한다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.gui.events import OfficeEvent


class EventBus:
    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[str]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        self._clients.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._clients.discard(q)

    def broadcast_threadsafe(self, event: OfficeEvent) -> None:
        """워커 스레드에서 호출. asyncio 루프에 안전하게 전달 (§8-2)."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._broadcast_sync, event.to_json())

    def _broadcast_sync(self, line: str) -> None:
        dead: list[asyncio.Queue[str]] = []
        for q in self._clients:
            try:
                q.put_nowait(line)
            except asyncio.QueueFull:
                dead.append(q)  # ponytail: 느린 클라이언트 drop, backpressure 필요 시 개선
        for q in dead:
            self._clients.discard(q)


event_bus = EventBus()
