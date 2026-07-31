"""OfficeEvent — GUI 이벤트 파이프라인의 단일 메시지 포맷.

WebSocket/콘솔/JSONL 모두 이 모델 하나로 직렬화한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OfficePayload(BaseModel):
    text: str | None = None
    output_len: int | None = None
    output_file: str | None = None
    tokens: dict[str, Any] | None = None
    from_cache: bool | None = None
    error: str | None = None
    elapsed_sec: float | None = None


class OfficeEvent(BaseModel):
    type: str
    ts: datetime = Field(default_factory=datetime.now)
    run_id: str | None = None
    crew: str | None = None
    agent: str | None = None
    task: str | None = None
    tool: str | None = None
    payload: OfficePayload = Field(default_factory=OfficePayload)

    def to_json(self) -> str:
        return self.model_dump_json()
