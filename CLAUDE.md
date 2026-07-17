# CLAUDE.md — AI-Interview-orchestrator

에이전트 정의 원본 및 워크플로우를 관리하는 오케스트레이터 레포.

## 레포 목적

- 11개 에이전트의 페르소나 정의 원본 (YAML) 관리
- 각 레포(web/server)의 `.claude/agents/` 서브에이전트 생성 스크립트
- Step별 워크플로우 정의
- CrewAI + Ollama 기반 자율 에이전트 실행 환경

## AI 모델 & 에이전트 프레임워크

- **프레임워크**: CrewAI v1.15.3 (MIT, self-hosted, 무료)
- **LLM**: Ollama 로컬 모델 (Tier 1: Gemma 4 26B 개발용 고정, Tier 2: Gemma 4 12B 유저 대면용)
- **Python**: 3.13 (.venv 가상환경)
- **실행**: `source .venv/bin/activate && python main.py <command>`
- **모든 모델 라이선스**: Apache 2.0 (상업적 사용 무제한, 로열티 없음)

### AI 모델 2-Tier 전략 (Ollama 로컬 모델)

자료 수집·개발용은 답변이 늦어도 고성능 모델을 고정하고, 서비스 내 유저 대면 콘텐츠 생성은 경량 모델을 사용한다.

| Tier | 모델 | RAM | 속도 | 용도 |
|------|------|-----|------|------|
| **Tier 1 (고성능)** | `gemma4:26b` MoE | ~15GB | ~70-80 t/s | 시드 데이터 생성, 학습 콘텐츠 작성, Q&A 검증, 시장 조사, PRD 작성 |
| **Tier 1 대안** | `qwen3.5:35b-a3b` MoE | ~20GB | ~70-80 t/s | 코딩 특화 태스크 |
| **Tier 2 (경량)** | `gemma4:12b` Dense | ~6.6GB | ~80-90 t/s | 유저 대면 콘텐츠 생성 (AI 요약·팁, 면접 피드백 등) |
| **Tier 2 대안** | `qwen3:8b` Dense | ~5.2GB | ~120+ t/s | 빠른 반복, 경량 태스크 |

- **Tier 1**: 품질 최우선, 응답 지연 허용 — ResearchCrew, PlanningCrew, ArchitectCrew 등 모든 개발용 Crew에 적용
- **Tier 2**: 속도 우선 — 향후 서비스용 콘텐츠 생성 Crew에 적용

### 사전 준비

```bash
# 1. Ollama 모델 다운로드 (최초 1회)
ollama pull gemma4:26b        # Tier 1 — 개발용 기본 모델 (~15GB)
ollama pull gemma4:12b        # Tier 2 — 유저 대면용 (~6.6GB)
ollama pull qwen3:8b          # Tier 2 대안 — 빠른 반복용 (선택)

# 2. Python 가상환경 활성화 + Crew 실행
source .venv/bin/activate
python main.py <command>      # 사용 가능한 명령어는 '실행 명령어' 섹션 참조
```

### 모델 선택 가이드 (M4 Pro 48GB, 273 GB/s 기준)

| 모델 | 타입 | 활성 | RAM | 속도 | Tool-call | 용도 |
|------|------|------|-----|------|-----------|------|
| `gemma4:26b` | MoE | 4B | ~15GB | ~70-80 t/s | ~90% | **Tier 1 — 개발용 기본 모델** |
| `gemma4:12b` | Dense | 12B | ~6.6GB | ~80-90 t/s | ~90% | **Tier 2 — 유저 대면용** |
| `qwen3:8b` | Dense | 8B | ~5.2GB | ~120+ t/s | ~85% | 빠른 반복 |
| `qwen3.5:35b-a3b` | MoE | 3B | ~20GB | ~70-80 t/s | 85% | 코딩 특화 |
| `qwen3:14b` | Dense | 14B | ~9GB | ~60-70 t/s | 85-90% | 범용 대안 |

### 모델 선정 근거

프레임워크 5종 비교 (CrewAI vs LangGraph vs smolagents vs AutoGen vs Swarm),
모델 6종 비교 (Gemma 4, Qwen3, Qwen3.5, Llama 3.3, DeepSeek R1, Phi-4)를 수행.

**검토 기준**: 라이선스(Apache 2.0 필수), M4 Pro 48GB 하드웨어 호환성,
에이전트 tool-call 신뢰도, 응답 속도(tok/s), RAM 사용량.

**Gemma 4 26B 개발용 기본 모델 채택 이유**:
1. MoE 아키텍처 → 활성 파라미터 4B로 26B 품질을 12B급 속도로 제공
2. ~15GB RAM → 48GB에서 여유롭게 구동
3. 자료 수집·분석·콘텐츠 생성 등 품질이 중요한 태스크에 최적
4. 네이티브 function calling 내장 → tool-call 신뢰도 ~90%
5. Apache 2.0 → MAU 제한 없음 (Llama의 7억 제한 vs 없음)

**Gemma 4 12B 유저 대면용 모델 선정 이유**:
1. ~6.6GB RAM → 경량, 다른 작업 병행 가능
2. ~80-90 tok/s → 빠른 응답 속도
3. MMLU Pro 77.2% → 유저 대면 품질 충분
4. tool-call 신뢰도 ~90%

**참고 자료**:
- HuggingFace Open LLM Leaderboard: huggingface.co/collections/open-llm-leaderboard
- HuggingFace 2026 LLM 비교: huggingface.co/blog/daya-shankar/open-source-llms
- Apple Silicon LLM 벤치마크: llmcheck.net/benchmarks

## 비용 제약

- **Claude API 토큰 사용 불가** — 이 레포에서는 유료 LLM API를 직접 호출하지 않는다
- 자율 에이전트 실행 시 Ollama 로컬 모델만 사용
- Claude Code 서브에이전트(.claude/agents/)는 사용 가능 (기존 구독 활용)

## 디렉토리 구조

```
agents/               # 에이전트 YAML 정의 원본 (11개)
src/
  config/
    llm.py            # Ollama LLM 설정 (2-Tier: 26B 고성능 / 12B 경량)
    crew_logger.py    # Crew 실행 로거 (BaseEventListener 기반)
  crews/
    research/         # Step 1: 시장 조사 — 전략 관리자
    planning/         # Step 2-4: 기획 — PM + PjM
    architect/        # 아키텍처 설계 — 풀스택 아키텍트 + 백엔드 시니어
    frontend/         # 프론트엔드 설계 — FE 시니어
    qa/               # QA 테스트 전략 — QA 엔지니어
    infra/            # 인프라 CI/CD — 인프라 전문가
    data/             # 데이터 파이프라인 — 데이터 엔지니어
    documentation/    # 문서 감사 — 서기관리 에이전트 + 노션 동기화
    review/           # 외부인사 리뷰 — 외부인사 (Devil's Advocate)
    (각 Crew: config/agents.yaml + config/tasks.yaml + crew.py)
scripts/              # 유틸리티 (sync, 변환 등)
docs/                 # 설계 문서
.claude/agents/       # 이 레포에서 사용하는 Claude Code 서브에이전트
main.py               # CrewAI 실행 엔트리포인트
output/               # Crew 실행 결과물 (gitignored)
logs/                 # Crew 실행 로그 — 에이전트 발화 추적용 (gitignored)
```

## 실행 명령어

```bash
source .venv/bin/activate
python main.py research      # Step 1: 시장 조사
python main.py planning      # Step 2-4: 기획 (PRD/스펙/유저스토리)
python main.py architect     # 아키텍처 설계 (스키마/데이터 흐름)
python main.py frontend      # 프론트엔드 설계 (컴포넌트/페이지 구조)
python main.py qa            # QA (테스트 전략/테스트 케이스)
python main.py infra         # 인프라 (CI/CD/배포 전략)
python main.py data          # 데이터 (스키마 최적화/파이프라인)
python main.py docs          # 문서 감사 (정합성/CHANGELOG/노션 초안)
python main.py review        # 외부인사 리뷰 (Devil's Advocate)

# 노션 동기화 (서기에이전트 초안 → Notion 반영)
python scripts/sync_notion.py              # 대화형 (페이지별 확인)
python scripts/sync_notion.py --dry-run    # 미리보기만
python scripts/sync_notion.py --auto       # 전체 자동 반영

# DB 콘텐츠 번역 (gemma4:12b, Tier 2)
python scripts/translate_content.py                # 전체 번역
python scripts/translate_content.py --dry-run      # 미리보기만
python scripts/translate_content.py --limit 5      # 5개만 테스트
python scripts/translate_content.py --nodes-only   # 노드만
python scripts/translate_content.py --questions-only  # 질문만
```

## Crew-에이전트 매핑 (9 Crew, 11 에이전트)

| Crew | 에이전트 | 산출물 |
|------|----------|--------|
| ResearchCrew | 전략 관리자 | 시장 조사 보고서 |
| PlanningCrew | PM + PjM | PRD, 기능 스펙, 유저 스토리 |
| ArchitectCrew | 풀스택 아키텍트 + 백엔드 시니어 | SQL 스키마, 데이터 흐름 |
| FrontendCrew | FE 시니어 | 컴포넌트 설계, 페이지 구조 |
| QACrew | QA 엔지니어 | 테스트 전략, 테스트 케이스 |
| InfraCrew | 인프라 전문가 | CI/CD, 배포 전략 |
| DataCrew | 데이터 엔지니어 | 스키마 최적화, 파이프라인 |
| DocumentationCrew | 서기관리 | 문서 감사, CHANGELOG, 노션 업데이트 초안 |
| ReviewCrew | 외부인사 | Devil's Advocate, 경쟁력 분석 |

> 모든 Crew는 Tier 1 (`gemma4:26b`) 사용 — 품질 최우선, 응답 지연 허용

## 개발 역할 분담 (필수 원칙)

**이 레포의 에이전트가 주도적으로 설계·분석·검증을 수행하고, Claude Code는 서포트 역할만 한다.**

### 워크플로우

1. **설계 단계** — Orchestrator 에이전트(CrewAI)가 주도
   - 마일스톤별 전용 스크립트(`scripts/design_*.py`)를 작성하여 관련 Crew 실행
   - FrontendCrew: 컴포넌트 설계, 페이지 구조 → `output/` 산출물 생성
   - QACrew: 테스트 전략, 테스트 케이스 → `output/` 산출물 생성
   - ArchitectCrew: 스키마 설계, 데이터 흐름 → `output/` 산출물 생성
   - ReviewCrew: Devil's Advocate 리뷰 → `output/` 산출물 생성

2. **구현 단계** — Claude Code가 에이전트 산출물 기반으로 서포트
   - 에이전트 산출물(`output/`)을 입력으로 받아 코드 구현
   - 에이전트 설계를 최대한 반영하되, 기술적 제약 시 조정 가능
   - 구현 완료 후 에이전트(QACrew)의 테스트 케이스로 검증

3. **검증 단계** — Orchestrator 에이전트가 최종 검토
   - DocumentationCrew: 문서 정합성 감사
   - ReviewCrew: 외부인사 관점 리뷰

### 노션 작성 원칙

- **노션 문서 작성/업데이트 시 서기에이전트(DocumentationCrew) 활용 필수**
- 서기에이전트가 노션용 초안을 생성 → 리뷰 후 노션에 반영하는 2단계 워크플로우
- 의사결정 기록(Decision Log) 등 긴급 로그는 예외적으로 직접 기록 가능

### 금지 사항

- Claude Code가 에이전트 없이 단독으로 설계 결정을 내리지 않는다
- 에이전트 산출물 없이 새로운 마일스톤의 구현을 시작하지 않는다
- 에이전트 설계와 다른 방향의 구현은 반드시 사유를 기록한다
- 노션 문서를 서기에이전트 경유 없이 직접 작성하지 않는다 (의사결정 로그 예외)

## 관련 레포

- `AI-Interview-web` — 프론트엔드 (Next.js 16, pnpm)
- `AI-Interview-server` — 백엔드 (Python, TBD)
