# CLAUDE.md — AI-Interview-orchestrator

에이전트 정의 원본 및 워크플로우를 관리하는 오케스트레이터 레포.

## 레포 목적

- 11개 에이전트의 페르소나 정의 원본 (YAML) 관리
- 각 레포(web/server)의 `.claude/agents/` 서브에이전트 생성 스크립트
- Phase별 워크플로우 정의
- 환경 설정/모델 선정 상세: `ONBOARDING.md` 참조
- CrewAI + Ollama 기반 자율 에이전트 실행 환경

## AI 모델 & 에이전트 프레임워크

- **프레임워크**: CrewAI v1.15.4 (MIT, self-hosted, 무료)
- **LLM**: Ollama 로컬 모델 (Tier 1: Gemma 4 26B 개발용 고정, Tier 2: Gemma 4 12B 유저 대면용)
- **Python**: 3.13 (.venv 가상환경)
- **실행**: `source .venv/bin/activate && python main.py <command>`
- **모든 모델 라이선스**: Apache 2.0 (상업적 사용 무제한, 로열티 없음)

### AI 모델 2-Tier 전략 (Ollama 로컬 모델)

| Tier | 모델 | RAM | 속도 | 용도 |
|------|------|-----|------|------|
| **Tier 1 (고성능)** | `gemma4:26b` MoE | ~15GB | ~70-80 t/s | 시드 데이터 생성, 학습 콘텐츠 작성, Q&A 검증, 시장 조사, PRD 작성 |
| **Tier 1 대안** | `qwen3.5:35b-a3b` MoE | ~20GB | ~70-80 t/s | 코딩 특화 태스크 |
| **Tier 2 (경량)** | `gemma4:12b` Dense | ~6.6GB | ~80-90 t/s | 유저 대면 콘텐츠 생성 (AI 요약·팁, 면접 피드백 등) |
| **Tier 2 대안** | `qwen3:8b` Dense | ~5.2GB | ~120+ t/s | 빠른 반복, 경량 태스크 |

- **Tier 1**: 품질 최우선, 응답 지연 허용 — 모든 개발용 Crew에 적용
- **Tier 2**: 속도 우선 — 향후 서비스용 콘텐츠 생성 Crew에 적용
- 모델 비교표, 선정 근거 상세: `ONBOARDING.md` 참조

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
  tools/
    file_tools.py     # 파일 조작 도구 (크로스 레포 읽기/쓰기, 경로 안전성 검증)
    notion_tools.py   # Notion REST API 도구 (읽기/쓰기/검색/수정/삭제/삽입)
  crews/
    research/         # Phase 1: 시장 조사 — 전략 관리자
    planning/         # Phase 2-4: 기획 — PM + PjM
    architect/        # 아키텍처 설계 — 풀스택 아키텍트 + 백엔드 시니어
    frontend/         # 프론트엔드 설계 — FE 시니어
    qa/               # QA 테스트 전략 — QA 엔지니어
    infra/            # 인프라 CI/CD — 인프라 전문가
    data/             # 데이터 파이프라인 — 데이터 엔지니어
    documentation/    # 문서 감사 — 서기관리 에이전트 + 노션 동기화
    review/           # 외부인사 리뷰 — 외부인사 (Devil's Advocate)
    codegen/          # 코드 생성 — 설계 문서 기반 타 레포 코드 생성
    notion_edit/      # AI 노션 편집 — 키워드 검색 + AI 검증으로 정확한 블록 편집
    (각 Crew: config/agents.yaml + config/tasks.yaml + crew.py)
scripts/              # 유틸리티 (sync, 변환, 테스트 등)
docs/                 # 설계 문서
.claude/agents/       # 이 레포에서 사용하는 Claude Code 서브에이전트
main.py               # CrewAI 실행 엔트리포인트
output/               # Crew 실행 결과물 (gitignored)
logs/                 # Crew 실행 로그 — 에이전트 발화 추적용 (gitignored)
.env                  # 환경 변수 (NOTION_TOKEN 등, gitignored)
.env.example          # 환경 변수 템플릿
```

## 실행 명령어

```bash
source .venv/bin/activate

# === 설계 Crew (Ollama 로컬 모델) ===
python main.py research      # Phase 1: 시장 조사
python main.py planning      # Phase 2-4: 기획 (PRD/스펙/유저스토리)
python main.py architect     # 아키텍처 설계 (스키마/데이터 흐름)
python main.py frontend      # 프론트엔드 설계 (컴포넌트/페이지 구조)
python main.py qa            # QA (테스트 전략/테스트 케이스)
python main.py infra         # 인프라 (CI/CD/배포 전략)
python main.py data          # 데이터 (스키마 최적화/파이프라인)
python main.py docs          # 문서 감사 (정합성/CHANGELOG/노션 초안)
python main.py review        # 외부인사 리뷰 (Devil's Advocate)

# === 코드 생성 (타 레포 대상) ===
python main.py codegen web "학습 페이지 컴포넌트 생성"     # web 레포에 코드 생성
python main.py codegen server "API 엔드포인트 생성"        # server 레포에 코드 생성
python main.py codegen orchestrator "스크립트 생성"        # orchestrator 레포에 코드 생성

# === 노션 직접 조작 (CLI) ===
python main.py notion list                                # 페이지 목록
python main.py notion read <페이지>                       # 페이지 읽기 (전체)
python main.py notion write <페이지> "마크다운 내용"       # 페이지에 추가
python main.py notion search <페이지> <키워드>            # 블록 검색 (ID+맥락)
python main.py notion update <블록ID> "새 내용"            # 블록 수정
python main.py notion delete <블록ID>                     # 블록 삭제
python main.py notion insert <페이지> <기준블록ID> "내용"  # 블록 뒤에 삽입

# === AI 노션 편집 (AI 모델이 검색+검증+편집) ===
python main.py notion-edit <페이지> "편집 지시"
# 예: python main.py notion-edit 의사결정 "Step 4 상태를 완료로 변경"
# 예: python main.py notion-edit 기획서 "카테고리 수를 9개에서 10개로 수정"

# === 산출물 관리 ===
python main.py artifacts       # 산출물 레지스트리 동기화 (로컬 → 노션)
python main.py meetings        # 에이전트 회의록 동기화 (3개 레포 → 노션, 일자+주제별 하위 페이지)

# === 유틸리티 스크립트 ===
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

## Crew-에이전트 매핑 (11 Crew, 11 YAML 에이전트 + 2 인라인 에이전트)

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
| CodegenCrew | 코드 생성 개발자 *(인라인)* | 타 레포(web/server) 코드 파일 생성 |
| NotionEditCrew | 노션 편집 에이전트 *(인라인)* | 키워드 검색 → AI 검증 → 정확한 블록 편집 |

> YAML 정의(`agents/`): 11개 — Crew 내 `config/agents.yaml`로 관리되는 에이전트
> 인라인 정의: 2개 — CodegenCrew, NotionEditCrew의 에이전트는 Crew 코드 내에서 직접 정의

> 모든 Crew는 Tier 1 (`gemma4:26b`) 사용 — 품질 최우선, 응답 지연 허용

### 커스텀 도구 (src/tools/)

| 도구 | 파일 | 용도 |
|------|------|------|
| `list_directory` | file_tools.py | 디렉토리 목록 (IGNORE_DIRS 필터링) |
| `list_directory_recursive` | file_tools.py | 재귀 탐색 (max_depth 제한) |
| `read_file` | file_tools.py | 파일 읽기 (프로젝트 범위 내 경로 검증) |
| `write_file` | file_tools.py | 파일 쓰기 (디렉토리 자동 생성) |
| `list_notion_pages` | notion_tools.py | 등록된 노션 페이지 목록 |
| `read_notion_page` | notion_tools.py | 페이지 읽기 (8000자 제한, 에이전트용) |
| `read_notion_page_full` | notion_tools.py | 페이지 읽기 (offset/limit 페이지네이션) |
| `append_to_notion_page` | notion_tools.py | 페이지 끝에 마크다운 추가 |
| `search_notion_blocks` | notion_tools.py | 키워드로 블록 검색 (ID+전후 맥락 반환) |
| `update_notion_block` | notion_tools.py | 블록 내용 수정 |
| `delete_notion_block` | notion_tools.py | 블록 삭제 |
| `insert_after_notion_block` | notion_tools.py | 특정 블록 뒤에 삽입 |
| `create_notion_child_page` | notion_tools.py | 부모 페이지 아래에 자식 페이지 생성 |
| `query_notion_database` | notion_tools.py | 데이터베이스 쿼리 |

### Notion API 안전 마진

- rich_text: 1860/2000자 (7% 여유)
- blocks/request: 93/100개 (7% 여유)
- 자동 청킹: 긴 텍스트는 1860자 단위로, 많은 블록은 93개 단위로 분할 전송

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
