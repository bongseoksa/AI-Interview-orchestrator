# AI-Interview-orchestrator 온보딩 가이드

이 문서는 AI-Interview-orchestrator 레포에 처음 참여하는 사람(또는 에이전트)이
환경 설정부터 실행, 종료까지 빠르게 시작할 수 있도록 안내한다.

---

## 1. 필수 개념

- **CrewAI**: Python 기반 멀티에이전트 프레임워크 — role/goal/backstory로 에이전트 정의, Task/Crew로 워크플로우 구성
- **Ollama**: 로컬 LLM 실행 도구 — 모델을 pull하여 로컬에서 추론, API 서버(port 11434) 제공
- **YAML 에이전트 정의**: `agents/*.yaml`이 11개 에이전트의 원본 정의 (Single Source of Truth)
- **Claude Code 서브에이전트**: `.claude/agents/*.md`는 Claude Code가 인식하는 페르소나 — CrewAI와 별도
- **Crew**: CrewAI의 실행 단위 — 여러 Agent + Task를 묶어서 sequential/hierarchical로 실행
- **MoE (Mixture of Experts)**: 전체 파라미터 중 일부만 활성화하는 모델 — 빠른 속도 + 높은 품질

## 2. 사전 요구사항

| 항목 | 최소 버전 | 확인 명령어 |
|------|----------|-----------|
| Python | 3.11+ | `python3 --version` |
| Ollama | 0.19+ | `ollama --version` |
| Git | 2.x | `git --version` |

## 3. 설치

```bash
cd AI-Interview-orchestrator

# Git pre-commit 훅 활성화 (최초 1회)
git config core.hooksPath .githooks

# Python 가상환경 (최초 1회, 이미 .venv 존재하면 생략)
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ollama 모델 다운로드 (최초 1회)
ollama pull gemma4:12b        # 기본 모델 (~6.6GB)
ollama pull gemma4:26b        # 고성능 (선택, ~15GB)
ollama pull qwen3:8b          # 빠른 반복용 (선택, ~5.2GB)
```

> `git config core.hooksPath .githooks`를 실행하면 커밋 시 민감 파일(.env, 인증서, 모델 파일 등) 차단 + 시크릿 패턴 스캔이 자동 수행됩니다.

## 4. 실행

```bash
# 1. Ollama 서버 시작 (별도 터미널 또는 백그라운드)
ollama serve

# 2. 가상환경 활성화
source .venv/bin/activate

# 3. Crew 실행
python main.py research       # Step 1: 시장 조사
python main.py planning       # Step 2-4: 기획
python main.py architect      # 아키텍처 설계
python main.py frontend       # 프론트엔드 설계
python main.py qa             # QA 테스트 전략
python main.py infra          # 인프라 CI/CD
python main.py data           # 데이터 파이프라인
python main.py docs           # 문서 감사
python main.py review         # 외부인사 리뷰
```

## 5. 종료

```bash
# CrewAI 실행: 완료 시 자동 종료, 중단 시 Ctrl+C
# Ollama 서버: 터미널에서 Ctrl+C 또는
#   macOS: 메뉴바 Ollama 아이콘 → Quit
# 가상환경 비활성화:
deactivate
```

## 6. 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `source .venv/bin/activate` | 가상환경 활성화 |
| `deactivate` | 가상환경 비활성화 |
| `python main.py research` | Step 1 시장 조사 실행 |
| `python main.py planning` | Step 2-4 기획 실행 |
| `python main.py architect` | 아키텍처 설계 실행 |
| `python main.py frontend` | 프론트엔드 설계 실행 |
| `python main.py qa` | QA 테스트 전략 실행 |
| `python main.py infra` | 인프라 CI/CD 실행 |
| `python main.py data` | 데이터 파이프라인 실행 |
| `python main.py docs` | 문서 감사 실행 |
| `python main.py review` | 외부인사 리뷰 실행 |
| `ollama serve` | Ollama 서버 시작 |
| `ollama list` | 설치된 모델 목록 |
| `ollama pull <model>` | 모델 다운로드 |
| `ollama rm <model>` | 모델 삭제 |
| `bash scripts/sync-agents.sh` | 에이전트 배포 현황 확인 |

## 7. 프로젝트 구조

```
agents/               # 에이전트 YAML 정의 원본 (11개, SSOT)
src/
  config/
    llm.py            # Ollama LLM 설정 + 모델 비교표
  crews/              # 9개 Crew (각각 config/agents.yaml + config/tasks.yaml + crew.py)
    research/         # Step 1: 시장 조사 — 전략 관리자
    planning/         # Step 2-4: 기획 — PM + PjM
    architect/        # 아키텍처 설계 — 풀스택 아키텍트 + 백엔드 시니어
    frontend/         # 프론트엔드 설계 — FE 시니어
    qa/               # QA 테스트 전략 — QA 엔지니어
    infra/            # 인프라 CI/CD — 인프라 전문가
    data/             # 데이터 파이프라인 — 데이터 엔지니어
    documentation/    # 문서 감사 — 서기관리 에이전트
    review/           # 외부인사 리뷰 — 외부인사
scripts/              # 유틸리티 (sync-agents.sh)
.claude/agents/       # Claude Code 서브에이전트 (7개)
main.py               # CrewAI 실행 엔트리포인트
output/               # Crew 실행 결과물 (gitignored)
.venv/                # Python 가상환경 (gitignored)
```

## 8. AI 모델 요약

### 로컬 모델 (Ollama)

| 모델 | 타입 | RAM | 속도 | Tier | 용도 | 라이선스 |
|------|------|-----|------|------|------|---------|
| `gemma4:12b` | Dense | ~6.6GB | ~80-90 t/s | **Tier 2** | 유저 대면, 빠른 반복 | Apache 2.0 |
| `gemma4:26b` | MoE | ~15GB | ~70-80 t/s | **Tier 1** | 고성능 분석, 콘텐츠 생성 | Apache 2.0 |
| `qwen3:8b` | Dense | ~5.2GB | ~120+ t/s | Tier 2 | 빠른 반복 | Apache 2.0 |
| `qwen3.5:35b-a3b` | MoE | ~20GB | ~70-80 t/s | Tier 1 | 코딩 특화 | Apache 2.0 |

하드웨어: Apple M4 Pro 48GB (273 GB/s 메모리 대역폭)

**2-Tier 원칙**: 자료 수집·개발 Crew는 Tier 1(26B, 품질 최우선, 응답 지연 허용), 유저 대면 콘텐츠 생성은 Tier 2(12B, 속도 우선)

## 9. 비용 제약

- **Claude API 토큰 사용 불가** — 유료 LLM API 직접 호출 금지
- CrewAI + Ollama = 완전 무료 (로컬 실행)
- Claude Code 서브에이전트(.claude/agents/)는 기존 구독 범위 내 사용 가능

## 10. 관련 문서

- `CLAUDE.md` — 에이전트 컨텍스트 (Claude Code용)
- `agents/*.yaml` — 에이전트 정의 원본
- `src/config/llm.py` — 모델 선정 근거 상세
- Notion 사업계획서: 에이전트 조직 구조, 실행 로드맵
