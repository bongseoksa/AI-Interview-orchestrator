"""Crew 실행 로거 — 에이전트 발화 및 작업 과정을 로컬 파일에 실시간 기록.

사용법: main.py에서 import만 하면 자동 등록된다.
    from src.config.crew_logger import crew_logger  # noqa: F401
"""

from __future__ import annotations

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

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def _truncate(text: Any, max_len: int = 500) -> str:
    """텍스트를 max_len 자로 잘라 한 줄로 반환한다."""
    s = str(text).replace("\n", " ").strip()
    if len(s) > max_len:
        return s[:max_len] + f"... (+{len(s) - max_len}자)"
    return s


def _agent_label(event: Any) -> str:
    """이벤트에서 에이전트 역할명을 추출한다."""
    role = getattr(event, "agent_role", None)
    if role:
        return role
    agent = getattr(event, "agent", None)
    if agent and hasattr(agent, "role"):
        return agent.role
    return "unknown"


def _task_label(event: Any) -> str:
    """이벤트에서 태스크명을 추출한다."""
    name = getattr(event, "task_name", None)
    if name:
        return name
    task = getattr(event, "task", None)
    if task:
        desc = getattr(task, "description", None)
        if desc:
            return _truncate(desc, 60)
        return str(task)[:60]
    return "unknown"


class CrewExecutionLogger(BaseEventListener):
    """모든 Crew 실행 과정을 logs/ 디렉토리에 실시간 기록한다."""

    def __init__(self) -> None:
        super().__init__()
        self._file: IO[str] | None = None
        self._crew_name: str = ""
        self._crew_start: datetime | None = None

    def _ensure_file(self, crew_name: str = "unknown") -> IO[str]:
        """로그 파일을 열거나 이미 열려있으면 재사용한다."""
        if self._file is None or self._file.closed:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = LOGS_DIR / f"{crew_name}_{ts}.log"
            self._file = open(path, "a", encoding="utf-8")
        return self._file

    def _write(self, tag: str, message: str, event: Any = None) -> None:
        """한 줄의 로그를 파일에 기록하고 즉시 flush한다."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f = self._ensure_file(self._crew_name)
        f.write(f"[{ts}] [{tag}] {message}\n")
        f.flush()

    def _close_file(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()
            self._file = None

    def setup_listeners(self, crewai_event_bus: Any) -> None:
        # ── Crew 레벨 ──

        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_start(source: Any, event: CrewKickoffStartedEvent) -> None:
            name = getattr(event, "crew_name", None) or "unknown"
            self._crew_name = name
            self._crew_start = datetime.now()
            self._ensure_file(name)
            inputs_str = _truncate(event.inputs) if event.inputs else "(없음)"
            self._write("CREW_START", f"{name} — inputs: {inputs_str}")

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def on_crew_done(source: Any, event: CrewKickoffCompletedEvent) -> None:
            name = getattr(event, "crew_name", None) or self._crew_name
            elapsed = ""
            if self._crew_start:
                delta = datetime.now() - self._crew_start
                elapsed = f" — {delta.total_seconds():.1f}초 소요"
            tokens = f", 총 토큰: {event.total_tokens}" if event.total_tokens else ""
            output_preview = _truncate(event.output, 200)
            self._write("CREW_DONE", f"{name} 완료{elapsed}{tokens}")
            self._write("CREW_OUTPUT", output_preview)
            self._close_file()

        @crewai_event_bus.on(CrewKickoffFailedEvent)
        def on_crew_fail(source: Any, event: CrewKickoffFailedEvent) -> None:
            self._write("CREW_FAIL", f"{self._crew_name} 실패 — {event.error}")
            self._close_file()

        # ── 에이전트 레벨 ──

        @crewai_event_bus.on(AgentExecutionStartedEvent)
        def on_agent_start(source: Any, event: AgentExecutionStartedEvent) -> None:
            role = _agent_label(event)
            task = _task_label(event)
            self._write("AGENT_START", f"{role} — task: {task}")

        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_done(source: Any, event: AgentExecutionCompletedEvent) -> None:
            role = _agent_label(event)
            task = _task_label(event)
            output_len = len(str(event.output)) if event.output else 0
            self._write("AGENT_DONE", f"{role} — task: {task} — 출력 {output_len}자")
            self._write("AGENT_OUTPUT", f"{role}: {_truncate(event.output, 300)}")

        @crewai_event_bus.on(AgentExecutionErrorEvent)
        def on_agent_error(source: Any, event: AgentExecutionErrorEvent) -> None:
            role = _agent_label(event)
            self._write("AGENT_ERROR", f"{role} — {_truncate(event.error)}")

        # ── 태스크 레벨 ──

        @crewai_event_bus.on(TaskStartedEvent)
        def on_task_start(source: Any, event: TaskStartedEvent) -> None:
            task = _task_label(event)
            self._write("TASK_START", task)

        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_done(source: Any, event: TaskCompletedEvent) -> None:
            task = _task_label(event)
            output = event.output
            out_file = getattr(output, "output_file", None) or ""
            raw_len = len(output.raw) if hasattr(output, "raw") and output.raw else 0
            suffix = f" → {out_file}" if out_file else ""
            self._write("TASK_DONE", f"{task} — {raw_len}자{suffix}")

        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_fail(source: Any, event: TaskFailedEvent) -> None:
            task = _task_label(event)
            self._write("TASK_FAIL", f"{task} — {_truncate(event.error)}")

        # ── 도구 사용 ──

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_start(source: Any, event: ToolUsageStartedEvent) -> None:
            role = _agent_label(event)
            tool = getattr(event, "tool_name", "unknown")
            args = _truncate(getattr(event, "tool_args", ""), 200)
            self._write("TOOL_START", f"{role} — {tool}({args})")

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool_done(source: Any, event: ToolUsageFinishedEvent) -> None:
            role = _agent_label(event)
            tool = getattr(event, "tool_name", "unknown")
            output_len = len(str(event.output)) if event.output else 0
            cached = " (cached)" if event.from_cache else ""
            self._write("TOOL_DONE", f"{role} — {tool} — {output_len}자{cached}")

        @crewai_event_bus.on(ToolUsageErrorEvent)
        def on_tool_error(source: Any, event: ToolUsageErrorEvent) -> None:
            role = _agent_label(event)
            tool = getattr(event, "tool_name", "unknown")
            self._write("TOOL_ERROR", f"{role} — {tool} — {_truncate(event.error)}")

        # ── LLM 호출 ──

        @crewai_event_bus.on(LLMCallCompletedEvent)
        def on_llm_done(source: Any, event: LLMCallCompletedEvent) -> None:
            usage = event.usage or {}
            prompt_tokens = usage.get("prompt_tokens", "?")
            completion_tokens = usage.get("completion_tokens", "?")
            call_type = event.call_type.value if event.call_type else "unknown"
            response_preview = _truncate(event.response, 300)
            self._write(
                "LLM_DONE",
                f"type={call_type}, tokens=({prompt_tokens}/{completion_tokens})",
            )
            self._write("LLM_RESPONSE", response_preview)

        @crewai_event_bus.on(LLMCallFailedEvent)
        def on_llm_fail(source: Any, event: LLMCallFailedEvent) -> None:
            self._write("LLM_FAIL", _truncate(event.error))


# 모듈 로드 시 글로벌 인스턴스 생성 → CrewAI 이벤트 버스에 자동 등록
crew_logger = CrewExecutionLogger()
