"""에이전트 회의록 동기화 — 로그 파싱(Python) + 내용 분석(LLM) + 페이지 생성(Python)

CLAUDE.md 규칙: 노션 문서 작성은 서기에이전트 경유 필수
실행: python main.py meetings

구조: 에이전트 회의록 페이지 아래에 일자+주제별 하위 페이지 생성
  에이전트 회의록/
    ├── 2026-07-17 — CodegenCrew 서버 초기 설정
    ├── 2026-07-18 — CodegenCrew FastAPI 구현
    └── ...

설계: Python이 로그 파싱 및 Notion 페이지 구조 생성을 보장하고,
      LLM은 각 회의의 내용 분석(요약/핵심 결정)만 담당한다.
"""

import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import read_file
from src.tools.notion_tools import (
    _resolve_page_id,
    _api_request,
    _markdown_to_blocks,
    _get_all_blocks,
    _block_text,
    append_to_notion_page,
    create_notion_child_page,
    MAX_BLOCKS_PER_REQUEST,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_INTERVIEW_ROOT = PROJECT_ROOT.parent
MEETING_PAGE = "에이전트 회의록"


# ── 1. 로그 파싱 (Python) ──


def parse_log_metadata(log_path: Path) -> dict | None:
    """로그 파일에서 메타데이터를 추출한다. 자기 참조 로그는 None 반환."""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # 자기 참조 로그 제외 (회의록 동기화 자체 + 개별 분석 태스크의 로그)
    head = content[:800]
    self_ref_keywords = [
        "에이전트 Crew 실행 로그를 분석",
        "회의록을 작성",
        "로그 파일을 읽고 회의 내용을 정리",
        "구조화된 회의록을 작성한다",
    ]
    if any(kw in head for kw in self_ref_keywords):
        return None

    # CREW_START 타임스탬프 추출
    crew_start = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[CREW_START\] (\S+)", content)
    if not crew_start:
        # design-*.log.txt 등 다른 형식
        task_start = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):", content)
        if not task_start:
            return None
        timestamp_str = task_start.group(1)
        crew_name = log_path.stem.replace(".", "_")
    else:
        timestamp_str = crew_start.group(1)
        crew_name = crew_start.group(2)

    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H:%M")

    # Crew 이름 정규화
    crew_name_map = {
        "crew": None,  # generic — 태스크에서 추출
    }
    if crew_name in crew_name_map:
        # TASK_START 또는 AGENT_START에서 실제 역할 추출
        agent_match = re.search(r"\[AGENT_START\] (.+?) —", content)
        if agent_match:
            agent_role = agent_match.group(1).strip()
            # 역할에서 Crew 종류 추론
            role_to_crew = {
                "프로덕트 매니저": "PlanningCrew",
                "Product Manager": "PlanningCrew",
                "프로젝트 매니저": "PlanningCrew",
                "Project Manager": "PlanningCrew",
                "시니어 QA": "ReviewCrew",
                "QA": "ReviewCrew",
                "시니어 프론트엔드": "ReviewCrew",
                "외부인사": "ReviewCrew",
                "External Advisor": "ReviewCrew",
                "서기관리": "DocumentationCrew",
                "Documentation Secretary": "DocumentationCrew",
                "풀스택 아키텍트": "ArchitectCrew",
                "데이터 엔지니어": "DataCrew",
                "인프라 전문가": "InfraCrew",
                "FE 시니어": "FrontendCrew",
            }
            for keyword, mapped_crew in role_to_crew.items():
                if keyword in agent_role:
                    crew_name = mapped_crew
                    break
            else:
                crew_name = agent_role.split("(")[0].strip()[:20]
        else:
            # TASK_START에서 주제 추출
            task_match = re.search(r"\[TASK_START\]\s*\n?\s*(.+?)[\n.]", content)
            if task_match:
                crew_name = task_match.group(1).strip()[:30]

    # 에이전트 목록 추출
    agents = []
    for m in re.finditer(r"\[AGENT_START\] (.+?) —", content):
        agent_name = m.group(1).strip()
        if agent_name not in agents:
            agents.append(agent_name)

    # 태스크 주제 추출 (첫 TASK_START 내용)
    task_desc = ""
    task_match = re.search(r"\[TASK_START\]\s*\n?\s*(.+?)(?:\n|$)", content)
    if not task_match:
        task_match = re.search(r'task_description["\']:\s*["\'](.+?)["\']', content)
    if task_match:
        task_desc = task_match.group(1).strip()[:100]

    # design-m5-m6 특수 처리
    if "design-m5-m6" in log_path.name:
        crew_name = "DesignCrew"
        task_desc = "M5/M6 구현 계획 수립"

    # 주제 결정
    topic = _infer_topic(crew_name, task_desc, content[:1000])

    # 페이지 제목 형식: YYYY-MM-DD HH:MM — CrewName 주제 (시간 포함으로 중복 방지)
    page_title = f"{date_str} {time_str} — {crew_name} {topic}"

    return {
        "log_file": log_path.name,
        "log_path": str(log_path),
        "timestamp": timestamp,
        "date": date_str,
        "time": time_str,
        "crew_name": crew_name,
        "agents": agents,
        "task_desc": task_desc,
        "topic": topic,
        "page_title": page_title,
        "content_size": len(content),
    }


def _infer_topic(crew_name: str, task_desc: str, head: str) -> str:
    """Crew 이름과 태스크 설명에서 회의 주제를 추론한다."""
    topics = {
        "CodegenCrew": {
            "server": "서버 코드 생성",
            "web": "웹 코드 생성",
            "health": "Health Check 엔드포인트",
            "FastAPI": "FastAPI 구현",
        },
        "DocumentationCrew": {
            "산출물 레지스트리": "산출물 레지스트리 작성",
            "매니페스트": "산출물 레지스트리 작성",
            "감사": "문서 정합성 감사",
            "정합성": "문서 정합성 감사",
            "Python": "Python 환경 표준화",
            "버전": "버전 표준화",
        },
        "NotionEditCrew": {
            "": "Notion 페이지 편집",
        },
        "PlanningCrew": {
            "M5": "M5/M6 전략 평가",
            "M6": "M5/M6 전략 평가",
        },
        "ReviewCrew": {
            "코드": "코드 품질 검수",
            "품질": "코드 품질 검수",
        },
        "DesignCrew": {
            "M5": "M5/M6 설계",
        },
    }

    crew_topics = topics.get(crew_name, {})
    combined = f"{task_desc} {head}"
    for keyword, topic in crew_topics.items():
        if keyword in combined:
            return topic

    # 기본값
    if task_desc:
        return task_desc[:40]
    return "Crew 실행"


def collect_logs() -> list[dict]:
    """logs/ 디렉토리의 모든 로그를 파싱하여 메타데이터 리스트로 반환한다."""
    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        return []

    meetings = []
    for f in sorted(logs_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            meta = parse_log_metadata(f)
            if meta:
                meetings.append(meta)

    # 시간순 정렬
    meetings.sort(key=lambda m: m["timestamp"])
    return meetings


def collect_cross_repo_context() -> str:
    """3개 레포의 git log 요약을 수집한다."""
    repos = {
        "orchestrator": AI_INTERVIEW_ROOT / "AI-Interview-orchestrator",
        "web": AI_INTERVIEW_ROOT / "AI-Interview-web",
        "server": AI_INTERVIEW_ROOT / "AI-Interview-server",
    }

    parts = []
    for name, repo_path in repos.items():
        if not repo_path.exists():
            parts.append(f"- **{name}**: (레포 미존재)")
            continue
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--since=2 weeks ago", "-10"],
                cwd=repo_path, capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                commits = result.stdout.strip().split("\n")
                parts.append(f"- **{name}**: 최근 {len(commits)}건 커밋 — {commits[0]}")
            else:
                parts.append(f"- **{name}**: 최근 커밋 없음")
        except Exception:
            parts.append(f"- **{name}**: git 정보 수집 실패")

    return "\n".join(parts)


# ── 2. LLM 분석 (서기에이전트) ──


def analyze_meeting_with_llm(meeting: dict, llm) -> str:
    """단일 회의(로그 파일)을 LLM으로 분석하여 구조화된 마크다운을 반환한다."""
    secretary = Agent(
        role="서기관리 에이전트 (Meeting Secretary)",
        goal=f"Crew 실행 로그를 분석하여 구조화된 회의록을 작성한다.",
        backstory="6년차 테크니컬 라이터. 간결하고 정확한 기록이 전문 분야.",
        llm=llm,
        tools=[read_file],
        allow_delegation=False,
        verbose=True,
    )

    task = Task(
        description=f"""
        아래 로그 파일을 읽고 회의 내용을 정리한다.

        [로그 파일]
        `{meeting['log_file']}` (경로: `logs/{meeting['log_file']}`)

        [기본 정보 — 이미 파싱됨]
        - 일시: {meeting['date']} {meeting['time']}
        - Crew: {meeting['crew_name']}
        - 참석자: {', '.join(meeting['agents']) if meeting['agents'] else '(로그에서 확인)'}

        [작업 지시]
        `read_file` 도구로 `logs/{meeting['log_file']}` 파일을 읽고, 다음을 추출하라:

        1. **안건**: 어떤 태스크를 수행했는지 (1~2줄)
        2. **주요 논의**: 에이전트가 수행한 핵심 분석/행동 (불릿 2~4개)
        3. **결정사항**: 핵심 결론 (불릿 1~3개)
        4. **산출물**: 생성된 파일명 또는 결과물 (불릿 1~2개)

        [출력 형식 — 반드시 이 형식 그대로 출력하라]
        ## 안건
        - (태스크 요약)

        ## 주요 논의
        - (핵심 분석/행동 1)
        - (핵심 분석/행동 2)

        ## 결정사항
        - (결론 1)

        ## 산출물
        - (파일명 또는 결과물)

        [주의]
        - 로그 전체를 복사하지 말고 핵심만 추출한다
        - 각 섹션은 2~4줄 이내로 간결하게 작성한다
        - 한국어로 작성한다
        """,
        expected_output="## 안건, ## 주요 논의, ## 결정사항, ## 산출물 4개 섹션의 마크다운",
        agent=secretary,
    )

    crew = Crew(
        agents=[secretary],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)


# ── 3. Notion 페이지 생성 (Python) ──


def create_meeting_page(meeting: dict, analysis: str, parent_page_id: str) -> str | None:
    """분석 결과를 Notion 하위 페이지로 생성한다."""
    title = meeting["page_title"]

    # 페이지 내용 구성
    agents_str = ", ".join(meeting["agents"]) if meeting["agents"] else "(미확인)"
    content = f"""## 기본 정보
- **일시**: {meeting['date']} {meeting['time']}
- **Crew**: {meeting['crew_name']}
- **참석자**: {agents_str}
- **로그**: `{meeting['log_file']}`

{analysis}
"""

    # Notion 자식 페이지 생성
    blocks = _markdown_to_blocks(content)
    body = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        },
    }
    if blocks:
        body["children"] = blocks[:MAX_BLOCKS_PER_REQUEST]

    resp = _api_request("POST", "/pages", body)
    if "error" in resp:
        print(f"  ERROR: {resp['error'][:200]}")
        return None

    new_page_id = resp.get("id", "")

    # 93블록 초과분 추가
    if len(blocks) > MAX_BLOCKS_PER_REQUEST:
        remaining = blocks[MAX_BLOCKS_PER_REQUEST:]
        for i in range(0, len(remaining), MAX_BLOCKS_PER_REQUEST):
            chunk = remaining[i:i + MAX_BLOCKS_PER_REQUEST]
            _api_request("PATCH", f"/blocks/{new_page_id}/children", {"children": chunk})

    print(f"  Created: {title} (id: {new_page_id})")
    return title


def update_parent_page(parent_page_id: str, meetings: list[dict], created_titles: list[str], repo_context: str):
    """부모 페이지(에이전트 회의록)에 요약 인덱스를 기록한다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    index_lines = "\n".join(f"- {t}" for t in created_titles)

    content = f"""---

## 프로젝트 현황 요약 (3개 레포)
{repo_context}

## 회의 인덱스 ({len(created_titles)}건)
{index_lines}

마지막 동기화: {now}
---
"""
    # 기존 블록 정리 (child_page 제외)
    blocks = _get_all_blocks(parent_page_id)
    for b in blocks:
        if b.get("type") != "child_page":
            _api_request("DELETE", f"/blocks/{b['id']}")

    # 새 요약 추가
    new_blocks = _markdown_to_blocks(content)
    if new_blocks:
        for i in range(0, len(new_blocks), MAX_BLOCKS_PER_REQUEST):
            chunk = new_blocks[i:i + MAX_BLOCKS_PER_REQUEST]
            _api_request("PATCH", f"/blocks/{parent_page_id}/children", {"children": chunk})


# ── 4. 중복 검사 ──


def get_existing_titles(parent_page_id: str) -> set[str]:
    """부모 페이지의 기존 하위 페이지 제목들을 반환한다."""
    blocks = _get_all_blocks(parent_page_id)
    titles = set()
    for b in blocks:
        if b.get("type") == "child_page":
            title = b.get("child_page", {}).get("title", "")
            if title:
                titles.add(title)
    return titles


# ── 메인 ──


def main():
    print("=" * 60)
    print("에이전트 회의록 동기화 — Python 구조 + LLM 분석")
    print("=" * 60)

    # 1. 로그 파싱
    meetings = collect_logs()
    print(f"\n파싱된 회의: {len(meetings)}건")
    for m in meetings:
        print(f"  {m['date']} {m['time']} — {m['crew_name']}: {m['topic']} ({m['log_file']})")

    if not meetings:
        print("분석할 로그가 없습니다.")
        return

    # 2. 크로스 레포 컨텍스트
    repo_context = collect_cross_repo_context()

    # 3. 중복 검사
    parent_page_id = _resolve_page_id(MEETING_PAGE)
    existing_titles = get_existing_titles(parent_page_id)
    print(f"\n기존 하위 페이지: {len(existing_titles)}건")

    # 4. LLM으로 각 회의 분석 + Notion 페이지 생성
    llm = get_llm(HIGH_PERF_MODEL)
    created_titles = []

    for i, meeting in enumerate(meetings):
        title = meeting["page_title"]

        # 중복 체크
        if title in existing_titles:
            print(f"\n[{i+1}/{len(meetings)}] Skip (이미 존재): {title}")
            created_titles.append(title)
            continue

        print(f"\n[{i+1}/{len(meetings)}] 분석 중: {title}")

        # LLM 분석
        try:
            analysis = analyze_meeting_with_llm(meeting, llm)
        except Exception as e:
            print(f"  LLM 분석 실패: {e}")
            analysis = "## 안건\n- (분석 실패)\n\n## 주요 논의\n- (로그 참조)\n\n## 결정사항\n- (로그 참조)\n\n## 산출물\n- (로그 참조)"

        # Notion 페이지 생성
        created = create_meeting_page(meeting, analysis, parent_page_id)
        if created:
            created_titles.append(created)

    # 5. 부모 페이지 업데이트
    print(f"\n부모 페이지 인덱스 업데이트 중...")
    update_parent_page(parent_page_id, meetings, created_titles, repo_context)

    # 6. 로컬 요약 저장
    summary_path = PROJECT_ROOT / "output" / "meeting-notes.md"
    summary_path.parent.mkdir(exist_ok=True)
    summary_lines = [
        "# 에이전트 회의록 요약",
        f"\n동기화 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"총 {len(created_titles)}건 회의\n",
    ]
    for t in created_titles:
        summary_lines.append(f"- {t}")
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"에이전트 회의록 동기화 완료")
    print(f"  총 {len(created_titles)}건 회의 기록")
    print(f"  로컬: output/meeting-notes.md")
    print(f"  노션: 에이전트 회의록 페이지 (일자+주제별 하위 페이지)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
