# Phase 5 보완 계획 (Advisor REJECT 수용 후 재검토)

**일자:** 2026-07-18
**참여 에이전트:** PM(전략수정) + Architect(인프라설계) + PjM(타임라인) + Advisor(재검토)
**실행 스크립트:** `scripts/revise_phase5_plan.py`
**결과:** REJECT(3.5/10) -> **PASS(8.5/10)**

---

## 1. PM 수정 전략 — 3개 FAIL 항목 해소

### 기존 문제점 자기 진단
| FAIL 항목 | 문제 | 해소 방법 |
|-----------|------|-----------|
| 현실성 | 서버 없이 AI 엔진 계획 | FastAPI를 M0(최우선)으로 배치 |
| 차별화 | "동적 질문" = GPT Wrapper | Rubric 기반 채점 엔진으로 전환 |
| 수익 모델 | Month 3에야 초안 설계 | Phase 5 M4에서 즉시 Freemium 실험 |

### 차별화 전략: "질문 생성 AI" -> "채점하는 AI"
- 151개 Q&A를 단순 질문 소스가 아닌 **평가 기준(Rubric)**으로 활용
- 3가지 채점 기준: 정확성(Accuracy), 깊이(Depth), 명료성(Clarity)
- 피드백 예시: "React Reconciliation 과정을 생략하여 정확도 60%"

### 수익 모델 (Freemium)
| | Free | Paid |
|--|------|------|
| 인터뷰 | 하루 3문 | 무제한 |
| 피드백 | 답변 요약만 | 상세 Rubric 채점 + 취약점 분석 |
| 결제 | - | Credit 충전 or Monthly |

### Lazy Auth 보완: Local-First, Sync-Later
1. IndexedDB/localStorage에 답변 임시 저장
2. Anonymous_UID로 서버측 추적
3. Auth 완료 시 Migration Trigger로 동기화
4. 이메일/알림톡 백업 (캐시 삭제 대비)

---

## 2. Architect 서버 인프라 설계

### FastAPI 디렉토리 구조
```
server/
  app/
    api/endpoints/     # interview, evaluation, user
    core/              # Config, Security(JWT), Logging
    services/
      interviewer.py   # State Machine
      rag_service.py   # Vector Search
      evaluator.py     # Rubric scoring
    models/            # Pydantic schemas
    main.py
  docker/
  tests/
```

### API 엔드포인트
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/v1/interview/start` | 세션 생성 + 첫 질문 | Yes |
| POST | `/v1/interview/submit` | 답변 제출 + 평가 + 다음 질문 | Yes |
| GET | `/v1/interview/{sid}/status` | 세션 상태 조회 | Yes |
| GET | `/v1/interview/{sid}/report` | 최종 리포트 | Yes |
| GET | `/v1/health` | 헬스체크 | No |

### State Machine (5단계)
INITIALIZING -> QUESTIONING -> EVALUATING -> CONCLUDING -> COMPLETED

### RAG: Hybrid 방식 (Option C 권장)
- **Phase 5 초기**: 151개 데이터 numpy 로컬 매칭 (구현 3~5일, 비용 $0)
- **Phase 6 이후**: pgvector로 확장 (대규모 데이터 지원)

### 비용 분석 (월 $5 미만)
| 항목 | 스택 | 비용 |
|------|------|------|
| Frontend | Vercel | $0 |
| Backend | Railway/Render | $0~$5 |
| DB/Auth | Supabase | $0 |
| LLM | Groq/DeepSeek | $0~$2 |

---

## 3. PjM 수정 타임라인 (8주)

### 운영 원칙
1. **Sequential Dependency** — M0 미완료 시 M1 진입 금지
2. **Single-Tasking** — 주 1개 핵심 목표만
3. **Minimum Viable Infrastructure** — 최소 비용 스택 우선

### 주 단위 계획
| 주차 | 마일스톤 | 핵심 목표 |
|------|----------|-----------|
| W1 | Phase 4 | 운영 부채 청산 (Auth 보완, RLS 검증) |
| W2 | M0 | FastAPI 기본 구조 + Dockerfile |
| W3 | M0 | Railway/Render 배포 + CI/CD |
| W4 | M1 | State Machine + 세션 API |
| W5 | M1 | Hybrid RAG 기초 (키워드 매칭) |
| W6 | M2 | Rubric 채점 엔진 + Prompt Engineering |
| W7 | M3 | Next.js <-> FastAPI 연동 + 채팅 UI |
| W8 | M4 | Freemium Paywall + Beta Launch |

### 리스크 대응
| 리스크 | Fallback |
|--------|----------|
| 인프라 지연 | ngrok 터널링 + Next.js API Routes 임시 |
| LLM 품질 미달 | Rule-based 평가 비중 확대 |
| Scope Creep | pgvector 전환은 Phase 6으로 강제 이관 |
| 데이터 오염 | user_responses 테이블 물리적 분리 |

---

## 4. Advisor 재검토 — PASS (8.5/10)

### 권고사항 반영 검증
| 권고 | 판정 |
|------|------|
| Infrastructure First | **PASS** — W2-W3에 서버 구축 배치, 구체적 배포 전략 |
| Domain Focus | **PASS** — Rubric 기반 피드백으로 가치 재정의, 151개 Gold Standard |
| Monetization | **PASS** — M4에서 Freemium + Credit 즉시 실험 |

### 평가
- 아키텍처: **Very High** — Hybrid RAG 영리한 접근, 비용 효율적
- 타임라인: **High** — 순차적 의존성 준수, 주 1개 목표 현실적

### 조건부 승인 전제 3개
1. M0 지연 시 M1 도약 절대 금지
2. Streaming Response + Loading UX 최우선
3. 데이터 격리(user_responses) 구현 직후 검증 필수

### 개선 요약
- 추상적 기능 -> 구체적 인프라 구축
- Generic Wrapper -> Domain Specialist (Rubric 채점 엔진)
- Feature-driven -> Business-driven (수익 검증 중심)

---

**산출물 파일:**
- `output/revised-pm-strategy.md` — PM 수정 전략 (전문)
- `output/revised-architect-infra.md` — 서버 인프라 설계서 (전문)
- `output/revised-pjm-plan.md` — PjM 수정 타임라인 (전문)
- `output/revised-advisor-recheck.md` — Advisor 재검토 (전문)
