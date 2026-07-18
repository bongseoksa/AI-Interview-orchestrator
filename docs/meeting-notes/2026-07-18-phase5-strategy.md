# Phase 5 진입 전략 논의 결과

**일자:** 2026-07-18
**참여 에이전트:** PM(전략평가) + PjM(실행계획) + External Advisor(검증)
**실행 스크립트:** `scripts/plan_next_phase.py`

---

## 1. PM 전략 보고 — Phase 4 완료 판정: GO (Conditional)

### 판정 근거
- P0 기능 7개 모두 구현 완료 (커리큘럼 대시보드, 개념 학습, 메타인지 진단, 랜딩, Auth, Progress Tracking, Default Tip)
- 운영 부채(Operational Debt) 해결 조건부 승인

### 즉시 실행 과제 (Phase 4 마무리)
| Priority | 과제 | 내용 |
|----------|------|------|
| P1 | Notion Status Sync | M5/M6 상태를 "Done"으로 업데이트 |
| P1 | Terminology | Step -> Phase 용어 통일 |
| P1 | Registry Cleanup | 날짜(2024->2026), 접두사(step->phase), 오타 수정 |
| P2 | Environment Alignment | Python 버전 통일 (3.11 vs 3.13) |
| P2 | Auth Risk | Lazy Auth 데이터 유실 방지 (LocalStorage 임시 저장) |
| P3 | Deployment | Vercel/Supabase 배포 테스트 |

### 3개월 로드맵
- **Month 1:** 안정화 + MVP 런칭 + 초기 유입 (커뮤니티 포지셔닝)
- **Month 2:** Phase 5 AI 면접 엔진 (Core Value, 해자 구축)
- **Month 3:** Phase 6 UX 고도화 + 리텐션 + 수익 모델 초안

### 성공 지표 (North Star)
- **Weekly Active Learning Sessions** — 학습 프로세스 완결성 측정

---

## 2. PjM 실행 계획 — 6주 타임라인

### Phase 4 Closing Checklist (6개 태스크)
| 태스크 | DoD | 담당 |
|--------|-----|------|
| Notion 마일스톤 동기화 | M5/M6 "Done" 반영 | NotionEdit |
| 용어 표준화 (Step->Phase) | 전 문서 교체 완료 | NotionEdit |
| 산출물 레지스트리 정비 | 날짜/접두사/에이전트명 수정 | NotionEdit |
| Python 환경 통일 (3.11) | pyproject.toml과 문서 일치 | Codegen |
| Lazy Auth 데이터 유실 방지 | Shadow Profile 설계안 확정 | Architect |
| MVP 배포 | 환경변수 + 도메인 접속 확인 | DevOps |

### Phase 5 마일스톤 (AI Interview Engine)
| 마일스톤 | 태스크 | 기간 |
|----------|--------|------|
| M1: AI Interviewer Core | State Machine + Prompt Engineering | 1주 |
| M2: RAG & Feedback | 답변 검증 + 피드백 엔진 | 2주 |
| M3: Interview UI/UX | 채팅 인터페이스 + 애니메이션 | 1주 |
| M4: Beta Launch | 피드백 수집 루프 | 0.5주 |

### 에이전트 실행 순서
Researcher -> Architect -> Codegen -> PromptEng -> NotionEdit

---

## 3. External Advisor 검증 — REJECT (3.5/10)

### 핵심 실패 항목
1. **현실성 FAIL** — 서버 인프라(Python Backend) 미구축 상태에서 RAG/AI 엔진 계획은 비현실적. "공장 없이 엔진 설계도만 그린 상태"
2. **전략적 FAIL** — 차별화 요소가 "동적 질문"이라는 일반적 기능에 의존. GPT-4 Wrapper와 차별화 불가
3. **기술적 FAIL** — RAG 구현에 필요한 Vector DB, 임베딩, Retrieval 로직은 Next.js Edge Function만으로 불가

### 기존 6건 리스크 대응 평가
| 리스크 | 판정 | 비고 |
|--------|------|------|
| Lazy Auth 역설 | Partial Pass | 브라우저 캐시 삭제 시 복구 플랜 미비 |
| ChatGPT 차별성 | Fail | 모호한 대안만 제시 |
| 해자 부재 | Partial Pass | 개인화 리포트는 데이터 축적 이후 |
| 수익 모델 부재 | Fail | 초기 유입 시 검증 전략 없음 |
| AI 할루시네이션 | Partial Pass | RAG 방향은 맞으나 인프라 모순 |
| 인프라 스케일링 | Pass | Rate Limit 도입 의지 확인 |

### 핵심 권고사항 3개
1. **[Infrastructure First]** Phase 5 시작과 동시에 Python 서버(FastAPI) 구축을 M1 최우선 과제로
2. **[Focus on Domain]** 프론트엔드 특화 검증 데이터셋 확보로 기술적 해자 구축
3. **[Monetization Experiment]** Phase 5부터 Paywall/Credit 시스템 즉시 테스트

---

## 4. 종합 대응 방안

외부인사 권고를 수용하여 다음 사항을 Phase 5 계획에 반영 예정:

1. **Phase 5 M1에 FastAPI 서버 구축 포함** — server 레포 활성화, RAG 인프라 기반 마련
2. **차별화 전략 전환** — 일반적 면접 -> 프론트엔드 도메인 특화 검증으로 전환
3. **Monetization 실험 앞당김** — 상세 피드백 리포트 유료화 검토 (Month 3 -> Phase 5 내)
4. **PjM 타임라인 수정** — 서버 구축 기간 추가 반영 필요

---

**산출물 파일:**
- `output/next-phase-pm-strategy.md` — PM 전략 보고서 (전문)
- `output/next-phase-pjm-plan.md` — PjM 실행 계획서 (전문)
- `output/next-phase-advisor-review.md` — 외부인사 검증 보고서 (전문)
