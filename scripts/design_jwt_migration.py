"""JWT 인증 마이그레이션 설계: Legacy JWT Secret → JWT Signing Keys (JWKS + RS256)

목적: Supabase의 Legacy JWT Secret(HS256) 기반 인증을
     새로운 JWT Signing Keys(RS256/JWKS) 기반으로 전환하는 설계.

배경:
  - Supabase가 Legacy JWT Secret에서 JWT Signing Keys로 전환 중
  - 새 방식은 RS256(비대칭키) 사용, JWKS 엔드포인트 제공
  - Supabase Auth 서버는 dual support: RS256(kid 기반) 우선, HS256(레거시) 폴백

참여 에이전트:
  - 풀스택 아키텍트: JWT 인증 아키텍처 설계 + 보안 분석
  - 백엔드 시니어: 실제 구현 코드 작성 (security.py, config.py 등)

실행: source .venv/bin/activate && python scripts/design_jwt_migration.py
산출물:
  - output/jwt-migration-design.md (설계 + 구현 코드)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory_recursive, read_file

# === 컨텍스트 ===
CONTEXT = """
[프로젝트: AI Interview — JWT 인증 마이그레이션]

[현재 상태]
- server 레포: FastAPI + python-jose (HS256) + Supabase JWT Secret
- 현재 security.py:
  ```python
  from fastapi import HTTPException, Security
  from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
  from jose import JWTError, jwt
  from app.core.config import settings

  _bearer = HTTPBearer()

  async def get_current_user(auth: HTTPAuthorizationCredentials = Security(_bearer)) -> str:
      try:
          payload = jwt.decode(auth.credentials, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
          user_id: str | None = payload.get("sub")
          if user_id is None:
              raise HTTPException(status_code=401, detail="Invalid token payload")
          return user_id
      except JWTError:
          raise HTTPException(status_code=401, detail="Could not validate credentials")
  ```
- 현재 config.py에 `SUPABASE_JWT_SECRET: str = ""` 사용 중

[Supabase JWT Signing Keys 정보 — context7 조사 결과]
1. Supabase Auth 서버는 `/.well-known/jwks.json` 엔드포인트를 통해 JWKS(JSON Web Key Set)를 제공
2. 응답 형식: { "keys": [{ "kty": "RSA", "kid": "key-id-1", "use": "sig", "alg": "RS256", "n": "...", "e": "AQAB" }] }
3. Auth 서버의 JWT 검증 로직 (Go 소스):
   - 토큰 헤더에 `kid`가 있으면 → RS256 공개키로 검증 (JWKS 기반)
   - `kid`가 없고 `alg`이 HS256이면 → Legacy Secret으로 검증
   - 즉, 서버 사이드에서 dual support 제공
4. 보안 권장사항: "Asymmetric keys (RS256, ES256, EdDSA) are recommended for production. Symmetric keys (HS256) are a fallback for backward compatibility."
5. python-jose는 RS256 + 공개키(PEM) 기반 JWT 검증을 지원

[JWKS URL 패턴]
- Supabase JWKS URL: {SUPABASE_URL}/auth/v1/.well-known/jwks.json
- 또는 Supabase가 직접 제공하는 JWT Public Key(PEM)를 사용 가능

[비용 제약]
- 무자본 1인 개인, 월 $5 미만 운영
- 추가 의존성 최소화

[기술 스택]
- Python 3.13, FastAPI >= 0.115
- python-jose[cryptography] 3.3.0+
- Supabase Free Tier

[요구사항]
1. RS256(JWKS/공개키) 기반 JWT 검증을 기본으로 전환
2. HS256(Legacy Secret) 폴백 지원 — 기존 토큰 호환성 유지
3. JWKS 캐싱 — 매 요청마다 JWKS 엔드포인트를 호출하지 않도록
4. 설정 변경 최소화 — .env에 JWKS URL 또는 공개키만 추가
5. 테스트 용이성 유지 — 테스트에서 JWT 생성이 쉬워야 함
"""

# === 에이전트 정의 ===
llm = get_llm(HIGH_PERF_MODEL)

architect = Agent(
    role="풀스택 아키텍트 (Full-Stack Architect)",
    goal="Supabase JWT Signing Keys 전환을 위한 인증 아키텍처를 설계한다",
    backstory=(
        "12년차 풀스택 아키텍트. JWT, OAuth2, JWKS 기반 인증 시스템 구축 경험 다수. "
        "HS256(대칭키)에서 RS256(비대칭키)으로의 마이그레이션을 여러 프로젝트에서 수행했다. "
        "보안과 성능의 균형을 잘 잡으며, 특히 키 로테이션과 캐싱 전략에 능하다. "
        "과도한 추상화를 경계하고, 필요한 최소한의 변경만 설계한다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive],
    allow_delegation=False,
    verbose=True,
)

backend_senior = Agent(
    role="백엔드 시니어 개발자 (Backend Senior Developer)",
    goal="아키텍트의 설계를 바탕으로 security.py, config.py 등의 실제 구현 코드를 작성한다",
    backstory=(
        "9년차 백엔드 개발자. Python/FastAPI + python-jose 전문가. "
        "Supabase를 백엔드에서 직접 연동한 경험이 풍부하다. "
        "JWKS 기반 JWT 검증, 키 캐싱, 비대칭키 처리에 능하다. "
        "코드는 복붙 가능한 수준으로 작성하며, 엣지 케이스를 꼼꼼히 처리한다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive],
    allow_delegation=False,
    verbose=True,
)

# === 태스크 정의 ===

task_design = Task(
    description=f"""JWT 인증 마이그레이션 설계 및 구현 코드를 작성한다.

{CONTEXT}

[수행 사항]

1. 아키텍처 설계:
   - RS256 + JWKS 기반 JWT 검증 흐름도
   - HS256 레거시 폴백 흐름
   - JWKS 캐싱 전략 (TTL 기반, 메모리 캐시)
   - 키 로테이션 대응 방안
   - 보안 분석: RS256 vs HS256 비교, 위협 모델

2. 구현 방식 결정:
   - 방식 A: JWKS URL에서 동적으로 공개키 fetch + 캐싱
   - 방식 B: Supabase 대시보드에서 JWT Public Key(PEM)를 복사하여 환경변수로 설정
   - 방식 C: 두 방식 모두 지원 (JWKS URL 우선, PEM 폴백)
   - 각 방식의 장단점 분석 후 최적 방식 선택

3. 구현 코드 (복붙 가능한 수준):
   - app/core/security.py — JWT 검증 (RS256 우선, HS256 폴백)
   - app/core/config.py — 새 환경변수 추가
   - .env.example — 업데이트
   - tests/test_auth.py — JWT 검증 테스트 (RS256 + HS256)

4. 마이그레이션 가이드:
   - 기존 HS256에서 RS256으로의 전환 단계
   - .env 파일 변경사항
   - 롤백 방법

server 레포의 현재 코드를 확인하려면 read_file 도구를 사용할 것.
server 레포 경로: /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-server
""",
    expected_output="""JWT 인증 마이그레이션 설계서:
1. 아키텍처 설계 (흐름도, 캐싱 전략, 보안 분석)
2. 구현 방식 결정 및 근거
3. 구현 코드 (security.py, config.py, .env.example, test_auth.py)
4. 마이그레이션 가이드 (전환 단계, 롤백 방법)""",
    agent=architect,
    output_file="output/jwt-migration-design.md",
)

task_implementation = Task(
    description=f"""아키텍트의 JWT 마이그레이션 설계를 바탕으로,
실제 구현할 코드를 파일별로 정확히 작성한다.

{CONTEXT}

[수행 사항]

1. security.py 전체 코드:
   - RS256 JWKS/PEM 기반 검증 (우선)
   - HS256 Legacy Secret 폴백
   - JWKS 캐싱 (httpx 비동기 fetch, TTL 캐시)
   - 에러 핸들링 (키 fetch 실패, 토큰 만료, 잘못된 서명 등)

2. config.py 수정사항:
   - 새로 추가할 환경변수와 기존 변수의 관계
   - 하위 호환성 (기존 SUPABASE_JWT_SECRET만 설정해도 동작)

3. .env.example 업데이트:
   - 새 변수 추가 + 주석으로 설명

4. test_auth.py 테스트 코드:
   - RS256 토큰 생성 + 검증 테스트
   - HS256 폴백 테스트
   - 만료 토큰, 잘못된 서명 테스트
   - JWKS 캐시 테스트

5. pyproject.toml 의존성 변경사항 (있다면)

server 레포의 현재 코드를 확인하려면 read_file 도구를 사용할 것.
server 레포 경로: /Users/bongseok.sa/Desktop/workspace/personal/AI-Interview/AI-Interview-server
""",
    expected_output="""JWT 인증 구현 상세:
1. security.py 전체 코드 (복붙 가능)
2. config.py 수정사항
3. .env.example 업데이트
4. test_auth.py 전체 코드
5. pyproject.toml 변경사항
6. 파일별 변경 요약""",
    agent=backend_senior,
    context=[task_design],
    output_file="output/jwt-migration-implementation.md",
)

# === Crew 실행 ===
crew = Crew(
    agents=[architect, backend_senior],
    tasks=[task_design, task_implementation],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("JWT 인증 마이그레이션 설계: HS256 → RS256 (JWKS)")
    print("=" * 60)
    print(f"모델: {HIGH_PERF_MODEL}")
    print("태스크:")
    print("  1) 아키텍트 — JWT 인증 아키텍처 설계 + 보안 분석")
    print("  2) 백엔드 시니어 — 실제 구현 코드 작성")
    print("=" * 60)
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("완료! 산출물:")
    print("  - output/jwt-migration-design.md (설계)")
    print("  - output/jwt-migration-implementation.md (구현 코드)")
    print("=" * 60)
