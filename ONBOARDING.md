# AI-Interview-orchestrator 온보딩 가이드

이 문서는 AI-Interview-orchestrator 레포에 처음 참여하는 사람(또는 에이전트)이
환경 설정부터 실행, 종료까지 빠르게 시작할 수 있도록 안내한다.

---

## 1. 필수 개념

- **CrewAI**: Python 기반 멀티에이전트 프레임워크 — role/goal/backstory로 에이전트 정의, Task/Crew로 워크플로우 구성
- **Ollama**: 로컬 LLM 실행 도구 — 모델을 pull하여 로컬에서 추론, API 서버(port 11434) 제공
- **YAML 에이전트 정의**: `agents/*.yaml`이 10개 에이전트의 원본 정의 (Single Source of Truth)
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

# Python 가상환경 (최초 1회, 이미 .venv 존재하면 생략)
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ollama 모델 다운로드 (최초 1회)
ollama pull gemma4:12b        # 기본 모델 (~6.6GB)
ollama pull gemma4:26b        # 고성능 (선택, ~15GB)
ollama pull qwen3:8b          # 빠른 반복용 (선택, ~5.2GB)
```

## 4. 실행

```bash
# 1. Ollama 서버 시작 (별도 터미널 또는 백그라운드)
ollama serve

# 2. 가상환경 활성화
source .venv/bin/activate

# 3. Crew 실행
python main.py research       # Step 1: 시장 조사
python main.py planning       # Step 2-4: 기획
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
| `ollama serve` | Ollama 서버 시작 |
| `ollama list` | 설치된 모델 목록 |
| `ollama pull <model>` | 모델 다운로드 |
| `ollama rm <model>` | 모델 삭제 |
| `bash scripts/sync-agents.sh` | 에이전트 배포 현황 확인 |

## 7. 프로젝트 구조

```
agents/               # 에이전트 YAML 정의 원본 (10개, SSOT)
src/
  config/
    agents.yaml       # CrewAI 에이전트 정의
    tasks.yaml        # CrewAI 태스크 정의
    llm.py            # Ollama LLM 설정 + 모델 비교표
  crews/
    research_crew.py  # Step 1: 시장 조사 Crew
    planning_crew.py  # Step 2-4: 기획 Crew
scripts/              # 유틸리티 (sync-agents.sh)
.claude/agents/       # Claude Code 서브에이전트 (6개)
main.py               # CrewAI 실행 엔트리포인트
output/               # Crew 실행 결과물 (gitignored)
.venv/                # Python 가상환경 (gitignored)
```

## 8. AI 모델 요약

| 모델 | 타입 | RAM | 속도 | 용도 | 라이선스 |
|------|------|-----|------|------|---------|
| `gemma4:12b` | Dense | ~6.6GB | ~80-90 t/s | **기본 (추천)** | Apache 2.0 |
| `gemma4:26b` | MoE | ~15GB | ~70-80 t/s | 고성능 분석 | Apache 2.0 |
| `qwen3:8b` | Dense | ~5.2GB | ~120+ t/s | 빠른 반복 | Apache 2.0 |
| `qwen3.5:35b-a3b` | MoE | ~20GB | ~70-80 t/s | 코딩 특화 | Apache 2.0 |

하드웨어: Apple M4 Pro 48GB (273 GB/s 메모리 대역폭)

## 9. 비용 제약

- **Claude API 토큰 사용 불가** — 유료 LLM API 직접 호출 금지
- CrewAI + Ollama = 완전 무료 (로컬 실행)
- Claude Code 서브에이전트(.claude/agents/)는 기존 구독 범위 내 사용 가능

## 10. 관련 문서

- `CLAUDE.md` — 에이전트 컨텍스트 (Claude Code용)
- `agents/*.yaml` — 에이전트 정의 원본
- `src/config/llm.py` — 모델 선정 근거 상세
- Notion 사업계획서: 에이전트 조직 구조, 실행 로드맵
