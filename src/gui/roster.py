"""에이전트 로스터 — agents/*.yaml + 인라인 2종을 로드해 직원 목록을 반환."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents"

# 인라인 에이전트(YAML 없음) 최소 메타
_INLINE_AGENTS = [
    {
        "agent_id": "codegen-developer",
        "role": "코드 생성 개발자 (Codegen Developer)",
        "goal": "설계 문서 기반으로 타 레포에 코드 파일 생성",
        "crew": "CodegenCrew",
    },
    {
        "agent_id": "notion-editor",
        "role": "노션 편집 에이전트 (Notion Editor)",
        "goal": "키워드 검색 → AI 검증 → 정확한 블록 편집",
        "crew": "NotionEditCrew",
    },
]


def load_roster() -> list[dict[str, Any]]:
    """전체 에이전트 로스터 반환."""
    roster: list[dict[str, Any]] = []
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError:
            # CrewAI YAML은 Jinja 템플릿 등으로 표준 YAML이 아닐 수 있음
            data = {"agent_id": path.stem, "role": path.stem}
        if data:
            data["_source"] = str(path.name)
            roster.append(data)
    roster.extend(_INLINE_AGENTS)
    return roster
