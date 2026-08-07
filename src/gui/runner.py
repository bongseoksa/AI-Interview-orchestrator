"""Crew runner — worker thread에서 kickoff, 순차 실행 보장 (§8-4)."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunSession:
    run_id: str
    crew: str
    status: RunStatus = RunStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: Any = None


class CrewRunner:
    """순차 실행 — ThreadPoolExecutor(1)이 곧 큐다 (§8-4, 07 §3).

    거절하지 않는다. 메신저처럼 지시가 쌓이고 순서대로 처리된다.
    """

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crew")
        self._lock = threading.Lock()
        self._current: RunSession | None = None
        self._pending = 0

    @property
    def current(self) -> RunSession | None:
        return self._current

    @property
    def is_busy(self) -> bool:
        return self._current is not None and self._current.status == RunStatus.RUNNING

    @property
    def queued(self) -> int:
        """대기 중(아직 시작 안 한) 지시 수."""
        return self._pending

    def run(self, crew_name: str, func: Callable[[], Any], run_id: str = "") -> RunSession:
        session = RunSession(run_id=run_id, crew=crew_name)
        with self._lock:
            self._pending += 1

        def _work() -> None:
            with self._lock:
                self._pending -= 1
                self._current = session  # 큐에서 꺼내진 시점이 곧 current
            session.status = RunStatus.RUNNING
            session.started_at = datetime.now()
            try:
                session.result = func()
                session.status = RunStatus.COMPLETED
            except Exception as e:
                session.error = str(e)
                session.status = RunStatus.FAILED
            finally:
                session.finished_at = datetime.now()

        self._executor.submit(_work)
        return session


crew_runner = CrewRunner()
