"""3개 레포 코드 품질 검수 — QA 엔지니어 + 시니어 FE 에이전트

오케스트레이터의 file_tools를 활용하여 3개 레포의 실제 코드를 읽고,
시니어 개발자 관점에서 성능, 보안, 코드 품질을 검수한다.

사용법:
  source .venv/bin/activate
  python scripts/code_review.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai import Agent, Crew, Process, Task

from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.config.crew_logger import crew_logger  # noqa: F401
from src.tools.file_tools import (
    list_directory,
    list_directory_recursive,
    read_file,
)

# --- 에이전트 정의 ---

qa_engineer = Agent(
    role="시니어 QA 엔지니어",
    goal=(
        "3개 레포(web, server, orchestrator)의 코드를 읽고 "
        "미사용 import, 불필요한 의존성, 에러 핸들링 부재, "
        "성능 이슈, 보안 취약점을 시니어 개발자 관점에서 검수한다."
    ),
    backstory=(
        "10년차 시니어 풀스택 엔지니어 겸 코드 리뷰어. "
        "'코드는 팀이 읽는 문서'라는 신념으로 모든 코드를 검수한다. "
        "미사용 변수, 불필요한 import, 에러 핸들링 부재, "
        "N+1 쿼리, XSS/CSRF 취약점, 메모리 누수 패턴을 정확히 잡아낸다. "
        "성능 최적화(리렌더링, 번들 사이즈, SSG/SSR 선택)에도 정통하다."
    ),
    llm=get_llm(HIGH_PERF_MODEL),
    tools=[list_directory, list_directory_recursive, read_file],
    allow_delegation=False,
    verbose=True,
)

fe_senior = Agent(
    role="시니어 프론트엔드 개발자",
    goal=(
        "Next.js 16 + React 19 프로젝트의 프론트엔드 코드를 "
        "성능, 접근성, 렌더링 최적화 관점에서 심층 검수한다."
    ),
    backstory=(
        "8년차 시니어 프론트엔드 엔지니어. React, Next.js 전문가. "
        "Server Component vs Client Component 분리 전략, "
        "불필요한 리렌더링, useEffect 의존성 배열 오류, "
        "번들 사이즈 최적화, Web Vitals 개선에 특화되어 있다. "
        "'use client'의 과도한 사용, 클라이언트 번들에 서버 전용 코드 혼입, "
        "i18n 번역 키 누락 등을 정확히 잡아낸다."
    ),
    llm=get_llm(HIGH_PERF_MODEL),
    tools=[list_directory, list_directory_recursive, read_file],
    allow_delegation=False,
    verbose=True,
)

# --- 레포 경로 ---

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_REPO = os.path.join(BASE, "AI-Interview-web")
SERVER_REPO = os.path.join(BASE, "AI-Interview-server")
ORCH_REPO = os.path.join(BASE, "AI-Interview-orchestrator")

# --- 태스크 정의 ---

task_orchestrator_review = Task(
    description=f"""
    오케스트레이터 레포의 코드 품질을 검수한다.

    대상 디렉토리: {ORCH_REPO}

    [검수 절차]
    1. list_directory_recursive 도구로 전체 구조 파악
    2. 아래 파일들을 read_file 도구로 직접 읽고 검수:
       - main.py (엔트리포인트)
       - src/config/llm.py (LLM 설정)
       - src/config/crew_logger.py (로거)
       - src/tools/file_tools.py (파일 도구)
       - src/tools/notion_tools.py (노션 도구)
       - scripts/generate_tips.py (M6 팁 생성)
       - scripts/translate_content.py (번역)
       - scripts/sync_notion.py (노션 동기화)

    [검수 항목 — 반드시 모두 확인]
    1. 미사용 import (import 했지만 사용하지 않는 모듈)
    2. 미사용 변수/함수
    3. 에러 핸들링 부재 (bare except, 에러 무시)
    4. 하드코딩된 값 (매직 넘버, URL, 경로)
    5. 타입 힌트 부재 또는 불일치
    6. 보안 이슈 (경로 탈출, 인젝션 가능성)
    7. 성능 이슈 (불필요한 루프, 비효율적 I/O)
    8. 코드 중복

    반드시 한국어로 작성하라. 파일별로 이슈를 정리하라.
    이슈가 없는 파일은 "이슈 없음"으로 표시하라.
    각 이슈에 심각도(Critical/High/Medium/Low)와 수정 제안을 포함하라.
    """,
    expected_output=(
        "오케스트레이터 레포 코드 리뷰 보고서 (마크다운). "
        "파일별 이슈 목록, 심각도, 수정 제안 포함."
    ),
    agent=qa_engineer,
    output_file="output/code-review-orchestrator.md",
)

task_web_review = Task(
    description=f"""
    웹(프론트엔드) 레포의 코드 품질을 검수한다.

    대상 디렉토리: {WEB_REPO}

    [검수 절차]
    1. list_directory_recursive 도구로 전체 구조 파악
    2. 아래 핵심 파일들을 read_file 도구로 직접 읽고 검수:
       - middleware.ts (미들웨어)
       - app/actions/progress.ts (서버 액션)
       - app/[locale]/dashboard/page.tsx (대시보드)
       - app/[locale]/learn/[category]/[slug]/page.tsx (개념 학습)
       - app/[locale]/learn/[category]/page.tsx (카테고리 목록)
       - app/[locale]/diagnosis/page.tsx (자가 진단)
       - components/auth/auth-modal.tsx (인증 모달)
       - components/learn/completion-button.tsx (학습 완료)
       - components/diagnosis/diagnosis-result.tsx (진단 결과)
       - providers/auth-provider.tsx (인증 프로바이더)
       - store/diagnosis.ts (Zustand 스토어)
       - lib/supabase/server.ts (서버 클라이언트)
       - lib/supabase/client.ts (브라우저 클라이언트)
       - lib/supabase/queries.ts (쿼리)

    [검수 항목 — 시니어 FE 관점]
    1. 미사용 import/변수
    2. Server Component에서 불필요한 'use client' 사용
    3. useEffect 의존성 배열 오류 (누락, 불필요한 포함)
    4. 불필요한 리렌더링 유발 패턴 (인라인 객체/함수)
    5. XSS 취약점 (dangerouslySetInnerHTML 사용처)
    6. 에러 바운더리 부재
    7. 접근성(a11y) 이슈 (aria 속성 누락, 키보드 내비게이션)
    8. i18n 하드코딩 문자열 (번역 키 없이 직접 텍스트 사용)
    9. Supabase 쿼리 최적화 (N+1, 불필요한 select *)
    10. 타입 안전성 (any 사용, 타입 단언 남용)

    반드시 한국어로 작성하라. 파일별로 이슈를 정리하라.
    각 이슈에 심각도(Critical/High/Medium/Low), 코드 위치(줄 번호), 수정 제안을 포함하라.
    """,
    expected_output=(
        "웹 레포 코드 리뷰 보고서 (마크다운). "
        "파일별 이슈 목록, 심각도, 줄 번호, 수정 제안 포함."
    ),
    agent=fe_senior,
    context=[task_orchestrator_review],
    output_file="output/code-review-web.md",
)

task_summary = Task(
    description=f"""
    오케스트레이터 레포와 웹 레포의 코드 리뷰 결과를 종합하여
    최종 검수 보고서를 작성한다.

    참고: server 레포({SERVER_REPO})는 아직 미착수 상태이므로
    CLAUDE.md 파일만 확인하여 내용 정합성을 검증한다.
    read_file 도구로 {SERVER_REPO}/CLAUDE.md를 읽어라.

    [최종 보고서 포함 사항]
    1. 전체 요약: Critical/High/Medium/Low별 이슈 수
    2. 즉시 수정 필요 (Critical + High): 파일, 줄 번호, 수정 방법
    3. 개선 권고 (Medium + Low): 우선순위별 정리
    4. 3개 레포 간 정합성: CLAUDE.md 정보 일치 여부
    5. 코드 품질 점수 (10점 만점)

    반드시 한국어로 작성하라.
    """,
    expected_output=(
        "3개 레포 코드 검수 종합 보고서 (마크다운). "
        "심각도별 이슈 집계, 즉시 수정 목록, 개선 권고, "
        "레포 간 정합성, 품질 점수 포함."
    ),
    agent=qa_engineer,
    context=[task_orchestrator_review, task_web_review],
    output_file="output/code-review-summary.md",
)

# --- Crew 실행 ---

def main():
    crew = Crew(
        agents=[qa_engineer, fe_senior],
        tasks=[task_orchestrator_review, task_web_review, task_summary],
        process=Process.sequential,
        verbose=True,
    )

    print("\n=== 3개 레포 코드 품질 검수 시작 ===")
    print(f"  Task 1: QA 엔지니어 — 오케스트레이터 레포 검수")
    print(f"  Task 2: 시니어 FE — 웹 레포 검수")
    print(f"  Task 3: QA 엔지니어 — 종합 보고서")
    print("=" * 60)

    result = crew.kickoff()

    print("\n=== 코드 검수 완료 ===")
    print("산출물:")
    print("  1. output/code-review-orchestrator.md")
    print("  2. output/code-review-web.md")
    print("  3. output/code-review-summary.md")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
