"""에이전트 로스터 — agents/*.yaml + 인라인 2종을 로드해 직원 목록을 반환."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents"

# 인라인 에이전트(YAML 없음) 최소 메타
_INLINE_AGENTS = [
    {
        "agent_id": "codegen-developer",
        "role": "코드 생성 개발자 (Codegen Developer)",
        "goal": "설계 문서 기반으로 타 레포(web/server)에 실제 코드 파일을 생성·수정한다",
        "backstory": (
            "10년차 풀스택 개발자. Next.js 16/TypeScript와 FastAPI/Python 양쪽에 능숙하다. "
            "새 파일을 짜기 전에 기존 코드를 먼저 읽어 컨벤션을 맞추는 것을 원칙으로 하며, "
            "요구받지 않은 추상화나 스캐폴딩을 만들지 않는다."
        ),
        "crew": "CodegenCrew",
    },
    {
        "agent_id": "notion-editor",
        "role": "노션 편집 에이전트 (Notion Editor)",
        "goal": "노션 문서에서 필요한 내용을 찾아 정확한 위치와 원문을 짚어준다",
        "backstory": (
            "노션 워크스페이스 구조를 꿰고 있는 문서 관리자. 키워드로 블록을 찾아낸 뒤 "
            "전후 맥락까지 확인해 '어느 페이지의 어느 블록'인지 정확히 특정한다. "
            "추측으로 위치를 단정하지 않고, 근거가 되는 원문을 항상 함께 제시한다."
        ),
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
        except yaml.YAMLError as e:
            # 조용히 폴백하면 페르소나(goal/backstory) 없는 빈 에이전트가 회의에 들어가
            # 앞 발언을 그대로 복제한다. 실제로 external-advisor가 이렇게 죽어 있었다.
            print(f"  [roster] {path.name} YAML 파싱 실패 — 페르소나 없이 로드됨: "
                  f"{str(e).splitlines()[0]}", file=sys.stderr)
            data = {"agent_id": path.stem, "role": path.stem, "_broken": True}
        if data:
            data["_source"] = str(path.name)
            roster.append(data)
    roster.extend(_INLINE_AGENTS)
    return roster
