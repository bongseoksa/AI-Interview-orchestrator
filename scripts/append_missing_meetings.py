"""누락된 회의 4건을 에이전트 회의록에 추가 — 서기에이전트

실행: python scripts/append_missing_meetings.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import read_file
from src.tools.notion_tools import (
    read_notion_page,
    read_notion_page_full,
    append_to_notion_page,
    search_notion_blocks,
    insert_after_notion_block,
)


def main():
    print("=" * 60)
    print("누락된 회의 4건 추가 — 서기에이전트")
    print("=" * 60)

    llm = get_llm(HIGH_PERF_MODEL)

    secretary = Agent(
        role="서기관리 에이전트 (Meeting Secretary)",
        goal="누락된 4개 Crew 실행 로그를 분석하여 기존 회의록에 추가한다.",
        backstory="6년차 테크니컬 라이터. 누락된 회의 기록을 보완하여 완전한 회의록을 유지한다. "
                  "기존 회의록의 형식과 동일한 구조로 작성한다.",
        llm=llm,
        tools=[
            read_file,
            read_notion_page,
            read_notion_page_full,
            append_to_notion_page,
            search_notion_blocks,
            insert_after_notion_block,
        ],
        allow_delegation=False,
        verbose=True,
    )

    t1_analyze = Task(
        description="""
        아래 4개의 누락된 로그 파일을 `read_file` 도구로 읽고, 각각의 회의록을 작성한다.

        [누락된 로그 파일 4개]
        1. `logs/design-m5-m6.log.txt` — M5/M6 설계 합동 회의 (5명 에이전트)
        2. `logs/crew_20260718_013222.log` — M5/M6 리뷰 회의 (PM + PjM + 외부인사)
        3. `logs/crew_20260718_103908.log` — 코드 리뷰 회의 (QA + FE 시니어)
        4. `logs/crew_20260718_125642.log` — 산출물 레지스트리 동기화 회의 (서기에이전트)

        [작업 지시]
        1. 각 로그 파일을 `read_file`로 읽는다
        2. 로그에서 다음을 추출한다:
           - 회의 일시 (CREW_START 또는 첫 타임스탬프)
           - 참석자 (AGENT_START에 나오는 에이전트 이름들)
           - 안건 (TASK_START에 나오는 태스크 설명)
           - 주요 논의 (에이전트가 수행한 핵심 분석/도구 사용)
           - 결정사항 (AGENT_OUTPUT/AGENT_DONE에서 핵심 결론 1~2줄)
           - 산출물 (생성된 파일명)
        3. 기존 회의록(#1~#7)에 이어서 #8~#11로 번호를 매긴다
        4. 시간순으로 정렬한다

        [출력 형식 — 기존 회의록과 동일한 구조]
        ### 회의 #N: [Crew/스크립트 이름] — YYYY-MM-DD HH:MM
        - **참석자**: (에이전트 이름들)
        - **안건**: (수행한 태스크 요약)
        - **주요 논의**:
          - (핵심 분석/행동)
        - **결정사항**:
          - (핵심 결론)
        - **산출물**: (파일명)

        [주의사항]
        - 로그 전체를 복사하지 말고, 핵심만 추출한다
        - design-m5-m6.log.txt는 CrewExecutionLogger가 아닌 다른 형식이므로 task_name과 타임스탬프로 파악한다
        - 시간순 정렬: crew_20260718_013222 → crew_20260718_103908 → design-m5-m6 → crew_20260718_125642
        """,
        expected_output="누락된 4개 회의의 구조화된 회의록. #8~#11 번호, 시간순.",
        agent=secretary,
    )

    t2_notion_append = Task(
        description="""
        이전 태스크에서 작성한 누락 회의 4건을 노션 '에이전트 회의록' 페이지에 추가한다.

        [작업 순서]
        1. `read_notion_page` 도구로 '에이전트 회의록' 페이지의 현재 내용을 확인한다
        2. `search_notion_blocks` 도구로 '레포 간 연동 현황' 블록을 찾는다
        3. 그 블록 바로 앞(즉, 회의 #7 이후)에 4개 회의록을 삽입해야 한다
           - `search_notion_blocks`로 '회의 #7' 블록을 찾는다
           - 회의 #7의 마지막 항목(산출물) 블록 ID를 찾는다
           - `insert_after_notion_block`으로 회의 #7 산출물 블록 뒤에 4개 회의록을 삽입한다
        4. 삽입이 어려우면 `append_to_notion_page`로 페이지 끝에 추가한다

        [주의사항]
        - 기존 내용을 삭제하지 않는다 — 추가만 한다
        - 대상 페이지: '에이전트 회의록'
        - 불릿 리스트 형식 사용
        - rich_text 2000자 제한 주의, 긴 내용은 분할 전송
        """,
        expected_output="노션 '에이전트 회의록' 페이지에 누락된 4개 회의가 추가됨.",
        agent=secretary,
        context=[t1_analyze],
    )

    crew = Crew(
        agents=[secretary],
        tasks=[t1_analyze, t2_notion_append],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    print(f"\n{'=' * 60}")
    print("누락 회의 4건 추가 완료")
    print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    main()
