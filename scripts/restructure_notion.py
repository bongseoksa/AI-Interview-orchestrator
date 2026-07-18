"""노션 페이지 전체 재구성 — 서기에이전트 + PM 협업

목적: 현재 노션 구조를 '각 직군이 진행/완료 상태를 명확히 인지할 수 있는' 구조로 재구성
참여 에이전트: 서기관리(구조 설계+콘텐츠 작성), PM(직군별 접근성 검증)

실행: source .venv/bin/activate && python scripts/restructure_notion.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory_recursive, read_file, write_file
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

# === 현재 노션 구조 + 문제점 + 목표 구조 컨텍스트 ===
RESTRUCTURE_CONTEXT = """
[현재 노션 구조 — 10개 페이지, 3-depth]
AI Interview (허브) — 3a0141f8-c327-80eb-ba18-d9637ff76f63
├── 기획서 — 3a0141f8-c327-81fe-bfbf-e35fd03e8c19
│   └── 시드 데이터 뱅크 — 3a0141f8-c327-81a8-9d4e-e9aaeb3665a3
├── 사업계획서 — 3a0141f8-c327-8186-9810-c8c025aa943b
│   ├── 에이전트 조직 구조 — 3a0141f8-c327-81e1-8d29-d4698f6e6161
│   └── 의사결정 기록 — 3a0141f8-c327-81fd-8884-e1a9447b1fc0
├── 프로젝트 진행 가이드 — 3a0141f8-c327-81ba-9d0e-e7444b9d2df8
│   ├── Step 1. 시장 조사 보고서 — 3a0141f8-c327-8189-8d69-dbc5531fff9a
│   ├── Step 2. PRD — 3a0141f8-c327-8111-a9bd-f62a1d4a92b9
│   ├── Step 3. Handoff 계획 — 3a0141f8-c327-8153-bd9f-ce64916fda71
│   └── 산출물 레지스트리 — 3a1141f8-c327-8166-8e33-dcdabdeb5dd1
└── 에이전트 회의록 — 3a1141f8-c327-8192-b8a9-f79376f12139

[핵심 문제점]
1. 직군별 탐색 불가: PM이 다음 액션을 알려면 3개 페이지를 넘나들어야 함
2. 정보 중복: 기술 스택이 사업계획서/기획서/PRD/Handoff 4곳에 반복
3. 용어 혼재: "Step" vs "Phase" 혼용
4. 레포 정보 부재: 3개 레포의 온보딩/구조/주요 기능이 노션에 없음
5. 산출물 미반영: output/ 37개 산출물 vs 노션 레지스트리 미동기화
6. 사업계획서 과부하: 사업 현황+레포+기술 스택+모델 전략+로드맵이 한 페이지에
7. Handoff 역할 불명확: 사실상 전체 진행 추적 + 체크리스트로 진행가이드와 중복

[목표 구조 — 5개 섹션, 15개 페이지]
AI Interview (프로젝트 허브) — 경량 대시보드 (프로젝트 개요 + Phase별 현황 + 직군별 접근 가이드)
│
├── 기획 & 제품 (섹션)
│   ├── 기획서 — 기존 페이지 유지, 내용 경량화 (기술 스택 중복 제거)
│   ├── PRD — 기존 페이지 유지 (진행가이드 하위에서 이동)
│   └── 시장 조사 보고서 — 기존 페이지 유지 (진행가이드 하위에서 이동)
│
├── 설계 & 아키텍처 (섹션)
│   ├── 기술 스택 & AI 모델 전략 — 신규 (사업계획서의 기술 부분 이관, SSOT)
│   ├── 에이전트 조직 구조 — 기존 페이지 유지 (사업계획서 하위에서 이동)
│   └── 시드 데이터 뱅크 — 기존 페이지 유지 (기획서 하위에서 이동)
│
├── 레포지토리 (섹션) — 신규
│   ├── AI-Interview-web — 신규 (CLAUDE.md/ONBOARDING.md 기반)
│   ├── AI-Interview-server — 신규 (CLAUDE.md/ONBOARDING.md 기반)
│   └── AI-Interview-orchestrator — 신규 (CLAUDE.md/ONBOARDING.md 기반)
│
├── 프로젝트 진행 (섹션)
│   ├── Phase별 마일스톤 & 체크리스트 — 기존 진행가이드+Handoff 통합
│   ├── 산출물 레지스트리 — 기존 페이지 유지, 내용 최신화
│   └── 의사결정 기록 — 기존 페이지 유지 (사업계획서 하위에서 이동)
│
└── 회의록 (섹션)
    └── 에이전트 회의록 — 기존 페이지 유지

[삭제 대상]
- 사업계획서: 기술 부분 → "기술 스택 & AI 모델 전략", 사업 현황 → 허브 개요. 나머지 이관 후 삭제
- Step 3. Handoff 계획: "Phase별 마일스톤 & 체크리스트"로 통합 후 삭제

[3개 레포 정보 — 레포지토리 페이지 작성에 사용]

== AI-Interview-web ==
- 기술 스택: Next.js 16.2.10, TypeScript 5.9.3, React 19.2.3, Tailwind CSS 3.4.19, shadcn/ui, Zustand 5.0.10, TanStack Query 5.90.19, RHF 7.71.1, Zod 4.3.5, pnpm 10.17.1
- i18n: next-intl 4.x (ko/en), URL prefix 라우팅
- DB: Supabase (PostgreSQL + Auth)
- 주요 페이지: /, /dashboard, /diagnosis, /learn/[category]/[slug], /learn/map
- 컴포넌트: 21개 (auth, common, diagnosis, learn, ui)
- 서브에이전트: FE시니어, QA, 서기 (3개)
- 현재 상태: Phase 4 구현 중 (M1~M6 완료, P0 기능 7개 확정)

== AI-Interview-server ==
- 기술 스택: Python 기반 (TBD — FastAPI vs Django 미정)
- DB: Supabase Free (PostgreSQL)
- 현재 상태: 스켈레톤 (코드 없음, 문서만 존재)
- 서브에이전트: BE시니어, 데이터엔지니어, QA (3개)
- 다음: Step 6 아키텍처 설계 후 구현 시작

== AI-Interview-orchestrator ==
- 기술 스택: Python 3.13, CrewAI v1.15.4, Ollama (Gemma 4 26B/12B)
- 11 Crew (13 에이전트): Research, Planning, Architect, Frontend, QA, Infra, Data, Documentation, Review, Codegen, NotionEdit
- 산출물: output/ 37개 파일 (설계 16, 리뷰 11, 로그 12+)
- 스크립트: scripts/ 18개
- 서브에이전트: 전략관리자, PM, PjM, 풀스택아키텍트, 인프라, 서기, 외부인사 (7개)
- 현재 상태: 11 Crew 전체 구현 완료, 모든 테스트 통과

[직군별 접근 가이드 — 허브 페이지에 포함]
- PM: 기획 & 제품 → 기획서, PRD
- PjM: 프로젝트 진행 → Phase별 마일스톤
- 풀스택 아키텍트: 설계 & 아키텍처, 레포지토리
- FE 시니어: 레포지토리 → web
- BE 시니어: 레포지토리 → server
- QA: 프로젝트 진행 → 산출물 (테스트 케이스)
- 데이터 엔지니어: 설계 & 아키텍처 → 시드 데이터 뱅크
- 인프라: 설계 & 아키텍처 → 기술 스택
- 서기관리: 전체 (정합성 감사), 회의록
- 외부인사: 기획 & 제품 (리뷰), 프로젝트 진행 (리스크)
"""

# === 에이전트 정의 ===
llm = get_llm(HIGH_PERF_MODEL)

doc_secretary = Agent(
    role="서기관리 에이전트 (Documentation Secretary)",
    goal="노션 페이지 구조를 재구성하여 각 직군이 진행/완료 상태를 명확히 파악할 수 있도록 한다",
    backstory=(
        "6년차 테크니컬 라이터. 대규모 프로젝트의 문서 체계를 여러 차례 재구성한 경험이 있다. "
        "'문서 구조가 업무 효율을 결정한다'는 신념으로, 각 직군이 필요한 정보를 "
        "1-2번의 클릭으로 찾을 수 있는 구조를 설계한다."
    ),
    llm=llm,
    tools=[
        list_directory_recursive, read_file, write_file,
        list_notion_pages, read_notion_page, read_notion_page_full,
        append_to_notion_page, search_notion_blocks,
        update_notion_block, delete_notion_block, insert_after_notion_block,
    ],
    allow_delegation=False,
    verbose=True,
)

pm_agent = Agent(
    role="프로덕트 매니저 (Product Manager)",
    goal="재구성된 노션 구조가 각 직군의 업무 흐름에 최적화되어 있는지 검증한다",
    backstory=(
        "8년차 프로덕트 매니저. 다양한 직군이 참여하는 프로젝트에서 "
        "'정보 접근성'이 생산성의 핵심 병목임을 경험으로 알고 있다. "
        "각 직군이 '내가 다음에 뭘 해야 하지?'를 즉시 알 수 있어야 한다."
    ),
    llm=llm,
    tools=[read_file, list_notion_pages, read_notion_page],
    allow_delegation=False,
    verbose=True,
)

# === 태스크 정의 ===

task1_audit = Task(
    description=f"""현재 노션 페이지를 전체 읽고, 목표 구조와 비교하여 재구성 계획을 수립한다.

{RESTRUCTURE_CONTEXT}

[수행 사항]
1. 노션의 기존 페이지를 모두 읽어 현재 내용을 파악한다 (list_notion_pages → read_notion_page로 각 페이지 읽기)
2. 3개 레포의 CLAUDE.md와 ONBOARDING.md를 읽는다:
   - /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-web/CLAUDE.md
   - /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-web/ONBOARDING.md
   - /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-server/CLAUDE.md
   - /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-server/ONBOARDING.md
   - /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-orchestrator/CLAUDE.md
   - /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-orchestrator/ONBOARDING.md
3. 각 기존 페이지의 내용이 목표 구조의 어느 페이지로 이관되는지 매핑표를 작성한다
4. 신규 페이지 4개(기술 스택, web, server, orchestrator)의 콘텐츠 소스를 정리한다
5. 삭제 대상 2개(사업계획서, Handoff)의 내용 이관 계획을 작성한다
6. 허브 페이지의 새로운 콘텐츠(경량 대시보드 + 직군별 접근 가이드)를 설계한다

반드시 모든 노션 페이지와 레포 문서를 실제로 읽어서 정확한 내용 기반으로 작업할 것.""",
    expected_output="""재구성 계획서 (마크다운):
1. 기존 → 목표 페이지 매핑표 (내용 이관 계획)
2. 신규 페이지 4개의 콘텐츠 소스 목록
3. 삭제 대상 이관 계획
4. 허브 페이지 새 콘텐츠 설계
5. 실행 순서 (의존성 고려)""",
    agent=doc_secretary,
    output_file="output/notion-restructure-plan.md",
)

task2_content = Task(
    description=f"""재구성 계획을 기반으로, 각 페이지의 최종 콘텐츠를 마크다운으로 작성한다.

{RESTRUCTURE_CONTEXT}

[작성 대상 — 총 15개 페이지]

=== 기존 페이지 수정 (7개) ===
1. 허브 (AI Interview): 경량 대시보드로 전면 재작성
   - 프로젝트 개요 (1인 무자본, 서비스 설명)
   - Phase별 현황 (Phase 0~4 상태)
   - 직군별 접근 가이드 테이블
   - 새로운 문서 구조 트리
2. 기획서: 기술 스택 중복 제거, 모델 전략 참조로 변경
3. 에이전트 조직 구조: 내용 유지, 위치만 변경
4. 시드 데이터 뱅크: 내용 유지, 위치만 변경
5. 산출물 레지스트리: output/ 최신 목록으로 갱신
6. 의사결정 기록: 내용 유지, 위치만 변경
7. 에이전트 회의록: 내용 유지

=== 기존 페이지 통합 (2개 → 1개) ===
8. Phase별 마일스톤 & 체크리스트: 진행가이드 + Handoff 통합
   - 완료된 Phase 0~3 요약
   - Phase 4 상세 (마일스톤 M1~M6 상태, 체크리스트)
   - 다음 액션
   - 에이전트 할당 현황
   - 리스크 & 완화

=== 기존 페이지 유지 (2개) ===
9. PRD: 내용 유지, 위치만 변경
10. 시장 조사 보고서: 내용 유지, 위치만 변경

=== 신규 페이지 (4개) ===
11. 기술 스택 & AI 모델 전략: 사업계획서의 기술 부분 + 모델 전략 통합 (SSOT)
12. AI-Interview-web: web 레포 CLAUDE.md/ONBOARDING.md 기반 온보딩 정보
13. AI-Interview-server: server 레포 CLAUDE.md/ONBOARDING.md 기반 온보딩 정보
14. AI-Interview-orchestrator: orchestrator 레포 CLAUDE.md/ONBOARDING.md 기반 온보딩 정보

[작성 규칙]
- 각 페이지를 "# [페이지 제목]" 섹션으로 구분
- Notion 호환 마크다운으로 작성 (heading, bullet, table, code, quote, divider)
- 중복 금지: 하나의 정보는 한 곳에만. 다른 페이지 참조 시 "상세는 [페이지명] 참조" 형태
- "Phase"로 용어 통일 (Step 표기 제거)
- 레포 페이지는 구조, 주요 기능, 기술 스택, 실행 방법, 엣지 케이스 포함
- 위치 변경만 되는 페이지는 "위치 변경만 — 내용 동일" 으로 표기

반드시 레포의 CLAUDE.md, ONBOARDING.md를 실제로 읽어서 정확한 내용 기반으로 작성할 것.
기존 노션 페이지도 read_notion_page로 읽어서 기존 내용을 기반으로 작성할 것.""",
    expected_output="""15개 페이지의 최종 콘텐츠 (마크다운). 각 페이지는 "# [페이지 제목]" 으로 구분.
신규 페이지 4개는 완전한 콘텐츠, 수정 페이지는 변경된 부분만, 위치 변경 페이지는 "위치 변경만" 표기.""",
    agent=doc_secretary,
    context=[task1_audit],
    output_file="output/notion-restructure-content.md",
)

task3_review = Task(
    description=f"""서기에이전트가 작성한 재구성 계획과 콘텐츠를 직군별 접근성 관점에서 검증한다.

{RESTRUCTURE_CONTEXT}

[검증 항목]
1. 각 직군(PM, PjM, 아키텍트, FE, BE, QA, 데이터, 인프라, 서기, 외부인사)이
   자기 역할에 필요한 정보를 1-2번 클릭으로 찾을 수 있는가?
2. "다음에 뭘 해야 하지?"를 즉시 알 수 있는 구조인가?
3. 정보 중복이 제거되었는가? (SSOT 원칙)
4. 누락된 정보는 없는가?
5. 레포지토리 페이지가 실제 온보딩에 충분한 정보를 담고 있는가?

[출력]
- 검증 결과 (Pass/Fail + 사유)
- 개선 제안 (있다면)
- 최종 승인 여부""",
    expected_output="""검증 보고서: 직군별 접근성 Pass/Fail, SSOT 준수 여부, 누락 항목,
개선 제안, 최종 승인 여부를 포함한 마크다운 보고서.""",
    agent=pm_agent,
    context=[task1_audit, task2_content],
    output_file="output/notion-restructure-review.md",
)

# === Crew 실행 ===
crew = Crew(
    agents=[doc_secretary, pm_agent],
    tasks=[task1_audit, task2_content, task3_review],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("노션 페이지 전체 재구성 — 서기에이전트 + PM 협업")
    print("=" * 60)
    print(f"모델: {HIGH_PERF_MODEL}")
    print("태스크: 1) 현황 분석 + 재구성 계획 → 2) 콘텐츠 작성 → 3) PM 검증")
    print("=" * 60)
    result = crew.kickoff(inputs={"topic": "노션 페이지 전체 재구성"})
    print("\n" + "=" * 60)
    print("완료! 산출물:")
    print("  - output/notion-restructure-plan.md (재구성 계획)")
    print("  - output/notion-restructure-content.md (페이지 콘텐츠)")
    print("  - output/notion-restructure-review.md (PM 검증)")
    print("=" * 60)
