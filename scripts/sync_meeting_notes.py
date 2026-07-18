"""에이전트 회의록 동기화 — 서기에이전트가 3개 레포를 검토하여 회의록을 구조화

CLAUDE.md 규칙: 노션 문서 작성은 서기에이전트 경유 필수
실행: python main.py meetings
"""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory, list_directory_recursive, read_file
from src.tools.notion_tools import (
    list_notion_pages,
    read_notion_page,
    read_notion_page_full,
    append_to_notion_page,
    search_notion_blocks,
    update_notion_block,
    delete_notion_block,
    insert_after_notion_block,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_INTERVIEW_ROOT = PROJECT_ROOT.parent  # AI-Interview/
MEETING_PAGE = "에이전트 회의록"


def collect_cross_repo_context() -> str:
    """3개 레포의 git log, CLAUDE.md 요약, 주요 변경사항을 수집한다."""
    repos = {
        "orchestrator": AI_INTERVIEW_ROOT / "AI-Interview-orchestrator",
        "web": AI_INTERVIEW_ROOT / "AI-Interview-web",
        "server": AI_INTERVIEW_ROOT / "AI-Interview-server",
    }

    context_parts = []

    for name, repo_path in repos.items():
        if not repo_path.exists():
            continue

        context_parts.append(f"\n{'='*50}")
        context_parts.append(f"레포: {name} ({repo_path.name})")
        context_parts.append(f"{'='*50}")

        # git log
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--since=2 weeks ago", "-30"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                context_parts.append(f"\n### Git 커밋 이력 (최근 2주)")
                context_parts.append(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # CLAUDE.md 요약 (첫 50줄)
        claude_md = repo_path / "CLAUDE.md"
        if claude_md.exists():
            lines = claude_md.read_text(encoding="utf-8").splitlines()[:50]
            context_parts.append(f"\n### CLAUDE.md 요약")
            context_parts.append("\n".join(lines))

    return "\n".join(context_parts)


def collect_log_manifest() -> str:
    """logs/ 디렉토리의 로그 파일 목록을 수집한다."""
    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        return "(로그 없음)"

    lines = []
    for f in sorted(logs_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            size_kb = f.stat().st_size / 1024
            from datetime import datetime
            modified = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            lines.append(f"- `{f.name}` ({size_kb:.1f}KB, {modified})")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("에이전트 회의록 동기화 — 서기에이전트 (3개 레포 검토)")
    print("=" * 60)

    # 1. 크로스 레포 컨텍스트 수집
    cross_repo_context = collect_cross_repo_context()
    print(f"\n크로스 레포 컨텍스트 수집 완료 ({len(cross_repo_context)} chars)")

    # 2. 로그 매니페스트 수집
    log_manifest = collect_log_manifest()
    print(f"로그 매니페스트 수집 완료 ({len(log_manifest)} chars)")

    # 3. 서기에이전트 생성
    llm = get_llm(HIGH_PERF_MODEL)

    secretary = Agent(
        role="서기관리 에이전트 (Meeting Secretary)",
        goal="프로젝트의 Crew 실행 로그를 분석하여 구조화된 회의록을 작성하고, "
             "3개 레포(web/server/orchestrator)의 진행 상황을 종합하여 "
             "노션 '에이전트 회의록' 페이지에 기록한다.",
        backstory="6년차 테크니컬 라이터 겸 프로젝트 코디네이터. "
                  "'기록되지 않은 회의는 없었던 회의와 같다'는 신념. "
                  "모든 Crew 실행을 하나의 회의로 간주하여 참석자(에이전트), "
                  "안건(태스크), 논의 내용, 결정사항, 산출물을 체계적으로 정리한다. "
                  "또한 3개 레포의 git 이력과 CLAUDE.md를 교차 검토하여 "
                  "프로젝트 전체 진행 상황을 파악하고 회의록에 반영한다.",
        llm=llm,
        tools=[
            list_directory,
            list_directory_recursive,
            read_file,
            list_notion_pages,
            read_notion_page,
            read_notion_page_full,
            append_to_notion_page,
            search_notion_blocks,
            update_notion_block,
            delete_notion_block,
            insert_after_notion_block,
        ],
        allow_delegation=False,
        verbose=True,
    )

    # 4. Task 1: 로그 분석 → 회의록 작성
    t1_analyze = Task(
        description=f"""
        에이전트 Crew 실행 로그를 분석하여 구조화된 회의록을 작성한다.
        또한 3개 레포의 컨텍스트를 검토하여 프로젝트 전체 현황을 파악한다.

        [로그 파일 목록]
        {log_manifest}

        [3개 레포 컨텍스트]
        {cross_repo_context}

        [작업 지시]

        1. **로그 분석**: `read_file` 도구로 각 로그 파일을 읽어서 다음을 추출한다:
           - 회의 일시 (CREW_START 타임스탬프)
           - 참석자 (어떤 에이전트가 참여했는지)
           - 안건 (어떤 태스크를 수행했는지)
           - 주요 논의/행동 (에이전트가 어떤 도구를 사용하고 어떤 분석을 했는지)
           - 결정사항/산출물 (AGENT_OUTPUT에서 핵심 결론)
           - 로그 파일 경로는 `logs/파일명`으로 지정한다

        2. **크로스 레포 현황 정리**: 위 컨텍스트를 기반으로
           - 각 레포의 최근 주요 변경사항 (git 커밋 기반)
           - 레포 간 연동 상태 (예: orchestrator 설계 → web 구현 반영 여부)
           - 현재 진행 중인 작업과 블로커

        3. **회의록 구조화**: 아래 형식으로 마크다운 문서를 작성한다

        [출력 형식]
        # 에이전트 회의록

        ## 프로젝트 현황 요약 (3개 레포)
        - **orchestrator**: (최근 주요 활동 요약)
        - **web**: (최근 주요 활동 요약)
        - **server**: (현재 상태)

        ## 회의 기록

        ### 회의 #N: [Crew 이름] — YYYY-MM-DD HH:MM
        - **참석자**: (에이전트 이름들)
        - **안건**: (수행한 태스크 요약)
        - **주요 논의**:
          - (에이전트가 수행한 핵심 분석/행동)
        - **결정사항**:
          - (핵심 결론 1~2줄)
        - **산출물**: (생성된 파일명)

        (시간순으로 모든 회의 기록)

        ## 레포 간 연동 현황
        - (orchestrator 설계 → web 구현 추적)

        [주의사항]
        - 각 Crew 실행을 하나의 '회의'로 취급한다
        - 시간순(오래된 것부터)으로 정렬한다
        - 로그가 길면 핵심만 추출한다 (전체를 복사하지 않는다)
        - 3개 레포의 git 커밋을 교차 참조하여 연동 상태를 분석한다
        """,
        expected_output="구조화된 에이전트 회의록 마크다운. 시간순 회의 기록 + 3개 레포 현황 포함.",
        agent=secretary,
        output_file="output/meeting-notes.md",
    )

    # 5. Task 2: 노션에 구조화하여 기록
    t2_notion_sync = Task(
        description=f"""
        회의록을 노션 '에이전트 회의록' 페이지에 기록한다.

        [작업 순서]
        1. `read_notion_page` 도구로 '에이전트 회의록' 페이지의 현재 내용을 확인한다
        2. 기존 내용이 있으면 `search_notion_blocks`로 각 섹션 블록을 찾아 삭제한다
           (단, 페이지 첫 번째 설명 단락은 유지한다)
        3. 이전 태스크에서 작성한 회의록 내용을 `append_to_notion_page` 도구로 기록한다

        [노션 기록 구조]
        아래 구조로 기록한다:

        ---
        ## 프로젝트 현황 요약 (3개 레포)
        (각 레포별 현황)

        ## 회의 기록
        (시간순 회의 목록)

        ## 레포 간 연동 현황
        (크로스 레포 추적)

        ---
        마지막 동기화: YYYY-MM-DD HH:MM
        ---

        [주의사항]
        - 노션 API의 rich_text 제한(2000자)을 고려하여 긴 내용은 분할 전송한다
        - 대상 페이지: '에이전트 회의록'
        - 테이블보다는 불릿 리스트가 Notion API 호환성이 높으므로 불릿 리스트를 사용한다
        - 회의가 많으면 최근 것 위주로 정리하되, 모든 회의를 포함한다
        """,
        expected_output="노션 '에이전트 회의록' 페이지에 구조화된 회의록이 기록됨.",
        agent=secretary,
        context=[t1_analyze],
    )

    crew = Crew(
        agents=[secretary],
        tasks=[t1_analyze, t2_notion_sync],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    print(f"\n{'=' * 60}")
    print("에이전트 회의록 동기화 완료")
    print(f"  로컬: output/meeting-notes.md")
    print(f"  노션: 에이전트 회의록 페이지")
    print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    main()
