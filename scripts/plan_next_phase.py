"""다음 작업 방향성 논의 — PM + PjM + 외부인사 3자 회의

목적: 현재 프로젝트 상태를 진단하고, 다음 작업 방향성 및 실행 계획을 수립한다.
참여 에이전트: PM(제품 전략), PjM(실행 계획), 외부인사(리스크 검증)

실행: source .venv/bin/activate && python scripts/plan_next_phase.py
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
)

# === 현재 프로젝트 상태 컨텍스트 ===
PROJECT_STATUS = """
[프로젝트: AI Interview]
프론트엔드 엔지니어를 위한 AI 기반 모의 인터뷰 연습 서비스.
운영: 무자본 1인 개인, 무료 서비스만 활용.

[완료된 Phase]
- Phase 0: 에이전트 시스템 구축 ✅ (11 Crew, 문서 관리 체계)
- Phase 1: 시장 조사 및 PRD 확정 ✅ (경쟁사 15개 분석, PRD 10섹션)
- Phase 2: 설계 및 아키텍처 ✅ (DB 스키마, API 구조, ADR 4건)
- Phase 3: 데이터 및 인프라 준비 ✅ (시드 데이터 151개, RLS 정책, CI/CD)

[현재 Phase: Phase 4 (MVP 핵심 기능 구현)]
| Milestone | Task | Status |
|-----------|------|--------|
| M1 | DB & Seed Data Setup | ✅ Done |
| M2 | Landing/Dashboard/학습 UI (SSG 151p) | ✅ Done |
| M3 | 메타인지 진단 (9개 카테고리) | ✅ Done |
| M4 | MVP P0 기능 확정 (7개) | ✅ Done |
| M5 | 프로그레스 트래킹 (Auth + user_progress) | ✅ Done (의사결정 기록 기준) |
| M6 | AI 요약/팁 (Default Tip 151개 생성 완료) | ✅ Done (의사결정 기록 기준) |

[문제: 노션 마일스톤 페이지에서 M5/M6가 아직 "🔲 대기"로 표시됨 — 의사결정 기록과 불일치]

[P0 기능 완료 현황 (의사결정 기록 기준)]
1. 커리큘럼 대시보드 (9개 카테고리 + 상태 시각화) ✅
2. 개념 학습 모듈 (SSG 151개 페이지) ✅
3. 메타인지 진단 (카테고리당 1개 질문, 결과 리포트) ✅
4. 랜딩 페이지 ✅
5. Supabase Auth + 지연 로그인 (Lazy Auth) ✅ M5
6. 프로그레스 트래킹 (user_progress 실시간 반영) ✅ M5
7. Default Tip (정적 면접 팁 151개) ✅ M6

[문서 감사 결과 (서기에이전트, 2026-07-18)]
- Critical: pyproject.toml Python 버전(>=3.11) vs CLAUDE.md/ONBOARDING.md(3.13) 불일치
- Warning: 인라인 에이전트(Codegen, NotionEdit) 표기 명확화 필요
- Pass: AI 모델 전략, CrewAI 버전, Phase 정의 정합

[산출물 레지스트리 이슈]
- 노션 산출물 레지스트리의 "마지막 동기화: 2024-05-23" — 날짜 오류(2026년이어야 함)
- 산출물명에 여전히 "step" 접두사 사용 (step1-market-research.md 등)
- 일부 에이전트명 오기입 (Codoggen → Codegen 등)

[의사결정 기록 이슈]
- 여전히 "Step" 용어 사용 중 — Phase로 통일 필요
- "9개 Crew" → "11개 Crew"로 갱신 필요한 부분 존재

[외부인사 기존 리스크 지적 (2026-07-18)]
1. Lazy Auth 역설 — 미인증 학습 진도 유실 리스크
2. ChatGPT 대비 차별성 부족 — 정적 팁 2~3문장의 한계
3. 해자 부재 — 복제 가능한 구조, 데이터 독점성 없음
4. 수익 모델 부재 — 성공할수록 손해 구조
5. AI 할루시네이션 — 기술 면접 서비스에서 틀린 정보는 치명적
6. 인프라 스케일링 — Supabase Free Tier 한계

[Future Phases (노션 기준)]
- Phase 5: AI 모의 면접 MVP (면접 설정, AI 면접 진행, 답변 피드백)
- Phase 6: 고도화 (회원가입/로그인, 히스토리, 꼬리질문, 성과 통계)
- Phase 7: 확장 (음성 기반 면접, 다국어, 행동/소프트 면접, 시스템 설계)

[기술 현황]
- web: Next.js 16, TypeScript, Tailwind CSS, shadcn/ui, Supabase (Auth+DB), i18n(ko/en)
- server: Python (미착수, Phase 6 이후)
- orchestrator: CrewAI v1.15.4, Ollama (Gemma 4 26B/12B), 11 Crew 구현 완료
"""

# === 에이전트 정의 ===
llm = get_llm(HIGH_PERF_MODEL)

pm = Agent(
    role="프로덕트 매니저 (Product Manager)",
    goal="Phase 4 완료 판정과 다음 Phase의 제품 전략 방향을 결정한다",
    backstory=(
        "8년차 프로덕트 매니저. EdTech 스타트업에서 0→1 제품 런칭을 3회 성공. "
        "'MVP는 완벽함이 아니라 학습 가능성이다'라는 원칙으로, "
        "최소한의 기능으로 최대한의 사용자 피드백을 얻는 전략을 설계한다. "
        "시장 데이터와 사용자 피드백 기반의 의사결정을 중시한다."
    ),
    llm=llm,
    tools=[read_file, read_notion_page, list_notion_pages],
    allow_delegation=False,
    verbose=True,
)

pjm = Agent(
    role="프로젝트 매니저 (Project Manager)",
    goal="Phase 4 완료 체크리스트를 검증하고, 다음 Phase의 실행 계획(마일스톤, 태스크, 일정)을 수립한다",
    backstory=(
        "7년차 프로젝트 매니저. 애자일 스크럼 마스터 자격 보유. "
        "'진행 상태가 불분명한 프로젝트는 이미 실패한 프로젝트'라는 원칙으로 "
        "모든 태스크를 명확한 DoD(Definition of Done)와 함께 정의한다. "
        "의존성 관리와 블로커 조기 식별에 탁월하다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive, read_notion_page, list_notion_pages],
    allow_delegation=False,
    verbose=True,
)

advisor = Agent(
    role="외부인사 (External Advisor)",
    goal="제안된 계획의 리스크와 실현 가능성을 비판적으로 검증한다",
    backstory=(
        "15년차 스타트업 자문위원 겸 엔젤 투자자. 100개 이상의 MVP를 리뷰한 경험. "
        "'아이디어는 가치가 없고, 실행만이 가치를 만든다'는 원칙으로 "
        "현실적인 실행 가능성과 시장 적합성을 냉정하게 평가한다. "
        "호의적이지 않으며, Devil's Advocate 역할을 충실히 수행한다."
    ),
    llm=llm,
    tools=[read_file, read_notion_page],
    allow_delegation=False,
    verbose=True,
)

# === 태스크 정의 ===

task1_pm_strategy = Task(
    description=f"""현재 프로젝트 상태를 분석하고, Phase 4 완료 판정 + 다음 작업 방향성을 제시한다.

{PROJECT_STATUS}

[수행 사항]
1. Phase 4 완료 판정:
   - P0 기능 7개가 모두 완료되었는가?
   - MVP 런칭이 가능한 상태인가?
   - 런칭 전 해야 할 작업이 남아있는가? (테스트, 배포, 도메인 등)

2. 다음 작업 우선순위 결정:
   - 노션 정합성 이슈 해소 (M5/M6 상태 갱신, Step→Phase, 산출물 레지스트리)
   - Phase 4 런칭 준비 (배포, 테스트, 모니터링)
   - Phase 5 진입 (AI 모의 면접)
   - 기존 외부인사 리스크 대응

3. 제품 전략 방향:
   - MVP 런칭 후 첫 사용자 피드백을 어떻게 수집할 것인가?
   - Phase 5(AI 면접)로 바로 갈 것인가, Phase 4 고도화를 먼저 할 것인가?
   - 1인 개발 제약 하에서 현실적인 다음 3개월 로드맵

Notion 페이지를 직접 읽어서 최신 상태를 확인할 것:
- 허브: read_notion_page("메인")
- 마일스톤: read_notion_page("마일스톤")
- 의사결정 기록: read_notion_page("의사결정 기록")""",
    expected_output="""제품 전략 보고서:
1. Phase 4 완료 판정 (Go/No-Go + 근거)
2. 즉시 해야 할 작업 목록 (우선순위별)
3. 다음 3개월 로드맵 (1인 개발 현실 반영)
4. MVP 런칭 전략 (배포, 피드백 수집, 성공 지표)""",
    agent=pm,
    output_file="output/next-phase-pm-strategy.md",
)

task2_pjm_plan = Task(
    description=f"""PM의 전략을 기반으로, 구체적인 실행 계획(마일스톤, 태스크, 체크리스트)을 수립한다.

{PROJECT_STATUS}

[수행 사항]
1. Phase 4 완료 체크리스트 작성:
   - 노션 정합성 이슈 해소 태스크 목록
   - 런칭 준비 태스크 목록 (배포, 환경변수, DNS, 모니터링)
   - DoD(Definition of Done) 정의

2. 다음 Phase 마일스톤 분해:
   - PM이 제안한 방향에 따라 구체적 마일스톤/태스크로 분해
   - 각 태스크별 담당 에이전트 할당
   - 의존성 맵 작성
   - 예상 소요 기간 (1인 개발 기준)

3. 블로커 및 리스크 식별:
   - 기술적 블로커 (서버 미착수, LLM 미확정 등)
   - 리소스 블로커 (1인 개발, 무자본)
   - 완화 방안

4. 에이전트 활용 계획:
   - 다음 Phase에서 각 Crew를 어떤 순서로 실행할 것인가?
   - 에이전트가 자동화할 수 있는 작업 vs 수동으로 해야 하는 작업

orchestrator 레포의 output/ 디렉토리를 확인하여 기존 산출물 현황을 파악할 것:
- list_directory_recursive 사용""",
    expected_output="""실행 계획서:
1. Phase 4 완료 체크리스트 (태스크 + DoD + 담당)
2. 다음 Phase 마일스톤 분해 (M-number, 태스크, 담당, 의존성, 예상 기간)
3. 블로커 및 리스크 목록 + 완화 방안
4. 에이전트 활용 계획 (Crew 실행 순서 + 자동화 vs 수동)
5. 전체 타임라인 (주 단위)""",
    agent=pjm,
    context=[task1_pm_strategy],
    output_file="output/next-phase-pjm-plan.md",
)

task3_advisor_review = Task(
    description=f"""PM의 전략과 PjM의 실행 계획을 비판적으로 검증한다.

{PROJECT_STATUS}

[검증 기준]

1. 현실성 검증:
   - 1인 무자본 제약 하에서 제안된 계획이 실행 가능한가?
   - 타임라인이 현실적인가? (과소/과대 추정 모두 문제)
   - 숨겨진 복잡성은 없는가?

2. 전략적 검증:
   - MVP 런칭이 시장에서 의미 있는 피드백을 줄 수 있는 수준인가?
   - 경쟁사 대비 차별화가 명확한가?
   - 수익 모델 부재 상태에서 성장 전략이 유효한가?

3. 기술적 검증:
   - 서버(server 레포)가 미착수인 상태에서 AI 면접 기능(Phase 5)은 어떻게 구현할 것인가?
   - Supabase Free Tier 한계는 현실적으로 언제 문제가 되는가?
   - AI 할루시네이션 리스크는 충분히 대응되었는가?

4. 누락 검증:
   - 간과된 리스크나 작업이 있는가?
   - 에이전트 활용 계획에 비효율은 없는가?

기존 외부인사 리스크 지적 6건의 대응 상태도 점검할 것.

호의적이지 않은 관점에서 구체적인 문제점과 대안을 제시할 것.""",
    expected_output="""검증 보고서:
1. 현실성 검증 (Pass/Fail + 구체적 문제점)
2. 전략적 검증 (Pass/Fail + 대안 제시)
3. 기술적 검증 (Pass/Fail + 블로커 분석)
4. 누락 항목 + 추가 리스크
5. 기존 6건 리스크 대응 상태 점검
6. 최종 판정 + 핵심 권고사항 3개
7. 종합 점수 (/10)""",
    agent=advisor,
    context=[task1_pm_strategy, task2_pjm_plan],
    output_file="output/next-phase-advisor-review.md",
)

# === Crew 실행 ===
crew = Crew(
    agents=[pm, pjm, advisor],
    tasks=[task1_pm_strategy, task2_pjm_plan, task3_advisor_review],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("다음 작업 방향성 논의 — PM + PjM + 외부인사 3자 회의")
    print("=" * 60)
    print(f"모델: {HIGH_PERF_MODEL}")
    print("태스크: 1) PM 전략 → 2) PjM 실행 계획 → 3) 외부인사 검증")
    print("=" * 60)
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("완료! 산출물:")
    print("  - output/next-phase-pm-strategy.md (PM 전략)")
    print("  - output/next-phase-pjm-plan.md (PjM 실행 계획)")
    print("  - output/next-phase-advisor-review.md (외부인사 검증)")
    print("=" * 60)
