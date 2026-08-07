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
from src.tools.notion_tools import read_notion_page, search_notion_blocks
from src.tools.file_tools import (
    list_directory,
    list_directory_recursive,
    read_file,
    write_file,
)

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

# 기본은 읽기 전용 — 회의는 논의지 실행이 아니다.
_DISCUSS_TOOLS = [list_directory, list_directory_recursive, read_file]

# 쓰기 권한은 명시적으로 준 에이전트만. file_tools의 PROJECT_BASE가 AI-Interview/라
# 크로스 레포(web/server) 쓰기가 열린다 — CLI CodegenCrew와 동일한 권한이다.
WRITER_IDS = {"codegen-developer"}

# 노션은 조회만 준다. 블록 수정·삭제는 CLI(`main.py notion-edit`) 전용으로 남긴다 —
# 채팅 오타 한 번에 지식베이스가 지워지면 안 된다.
_NOTION_READ_TOOLS = {"notion-editor": [read_notion_page, search_notion_blocks]}


def _make_agent(spec: dict[str, Any]) -> Agent:
    aid = spec.get("agent_id", "")
    tools = _DISCUSS_TOOLS + ([write_file] if aid in WRITER_IDS else [])
    tools += _NOTION_READ_TOOLS.get(aid, [])
    return Agent(
        role=spec.get("role") or aid,
        goal=str(spec.get("goal") or "맡은 관점에서 안건을 검토한다").strip(),
        backstory=str(spec.get("backstory") or spec.get("role") or "").strip() or "전문가",
        llm=get_llm(HIGH_PERF_MODEL),
        tools=tools,
        allow_delegation=False,
        verbose=True,
    )


REPO_HINT = (
    "레포 경로 — web: ../AI-Interview-web, server: ../AI-Interview-server, "
    "orchestrator: (현재 레포). 경로는 AI-Interview/ 기준 상대경로로 쓴다."
)


def _task_for(aid: str, agent: Agent, agenda: str, instruction: str, ctx: str, first: bool = True) -> Task:
    """쓰기 권한이 있는 에이전트에겐 '의견'이 아니라 '실행'을 시킨다.

    지시 원문(instruction)을 그대로 넣는다. agenda는 40자 제목이라 조건·제약이
    날아간다 — 제목과 지시를 겸하게 두면 에이전트가 뭘 하라는 건지 알 수 없다.
    """
    detail = f"[지시 원문]\n{instruction}\n" if instruction else ""
    if aid in WRITER_IDS:
        return Task(
            description=(
                f"[작업] {agenda}\n{detail}{ctx}\n"
                f"{REPO_HINT}\n"
                f"1) list_directory/read_file로 대상 레포의 기존 구조와 컨벤션을 먼저 파악하라.\n"
                f"2) 기존 코드 스타일에 맞춰 write_file로 파일을 실제로 생성/수정하라.\n"
                f"의견만 내지 말고 반드시 write_file을 호출하라. "
                f"마지막에 생성·수정한 파일 경로 목록을 한국어로 보고하라."
            ),
            expected_output="생성·수정한 파일 경로 목록과 각 파일의 역할 요약",
            agent=agent,
        )
    # 순차 릴레이라 앞 발언이 context로 들어온다. 지시가 모두 같으면 뒤 발언자가
    # 앞 발언을 그대로 고쳐 쓴다 — 회의가 아니라 에코가 된다.
    turn = (
        "먼저 발언한다. 안건에 대한 당신의 입장을 세우라.\n"
        if first
        else (
            "앞선 참석자들의 발언이 맥락으로 주어진다.\n"
            "- 이미 나온 논거를 다시 쓰지 마라. 요약도 하지 마라.\n"
            "- 동의/반박을 먼저 한 줄로 밝히고, 당신 역할에서만 나올 수 있는 논점을 더하라.\n"
        )
    )
    return Task(
        description=(
            f"[안건] {agenda}\n{detail}{ctx}\n"
            f"당신은 '{agent.role}'로서 발언한다. 다른 직군을 흉내내지 마라.\n"
            f"{turn}"
            f"필요하면 read_file/list_directory로 레포를 직접 확인하라. 한국어로 답하라.\n"
            f"마크다운 제목(#)은 쓰지 말고 굵은 글씨와 불릿으로만 구조화하라."
        ),
        expected_output="입장과 근거가 담긴 의견 (앞 발언과 중복 없이)",
        agent=agent,
    )


def build_crew(
    agent_ids: list[str], agenda: str, instruction: str = "", context: str = ""
) -> tuple[Crew, bool]:
    """참석자 2명+ → 서기 Task를 마지막에 붙인다. 반환: (crew, is_meeting)"""
    cat = _catalog()
    member_ids = [i for i in agent_ids if i in cat]
    members = [_make_agent(cat[i]) for i in member_ids]
    if not members:
        raise ValueError(f"유효한 에이전트 없음: {agent_ids}")

    is_meeting = len(members) >= 2
    ctx = f"\n[참고 맥락]\n{context}\n" if context else ""

    tasks = [
        _task_for(aid, m, agenda, instruction, ctx, first=(i == 0))
        for i, (aid, m) in enumerate(zip(member_ids, members))
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


_MD_HEADING = re.compile(r"^(#{1,6})\s", re.M)


def _demote(md: str) -> str:
    """발언 본문의 제목을 h4 이하로 낮춘다.

    화자를 '### 이름'으로 찍는데 본문에도 '###'가 있으면 화자 구분이 묻힌다.
    실제로 회의록에서 화자 3명이 헤딩 11개에 섞여 읽을 수 없었다.
    """
    return _MD_HEADING.sub(lambda m: "#" * min(6, max(4, len(m.group(1)) + 1)) + " ", md)


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
        lines += ["---", "", f"### {speaker}", "", _demote(raw.strip()), ""]
    return "\n".join(lines)


# ── 실행 (07 §7) ──


def dispatch(text: str, on_event: Callable[[str, dict], None] | None = None) -> dict[str, Any]:
    """메시지 → {run_id, agents, agenda, run} 또는 {ask}. run()은 runner가 워커에서 호출."""
    decision = route(text)
    if decision["ask"]:
        return {"ask": decision["ask"]}

    _history.append(f"사용자: {text}")
    agent_ids, agenda = decision["agents"], decision["agenda"]
    instruction = _MENTION.sub("", text).strip()  # 멘션만 뺀 지시 원문 — 절단하지 않는다
    run_id = f"chat_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"

    def _run() -> Any:
        crew, is_meeting = build_crew(agent_ids, agenda, instruction)
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
