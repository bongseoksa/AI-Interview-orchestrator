"""Phase 5 계획 보완 논의 — Advisor REJECT 피드백 수용 후 재검토

목적: 외부인사의 REJECT(3.5/10) 판정을 수용하여 3개 핵심 권고사항을 반영한
      보완 계획을 수립하고, 재검토를 받는다.
참여 에이전트: PM(전략 수정) + Architect(서버 인프라 설계) + PjM(타임라인 수정) + Advisor(재검토)

권고사항:
1. [Infrastructure First] Phase 5 시작과 동시에 Python 서버(FastAPI) 구축
2. [Focus on Domain] 프론트엔드 특화 검증 데이터셋 확보로 기술적 해자 구축
3. [Monetization Experiment] Phase 5부터 Paywall/Credit 시스템 즉시 테스트

실행: source .venv/bin/activate && python scripts/revise_phase5_plan.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory_recursive, read_file
from src.tools.notion_tools import list_notion_pages, read_notion_page

# === 컨텍스트: 이전 논의 결과 + Advisor 피드백 ===
PREVIOUS_CONTEXT = """
[프로젝트: AI Interview]
프론트엔드 엔지니어를 위한 AI 기반 모의 인터뷰 연습 서비스.
운영: 무자본 1인 개인, 무료 서비스만 활용.

[현재 상태]
- Phase 0~3: 완료 (에이전트 시스템, 시장 조사, 설계, 데이터/인프라)
- Phase 4: P0 기능 7개 모두 구현 완료 (GO Conditional — 운영 부채 해결 조건부)
  1. 커리큘럼 대시보드 (9개 카테고리) ✅
  2. 개념 학습 모듈 (SSG 151페이지) ✅
  3. 메타인지 진단 (결과 리포트) ✅
  4. 랜딩 페이지 ✅
  5. Supabase Auth + Lazy Auth ✅
  6. 프로그레스 트래킹 ✅
  7. Default Tip (151개) ✅

[기술 스택]
- web: Next.js 16, TypeScript, Tailwind CSS, shadcn/ui, Supabase (Auth+DB), i18n(ko/en)
- server: Python (미착수 — 현재 GET /health 엔드포인트만 존재)
- orchestrator: CrewAI v1.15.4, Ollama (Gemma 4 26B/12B), 11 Crew
- DB: Supabase PostgreSQL (nodes, questions, user_progress 테이블, RLS 적용)
- 시드 데이터: 151개 Q&A (9 카테고리, 3 난이도), default_tip 생성 완료

[이전 논의 — PM 전략 (GO Conditional)]
- 3개월 로드맵: Month 1 안정화+런칭, Month 2 AI 면접 엔진, Month 3 UX 고도화+수익 모델
- 성공 지표: Weekly Active Learning Sessions

[이전 논의 — PjM 실행 계획 (6주 타임라인)]
- W1: Phase 4 부채 청산
- W2: AI Interviewer Core (State Machine + Prompt)
- W3-4: RAG & Feedback (답변 검증 + 피드백 엔진)
- W5: Interview UI/UX (채팅 인터페이스)
- W6: Beta Launch

[외부인사 판정: REJECT (3.5/10)]

[외부인사 핵심 비판 3개]
1. **현실성 FAIL** — Python Backend 미구축 상태에서 RAG/AI 엔진 계획은 비현실적.
   "엔진 설계도는 그렸는데, 공장이 아직 안 지어진 상태"
   1인 개발자가 운영 부채 + 핵심 기능 + 마케팅을 동시 수행은 물리적 불가능 (관리자의 함정)

2. **전략적 FAIL** — "동적 질문 생성"은 이미 GPT-4 Wrapper들이 구현 중.
   Domain-Specific한 가치(프론트엔드 특화 검증 데이터셋)가 아닌 경험적 차별화에 머물러 있음.
   수익 모델 실험이 Month 3은 너무 늦음 — 초기 유입 시 Paywall 테스트 필요.

3. **기술적 FAIL** — RAG 구현에 Vector DB, 임베딩, Retrieval 로직 필요.
   Next.js Edge Function만으로 RAG 파이프라인 구현 불가.
   Supabase Free Tier 한계 + UX 트레이드오프 관리 전략 부재.

[외부인사 핵심 권고사항 3개]
1. [Infrastructure First] Phase 5 시작과 동시에 Python 서버(FastAPI) 구축을 M1 최우선 과제로
2. [Focus on Domain] "동적 질문" 대신 프론트엔드 특화 검증 데이터셋 확보로 기술적 해자 구축
3. [Monetization Experiment] Phase 5부터 Paywall/Credit 시스템으로 지불 의사 즉시 테스트

[외부인사 추가 지적]
- Data Poisoning Risk: 사용자 답변을 학습 데이터로 활용 시 오염 방지 기제 누락
- DevOps 복잡성: Next.js + Python Backend 통합 배포 전략 부재
- Lazy Auth: 브라우저 캐시 삭제 시 데이터 복구 플랜 미비
"""

# === 에이전트 정의 ===
llm = get_llm(HIGH_PERF_MODEL)

pm = Agent(
    role="프로덕트 매니저 (Product Manager)",
    goal="외부인사의 REJECT 피드백을 수용하여 Phase 5 제품 전략을 근본적으로 수정한다",
    backstory=(
        "8년차 프로덕트 매니저. 외부인사의 REJECT 판정을 진지하게 받아들이고, "
        "3개 핵심 권고사항(Infrastructure First, Domain Focus, Monetization)을 "
        "전략에 통합한다. 기존 계획의 문제점을 솔직히 인정하고, "
        "1인 개발 제약 하에서 현실적으로 실행 가능한 수정안을 제시한다. "
        "특히 수익 모델 검증 시점을 앞당기고, 차별화 전략을 구체화해야 한다."
    ),
    llm=llm,
    tools=[read_file, read_notion_page, list_notion_pages],
    allow_delegation=False,
    verbose=True,
)

architect = Agent(
    role="풀스택 아키텍트 (Full-Stack Architect)",
    goal="Phase 5에서 Python 서버(FastAPI) 인프라를 설계하고, RAG 파이프라인 아키텍처를 제안한다",
    backstory=(
        "10년차 풀스택 아키텍트. FastAPI + Supabase + LLM 통합 경험 다수. "
        "1인 개발 프로젝트에서 최소 인프라로 최대 효과를 내는 설계에 능하다. "
        "현재 server 레포에는 GET /health만 있는 상태이며, "
        "여기에 AI 면접 엔진(RAG, Prompt Engineering, 피드백 생성)을 "
        "단계적으로 구축하는 아키텍처를 설계해야 한다. "
        "Supabase의 pgvector 확장, Ollama 로컬 모델 활용, "
        "배포 전략(Vercel + 별도 Python 서버)을 고려한다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive, read_notion_page],
    allow_delegation=False,
    verbose=True,
)

pjm = Agent(
    role="프로젝트 매니저 (Project Manager)",
    goal="수정된 전략과 아키텍처를 바탕으로 Phase 5 실행 타임라인을 재수립한다",
    backstory=(
        "7년차 프로젝트 매니저. 애자일 스크럼 마스터 자격 보유. "
        "이전 계획이 REJECT된 핵심 이유(서버 미구축, 비현실적 타임라인)를 반영하여 "
        "서버 구축 기간을 포함한 현실적인 타임라인을 재수립한다. "
        "1인 개발자의 물리적 한계를 고려하여 병렬 작업 최소화, "
        "순차적 의존성 기반의 실행 계획을 세운다."
    ),
    llm=llm,
    tools=[read_file, list_directory_recursive, read_notion_page, list_notion_pages],
    allow_delegation=False,
    verbose=True,
)

advisor = Agent(
    role="외부인사 (External Advisor)",
    goal="보완된 계획이 이전 REJECT 사유를 충분히 해소했는지 재검증한다",
    backstory=(
        "15년차 스타트업 자문위원 겸 엔젤 투자자. "
        "이전 회의에서 3.5/10으로 REJECT했으며, 3개 핵심 권고사항을 제시했다. "
        "이번 재검토에서는 해당 권고사항이 실질적으로 반영되었는지, "
        "단순히 문서만 수정한 것이 아닌 실행 가능한 수준으로 개선되었는지를 검증한다. "
        "여전히 호의적이지 않으며, Pass 기준은 6/10 이상이다."
    ),
    llm=llm,
    tools=[read_file, read_notion_page],
    allow_delegation=False,
    verbose=True,
)

# === 태스크 정의 ===

task1_pm_revised_strategy = Task(
    description=f"""외부인사의 REJECT(3.5/10) 판정을 수용하여 Phase 5 전략을 근본적으로 수정한다.

{PREVIOUS_CONTEXT}

[수행 사항]
1. 기존 전략의 문제점 인정:
   - 서버 인프라 없이 AI 엔진을 계획한 모순
   - "동적 질문"이라는 모호한 차별화
   - 수익 모델 검증 지연

2. 수정된 Phase 5 전략:
   - [Infrastructure First 반영] 서버 구축을 Phase 5 최우선으로
   - [Domain Focus 반영] 프론트엔드 도메인 특화 전략 구체화
     - 기존 151개 Q&A 데이터를 어떻게 활용할 것인가?
     - "프론트엔드 성능 최적화", "React 내부 동작 원리" 등 고급 주제 특화
     - ChatGPT가 못하는 것: 구조화된 평가 루브릭 + 도메인 데이터 독점
   - [Monetization 반영] Phase 5 내 수익 실험 구체화
     - 무료: 기본 진단 + 3개 면접 질문
     - 유료: 상세 피드백 리포트 + 무제한 면접 + 취약점 분석
     - 결제 시스템: Stripe/Toss Payments 중 선택 기준

3. 수정된 성공 지표:
   - 학습 완결성 지표 외에 전환율(Conversion Rate) 지표 추가
   - Free → Paid 전환 가설 설정

4. Lazy Auth 보완:
   - 비인증 사용자 데이터 임시 보존 방법 구체화""",
    expected_output="""수정된 제품 전략 보고서:
1. 기존 전략 문제점 자기 진단 (3개 FAIL 항목별)
2. 수정된 Phase 5 전략 (3개 권고사항 반영)
3. 차별화 전략 구체화 (Domain Focus)
4. 수익 모델 실험 계획 (Monetization)
5. 수정된 성공 지표 및 KPI
6. Lazy Auth 보완 방안""",
    agent=pm,
    output_file="output/revised-pm-strategy.md",
)

task2_architect_infra = Task(
    description=f"""Phase 5에서 필요한 서버 인프라와 AI 엔진 아키텍처를 설계한다.

{PREVIOUS_CONTEXT}

[현재 server 레포 상태]
- FastAPI main.py에 GET /health만 구현
- Python 3.13, 가상환경 준비 완료
- DB: Supabase PostgreSQL (nodes, questions, user_progress)

[설계 요구사항]
1. FastAPI 서버 아키텍처:
   - API 엔드포인트 설계 (면접 시작/질문 생성/답변 평가/피드백)
   - 인증 연동 (Supabase JWT 검증)
   - CORS 설정 (Next.js 프론트엔드 연동)

2. AI 면접 엔진 설계:
   - 면접 상태 머신 (State Machine): 시작 → 질문 → 답변 → 평가 → 다음질문/종료
   - 질문 생성 방식: 기존 151개 Q&A 데이터 기반 + LLM 꼬리 질문
   - 답변 평가 방식: 루브릭 기반 채점 (정확성/깊이/실무 연관성)

3. RAG 파이프라인 (현실적 1인 개발 범위):
   - 옵션 A: Supabase pgvector + 임베딩 (본격 RAG)
   - 옵션 B: 키워드 매칭 + 시드 데이터 검색 (경량 대안)
   - 옵션 C: 단계적 도입 (B로 시작 → A로 발전)
   - 각 옵션의 구현 난이도, 소요 시간, 품질 비교

4. 배포 전략:
   - Next.js (Vercel) + FastAPI 서버 배포 옵션
   - 무료/저비용 Python 서버 호스팅 (Railway, Render, Fly.io 등)
   - 환경변수 관리 및 CI/CD

5. 비용 분석:
   - Supabase Free Tier 한계 분석 (DB, Auth, Storage)
   - LLM 비용: Ollama 로컬 vs Cloud API 비교
   - 서버 호스팅 비용 (무자본 제약 반영)

orchestrator 레포의 기존 아키텍처 산출물을 참고할 것:
- read_file로 output/ 디렉토리의 기존 설계 문서 확인
- list_directory_recursive로 server 레포 구조 파악""",
    expected_output="""서버 인프라 및 AI 엔진 아키텍처 설계서:
1. FastAPI 서버 구조 (디렉토리 구조, 엔드포인트 목록, 인증 연동)
2. AI 면접 엔진 상태 머신 설계
3. 질문 생성 / 답변 평가 로직 설계
4. RAG 파이프라인 옵션 비교 및 권장안
5. 배포 전략 및 인프라 구성도
6. 비용 분석 및 무자본 제약 대응""",
    agent=architect,
    context=[task1_pm_revised_strategy],
    output_file="output/revised-architect-infra.md",
)

task3_pjm_revised_plan = Task(
    description=f"""수정된 전략과 아키텍처를 바탕으로 Phase 5 실행 타임라인을 재수립한다.

{PREVIOUS_CONTEXT}

[이전 계획의 문제점 — 외부인사 지적]
- 서버 구축 기간이 빠져있었음 (가장 큰 모순)
- 1인 개발자가 동시에 너무 많은 것을 진행하려 함 (관리자의 함정)
- RAG 구현 난이도를 과소 평가함

[수정 방향]
1. 서버 구축(FastAPI)을 Phase 5 M0로 선행 배치
2. 병렬 작업 최소화 — 한 번에 하나의 핵심 태스크만 집중
3. RAG는 경량 버전(키워드 매칭)으로 시작하여 단계적 고도화
4. 수익 실험은 별도 마일스톤이 아닌, 기존 마일스톤에 통합
5. 운영 부채 해결은 Phase 4 마무리로 W1에 집중

[재수립 요구사항]
1. Phase 5 마일스톤 재분해:
   - M0: 서버 인프라 구축 (FastAPI + 배포 + CI/CD)
   - M1: AI 면접 코어 (상태 머신 + 질문 선택 + 기본 평가)
   - M2: 피드백 엔진 (답변 분석 + 루브릭 채점 + 리포트)
   - M3: 면접 UI (채팅 인터페이스 + 실시간 상호작용)
   - M4: 수익 실험 + Beta Launch
   - 각 마일스톤별 DoD, 담당 에이전트, 예상 기간

2. 에이전트 활용 순서:
   - 아키텍트의 설계를 기반으로 Crew 실행 순서 재정의
   - 서버 구축에 CodegenCrew 활용 계획

3. 현실적 타임라인:
   - 1인 개발자 기준 주 단위 계획 (주 30~40시간 기준)
   - 각 주의 핵심 목표 1개만 설정 (멀티태스킹 금지)
   - 버퍼 기간 포함

4. 리스크 대응 업데이트:
   - 서버 구축 지연 시 대안
   - LLM 품질 미달 시 fallback""",
    expected_output="""수정된 실행 계획서:
1. Phase 5 마일스톤 재분해 (M0~M4, DoD, 담당, 기간)
2. 주 단위 타임라인 (각 주 핵심 목표 1개)
3. 에이전트 활용 계획 (Crew 실행 순서)
4. 리스크 대응 업데이트
5. Phase 4 마무리 → Phase 5 전환 체크리스트""",
    agent=pjm,
    context=[task1_pm_revised_strategy, task2_architect_infra],
    output_file="output/revised-pjm-plan.md",
)

task4_advisor_recheck = Task(
    description=f"""보완된 계획(PM 수정 전략 + Architect 인프라 설계 + PjM 수정 타임라인)을 재검증한다.

{PREVIOUS_CONTEXT}

[이전 판정: REJECT (3.5/10)]
[Pass 기준: 6/10 이상]

[재검증 기준]
1. 권고사항 반영 검증:
   - [Infrastructure First] Python 서버 구축이 실행 계획에 구체적으로 포함되었는가?
     - 단순히 "서버를 만든다"가 아닌, 어떤 기술 스택으로, 어떤 순서로, 어디에 배포하는지가 명확한가?
   - [Focus on Domain] 차별화 전략이 "프론트엔드 특화"로 구체화되었는가?
     - 기존 151개 Q&A 데이터의 활용 방법이 명확한가?
     - ChatGPT/경쟁사 대비 실질적 우위가 있는가?
   - [Monetization] 수익 실험이 Phase 5 내에 포함되었는가?
     - Free/Paid 경계가 합리적인가?
     - 결제 시스템 선택이 현실적인가?

2. 아키텍처 검증:
   - RAG 파이프라인이 1인 개발 범위 내에서 실현 가능한가?
   - 서버 배포 비용이 무자본 제약을 충족하는가?
   - Supabase Free Tier 한계를 실질적으로 해결하는가?

3. 타임라인 검증:
   - 서버 구축 기간이 현실적인가?
   - 주 1개 핵심 목표가 실제로 지켜질 수 있는가?
   - 버퍼가 충분한가?

4. 잔여 리스크:
   - 여전히 해결되지 않은 문제는?
   - 새로 발생한 리스크는?

이전 REJECT의 핵심 사유가 해소되었는지에 집중하여 재검증할 것.
단순히 문서를 정리한 것이 아닌, 실질적인 개선이 이루어졌는지 판단할 것.""",
    expected_output="""재검증 보고서:
1. 권고사항 반영 검증 (3개 항목별 Pass/Fail/Partial)
2. 아키텍처 검증 (실현 가능성 평가)
3. 타임라인 검증 (현실성 평가)
4. 잔여 리스크 및 신규 리스크
5. 이전 대비 개선점 요약
6. 최종 재판정 + 점수 (/10)
7. 조건부 승인 시 필수 전제조건""",
    agent=advisor,
    context=[task1_pm_revised_strategy, task2_architect_infra, task3_pjm_revised_plan],
    output_file="output/revised-advisor-recheck.md",
)

# === Crew 실행 ===
crew = Crew(
    agents=[pm, architect, pjm, advisor],
    tasks=[task1_pm_revised_strategy, task2_architect_infra, task3_pjm_revised_plan, task4_advisor_recheck],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 계획 보완 논의 — Advisor REJECT 피드백 수용 후 재검토")
    print("=" * 60)
    print(f"모델: {HIGH_PERF_MODEL}")
    print("태스크:")
    print("  1) PM 전략 수정 (3개 권고사항 반영)")
    print("  2) Architect 서버 인프라 설계 (Infrastructure First)")
    print("  3) PjM 타임라인 재수립 (서버 구축 포함)")
    print("  4) Advisor 재검토 (Pass 기준: 6/10)")
    print("=" * 60)
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("완료! 산출물:")
    print("  - output/revised-pm-strategy.md (PM 수정 전략)")
    print("  - output/revised-architect-infra.md (서버 인프라 설계)")
    print("  - output/revised-pjm-plan.md (PjM 수정 타임라인)")
    print("  - output/revised-advisor-recheck.md (Advisor 재검토)")
    print("=" * 60)
