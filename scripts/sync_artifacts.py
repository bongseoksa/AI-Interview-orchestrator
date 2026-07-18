"""산출물 레지스트리 동기화 — 서기에이전트가 로컬 산출물을 스캔하고 노션에 구조화

CLAUDE.md 규칙: 노션 문서 작성은 서기에이전트 경유 필수
실행: python main.py artifacts
"""

import sys
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
ARTIFACT_PAGE = "산출물 레지스트리"


def build_local_manifest() -> str:
    """logs/, output/, scripts/ 파일 목록을 수집하여 매니페스트 문자열 생성."""
    manifest_lines = []

    for dirname in ["output", "logs", "scripts"]:
        dirpath = PROJECT_ROOT / dirname
        if not dirpath.exists():
            continue
        manifest_lines.append(f"\n### {dirname}/")
        files = sorted(dirpath.iterdir())
        for f in files:
            if f.is_file() and not f.name.startswith(".") and f.name != "__pycache__":
                size_kb = f.stat().st_size / 1024
                mtime = f.stat().st_mtime
                from datetime import datetime
                modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                manifest_lines.append(
                    f"- `{f.name}` ({size_kb:.1f}KB, {modified})"
                )

    return "\n".join(manifest_lines)


def main():
    print("=" * 60)
    print("산출물 레지스트리 동기화 — 서기에이전트")
    print("=" * 60)

    # 1. 로컬 매니페스트 수집 (Python으로 빠르게)
    manifest = build_local_manifest()
    print(f"\n로컬 매니페스트 수집 완료 ({len(manifest)} chars)")

    # 2. 서기에이전트 생성
    llm = get_llm(HIGH_PERF_MODEL)

    secretary = Agent(
        role="서기관리 에이전트 (Documentation Secretary)",
        goal="프로젝트의 로컬 산출물(output/, logs/, scripts/)을 체계적으로 분류하고, "
             "노션 '산출물 레지스트리' 페이지에 구조화된 형태로 기록한다.",
        backstory="6년차 테크니컬 라이터 겸 프로젝트 코디네이터. "
                  "'기록되지 않은 산출물은 존재하지 않는 것과 같다'는 신념. "
                  "모든 Crew 실행 결과를 분류하고, 핵심 내용을 요약하여 "
                  "프로젝트 이해관계자가 빠르게 파악할 수 있도록 정리한다. "
                  "현재 AI Interview 프로젝트의 오케스트레이터 산출물을 관리하고 있다.",
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

    # 3. Task 1: 산출물 분류 및 요약
    t1_classify = Task(
        description=f"""
        아래 로컬 파일 매니페스트를 분석하여 산출물 레지스트리를 작성한다.

        [로컬 파일 매니페스트]
        {manifest}

        [분류 기준]
        산출물을 아래 카테고리로 분류한다:

        1. **설계 산출물 (Design Artifacts)** — output/ 중 설계 관련
           - Step별 산출물 (step1-*, step2-*, step3-*, step4-*)
           - 마일스톤별 설계 (design-*, frontend-*, data-*)
           - 아키텍처/인프라 (infra-*, qa-*)

        2. **리뷰 산출물 (Review Artifacts)** — output/ 중 리뷰/감사
           - 코드 리뷰 (code-review-*)
           - 외부 리뷰 (review-*, m5-m6-*)
           - 문서 감사 (doc-*, spec-*)

        3. **실행 로그 (Execution Logs)** — logs/
           - Crew별 실행 기록

        4. **유틸리티 스크립트 (Scripts)** — scripts/
           - 설계 스크립트 (design_*)
           - 동기화/유틸 (sync_*, audit_*, generate_*, translate_*)
           - 테스트 (test_*, verify_*)

        [작업 지시]
        1. 각 파일의 내용을 `read_file` 도구로 읽어서 핵심 내용을 1~2줄로 요약한다
           - output/ 파일은 반드시 읽고 요약한다
           - logs/ 파일은 파일명과 날짜로 실행 기록만 정리한다
           - scripts/ 파일은 파일명과 용도만 정리한다
        2. 카테고리별로 정리한 마크다운 레지스트리를 작성한다

        [출력 형식]
        마크다운 문서. 카테고리별 테이블 형식:
        | 파일명 | 생성 Crew | 핵심 내용 요약 | 날짜 |
        """,
        expected_output="산출물 레지스트리 마크다운. 카테고리별 분류, 파일별 요약 포함.",
        agent=secretary,
        output_file="output/artifact-registry.md",
    )

    # 4. Task 2: 노션 페이지에 구조화하여 기록
    t2_notion_sync = Task(
        description=f"""
        산출물 레지스트리를 노션 '산출물 레지스트리' 페이지에 기록한다.

        [작업 순서]
        1. 먼저 `read_notion_page` 도구로 '산출물 레지스트리' 페이지의 현재 내용을 확인한다
        2. 기존 내용이 있으면 `search_notion_blocks`로 각 섹션 블록을 찾아 `delete_notion_block`으로 삭제한다
           (단, 페이지 첫 번째 설명 단락은 유지한다)
        3. 이전 태스크에서 작성한 레지스트리 내용을 `append_to_notion_page` 도구로 기록한다

        [노션 기록 형식]
        아래 구조로 기록한다:

        ---
        ## 설계 산출물 (Design Artifacts)
        (테이블 또는 목록)

        ## 리뷰 산출물 (Review Artifacts)
        (테이블 또는 목록)

        ## 실행 로그 (Execution Logs)
        (테이블 또는 목록)

        ## 유틸리티 스크립트 (Scripts)
        (테이블 또는 목록)

        ---
        마지막 동기화: YYYY-MM-DD HH:MM
        ---

        [주의사항]
        - 노션 API의 rich_text 제한(2000자)을 고려하여 긴 내용은 분할 전송한다
        - 대상 페이지: '산출물 레지스트리'
        - 테이블보다는 불릿 리스트가 Notion API 호환성이 높으므로 불릿 리스트를 사용한다
        """,
        expected_output="노션 '산출물 레지스트리' 페이지에 구조화된 산출물 목록이 기록됨.",
        agent=secretary,
        context=[t1_classify],
    )

    crew = Crew(
        agents=[secretary],
        tasks=[t1_classify, t2_notion_sync],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    print(f"\n{'=' * 60}")
    print("산출물 레지스트리 동기화 완료")
    print(f"  로컬: output/artifact-registry.md")
    print(f"  노션: 산출물 레지스트리 페이지")
    print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    main()
