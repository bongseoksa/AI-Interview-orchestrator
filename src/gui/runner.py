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
    """순차 실행 — 한 번에 하나만 (§8-4)."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crew")
        self._lock = threading.Lock()
        self._current: RunSession | None = None

    @property
    def current(self) -> RunSession | None:
        return self._current

    @property
    def is_busy(self) -> bool:
        return self._current is not None and self._current.status == RunStatus.RUNNING

    def run(self, crew_name: str, func: Callable[[], Any]) -> RunSession:
        with self._lock:
            if self.is_busy:
                raise RuntimeError(f"이미 실행 중: {self._current.crew}")  # type: ignore[union-attr]
            session = RunSession(run_id="", crew=crew_name)
            self._current = session

        def _work() -> None:
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
