"""M5/M6 작업 사항 에이전트 논의 — PM, PjM, 외부인사가 전략·계획·검증 수행

M5 (Auth + Progress Tracking)와 M6 (Default Tip 생성) 구현 사항에 대해
에이전트들이 전략적 관점에서 논의하고 검증한다.

사용법:
  source .venv/bin/activate
  python scripts/review_m5_m6.py
"""

import sys
import os

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai import Agent, Crew, Process, Task

from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.config.crew_logger import crew_logger  # noqa: F401

# --- 에이전트 정의 (YAML과 동일한 페르소나) ---

pm = Agent(
    role="프로덕트 매니저 (Product Manager)",
    goal=(
        "AI Interview 서비스의 M5/M6 구현 결과를 전략적으로 평가하고, "
        "MVP P0 런칭 준비 상태를 점검한다."
    ),
    backstory=(
        "8년차 프로덕트 매니저. B2C EdTech 서비스의 기획부터 런칭까지 전 과정을 주도해왔다. "
        "'사용자가 이 화면에서 3초 안에 다음 행동을 알 수 있는가?'를 항상 자문하며, "
        "스코프 크립을 경계하고, MVP와 후순위를 냉정하게 분리한다."
    ),
    llm=get_llm(HIGH_PERF_MODEL),
    verbose=True,
)

pjm = Agent(
    role="프로젝트 매니저 (Project Manager)",
    goal=(
        "M5/M6 구현의 기술적 완성도를 점검하고, "
        "남은 작업 항목과 리스크를 식별하여 런칭 체크리스트를 작성한다."
    ),
    backstory=(
        "7년차 프로젝트 매니저. 애자일 환경에서 다양한 규모의 스쿼드를 운영해왔다. "
        "'모호한 스펙은 모호한 결과물을 만든다'는 신념으로, 엣지 케이스와 "
        "Acceptance Criteria를 반드시 명시한다."
    ),
    llm=get_llm(HIGH_PERF_MODEL),
    verbose=True,
)

advisor = Agent(
    role="외부인사 (External Advisor)",
    goal=(
        "M5/M6 구현 결과에 대해 Devil's Advocate 관점에서 "
        "놓치기 쉬운 맹점과 리스크를 냉정하게 지적한다."
    ),
    backstory=(
        "15년차 스타트업 자문위원 겸 엔젤 투자자. "
        "'왜 이 서비스가 실패할 수 있는가'를 먼저 묻는 습관이 체화되어 있다. "
        "'좋다/괜찮다'는 표현을 사용하지 않으며, 개선점과 리스크를 중심으로 피드백한다."
    ),
    llm=get_llm(HIGH_PERF_MODEL),
    verbose=True,
)

# --- 컨텍스트: M5/M6 구현 사항 요약 ---

CONTEXT = """
## 프로젝트 현황

AI Interview — 프론트엔드 엔지니어를 위한 AI 기반 CS 기술 학습 및 모의 면접 서비스.
무자본 1인 개발, 무료 인프라(Vercel, Supabase Free Tier).

### MVP P0 기능 7개 (Phase 0: 개념 학습)
1. Dashboard (대시보드) — 완료
2. Learning Module (개념 학습) — 완료
3. Diagnosis (자가 진단) — 완료
4. Landing Page — 완료
5. Auth + Progress (인증+학습 진도) — M5로 완료
6. Progress Tracking (진도 추적) — M5로 완료
7. Default Tip (면접 팁) — M6 진행중

### M5 구현 완료 사항 (Auth + Progress Tracking)
- **middleware.ts**: next-intl 미들웨어 + Supabase SSR 세션 리프레시 통합
  - JWT 만료(기본 1시간) 시 서버사이드에서 자동 갱신
  - 이전에는 클라이언트 사이드만 세션 관리 → 서버 컴포넌트에서 인증 실패 가능성 있었음
- **progress.ts**: revalidatePath 범위를 "/learn" 레이아웃 레벨로 확대
- **Lazy Auth 패턴**: 로그인 없이 브라우징 가능, Self-Assessment 클릭 시에만 인증 요구
- **기존 구현 활용**: auth-provider, auth-modal, completion-button, diagnosis-result 모두 이전 마일스톤에서 이미 구현됨 → M5는 미들웨어 보완 1건으로 완료

### M6 진행중 사항 (Default Tip 생성)
- **현재 상태**: 151개 노드 모두 default_tip 컬럼에 데이터 있으나, "핵심 키워드: X, Y, Z" 수준의 최소한 팁
- **목표**: Ollama gemma4:26b로 2~3문장의 실질적 면접 조언 팁으로 업그레이드
- **스크립트**: scripts/generate_tips.py 작성 완료 (아직 미실행)
  - Supabase REST API로 노드 조회 → Ollama로 팁 생성 → DB 업데이트
  - --dry-run, --limit 옵션 지원
- **팁 표시**: web의 개념 학습 페이지에서 이미 default_tip을 스타일링된 카드로 렌더링 중

### 기술 스택
- Next.js 16 (App Router) + TypeScript + Tailwind + shadcn/ui
- Supabase (Auth, PostgreSQL, RLS)
- Ollama 로컬 모델 (gemma4:26b, gemma4:12b)
- i18n: next-intl 4.x (ko/en)

### 데이터 현황
- 151개 Q&A 노드 (9개 카테고리, 3단계 난이도)
- 카테고리: HTML(20), CSS(20), JavaScript(25), React(17), Next.js(14), 인프라/보안/네트워크(16), 형상관리(12), 성능/SEO(14), AI/LLM(13)
- 난이도: 주니어(70), 미드(49), 시니어(32)
- 한국어/영어 번역 완료 (node_translations, question_translations)
"""

# --- 태스크 정의 ---

task_strategy = Task(
    description=f"""
    아래 M5/M6 구현 사항을 검토하고, 제품 전략 관점에서 평가하라.

    {CONTEXT}

    [평가 항목 — 반드시 모두 다룰 것]
    1. M5 Lazy Auth 전략 평가
       - "로그인 없이 브라우징, 학습 완료 시에만 인증" 전략이 초기 사용자 획득에 효과적인가?
       - 이 패턴의 전환율(conversion) 예상치와 리스크
       - 경쟁 서비스(GreatFrontEnd, LeetCode 등)의 인증 전략과 비교

    2. M6 Default Tip 전략 평가
       - 정적 팁(배치 생성) vs 실시간 LLM 팁의 사용자 가치 차이
       - 151개 노드 × 2~3문장 팁이 사용자에게 충분한 가치를 제공하는가?
       - "면접 팁"이 서비스 차별화 요소로 작동할 수 있는가?

    3. MVP P0 런칭 준비 상태
       - 7개 P0 기능 중 6개 완료 + 1개 진행중 — 런칭 가능 상태인가?
       - MVP에서 빠져야 할 기능이나, 반드시 추가해야 할 기능이 있는가?
       - 런칭 후 첫 1주 사용자 피드백에서 가장 많이 나올 불만 예상

    4. 시장 전략
       - 현재 콘텐츠(151개 노드)로 초기 사용자를 확보할 수 있는가?
       - 타겟(CS 면접 준비 프론트엔드 개발자)의 실제 규모와 접근 채널
       - 무료 서비스의 초기 사용자 획득 전략 제안

    반드시 한국어로 작성하라. 각 항목에 대해 구체적 근거와 데이터 기반 추정을 포함하라.
    """,
    expected_output=(
        "M5/M6 제품 전략 평가 보고서 (마크다운). "
        "Lazy Auth 전략 평가, Default Tip 가치 분석, MVP 런칭 준비도, "
        "시장 전략 제안 포함. 각 항목에 구체적 근거와 수치 포함."
    ),
    agent=pm,
    output_file="output/m5-m6-strategy-review.md",
)

task_technical = Task(
    description=f"""
    PM의 전략 평가를 참고하여, M5/M6의 기술적 완성도와 런칭 체크리스트를 작성하라.

    {CONTEXT}

    [점검 항목 — 반드시 모두 다룰 것]
    1. M5 기술 완성도
       - middleware.ts의 Supabase SSR 세션 리프레시가 올바르게 작동하는가?
       - JWT 만료 시나리오: 1시간 후, 7일 후(refresh token), 30일 후 각각 어떻게 처리되는가?
       - RLS(Row Level Security) 정책과 Lazy Auth 패턴의 호환성
       - 서버 컴포넌트에서 인증 상태 읽기의 안정성

    2. M6 기술 완성도
       - generate_tips.py 스크립트의 안정성 (에러 핸들링, 재시도 로직)
       - 151개 노드 × Ollama 생성 시 예상 소요 시간
       - 팁 품질 검증 방법 (길이, 한국어 정합성, 할루시네이션 체크)
       - 기존 "핵심 키워드: X, Y, Z" 팁을 덮어쓰는 것의 안전성 (rollback 계획)

    3. 런칭 전 필수 체크리스트
       - 빌드 성공 여부 (SSG 330페이지)
       - Supabase RLS 정책 점검
       - 환경 변수 설정 (production)
       - 에러 모니터링 설정 여부
       - i18n 번역 완성도 (ko/en)
       - 성능: LCP, FCP, CLS 기준치

    4. 리스크 및 엣지 케이스
       - 동시 사용자 증가 시 Supabase Free Tier 한계
       - Ollama 모델 서비스 중단 시 fallback
       - default_tip이 비어있는 노드의 UI 처리

    반드시 한국어로 작성하라. 체크리스트는 ✅/🔲 형태로 명확히 표시하라.
    """,
    expected_output=(
        "M5/M6 기술 점검 및 런칭 체크리스트 (마크다운). "
        "M5/M6 기술 완성도 평가, 런칭 전 필수 체크리스트, "
        "리스크 및 엣지 케이스 정리. 각 항목에 상태 표시(✅/🔲) 포함."
    ),
    agent=pjm,
    context=[task_strategy],
    output_file="output/m5-m6-technical-review.md",
)

task_devils_advocate = Task(
    description=f"""
    PM과 PjM의 평가를 참고하여, Devil's Advocate 관점에서 M5/M6 구현과 MVP 런칭 계획의
    맹점과 리스크를 냉정하게 지적하라.

    {CONTEXT}

    [비판 관점 — 3축 분석]
    1. 사용자 관점:
       - Lazy Auth: 로그인 없이 학습 → 진도 저장 안 됨 → 재방문 시 처음부터?
       - Default Tip: 정적 팁 2~3문장이 사용자에게 "AI 서비스"라는 인상을 줄 수 있는가?
       - 151개 노드: 사용자가 학습 완료까지 얼마나 걸리며, 완료 후 재방문 이유는?
       - ChatGPT에 "React 면접 팁 알려줘"라고 물어보는 것 대비 어떤 이점?

    2. 시장 관점:
       - MVP P0가 "개념 학습 + 자가진단"에 집중 → 이것만으로 초기 사용자를 끌 수 있나?
       - 경쟁사가 동일 기능을 2주 만에 복제할 수 있는 구조 아닌가?
       - "프론트엔드 면접 준비" 시장의 실제 크기와 지불 의향(willingness to pay)
       - 무료 서비스의 지속가능성: 운영 비용은 누가 부담하는가?

    3. 기술 관점:
       - Supabase Free Tier: 500MB 스토리지, 월 50K 함수 호출 → 사용자 몇 명까지 버티는가?
       - Ollama 로컬 모델로 생성한 팁의 품질: 할루시네이션, 부정확한 기술 정보 리스크
       - 1인 개발에서 보안 취약점 발견 시 대응 능력
       - Next.js 16의 SSG 330페이지: 노드 추가 시 빌드 시간 선형 증가 문제

    [피드백 원칙]
    - "좋다/괜찮다" 표현 절대 금지
    - 모든 지적에 구체적 근거 또는 반례 포함
    - 마지막에 "이 피드백에도 불구하고 런칭을 진행해야 하는가?" 질문 포함

    반드시 한국어로 작성하라.
    """,
    expected_output=(
        "Devil's Advocate 리뷰 보고서 (마크다운). "
        "사용자/시장/기술 3축 분석, 각 축별 리스크와 맹점, "
        "구체적 근거, 대응 제안 포함. "
        "마지막에 '그럼에도 런칭해야 하는가?' 질문 포함."
    ),
    agent=advisor,
    context=[task_strategy, task_technical],
    output_file="output/m5-m6-devils-advocate.md",
)

# --- Crew 실행 ---

def main():
    crew = Crew(
        agents=[pm, pjm, advisor],
        tasks=[task_strategy, task_technical, task_devils_advocate],
        process=Process.sequential,
        verbose=True,
    )

    print("\n=== M5/M6 에이전트 논의 시작 ===")
    print("  Task 1: PM — 제품 전략 평가")
    print("  Task 2: PjM — 기술 완성도 + 런칭 체크리스트")
    print("  Task 3: 외부인사 — Devil's Advocate 리뷰")
    print("=" * 60)

    result = crew.kickoff()

    print("\n=== 에이전트 논의 완료 ===")
    print("산출물:")
    print("  1. output/m5-m6-strategy-review.md")
    print("  2. output/m5-m6-technical-review.md")
    print("  3. output/m5-m6-devils-advocate.md")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
