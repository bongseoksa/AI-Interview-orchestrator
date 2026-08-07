"""지시 채팅 디스패처 — 메시지 → 라우팅 → 실행 (docs/gui/07-chat-and-meeting.md)

참석자 수가 곧 모드다:
  1명  → 채팅 답변. 회의록/결정사항 없음
  2명+ → 회의. 서기 Task 추가 + 문서 2건 생성 → 확인함
"""

from __future__ import annotations

import json
import re
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from crewai import Agent, Crew, Process, Task

from src.config.llm import DEFAULT_MODEL, HIGH_PERF_MODEL, get_llm
from src.gui.roster import load_roster
from src.tools.file_tools import list_directory, list_directory_recursive, read_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MEETINGS_DIR = PROJECT_ROOT / "output" / "meetings"

SECRETARY_ID = "doc-secretary"

# 최근 대화 — 라우터 프롬프트에 주입. CrewAI Memory/벡터 DB 안 쓴다 (07 §11)
_history: deque[str] = deque(maxlen=10)


# ── 문서 명명 (07 §6) — 파일명과 노션 페이지 제목의 단일 소스 ──

_SLUG_STRIP = re.compile(r'[/\\:*?"<>|_\n\r\t]')
_SLUG_SPACE = re.compile(r"\s+")


AGENDA_LIMIT = 40


def trim(s: str, limit: int = AGENDA_LIMIT) -> str:
    """어절 경계에서 자른다. 이 문자열이 곧 노션 페이지 제목이라 중간에서 끊기면 안 읽힌다.

    @멘션 경로는 지시 원문을 그대로 안건으로 쓰므로 절단이 항상 걸린다.
    끊을 어절 경계가 너무 앞이면(제목의 절반 미만) 그냥 자른다 — 빈 제목 방지.
    """
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    i = max(cut.rfind(" "), cut.rfind("-"))
    return (cut[:i] if i > limit // 2 else cut).strip(" -")


def slugify(agenda: str, limit: int = AGENDA_LIMIT) -> str:
    """안건 → 파일명 안전 슬러그. 한글 유지, 공백→'-', 구분자 '_' 제거."""
    s = _SLUG_STRIP.sub("", agenda or "").strip()
    s = _SLUG_SPACE.sub("-", s).strip("-")
    return trim(s, limit) or "무제"


def doc_name(date: str, agenda: str, kind: str, taken: set[str] | None = None) -> str:
    """{일자}_{타이틀}_{종류}. 충돌 시 _2, _3... (시간 안 붙인다 — 이름이 길어진다)"""
    base = f"{date}_{slugify(agenda)}_{kind}"
    if not taken or base not in taken:
        return base
    n = 2
    while f"{base}_{n}" in taken:
        n += 1
    return f"{base}_{n}"


def _existing_names() -> set[str]:
    if not MEETINGS_DIR.exists():
        return set()
    return {p.stem for p in MEETINGS_DIR.glob("*.md")}


# ── 라우팅 (07 §4) — 3단 폴백 ──

_MENTION = re.compile(r"@([a-zA-Z][a-zA-Z0-9-]+)")


def _catalog() -> dict[str, dict[str, Any]]:
    return {a["agent_id"]: a for a in load_roster() if a.get("agent_id")}


def parse_mentions(text: str, valid_ids: set[str]) -> list[str]:
    """폴백 1 — @멘션이 있으면 LLM을 건너뛴다."""
    seen: list[str] = []
    for m in _MENTION.findall(text):
        if m in valid_ids and m not in seen:
            seen.append(m)
    return seen


def _router_prompt(text: str, cat: dict[str, dict]) -> str:
    roster_lines = "\n".join(
        f"- {aid}: {a.get('role', aid)} — {str(a.get('goal', '')).strip()[:70]}"
        for aid, a in cat.items()
    )
    ctx = "\n".join(f"- {h}" for h in _history) or "(없음)"
    return f"""당신은 사내 메신저의 업무 라우터다. 사용자 지시를 읽고 담당 에이전트를 배정한다.

[에이전트 목록]
{roster_lines}

[최근 대화]
{ctx}

[사용자 지시]
{text}

[규칙]
- 단순 질문/단일 작업이면 agents에 1명만 넣는다.
- 여러 관점의 논의·결정이 필요하면 2~4명을 넣는다 (그러면 회의가 된다).
- {SECRETARY_ID}는 회의 시 자동 참석하므로 agents에 넣지 마라.
- agenda는 회의/작업 제목이다. 20자 이내 한국어 명사구로 쓴다.
- 판단이 불가능하면 agents를 빈 배열로 두고 ask에 되물을 질문을 넣는다.

[출력 — JSON만. 설명·마크다운 금지]
{{"agents": ["agent_id", ...], "agenda": "제목", "ask": null}}"""


def _extract_json(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else None
    except json.JSONDecodeError:
        return None


def route(text: str, llm_call: Callable[[str], str] | None = None) -> dict[str, Any]:
    """메시지 → {agents, agenda, ask}. ask가 있으면 실행하지 않고 되묻는다."""
    cat = _catalog()
    valid = set(cat)

    mentioned = parse_mentions(text, valid)
    if mentioned:
        agenda = _MENTION.sub("", text).strip() or "지시"
        return {"agents": mentioned, "agenda": trim(agenda), "ask": None}

    if llm_call is None:
        llm = get_llm(DEFAULT_MODEL)
        llm_call = lambda p: str(llm.call(p))  # noqa: E731

    try:
        parsed = _extract_json(llm_call(_router_prompt(text, cat)))
    except Exception as e:
        return {"agents": [], "agenda": "", "ask": f"라우터 오류: {e}. 누구에게 시킬지 @멘션으로 지정해 주세요."}

    agents = [a for a in (parsed or {}).get("agents", []) if a in valid and a != SECRETARY_ID]
    if not agents:
        ask = (parsed or {}).get("ask") or "누구에게 시킬까요? @멘션으로 지정해 주세요."
        return {"agents": [], "agenda": "", "ask": ask}

    return {"agents": agents[:4], "agenda": trim(str((parsed or {}).get("agenda") or text)), "ask": None}


# ── Crew 조립 (07 §5) ──

_DISCUSS_TOOLS = [list_directory, list_directory_recursive, read_file]


def _make_agent(spec: dict[str, Any]) -> Agent:
    return Agent(
        role=spec.get("role") or spec["agent_id"],
        goal=str(spec.get("goal") or "맡은 관점에서 안건을 검토한다").strip(),
        backstory=str(spec.get("backstory") or spec.get("role") or "").strip() or "전문가",
        llm=get_llm(HIGH_PERF_MODEL),
        tools=_DISCUSS_TOOLS,
        allow_delegation=False,
        verbose=True,
    )


def build_crew(agent_ids: list[str], agenda: str, context: str = "") -> tuple[Crew, bool]:
    """참석자 2명+ → 서기 Task를 마지막에 붙인다. 반환: (crew, is_meeting)"""
    cat = _catalog()
    members = [_make_agent(cat[i]) for i in agent_ids if i in cat]
    if not members:
        raise ValueError(f"유효한 에이전트 없음: {agent_ids}")

    is_meeting = len(members) >= 2
    ctx = f"\n[참고 맥락]\n{context}\n" if context else ""

    tasks = [
        Task(
            description=(
                f"[안건] {agenda}{ctx}\n"
                f"당신의 전문 관점에서 안건을 검토하고 근거를 갖춘 의견과 권고안을 제시하라.\n"
                f"필요하면 read_file/list_directory로 레포를 직접 확인하라. 한국어로 답하라."
            ),
            expected_output="근거와 권고안이 포함된 의견",
            agent=m,
        )
        for m in members
    ]

    if not is_meeting:
        return Crew(agents=members, tasks=tasks, process=Process.sequential, verbose=True), False

    secretary = _make_agent(cat[SECRETARY_ID])
    tasks.append(
        Task(
            description=(
                f"[안건] {agenda}\n"
                f"위 참석자들의 논의에서 결정사항·미결·액션아이템을 추출하라.\n"
                f"논의에 없는 내용을 지어내지 마라. 한국어로 작성하라."
            ),
            expected_output="## 결정사항 / ## 미결 / ## 액션아이템 3개 섹션의 마크다운",
            agent=secretary,
            context=list(tasks),
        )
    )
    return Crew(agents=members + [secretary], tasks=tasks, process=Process.sequential, verbose=True), True


# ── 회의록 조립 (07 §6) — LLM 안 쓴다. task 출력 원문 = 속기록 (D8 무절단) ──


def build_transcript(agenda: str, agent_ids: list[str], crew_output: Any) -> str:
    cat = _catalog()
    roles = [cat[i].get("role", i) for i in agent_ids if i in cat]
    outs = list(getattr(crew_output, "tasks_output", []) or [])

    lines = [
        f"# {agenda}",
        "",
        f"- **일시**: {datetime.now():%Y-%m-%d %H:%M}",
        f"- **참석자**: {', '.join(roles)}",
        "",
        "## 발언 전문",
        "",
    ]
    for i, out in enumerate(outs):
        speaker = getattr(getattr(out, "agent", None), "role", None) or (
            roles[i] if i < len(roles) else "서기관리 에이전트"
        )
        raw = getattr(out, "raw", None) or str(out)
        lines += [f"### {speaker}", "", raw.strip(), ""]
    return "\n".join(lines)


# ── 실행 (07 §7) ──


def dispatch(text: str, on_event: Callable[[str, dict], None] | None = None) -> dict[str, Any]:
    """메시지 → {run_id, agents, agenda, run} 또는 {ask}. run()은 runner가 워커에서 호출."""
    decision = route(text)
    if decision["ask"]:
        return {"ask": decision["ask"]}

    _history.append(f"사용자: {text}")
    agent_ids, agenda = decision["agents"], decision["agenda"]
    run_id = f"chat_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"

    def _run() -> Any:
        crew, is_meeting = build_crew(agent_ids, agenda)
        result = crew.kickoff()
        _history.append(f"결과({agenda}): {str(result)[:200]}")
        if is_meeting:
            _save_meeting_docs(run_id, agenda, agent_ids, result, on_event)
        return result

    return {"run_id": run_id, "agents": agent_ids, "agenda": agenda, "run": _run}


def _save_meeting_docs(
    run_id: str,
    agenda: str,
    agent_ids: list[str],
    result: Any,
    on_event: Callable[[str, dict], None] | None,
) -> None:
    """초안 2건 저장 + 확인함 등록. 노션 쓰기는 승인 후 (CLAUDE.md 2단계 규칙)."""
    from src.gui.review import enqueue

    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
    date = f"{datetime.now():%Y-%m-%d}"
    taken = _existing_names()

    docs = []
    for kind, body in (
        ("회의록", build_transcript(agenda, agent_ids, result)),
        ("결정사항", f"# {agenda} — 결정사항\n\n- **일시**: {date}\n\n{str(result).strip()}\n"),
    ):
        name = doc_name(date, agenda, kind, taken)
        taken.add(name)
        path = MEETINGS_DIR / f"{name}.md"
        path.write_text(body, encoding="utf-8")
        docs.append({"kind": kind, "title": name, "path": str(path)})

    enqueue(run_id, agenda, date, docs)
    if on_event:
        on_event("review.pending", {"run_id": run_id, "agenda": agenda, "docs": docs})
