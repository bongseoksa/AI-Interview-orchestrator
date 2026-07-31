"""GUIEventListener — CrewAI 이벤트를 OfficeEvent로 변환, 콘솔 출력 + JSONL 적재.

crew_logger.py의 형제 리스너. 같은 이벤트 버스에 병존한다.
사용법: main.py에서 import만 하면 자동 등록.
    from src.gui.listener import gui_listener  # noqa: F401
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import IO, Any

from crewai.events import BaseEventListener
from crewai.events import (
    CrewKickoffStartedEvent,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
    AgentExecutionStartedEvent,
    AgentExecutionCompletedEvent,
    AgentExecutionErrorEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
    ToolUsageErrorEvent,
    LLMCallCompletedEvent,
    LLMCallFailedEvent,
)

from src.gui.events import OfficeEvent, OfficePayload

SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "gui_data" / "sessions"

# ponytail: 콘솔 색상, 실 사용시 colorama 등으로 대체
_BLUE = "\033[94m"
_RESET = "\033[0m"


def _agent_label(event: Any) -> str | None:
    role = getattr(event, "agent_role", None)
    if role:
        return role
    agent = getattr(event, "agent", None)
    if agent and hasattr(agent, "role"):
        return agent.role
    return None


def _task_label(event: Any) -> str | None:
    name = getattr(event, "task_name", None)
    if name:
        return name
    task = getattr(event, "task", None)
    if task:
        desc = getattr(task, "description", None)
        if desc:
            return str(desc)[:80]
        return str(task)[:80]
    return None


class GUIEventListener(BaseEventListener):
    """CrewAI 이벤트 → OfficeEvent JSON 변환 + 콘솔 출력 + JSONL 적재."""

    def __init__(self) -> None:
        super().__init__()
        self._run_id: str | None = None
        self._crew_name: str | None = None
        self._crew_start: datetime | None = None
        self._jsonl: IO[str] | None = None
        # 외부에서 주입 가능 (GM1+: bus.broadcast)
        self._broadcast: Any = None

    def _emit(self, event: OfficeEvent) -> None:
        """OfficeEvent를 콘솔 + JSONL + (향후) WebSocket으로 방출."""
        line = event.to_json()

        # 1) 콘솔
        print(f"{_BLUE}[OFFICE]{_RESET} {line}", file=sys.stderr)

        # 2) JSONL 적재 (무절단 — §8-5 D8)
        if self._jsonl and not self._jsonl.closed:
            self._jsonl.write(line + "\n")
            self._jsonl.flush()

        # 3) 향후 WebSocket broadcast hook
        if self._broadcast:
            try:
                self._broadcast(event)
            except Exception:
                pass  # 리스너 예외가 Crew 실행을 멈추면 안 된다

    def _open_session(self, run_id: str) -> None:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSIONS_DIR / f"{run_id}.jsonl"
        self._jsonl = open(path, "a", encoding="utf-8")

    def _close_session(self) -> None:
        if self._jsonl and not self._jsonl.closed:
            self._jsonl.close()
            self._jsonl = None

    def _make(self, type_: str, **kwargs: Any) -> OfficeEvent:
        return OfficeEvent(
            type=type_,
            run_id=self._run_id,
            crew=self._crew_name,
            **kwargs,
        )

    def setup_listeners(self, crewai_event_bus: Any) -> None:

        # ── Crew ──

        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_start(source: Any, event: CrewKickoffStartedEvent) -> None:
            self._crew_name = getattr(event, "crew_name", None) or "unknown"
            self._run_id = f"{self._crew_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            self._crew_start = datetime.now()
            self._open_session(self._run_id)
            self._emit(self._make(
                "crew.started",
                payload=OfficePayload(text=str(event.inputs) if event.inputs else None),
            ))

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def on_crew_done(source: Any, event: CrewKickoffCompletedEvent) -> None:
            elapsed = None
            if self._crew_start:
                elapsed = (datetime.now() - self._crew_start).total_seconds()
            self._emit(self._make(
                "crew.completed",
                payload=OfficePayload(
                    text=str(event.output) if event.output else None,  # 무절단
                    tokens={"total": event.total_tokens} if event.total_tokens else None,
                    elapsed_sec=elapsed,
                ),
            ))
            self._close_session()

        @crewai_event_bus.on(CrewKickoffFailedEvent)
        def on_crew_fail(source: Any, event: CrewKickoffFailedEvent) -> None:
            self._emit(self._make(
                "crew.failed",
                payload=OfficePayload(error=str(event.error)),
            ))
            self._close_session()

        # ── Agent ──

        @crewai_event_bus.on(AgentExecutionStartedEvent)
        def on_agent_start(source: Any, event: AgentExecutionStartedEvent) -> None:
            self._emit(self._make(
                "agent.started",
                agent=_agent_label(event),
                task=_task_label(event),
            ))

        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_done(source: Any, event: AgentExecutionCompletedEvent) -> None:
            output = str(event.output) if event.output else ""
            self._emit(self._make(
                "agent.completed",
                agent=_agent_label(event),
                task=_task_label(event),
                payload=OfficePayload(
                    text=output,  # 무절단 — 표시용 절단은 프론트에서
                    output_len=len(output),
                ),
            ))

        @crewai_event_bus.on(AgentExecutionErrorEvent)
        def on_agent_error(source: Any, event: AgentExecutionErrorEvent) -> None:
            self._emit(self._make(
                "agent.error",
                agent=_agent_label(event),
                payload=OfficePayload(error=str(event.error)),
            ))

        # ── Task ──

        @crewai_event_bus.on(TaskStartedEvent)
        def on_task_start(source: Any, event: TaskStartedEvent) -> None:
            self._emit(self._make("task.started", task=_task_label(event)))

        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_done(source: Any, event: TaskCompletedEvent) -> None:
            output = event.output
            out_file = getattr(output, "output_file", None) or None
            raw = output.raw if hasattr(output, "raw") and output.raw else ""
            self._emit(self._make(
                "task.completed",
                task=_task_label(event),
                payload=OfficePayload(
                    text=raw,  # 무절단
                    output_len=len(raw),
                    output_file=str(out_file) if out_file else None,
                ),
            ))

        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_fail(source: Any, event: TaskFailedEvent) -> None:
            self._emit(self._make(
                "task.failed",
                task=_task_label(event),
                payload=OfficePayload(error=str(event.error)),
            ))

        # ── Tool ──

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_start(source: Any, event: ToolUsageStartedEvent) -> None:
            self._emit(self._make(
                "tool.started",
                agent=_agent_label(event),
                tool=getattr(event, "tool_name", None),
                payload=OfficePayload(text=str(getattr(event, "tool_args", ""))),
            ))

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool_done(source: Any, event: ToolUsageFinishedEvent) -> None:
            output = str(event.output) if event.output else ""
            self._emit(self._make(
                "tool.finished",
                agent=_agent_label(event),
                tool=getattr(event, "tool_name", None),
                payload=OfficePayload(
                    text=output,  # 무절단
                    output_len=len(output),
                    from_cache=event.from_cache if hasattr(event, "from_cache") else None,
                ),
            ))

        @crewai_event_bus.on(ToolUsageErrorEvent)
        def on_tool_error(source: Any, event: ToolUsageErrorEvent) -> None:
            self._emit(self._make(
                "tool.error",
                agent=_agent_label(event),
                tool=getattr(event, "tool_name", None),
                payload=OfficePayload(error=str(event.error)),
            ))

        # ── LLM ──

        @crewai_event_bus.on(LLMCallCompletedEvent)
        def on_llm_done(source: Any, event: LLMCallCompletedEvent) -> None:
            usage = event.usage or {}
            self._emit(self._make(
                "llm.completed",
                payload=OfficePayload(
                    text=str(event.response) if event.response else None,  # 무절단
                    tokens={
                        "prompt": usage.get("prompt_tokens"),
                        "completion": usage.get("completion_tokens"),
                    },
                ),
            ))

        @crewai_event_bus.on(LLMCallFailedEvent)
        def on_llm_fail(source: Any, event: LLMCallFailedEvent) -> None:
            self._emit(self._make(
                "llm.failed",
                payload=OfficePayload(error=str(event.error)),
            ))


# 모듈 로드 시 글로벌 인스턴스 → CrewAI 이벤트 버스 자동 등록
gui_listener = GUIEventListener()
