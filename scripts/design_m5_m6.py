"""M5(프로그레스 트래킹) + M6(AI 요약/팁) 세부 구현 계획 — 에이전트 협업 설계

CLAUDE.md 규칙: 마일스톤별 전용 스크립트(scripts/design_*.py)로 관련 Crew 실행
참여 에이전트: PM, PjM, FE 시니어, 풀스택 아키텍트, QA 엔지니어
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL


# === 현재 상태 컨텍스트 (에이전트에게 제공) ===
CURRENT_STATE = """
[프로젝트 현재 상태 — 2026-07-18]

1. 완료된 작업:
   - Phase 0~3 완료 (에이전트 시스템, 시장조사, PRD, Handoff)
   - Supabase 스키마 배포 (nodes/questions/user_progress + RLS)
   - 138개 시드 데이터 적재 (9개 카테고리, 3난이도)
   - SSG 151페이지 빌드 성공 (dashboard, learn/[category]/[slug])
   - i18n 다국어 지원 (ko/en, next-intl)
   - DB 번역 완료 (node_translations/question_translations)
   - M3 메타인지 진단 완료 (9개 진단 질문 + 진단 UI + 결과 리포트)
   - MVP P0 기능 7개 확정

2. 웹 프로젝트 구현 현황:
   - auth-provider.tsx 존재 (Supabase Auth 연동)
   - app/actions/progress.ts 존재 (프로그레스 액션)
   - app/[locale]/diagnosis/ 존재 (M3 진단 페이지)
   - middleware.ts 존재 (Supabase Auth 세션 갱신)
   - Supabase client/server 유틸리티 설정 완료

3. DB 스키마:
   - nodes: id, slug, title, category, description, keywords, default_tip, ...
   - questions: id, node_id, question, difficulty, answer_guide, keywords, ...
   - user_progress: id, user_id, node_id, status, confidence_level, ...
   - node_translations / question_translations (번역 테이블)
   - RLS: nodes/questions public read, user_progress auth.uid() 기반

4. 기술 스택:
   - Next.js 16.2.10, TypeScript 5.9.3, React 19.2.3
   - Tailwind CSS 3.4.19, shadcn/ui
   - Zustand 5.0.10, TanStack Query 5.90.19
   - React Hook Form 7.71.1, Zod 4.3.5
   - Supabase (PostgreSQL + Auth), pnpm 10.17.1
   - next-intl (i18n)

5. 비용 제약:
   - 무자본 1인 개인, 무료 서비스만 활용
   - Supabase Free Tier (500MB DB, 50K rows)
   - LLM: Ollama 로컬 모델만 (서비스용 Tier 2: gemma4:12b)

6. 기존 리뷰 의견 (외부인사 Devil's Advocate):
   - Lazy Auth의 역설: 로그인 없이 학습 → 진도 미저장 인식 시 이탈 위험
   - ChatGPT 대비 차별성 부족: 정적 팁 vs 동적 AI 답변
   - 임시 익명 세션 저장 로직 필요성 제기
   - AI 생성 팁 전문가 검증 프로세스 필요
"""

M5_REQUIREMENTS = """
[M5: 프로그레스 트래킹 — 요구사항]

PRD 정의:
- Supabase Auth 연동 (Google/GitHub OAuth)
- user_progress 테이블에 학습 진도 실시간 반영
- Lazy Auth 패턴: 로그인 없이 브라우징 → 진도 저장 시 로그인 유도
- 학습 완료/자가 평가 시 confidence_level 업데이트
- 대시보드에 카테고리별 완료율 표시

기존 구현:
- auth-provider.tsx 존재
- app/actions/progress.ts 존재
- middleware.ts 세션 갱신 존재
- user_progress 테이블 + RLS 정책 존재

확정 사항 (OQ-1):
- Supabase Auth 도입 확정
- RLS 기반 user_progress 보호
"""

M6_REQUIREMENTS = """
[M6: AI 요약/팁 — 요구사항]

PRD 정의:
- 각 노드(개념)에 AI가 생성한 면접 팁 표시
- LLM 실패 시 default_tip 컬럼으로 Fallback
- "면접관처럼 날카로운" 문체의 Actionable Advice

기존 구현:
- default_tip 컬럼 존재 (nodes 테이블)
- 151개 노드에 기본 키워드 수준의 팁 존재
- Ollama 스크립트(scripts/generate_tips.py) 통해 배치 생성 예정

확정 사항 (OQ-3):
- SSG (빌드 타임 정적 생성, AI 요약만 동적)
- 비용 0원 원칙 (Ollama 로컬 모델)
"""


def create_agents():
    """5명의 에이전트 생성 — 기존 YAML 페르소나 기반"""
    llm = get_llm(HIGH_PERF_MODEL)

    pm = Agent(
        role="프로덕트 매니저 (Product Manager)",
        goal="M5/M6 기능의 사용자 가치를 극대화하는 구현 계획을 수립한다. "
             "스코프 크립을 경계하고, MVP 범위 내에서 최대 임팩트를 낸다.",
        backstory="8년차 프로덕트 매니저. B2C EdTech 서비스 기획 전문. "
                  "'사용자가 3초 안에 다음 행동을 알 수 있는가?'를 항상 자문한다. "
                  "현재 AI Interview 서비스의 M5(프로그레스 트래킹) + M6(AI 요약/팁) 구현을 계획 중이다.",
        llm=llm,
        verbose=True,
    )

    pjm = Agent(
        role="프로젝트 매니저 (Project Manager)",
        goal="M5/M6 구현을 작업 단위로 분해하고, 실행 순서와 의존성을 명확히 정의한다. "
             "각 작업에 Acceptance Criteria를 반드시 명시한다.",
        backstory="7년차 프로젝트 매니저. '모호한 스펙은 모호한 결과물을 만든다'는 신념. "
                  "태스크를 독립 작업 가능한 최소 단위로 분리한다. "
                  "현재 AI Interview M5/M6 작업 분배를 담당하고 있다.",
        llm=llm,
        verbose=True,
    )

    fe = Agent(
        role="프론트엔드 시니어 개발자 (Frontend Senior)",
        goal="M5/M6 기능의 프론트엔드 컴포넌트 설계와 상태 관리 전략을 수립한다. "
             "서버/클라이언트 컴포넌트 분리, 접근성, 반응형을 고려한다.",
        backstory="9년차 프론트엔드 개발자. Next.js App Router, Supabase Auth, "
                  "Zustand + TanStack Query 기반 상태 관리에 특화. "
                  "Web Vitals(LCP, INP, CLS) 지속 측정. 접근성은 기본. "
                  "현재 AI Interview 서비스의 프론트엔드를 담당 중.",
        llm=llm,
        verbose=True,
    )

    architect = Agent(
        role="풀스택 아키텍트 (Fullstack Architect)",
        goal="M5/M6의 데이터 흐름, API 설계, 인증 아키텍처를 검증한다. "
             "과도한 추상화를 경계하고 현재 필요한 수준의 복잡도만 허용한다.",
        backstory="12년차 풀스택 개발자. 기술 선택 시 '트렌디함'보다 '유지보수성' 우선. "
                  "모든 기술 의사결정은 ADR로 기록. "
                  "현재 AI Interview의 Supabase 아키텍처를 담당 중.",
        llm=llm,
        verbose=True,
    )

    qa = Agent(
        role="QA 엔지니어 (QA Engineer)",
        goal="M5/M6 기능의 테스트 전략과 핵심 테스트 케이스를 정의한다. "
             "엣지 케이스, 에러 경로, 경계값을 반드시 검증한다.",
        backstory="6년차 QA 엔지니어. '버그는 발견이 늦을수록 비용이 기하급수적으로 증가' 원칙. "
                  "개발 초기 단계부터 테스트 전략을 수립. "
                  "현재 AI Interview의 QA를 담당 중.",
        llm=llm,
        verbose=True,
    )

    return pm, pjm, fe, architect, qa


def create_tasks(pm, pjm, fe, architect, qa):
    """M5/M6 설계 태스크 정의 — sequential chaining"""

    # Task 1: PM — 기능 우선순위 및 사용자 시나리오
    t1_feature_plan = Task(
        description=f"""
        M5(프로그레스 트래킹)와 M6(AI 요약/팁) 기능의 구현 계획을 수립한다.

        {CURRENT_STATE}
        {M5_REQUIREMENTS}
        {M6_REQUIREMENTS}

        [작성할 내용]
        1. M5/M6 각 기능의 사용자 시나리오 (Happy Path + Edge Case)
        2. 기능 우선순위 정리 (Must/Should/Could)
        3. 사용자 여정 (User Journey) — 비로그인 → 학습 → 로그인 유도 → 진도 저장
        4. 외부인사 리뷰에서 제기된 Lazy Auth 역설 해결 방안
        5. M6 AI 팁의 차별화 전략 (ChatGPT 대비)
        6. 구현 순서 권고 (M5 먼저 vs M6 먼저 vs 병렬)
        """,
        expected_output="M5/M6 기능 계획서 (마크다운). 사용자 시나리오, 우선순위, "
                        "User Journey, Lazy Auth 해결안, AI 팁 차별화, 구현 순서 포함.",
        agent=pm,
    )

    # Task 2: 아키텍트 — 기술 아키텍처 검증
    t2_architecture = Task(
        description=f"""
        PM의 기능 계획을 기반으로 M5/M6의 기술 아키텍처를 설계한다.

        {CURRENT_STATE}

        [설계할 내용]
        1. Supabase Auth 흐름 상세 (Google/GitHub OAuth → session → RLS)
        2. Lazy Auth 구현 패턴 — 비로그인 학습 → 로그인 시 임시 데이터 마이그레이션 여부
        3. user_progress CRUD API 설계 (Server Actions vs Route Handler)
        4. M6 AI 팁 생성 파이프라인 (Ollama 배치 → DB 저장 → SSG 빌드)
        5. 데이터 흐름도 (Auth → Progress → Dashboard 반영)
        6. Free Tier 한도 내 운영 가능성 재검증
        7. ADR: 주요 기술 의사결정 기록
        """,
        expected_output="M5/M6 기술 아키텍처 문서 (마크다운). Auth 흐름, "
                        "Lazy Auth 패턴, API 설계, 데이터 흐름도, ADR 포함.",
        agent=architect,
        context=[t1_feature_plan],
    )

    # Task 3: FE 시니어 — 컴포넌트 및 상태 설계
    t3_frontend = Task(
        description=f"""
        아키텍처 설계를 기반으로 M5/M6의 프론트엔드 구현 계획을 작성한다.

        {CURRENT_STATE}

        [설계할 내용]
        1. M5 관련 컴포넌트:
           - 로그인/회원가입 UI (OAuth 버튼)
           - 프로그레스 바/뱃지 (대시보드, 카테고리별)
           - 학습 완료 버튼 + confidence 입력 UI
           - 로그인 유도 모달/배너 (Lazy Auth)
        2. M6 관련 컴포넌트:
           - AI 팁 카드 (노드 상세 페이지 내)
           - 팁 로딩/폴백 UI
        3. 상태 관리 전략:
           - Auth 상태: Supabase + Context
           - Progress 상태: TanStack Query (서버) vs Zustand (클라이언트)
           - Optimistic Update 전략
        4. 서버 컴포넌트 vs 클라이언트 컴포넌트 분리
        5. 접근성(a11y) 체크리스트
        6. 반응형 브레이크포인트 전략
        """,
        expected_output="M5/M6 프론트엔드 설계서 (마크다운). 컴포넌트 트리, "
                        "Props 인터페이스, 상태 관리, 서버/클라이언트 분리, a11y 포함.",
        agent=fe,
        context=[t1_feature_plan, t2_architecture],
    )

    # Task 4: PjM — 작업 분해 및 실행 계획
    t4_task_breakdown = Task(
        description=f"""
        PM/아키텍트/FE의 설계를 기반으로 M5/M6 구현 작업을 분해한다.

        {CURRENT_STATE}

        [작성할 내용]
        1. 작업 목록 (Task List) — 각 작업에:
           - Task ID (예: M5-01, M6-01)
           - 제목
           - 설명
           - Acceptance Criteria (Given-When-Then)
           - 의존성 (선행 작업)
           - 예상 복잡도 (S/M/L)
           - 담당 (Claude Code / CrewAI Crew)
        2. 실행 순서 (의존성 기반 DAG)
        3. 마일스톤 체크포인트 (중간 검증 시점)
        4. 리스크 및 블로커 목록
        5. Definition of Done (완료 기준)
        """,
        expected_output="M5/M6 작업 분해 문서 (마크다운). Task 목록, AC, "
                        "실행 순서, 마일스톤, 리스크, DoD 포함.",
        agent=pjm,
        context=[t1_feature_plan, t2_architecture, t3_frontend],
    )

    # Task 5: QA — 테스트 전략 및 핵심 케이스
    t5_qa_plan = Task(
        description=f"""
        작업 분해를 기반으로 M5/M6의 테스트 전략과 핵심 테스트 케이스를 작성한다.

        [테스트 대상]
        - M5: OAuth 로그인, 세션 관리, progress CRUD, RLS 보안, Lazy Auth 전환
        - M6: AI 팁 표시, 폴백 동작, 팁 품질 검증

        [작성할 내용]
        1. 테스트 전략 — 단위/통합/E2E 비율 및 도구
        2. 핵심 테스트 케이스 (TC-ID, Given-When-Then, 우선순위)
           - Happy Path: 로그인 → 학습 → 진도 저장 → 대시보드 반영
           - Edge Case: 세션 만료, 동시 디바이스, 오프라인
           - Error Path: Auth 실패, DB 에러, LLM 타임아웃
           - Security: RLS 우회 시도, 타인 데이터 접근
        3. AI 팁 품질 QA 체크리스트 (Hallucination, 문체, 길이)
        4. 성능 기준 (Web Vitals 목표)
        """,
        expected_output="M5/M6 테스트 계획서 (마크다운). 테스트 전략, "
                        "테스트 케이스 표, AI QA 체크리스트, 성능 기준 포함.",
        agent=qa,
        context=[t4_task_breakdown],
    )

    return [t1_feature_plan, t2_architecture, t3_frontend, t4_task_breakdown, t5_qa_plan]


def main():
    print("=" * 60)
    print("M5/M6 세부 구현 계획 — 에이전트 협업 설계")
    print("참여: PM, PjM, FE 시니어, 풀스택 아키텍트, QA")
    print("=" * 60)

    pm, pjm, fe, architect, qa = create_agents()
    tasks = create_tasks(pm, pjm, fe, architect, qa)

    crew = Crew(
        agents=[pm, architect, fe, pjm, qa],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        output_log_file="logs/design-m5-m6.log",
    )

    result = crew.kickoff()

    # 결과를 파일로 저장
    output_path = Path(__file__).resolve().parent.parent / "output" / "design-m5-m6-plan.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"""# M5/M6 세부 구현 계획 — 에이전트 협업 산출물

> 생성일: 2026-07-18
> 참여 에이전트: PM, PjM, FE 시니어, 풀스택 아키텍트, QA
> 모델: {HIGH_PERF_MODEL} (Ollama 로컬)

---

{result.raw}
""", encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"산출물 저장: {output_path}")
    print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    main()
