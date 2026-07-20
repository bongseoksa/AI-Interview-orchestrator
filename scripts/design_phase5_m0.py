"""Phase 5 M0: FastAPI 서버 인프라 상세 설계 — 아키텍트 + 백엔드 시니어 + QA

목적: revised-architect-infra.md의 고수준 설계를 실제 구현 가능한 상세 설계로 구체화.
     server 레포에 바로 적용할 수 있는 수준의 산출물 생성.

참여 에이전트:
  - 풀스택 아키텍트: 프로젝트 구조 + API 명세 + 인증 연동 상세 설계
  - 백엔드 시니어: FastAPI 코드 구조 + Supabase 연동 + 배포 설정 상세 설계
  - QA 엔지니어: M0 완료 기준 테스트 케이스 + CI/CD 검증 체크리스트

실행: source .venv/bin/activate && python scripts/design_phase5_m0.py
산출물:
  - output/phase5-m0-api-spec.md (API 명세 + 프로젝트 구조)
  - output/phase5-m0-implementation.md (구현 상세 + 배포 설정)
  - output/phase5-m0-test-plan.md (테스트 케이스 + DoD 체크리스트)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory_recursive, read_file
from src.tools.notion_tools import read_notion_page

# === 컨텍스트 ===
CONTEXT = """
[프로젝트: AI Interview — Phase 5 M0: Infrastructure First]

[프로젝트 현황]
- web: Next.js 16, Supabase Auth+DB, Vercel 배포, Phase 4 완료 (P0 7개 기능)
- server: 빈 레포 — 문서만 존재 (CLAUDE.md, ONBOARDING.md, README.md, .claude/agents/)
  - Python 환경, FastAPI, main.py 등 아무것도 없음
  - .githooks/pre-commit 존재
- orchestrator: CrewAI + Ollama, 11 Crew 운영 중

[기존 고수준 설계 (revised-architect-infra.md 요약)]
- FastAPI 서버 구조: app/api/, app/core/, app/services/, app/models/
- API Endpoints: POST /v1/interview/start, POST /v1/interview/submit,
  GET /v1/interview/{sid}/status, GET /v1/interview/{sid}/report, GET /v1/health
- 인증: Supabase JWT 검증 (python-jose)
- 배포: Docker + Railway/Render
- LLM: Dev=Ollama 로컬, Prod=Groq/DeepSeek
- 비용: 월 $5 미만

[M0 DoD (PjM 계획서)]
- API Health Check 성공
- Dockerize 완료
- Railway/Render 자동 배포 확인

[M0 범위 — 2주 (W2-W3)]
- W2: FastAPI 기본 아키텍처 및 프로젝트 구조 설계/구현
- W3: 배포 및 CI/CD 자동화

[비용 제약]
- 무자본 1인 개인
- 서버 호스팅: Railway/Render Free Tier
- DB: Supabase Free Tier (이미 web에서 사용 중)

[기술 선택 전제]
- Python 3.13
- FastAPI (비동기, 고성능)
- Supabase PostgreSQL (기존 DB 공유)
- Docker (컨테이너화)
- GitHub Actions (CI/CD)

[web 레포 Supabase 설정 참고]
- NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY 사용 중
- Supabase Auth: 이메일+OAuth, JWT 기반
- RLS: nodes/questions public read, user_progress auth.uid() 기반
- 테이블: nodes, questions, user_progress, node_translations, question_translations

[M0에서 구현하지 않는 것]
- AI 면접 엔진 (M1)
- RAG 파이프라인 (M1-M2)
- Rubric 채점 (M2)
- 프론트엔드 연동 (M3)
- 결제 시스템 (M4)
"""

# === 에이전트 정의 ===
llm = get_llm(HIGH_PERF_MODEL)

architect = Agent(
    role="풀스택 아키텍트 (Full-Stack Architect)",
    goal="server 레포에 바로 적용할 수 있는 FastAPI 프로젝트 구조와 API 명세를 상세 설계한다",
    backstory=(
        "12년차 풀스택 아키텍트. FastAPI + Supabase 프로덕션 경험 다수. "
        "빈 레포에서 프로덕션 레디 서버를 구축하는 과정을 수십 번 경험했다. "
        "과도한 추상화를 경계하고, M0 범위(인프라 구축)에 필요한 최소한만 설계한다. "
        "M1 이후에 추가될 면접 엔진/RAG는 확장 포인트만 남기고 구현하지 않는다. "
        "모든 설계 결정은 ADR(Architecture Decision Record) 형식으로 근거를 명시한다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive, read_notion_page],
    allow_delegation=False,
    verbose=True,
)

backend_senior = Agent(
    role="백엔드 시니어 개발자 (Backend Senior Developer)",
    goal="아키텍트의 설계를 바탕으로 실제 구현 가이드와 배포 설정을 작성한다",
    backstory=(
        "9년차 백엔드 개발자. Python/FastAPI 전문가. "
        "Supabase를 백엔드에서 직접 연동한 경험이 풍부하다. "
        "Railway/Render 배포, Docker 최적화, GitHub Actions CI/CD 구축에 능하다. "
        "1인 개발자가 운영 부하 없이 유지할 수 있는 심플한 구조를 지향한다. "
        "에러 핸들링에 엄격하며, 모든 외부 의존성에 타임아웃과 재시도 정책을 적용한다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive],
    allow_delegation=False,
    verbose=True,
)

qa_engineer = Agent(
    role="QA 엔지니어 (QA Engineer)",
    goal="M0 완료 기준(DoD)을 검증할 테스트 케이스와 CI/CD 검증 체크리스트를 작성한다",
    backstory=(
        "6년차 QA 엔지니어. API 테스트 자동화(pytest + httpx) 전문가. "
        "인프라 구축 단계에서의 테스트 전략을 잘 알고 있다: "
        "헬스체크, CORS, 인증 미들웨어, Docker 빌드, 배포 파이프라인 검증. "
        "M0는 비즈니스 로직이 없으므로, 인프라 안정성과 배포 파이프라인 검증에 집중한다."
    ),
    llm=llm,
    tools=[read_file],
    allow_delegation=False,
    verbose=True,
)

# === 태스크 정의 ===

task1_api_spec = Task(
    description=f"""Phase 5 M0: FastAPI 서버 프로젝트 구조와 API 명세를 상세 설계한다.

{CONTEXT}

[수행 사항]

1. 프로젝트 디렉토리 구조 (server 레포):
   - 전체 파일/폴더 트리 (파일명까지)
   - 각 파일의 역할 1줄 설명
   - M0에서 생성할 파일 vs M1 이후에 추가할 파일 구분

2. API 명세 (M0 범위):
   - GET /v1/health — 헬스체크 (DB 연결 상태 포함)
   - 향후 M1에서 추가될 엔드포인트의 라우터 구조만 준비 (빈 라우터)
   - Request/Response 스키마 (Pydantic v2)
   - 에러 응답 형식 통일

3. Supabase 연동 설계:
   - supabase-py 클라이언트 설정 (서비스 롤 키 vs anon 키 사용 기준)
   - JWT 검증 미들웨어 상세 (python-jose vs PyJWT 선택 근거)
   - 기존 web 레포와 같은 Supabase 프로젝트 공유 시 주의사항

4. CORS 설정:
   - 개발 환경 (localhost:3000)
   - 프로덕션 환경 (Vercel 도메인)
   - 환경별 분기 전략

5. 환경 변수 목록:
   - .env 파일에 필요한 모든 변수 (이름, 설명, 예시값)
   - .env.example 템플릿

6. 의존성 목록:
   - pyproject.toml 또는 requirements.txt에 들어갈 패키지
   - 각 패키지의 용도와 버전 제약

server 레포의 현재 파일을 확인하려면 read_file 또는 list_directory_recursive 도구를 사용할 것.""",
    expected_output="""Phase 5 M0 API 명세서:
1. 프로젝트 디렉토리 구조 (전체 파일 트리 + 역할 설명)
2. API 엔드포인트 명세 (M0 범위 + M1 확장 포인트)
3. Supabase 연동 설계 (클라이언트 설정, JWT 검증)
4. CORS 설정 (환경별)
5. 환경 변수 목록 (.env.example)
6. 의존성 목록 (패키지 + 버전)
7. ADR: 주요 기술 선택 근거""",
    agent=architect,
    output_file="output/phase5-m0-api-spec.md",
)

task2_implementation = Task(
    description=f"""아키텍트의 API 명세를 바탕으로, 실제 구현 가이드와 배포 설정을 작성한다.

{CONTEXT}

[수행 사항]

1. 핵심 파일별 구현 가이드:
   - main.py: FastAPI 앱 초기화, 미들웨어, 라우터 마운트
   - app/core/config.py: Pydantic Settings 기반 환경 변수 관리
   - app/core/supabase.py: Supabase 클라이언트 싱글톤
   - app/core/auth.py: JWT 검증 의존성 (Depends)
   - app/api/v1/health.py: 헬스체크 엔드포인트
   - 각 파일의 핵심 코드 스니펫 (복붙 가능한 수준)

2. Docker 설정:
   - Dockerfile (멀티스테이지 빌드, Python 3.13 slim)
   - .dockerignore
   - docker-compose.yml (로컬 개발용)
   - 이미지 크기 최적화 전략

3. 배포 설정 (Railway vs Render 비교 후 선택):
   - 선택한 플랫폼의 설정 파일
   - 무료 티어 제약사항 및 대응
   - 자동 배포 트리거 (main 브랜치 push)

4. GitHub Actions CI/CD:
   - .github/workflows/ci.yml: 린트 + 테스트 + 타입체크
   - .github/workflows/deploy.yml: 배포 자동화
   - 시크릿 관리 (환경 변수)

5. 개발 환경 설정:
   - pyproject.toml (의존성 + 스크립트 + 린터 설정)
   - 로컬 실행 명령어 (uvicorn)
   - 가상환경 설정 가이드

6. 기존 server 레포 파일과의 통합:
   - .githooks/pre-commit 유지
   - .claude/agents/ 유지
   - CLAUDE.md 업데이트 필요 사항""",
    expected_output="""Phase 5 M0 구현 가이드:
1. 핵심 파일별 코드 스니펫 (복붙 가능)
2. Dockerfile + docker-compose.yml
3. 배포 플랫폼 선택 및 설정
4. GitHub Actions CI/CD 워크플로우
5. pyproject.toml (의존성 + 설정)
6. 개발 환경 설정 가이드
7. 기존 파일 통합 방안""",
    agent=backend_senior,
    context=[task1_api_spec],
    output_file="output/phase5-m0-implementation.md",
)

task3_test_plan = Task(
    description=f"""M0 완료 기준(DoD)을 검증할 테스트 케이스와 체크리스트를 작성한다.

{CONTEXT}

[M0 DoD 재확인]
1. API Health Check 성공 (GET /v1/health → 200 OK, DB 연결 상태 포함)
2. Dockerize 완료 (docker build + docker run으로 서버 기동)
3. Railway/Render 자동 배포 확인 (main push → 자동 배포 → 헬스체크 통과)

[수행 사항]

1. 단위 테스트 케이스 (pytest):
   - 헬스체크 엔드포인트 테스트
   - CORS 헤더 검증
   - JWT 검증 미들웨어 테스트 (유효/만료/누락 토큰)
   - 환경 변수 로딩 테스트
   - 에러 응답 형식 검증

2. 통합 테스트 케이스:
   - Supabase 연결 테스트 (실제 DB ping)
   - Docker 빌드 + 컨테이너 기동 테스트
   - API 응답 시간 기준 (헬스체크 < 500ms)

3. CI/CD 검증 체크리스트:
   - GitHub Actions 파이프라인 통과 기준
   - 배포 후 스모크 테스트 (프로덕션 헬스체크)
   - 롤백 절차

4. M0 완료 체크리스트:
   - 모든 DoD 항목의 Pass/Fail 기준 명확화
   - 각 항목별 검증 명령어 또는 URL
   - M1 진입 전 필수 확인사항""",
    expected_output="""Phase 5 M0 테스트 계획서:
1. 단위 테스트 케이스 목록 (pytest, 테스트 코드 스니펫 포함)
2. 통합 테스트 케이스 목록
3. CI/CD 검증 체크리스트
4. M0 완료(DoD) 체크리스트 (Pass/Fail 기준 + 검증 명령어)
5. M1 진입 전 필수 확인사항""",
    agent=qa_engineer,
    context=[task1_api_spec, task2_implementation],
    output_file="output/phase5-m0-test-plan.md",
)

# === Crew 실행 ===
crew = Crew(
    agents=[architect, backend_senior, qa_engineer],
    tasks=[task1_api_spec, task2_implementation, task3_test_plan],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 M0: FastAPI 서버 인프라 상세 설계")
    print("=" * 60)
    print(f"모델: {HIGH_PERF_MODEL}")
    print("태스크:")
    print("  1) 아키텍트 — API 명세 + 프로젝트 구조")
    print("  2) 백엔드 시니어 — 구현 가이드 + 배포 설정")
    print("  3) QA — 테스트 케이스 + DoD 체크리스트")
    print("=" * 60)
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("완료! 산출물:")
    print("  - output/phase5-m0-api-spec.md (API 명세 + 프로젝트 구조)")
    print("  - output/phase5-m0-implementation.md (구현 가이드 + 배포 설정)")
    print("  - output/phase5-m0-test-plan.md (테스트 + DoD 체크리스트)")
    print("=" * 60)
