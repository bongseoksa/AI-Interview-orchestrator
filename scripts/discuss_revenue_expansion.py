"""수익모델 + 다직군 확장 전략 검토 — PM/PjM 전략 논의 + 외부인사 검증

실행: python scripts/discuss_revenue_expansion.py
산출물:
  - output/revenue-pm-strategy.md (PM 전략 평가)
  - output/revenue-pjm-execution.md (PjM 실행 계획)
  - output/revenue-advisor-review.md (외부인사 검증)
"""

from crewai import Agent, Crew, Process, Task

from src.config.llm import get_llm, HIGH_PERF_MODEL

CONTEXT = """
[AI Interview 서비스 현황]
- 프론트엔드 엔지니어를 위한 AI 기반 CS 기술 학습 및 모의 면접 서비스
- Phase 4 완료: MVP P0 7개 기능 구현 (학습/진단/인증/진도/팁), Phase 5 준비 중
- 운영: 무자본 1인 개인, 사업자 미등록, 도메인 미구입
- 기술: Next.js 16(web) + FastAPI(server, Phase 5 M0) + CrewAI+Ollama(orchestrator)
- 151개 학습 노드, 9개 카테고리, Q&A DB 구축 완료

[이전 의사결정 — 수익모델]
- Phase 5 M4에서 Freemium + Credit 즉시 실험 확정
- Free: 9개 카테고리 기본 학습 + 일 3문 인터뷰 + 답변 요약만
- Paid: 무제한 인터뷰 + 상세 Rubric 채점 + 취약점 분석 로드맵
- 결제: Stripe 우선 (글로벌), Toss Payments 전환 가능

[이전 의사결정 — 광고 수익모델 검토 (웹서치 기반)]
- Freemium + 광고 하이브리드 모델 제안됨
- Stage 1 (Beta): 무료 + AdSense 광고 -> 트래픽 검증
- Stage 2 (Growth): Freemium 도입 — Free(일 3문 + 광고) / Paid(무제한 + 광고 제거 + 상세 채점)
- Stage 3 (Scale): Stripe/Toss Payments 결제 연동, 구독 모델
- 제휴 마케팅: 개발 도서/강의 플랫폼 제휴 (인프런, 유데미 등)

[검토 요청 사항]
1. 광고 수익모델의 적합성 재검토
   - AI 면접 학습 서비스에 광고가 UX를 해치지 않는가?
   - 사업자등록 전 단계에서 광고 수익이 현실적인가?
   - AdSense 승인 요건 (트래픽, 콘텐츠 양, 독창성)을 충족할 수 있는가?
   - 광고 수익 vs 사용자 경험 트레이드오프
   - 학습 서비스에서 광고는 오히려 신뢰도를 떨어뜨리지 않는가?

2. 다직군 확장 전략 검토
   - 현재: 프론트엔드 특화 (9개 카테고리, 151개 노드)
   - 확장 계획: 백엔드, 기획(PM), UXUI, 데이터 매니저, 그 외 직군
   - 확장 순서/우선순위는 어떻게 정해야 하는가?
   - 카테고리 구조를 어떻게 설계해야 확장이 용이한가?
   - 직군별 콘텐츠 차별화 전략
   - TAM 확대 효과 vs 집중력 분산 리스크
   - 수익모델과 확장 전략의 연계 (직군별 유료화 가능성)

3. 수익모델과 확장 전략의 최적 조합
   - 광고 vs Freemium vs 구독 vs 1회 결제 — 어떤 조합이 최적인가?
   - 초기 트래픽이 적은 상태에서 현실적 수익 전략은?
   - 다직군 확장 시 수익모델을 어떻게 적용할 것인가?
"""


def run():
    llm = get_llm(HIGH_PERF_MODEL)

    # === PM (전략 평가) ===
    pm = Agent(
        role="프로덕트 매니저 (Product Manager)",
        goal="AI Interview 서비스의 수익모델과 다직군 확장 전략을 전략적으로 평가하고 최적 방안을 제시한다.",
        backstory=(
            "8년차 B2C EdTech 프로덕트 매니저. "
            "Duolingo, Coursera, 인프런 등 학습 서비스의 수익화 전략을 깊이 연구해왔다. "
            "광고 수익, Freemium, 구독 모델의 장단점을 실제 데이터로 비교 분석할 수 있다. "
            "서비스 확장 시 '집중 vs 확산'의 트레이드오프를 냉정하게 판단한다. "
            "스코프 크립을 경계하며 MVP와 후순위를 분리하는 습관이 체화되어 있다."
        ),
        llm=llm,
        verbose=True,
    )

    # === PjM (실행 계획) ===
    pjm = Agent(
        role="프로젝트 매니저 (Project Manager)",
        goal="수익모델 도입과 다직군 확장의 구체적 실행 계획, 타임라인, 기술적 선행 조건을 정의한다.",
        backstory=(
            "7년차 애자일 프로젝트 매니저. "
            "1인 개발 환경에서의 현실적 실행 가능성을 최우선으로 고려한다. "
            "사업자등록, 결제 시스템 연동, 콘텐츠 파이프라인 등 비기술적 태스크도 "
            "프로젝트 타임라인에 반영하는 것을 원칙으로 한다. "
            "모호한 스펙은 모호한 결과물을 만든다는 신념으로 엣지 케이스를 명시한다."
        ),
        llm=llm,
        verbose=True,
    )

    # === 외부인사 (Devil's Advocate) ===
    advisor = Agent(
        role="외부인사 (External Advisor)",
        goal="수익모델과 확장 전략의 맹점과 리스크를 비우호적이고 냉정하게 지적한다.",
        backstory=(
            "15년차 스타트업 자문위원 겸 엔젤 투자자. "
            "수백 개의 초기 서비스 수익화 시도를 지켜보며 '왜 이 수익모델이 실패하는가'를 먼저 묻는 습관이 체화되어 있다. "
            "특히 EdTech 서비스의 광고 수익 함정, 무분별한 확장으로 인한 실패 사례를 잘 알고 있다. "
            "'좋다/괜찮다' 표현을 절대 사용하지 않으며, 모든 피드백에 구체적 근거와 반례를 포함한다. "
            "10점 만점 스코어링으로 최종 평가한다."
        ),
        llm=llm,
        verbose=True,
    )

    # === Task 1: PM 전략 평가 ===
    pm_strategy = Task(
        description=f"""
{CONTEXT}

[PM 전략 평가 지시]
위 컨텍스트를 기반으로 다음 3가지를 전략적으로 평가하라:

1. **광고 수익모델 적합성 판정**
   - AI 면접 학습 서비스에서 광고가 적합한가? (UX 영향, 브랜드 신뢰도)
   - 학습 중 광고 노출이 '학습 몰입'을 방해하지 않는가?
   - 초기 트래픽 부족 상태에서 AdSense 수익이 의미있는 수준인가?
   - 경쟁사(LeetCode, GreatFrontEnd, 인프런)의 수익모델 분석
   - GO / HOLD / REJECT 판정 + 근거

2. **다직군 확장 전략 (프론트엔드 → 풀스택)**
   - 확장 직군 우선순위 제안 (시장 규모, 콘텐츠 재활용도, 경쟁 강도 기준)
   - 카테고리 아키텍처 설계 방향 (직군별 독립 vs 공유 구조)
   - 각 직군별 TAM/SAM 추정 및 수익 잠재력
   - 확장 시점: Phase 5 내인지, Phase 6 이후인지

3. **최적 수익모델 조합 제안**
   - 광고/Freemium/구독/1회결제/제휴마케팅 중 최적 조합
   - Phase별 수익모델 로드맵 (Phase 5 → 6 → 7)
   - 1인 운영에서 수익모델 운영 공수 최소화 방안
""",
        expected_output=(
            "수익모델 + 다직군 확장 전략 보고서 (마크다운). "
            "광고 적합성 GO/HOLD/REJECT 판정, 직군 확장 우선순위, "
            "최적 수익모델 조합, Phase별 로드맵 포함."
        ),
        agent=pm,
        output_file="output/revenue-pm-strategy.md",
    )

    # === Task 2: PjM 실행 계획 ===
    pjm_execution = Task(
        description=f"""
{CONTEXT}

PM의 전략 평가를 기반으로 다음의 구체적 실행 계획을 수립하라:

1. **수익모델 도입 실행 계획**
   - 사업자등록 절차 및 타임라인 (간이과세 vs 일반과세, 비상주사무실)
   - 광고/결제 시스템 도입 시 기술적 선행 조건
   - AdSense 승인까지의 예상 기간 및 준비 사항
   - Stripe/Toss Payments 연동 기술 스펙

2. **다직군 확장 실행 계획**
   - 카테고리 DB 스키마 확장 설계 (현재 9개 카테고리 → 직군별 확장)
   - 콘텐츠 파이프라인: 새 직군의 Q&A 시드 데이터 생성 방법
   - Orchestrator Crew 활용: ResearchCrew로 각 직군 시장 조사 → DataCrew로 시드 생성
   - 예상 공수 (1인 개발 기준)

3. **통합 타임라인**
   - Phase 5 마일스톤과의 연계
   - 수익모델 도입과 직군 확장의 병행/순차 여부
   - 리스크 및 블로커 목록
""",
        expected_output=(
            "수익모델 + 다직군 확장 실행 계획서 (마크다운). "
            "사업자등록 절차, 기술 선행조건, DB 스키마 확장 설계, "
            "콘텐츠 파이프라인, 통합 타임라인, 리스크 목록 포함."
        ),
        agent=pjm,
        context=[pm_strategy],
        output_file="output/revenue-pjm-execution.md",
    )

    # === Task 3: 외부인사 검증 ===
    advisor_review = Task(
        description=f"""
{CONTEXT}

PM의 전략 평가와 PjM의 실행 계획을 검토하고 Devil's Advocate 관점에서 검증하라.

[검증 포인트]
1. **광고 수익모델 비판**
   - 학습 서비스에 광고를 넣는 것이 정말 합리적인가?
   - DAU 100~1000 수준에서 AdSense 월 수익 예측치는?
   - 광고가 서비스의 '전문성' 이미지를 훼손하지 않는가?
   - 광고 수익을 위해 투입해야 하는 공수 대비 실제 수익은?

2. **다직군 확장 비판**
   - 프론트엔드도 아직 검증 안 된 상태에서 확장은 시기상조 아닌가?
   - 직군별 콘텐츠 품질을 1인이 관리할 수 있는가?
   - "모든 직군을 커버한다"는 것이 차별화가 아니라 희석이 될 수 있다
   - 경쟁사가 이미 멀티 직군을 제공하는 상황에서 후발주자의 우위는?

3. **수익모델 + 확장의 함정**
   - 수익 없이 확장하면 비용만 증가하는 '죽음의 계곡' 리스크
   - 1인 운영에서 사업자등록, 세금 신고, 법률 준수까지 감당 가능한가?
   - Phase 5(서버 구축)도 안 했는데 수익모델/확장을 논하는 것이 우선순위 역전 아닌가?

[평가 기준]
- 10점 만점으로 전체 계획 스코어링
- PASS(7점 이상) / CONDITIONAL PASS(5~6점) / REJECT(4점 이하)
- 각 지적사항에 대한 구체적 대안 또는 조건 제시
""",
        expected_output=(
            "외부인사 검증 보고서 (마크다운). "
            "광고/확장/수익모델 각각에 대한 비판적 분석, "
            "10점 만점 스코어링, PASS/REJECT 판정, "
            "구체적 조건부 승인 전제 목록 포함."
        ),
        agent=advisor,
        context=[pm_strategy, pjm_execution],
        output_file="output/revenue-advisor-review.md",
    )

    crew = Crew(
        agents=[pm, pjm, advisor],
        tasks=[pm_strategy, pjm_execution, advisor_review],
        process=Process.sequential,
        verbose=True,
    )

    print("\n=== 수익모델 + 다직군 확장 전략 검토 시작 ===")
    print("참여 에이전트: PM(전략평가) + PjM(실행계획) + 외부인사(검증)")
    print("=" * 60)

    result = crew.kickoff()

    print("\n=== 검토 완료 ===")
    print("산출물:")
    print("  - output/revenue-pm-strategy.md (PM 전략 평가)")
    print("  - output/revenue-pjm-execution.md (PjM 실행 계획)")
    print("  - output/revenue-advisor-review.md (외부인사 검증)")

    return result


if __name__ == "__main__":
    run()
