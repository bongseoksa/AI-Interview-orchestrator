"""Unit Economics 계산서 — 외부인사 REJECT 해소를 위한 손익분기점 분석

외부인사 REJECT (4/10) 조건부 승인 사항 #1:
"사용자 1인당 예상 API 비용(Token Cost) 대비,
 Freemium 모델의 결제 전환율에 따른 Break-even Point 계산서를 제출할 것"

실행: PYTHONPATH=. python scripts/calc_unit_economics.py
산출물:
  - output/unit-economics-architect.md (아키텍트 비용 분석)
  - output/unit-economics-pm.md (PM 수익/가격 전략)
  - output/unit-economics-advisor.md (외부인사 재검증)
"""

from crewai import Agent, Crew, Process, Task

from src.config.llm import get_llm, HIGH_PERF_MODEL

COST_DATA = """
[인프라 비용 데이터 — 실제 확정 사항]

1. 현재 인프라 (Phase 4 완료 상태)
   - Vercel: Free Tier (100GB bandwidth, 무제한 배포)
   - Supabase: Free Tier (500MB DB, 50,000 MAU auth, 1GB storage)
   - Ollama: 로컬 실행 (비용 $0, M4 Pro 48GB 맥북에서 구동)
   - 도메인: 연 1~3만원 ($10~25/year)
   - 총 고정 비용: ~$2/month (도메인 할부 기준)

2. Phase 5 추가 인프라 (확정 계획)
   - FastAPI 서버: Railway/Render 배포 (Free Tier → $5~7/month at scale)
   - 서비스 LLM: Groq 또는 DeepSeek (저비용 고속)
     - Groq: Llama 3.1 70B — $0.59/M input tokens, $0.79/M output tokens
     - DeepSeek V3: $0.27/M input tokens, $1.10/M output tokens
     - DeepSeek R1 (추론): $0.55/M input tokens, $2.19/M output tokens
   - Supabase Pro (필요 시): $25/month (8GB DB, unlimited auth)
   - 총 예상 고정 비용: $5~32/month

3. 사용자 인터뷰 세션당 토큰 사용량 추정
   - 질문 1개 생성: ~500 input tokens + ~300 output tokens
   - 답변 평가 (Rubric 채점): ~1,000 input tokens + ~500 output tokens
   - 후속 질문 (꼬리 질문) 1회: ~800 input tokens + ~400 output tokens
   - 세션 전체 (5문 기준):
     - Input: ~11,500 tokens (질문5 + 평가5 + 꼬리5)
     - Output: ~6,000 tokens (답변5 + 평가5 + 꼬리5)
   - 세션 요약 리포트: ~2,000 input + ~1,000 output tokens
   - 총 세션당: ~13,500 input + ~7,000 output tokens

4. Free 사용자 제한 (확정)
   - 일 3문 인터뷰 (꼬리 질문 없음, 요약 답변만)
   - 세션당: ~4,500 input + ~2,400 output tokens

5. Paid 사용자 기능 (확정)
   - 무제한 인터뷰 + 상세 Rubric 채점 + 취약점 분석 로드맵
   - 평균 일 2세션 × 5문 가정

6. 기존 데이터 자산
   - 151개 학습 노드 (SSG 정적 — API 비용 $0)
   - 151개 Default Tip (정적 — API 비용 $0)
   - 9개 카테고리 대시보드 (정적 — API 비용 $0)
   - 진단 질문 (정적 세트 — API 비용 $0)

7. 경쟁사 가격 참고
   - LeetCode Premium: $35/month, $159/year
   - GreatFrontEnd: $15/month, $90/year
   - InterviewCake: $249 lifetime
   - 인프런 월 구독: 월 24,900원 (~$18)

8. 환율 기준: 1 USD = 1,350 KRW

[외부인사 REJECT 사유 — 해소 대상]
1. Unit Economics 부재 — 1인당 API 비용 vs 수익 구조 미계산
2. 트래픽 늘수록 적자 확대 구조 우려
3. Break-even Point 미제시
4. 광고 모델 폐기 확정 → Subscription + Affiliate만으로 수익성 증명 필요
"""


def run():
    llm = get_llm(HIGH_PERF_MODEL)

    # === Architect (비용 분석) ===
    architect = Agent(
        role="풀스택 아키텍트 (Full-stack Architect)",
        goal="AI Interview 서비스의 인프라 비용과 사용자당 API 비용을 정밀하게 계산한다.",
        backstory=(
            "10년차 클라우드 아키텍트. LLM API 비용 최적화와 서버리스 인프라 설계의 전문가. "
            "Token 단위 비용 계산, 캐싱 전략에 의한 비용 절감, 트래픽 단계별 인프라 스케일링 비용을 "
            "스프레드시트 수준의 정밀도로 산출할 수 있다. "
            "모든 수치에 단위와 계산 과정을 명시하며, 낙관적 추정보다 보수적 추정을 선호한다."
        ),
        llm=llm,
        verbose=True,
    )

    # === PM (수익/가격 전략) ===
    pm = Agent(
        role="프로덕트 매니저 (Product Manager)",
        goal="Unit Economics 기반으로 최적 가격 정책과 손익분기점을 도출한다.",
        backstory=(
            "8년차 B2C SaaS 프로덕트 매니저. Spotify, Notion, Figma 등의 Freemium 전환율 벤치마크를 "
            "숙지하고 있으며, EdTech 서비스의 가격 민감도와 WTP(Willingness to Pay)를 데이터 기반으로 "
            "판단한다. ARPU, LTV, CAC, Payback Period 등 SaaS 핵심 지표를 계산하고, "
            "가격 정책의 심리학적 효과(앵커링, 디코이)까지 고려한다."
        ),
        llm=llm,
        verbose=True,
    )

    # === 외부인사 (재검증) ===
    advisor = Agent(
        role="외부인사 (External Advisor)",
        goal="Unit Economics 계산서를 이전 REJECT 사유 기준으로 재검증하고, PASS/REJECT를 판정한다.",
        backstory=(
            "15년차 스타트업 자문위원 겸 엔젤 투자자. "
            "이전 리뷰에서 4/10 REJECT를 내렸으며, 핵심 사유는 'Unit Economics 부재'였다. "
            "이번에 제출된 계산서가 다음을 충족하는지 검증한다: "
            "(1) 사용자 1인당 API 비용이 정밀하게 산출되었는가, "
            "(2) Freemium 전환율 시나리오별 Break-even Point가 명시되었는가, "
            "(3) 트래픽 증가 시에도 수익 > 비용 구조가 유지되는가, "
            "(4) 보수적 시나리오에서도 사업 지속 가능성이 있는가. "
            "'좋다/괜찮다' 표현을 사용하지 않으며, 숫자로만 판단한다. "
            "10점 만점 스코어링으로 최종 평가한다."
        ),
        llm=llm,
        verbose=True,
    )

    # === Task 1: 아키텍트 비용 분석 ===
    cost_analysis = Task(
        description=f"""
{COST_DATA}

위 데이터를 기반으로 다음을 정밀하게 계산하라:

## 1. 사용자 1인당 API 비용 (Per-User API Cost)

### 1.1 Free 사용자 (일 3문 제한)
- 일 1회 세션 × 3문 기준 토큰 사용량
- Groq와 DeepSeek 각각의 일/월 비용 계산
- 월간 비용 (MAU 기준)

### 1.2 Paid 사용자 (무제한)
- 일 평균 2세션 × 5문 기준 토큰 사용량
- Groq와 DeepSeek 각각의 일/월 비용 계산
- 월간 비용

### 1.3 비용 절감 전략 (Cost Optimization)
- 캐싱: 동일 질문 재사용 시 절감률 추정 (70% 캐시 히트 가정)
- Rubric 사전 생성: Gold Standard 151개 Rubric 정적 저장 시 절감
- 하이브리드 LLM: 간단한 평가는 소형 모델, 상세 채점만 대형 모델
- 각 전략 적용 후 조정된 비용 재계산

## 2. 인프라 고정 비용 (Fixed Cost by Scale)

| 단계 | DAU | MAU | Vercel | Supabase | Server | LLM API | 총 월비용 |
각 단계별 구체적 수치를 산출하라:
- Stage 0: DAU 10, MAU 50
- Stage 1: DAU 50, MAU 300
- Stage 2: DAU 200, MAU 1,500
- Stage 3: DAU 1,000, MAU 8,000
- Stage 4: DAU 5,000, MAU 40,000

## 3. 총 비용 테이블 (Total Cost = Fixed + Variable)
위 5개 단계 × Free/Paid 비율별 총 비용 매트릭스

모든 계산에 단위(tokens, USD, KRW)와 계산 과정을 명시할 것.
보수적 추정 원칙: 캐시 히트율은 50%로 낮춰서 별도 행으로 표기.
""",
        expected_output=(
            "Unit Economics 비용 분석서 (마크다운). "
            "Free/Paid 사용자별 일/월 API 비용, 5단계 인프라 비용 테이블, "
            "비용 절감 전략별 절감률, 총 비용 매트릭스 포함. "
            "모든 수치에 계산 과정 명시."
        ),
        agent=architect,
        output_file="output/unit-economics-architect.md",
    )

    # === Task 2: PM 수익/가격 전략 ===
    revenue_strategy = Task(
        description=f"""
{COST_DATA}

아키텍트의 비용 분석을 기반으로 다음을 산출하라:

## 1. 가격 정책 설계 (Pricing Strategy)

### 1.1 경쟁사 벤치마크 분석
- LeetCode ($35/mo), GreatFrontEnd ($15/mo), 인프런 (24,900원/mo) 대비 포지셔닝
- AI Interview의 제공 가치 대비 적정 가격대 도출

### 1.2 가격 옵션 제안 (최소 3안)
각 안에 대해:
- Monthly / Annual 가격
- 할인율 (연간 결제 시)
- 타겟 전환율 추정
- 예상 ARPU (Average Revenue Per User)

### 1.3 심리적 가격 전략
- 앵커링 효과를 위한 티어 구성
- Free → Paid 전환 트리거 설계

## 2. Unit Economics 핵심 지표

### 2.1 ARPU (Average Revenue Per User)
- Free 사용자 ARPU = $0
- Paid 사용자 ARPU = 가격 - 결제 수수료(Stripe 2.9%+$0.30)
- Blended ARPU = Paid 비율별 가중 평균

### 2.2 사용자 1인당 마진 (Per-User Margin)
- Free 사용자: 마진 = -API 비용 (순손실)
- Paid 사용자: 마진 = ARPU - API 비용
- Blended Margin = 전환율별 계산

### 2.3 LTV (Customer Lifetime Value)
- 평균 구독 기간 추정 (EdTech 벤치마크: 3~6개월)
- LTV = ARPU × 평균 구독 개월 수
- LTV:CAC 비율 (CAC = 자연 유입 가정 시 ~$0)

## 3. Break-even Point (손익분기점)

### 3.1 시나리오별 BEP
| 시나리오 | 전환율 | 가격 | MAU | Paid Users | 월수익 | 월비용 | 월순익 | BEP 도달 |
다음 6개 시나리오를 모두 계산:
- Pessimistic: 전환율 2%, 저가격
- Conservative: 전환율 3%, 중간가격
- Base: 전환율 5%, 중간가격
- Optimistic: 전환율 7%, 중간가격
- Aggressive: 전환율 10%, 고가격
- Best Case: 전환율 15%, 고가격

각 시나리오에서 "월 순익 > 0"이 되는 최소 MAU를 산출하라.

### 3.2 트래픽 증가 시 수익-비용 추이
- MAU 50 → 100 → 300 → 1,000 → 5,000 → 10,000 → 50,000
- 각 단계에서 수익과 비용의 교차점 확인
- "성공할수록 망하는 구조"가 아님을 증명 (수익 증가율 > 비용 증가율)

## 4. 최종 가격 정책 권고
- 추천 가격 (Monthly/Annual, KRW/USD)
- 추천 전환 전략
- Phase 5 M4에서의 구체적 실행 방안
""",
        expected_output=(
            "Unit Economics 수익 분석서 (마크다운). "
            "3개 가격안, ARPU/LTV/Margin 계산, 6개 시나리오 BEP 테이블, "
            "MAU별 수익-비용 추이, 최종 가격 권고 포함. "
            "모든 수치에 계산 과정과 근거 명시."
        ),
        agent=pm,
        context=[cost_analysis],
        output_file="output/unit-economics-pm.md",
    )

    # === Task 3: 외부인사 재검증 ===
    advisor_review = Task(
        description=f"""
이전 REJECT (4/10) 조건부 승인 사항 #1에 대한 응답으로
아키텍트의 비용 분석과 PM의 수익 전략이 제출되었다.

[이전 REJECT 사유]
1. Unit Economics 부재 — 1인당 API 비용 vs 수익 구조 미계산
2. 트래픽 늘수록 적자 확대 구조 우려 (성공할수록 망하는 구조)
3. Break-even Point 미제시
4. 광고 폐기 후 Subscription + Affiliate만으로 수익성 증명 필요

[검증 체크리스트]
1. **비용 정밀도 검증:**
   - 토큰 사용량 추정이 현실적인가? (과소 추정은 없는가?)
   - 인프라 비용 단계별 산출이 합리적인가?
   - 숨겨진 비용(세금, 결제 수수료, 환불, 고객 지원)이 빠져있지 않은가?

2. **수익 현실성 검증:**
   - 전환율 추정이 EdTech 업계 벤치마크와 일치하는가?
   - 가격이 경쟁사 대비 합리적인가?
   - LTV 추정이 과장되지 않았는가?

3. **BEP 검증:**
   - 보수적 시나리오(전환율 2~3%)에서도 BEP 도달이 가능한가?
   - BEP 도달까지 필요한 MAU가 현실적으로 달성 가능한가?

4. **구조적 건전성:**
   - MAU 증가 시 수익 증가율 > 비용 증가율인가?
   - Paid 1명이 Free 몇 명의 비용을 커버하는가?
   - 최악의 시나리오에서 월 최대 손실액은 얼마인가?

[평가 기준]
- 10점 만점 스코어링
- PASS (7점 이상) / CONDITIONAL PASS (5~6점) / REJECT (4점 이하)
- 이전 4/10에서 몇 점으로 변경되는지 명시
- 각 지적사항에 대한 구체적 수치 기반 판단
""",
        expected_output=(
            "외부인사 Unit Economics 재검증 보고서 (마크다운). "
            "비용 정밀도, 수익 현실성, BEP 타당성, 구조적 건전성 각각에 대한 "
            "수치 기반 검증 결과. 10점 만점 스코어링. "
            "이전 REJECT(4/10) → 변경 점수 명시. "
            "PASS/CONDITIONAL PASS/REJECT 판정과 잔여 리스크 목록."
        ),
        agent=advisor,
        context=[cost_analysis, revenue_strategy],
        output_file="output/unit-economics-advisor.md",
    )

    crew = Crew(
        agents=[architect, pm, advisor],
        tasks=[cost_analysis, revenue_strategy, advisor_review],
        process=Process.sequential,
        verbose=True,
    )

    print("\n=== Unit Economics 계산서 작성 시작 ===")
    print("참여 에이전트: Architect(비용분석) + PM(수익전략) + Advisor(재검증)")
    print("목표: 외부인사 REJECT(4/10) → PASS(7+/10) 해소")
    print("=" * 60)

    result = crew.kickoff()

    print("\n=== Unit Economics 계산서 완료 ===")
    print("산출물:")
    print("  - output/unit-economics-architect.md (비용 분석)")
    print("  - output/unit-economics-pm.md (수익/가격 전략)")
    print("  - output/unit-economics-advisor.md (외부인사 재검증)")

    return result


if __name__ == "__main__":
    run()
