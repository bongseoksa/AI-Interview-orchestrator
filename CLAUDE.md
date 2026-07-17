# CLAUDE.md — AI-Interview-orchestrator

에이전트 정의 원본 및 워크플로우를 관리하는 오케스트레이터 레포.

## 레포 목적

- 10개 에이전트의 페르소나 정의 원본 (YAML) 관리
- 각 레포(web/server)의 `.claude/agents/` 서브에이전트 생성 스크립트
- Step별 워크플로우 정의
- CrewAI + Ollama 기반 자율 에이전트 실행 환경

## AI 모델 & 에이전트 프레임워크

- **프레임워크**: CrewAI v1.15.3 (MIT, self-hosted, 무료)
- **LLM**: Ollama 로컬 모델 (Qwen3 14B 기본, 32B 고성능)
- **Python**: 3.13 (.venv 가상환경)
- **실행**: `source .venv/bin/activate && python main.py <command>`

### 사전 준비

```bash
# 1. Ollama 모델 다운로드 (최초 1회)
ollama pull qwen3:14b

# 2. Python 가상환경 활성화
source .venv/bin/activate

# 3. Crew 실행
python main.py research   # Step 1: 시장 조사
python main.py planning   # Step 2-4: 기획
```

### 모델 선택 가이드 (M4 Pro 48GB 기준)

| 모델 | VRAM | 용도 |
|------|------|------|
| `qwen3:8b` | ~6GB | 가벼운 태스크, 빠른 반복 |
| `qwen3:14b` | ~9GB | **기본 추천** — 균형 |
| `qwen3:32b` | ~20GB | 고성능 (복잡한 분석/설계) |
| `llama3.3` | ~8GB | 범용 대안 |

## 비용 제약

- **Claude API 토큰 사용 불가** — 이 레포에서는 유료 LLM API를 직접 호출하지 않는다
- 자율 에이전트 실행 시 Ollama 로컬 모델만 사용
- Claude Code 서브에이전트(.claude/agents/)는 사용 가능 (기존 구독 활용)

## 디렉토리 구조

```
agents/               # 에이전트 YAML 정의 원본 (10개)
src/
  config/
    agents.yaml       # CrewAI 에이전트 정의
    tasks.yaml        # CrewAI 태스크 정의
    llm.py            # Ollama LLM 설정
  crews/
    research_crew.py  # Step 1: 시장 조사 Crew
    planning_crew.py  # Step 2-4: 기획 Crew
scripts/              # 유틸리티 (sync, 변환 등)
.claude/agents/       # 이 레포에서 사용하는 Claude Code 서브에이전트
main.py               # CrewAI 실행 엔트리포인트
output/               # Crew 실행 결과물 (gitignored)
```

## 관련 레포

- `AI-Interview-web` — 프론트엔드 (Next.js 16, pnpm)
- `AI-Interview-server` — 백엔드 (Python, TBD)
