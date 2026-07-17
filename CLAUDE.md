# CLAUDE.md — AI-Interview-orchestrator

에이전트 정의 원본 및 워크플로우를 관리하는 오케스트레이터 레포.

## 레포 목적

- 10개 에이전트의 페르소나 정의 원본 (YAML) 관리
- 각 레포(web/server)의 `.claude/agents/` 서브에이전트 생성 스크립트
- Step별 워크플로우 정의
- CrewAI + Ollama 기반 자율 에이전트 실행 환경

## AI 모델 & 에이전트 프레임워크

- **프레임워크**: CrewAI v1.15.3 (MIT, self-hosted, 무료)
- **LLM**: Ollama 로컬 모델 (Gemma 4 12B 기본, Gemma 4 26B 고성능)
- **Python**: 3.13 (.venv 가상환경)
- **실행**: `source .venv/bin/activate && python main.py <command>`
- **모든 모델 라이선스**: Apache 2.0 (상업적 사용 무제한, 로열티 없음)

### 사전 준비

```bash
# 1. Ollama 모델 다운로드 (최초 1회)
ollama pull gemma4:12b        # 기본 모델 (~6.6GB)
ollama pull gemma4:26b        # 고성능 모델 (~15GB, 선택)
ollama pull qwen3:8b          # 빠른 반복용 (선택)

# 2. Python 가상환경 활성화
source .venv/bin/activate

# 3. Crew 실행
python main.py research   # Step 1: 시장 조사
python main.py planning   # Step 2-4: 기획
```

### 모델 선택 가이드 (M4 Pro 48GB, 273 GB/s 기준)

| 모델 | 타입 | 활성 | RAM | 속도 | Tool-call | 용도 |
|------|------|------|-----|------|-----------|------|
| `gemma4:12b` | Dense | 12B | ~6.6GB | ~80-90 t/s | ~90% | **기본 추천** |
| `gemma4:26b` | MoE | 4B | ~15GB | ~70-80 t/s | ~90% | 고성능 분석 |
| `qwen3:8b` | Dense | 8B | ~5.2GB | ~120+ t/s | ~85% | 빠른 반복 |
| `qwen3.5:35b-a3b` | MoE | 3B | ~20GB | ~70-80 t/s | 85% | 코딩 특화 |
| `qwen3:14b` | Dense | 14B | ~9GB | ~60-70 t/s | 85-90% | 범용 대안 |

### 모델 선정 근거

프레임워크 5종 비교 (CrewAI vs LangGraph vs smolagents vs AutoGen vs Swarm),
모델 6종 비교 (Gemma 4, Qwen3, Qwen3.5, Llama 3.3, DeepSeek R1, Phi-4)를 수행.

**검토 기준**: 라이선스(Apache 2.0 필수), M4 Pro 48GB 하드웨어 호환성,
에이전트 tool-call 신뢰도, 응답 속도(tok/s), RAM 사용량.

**Gemma 4 12B 채택 이유**:
1. 네이티브 function calling 내장 → tool-call 신뢰도 최고 (~90%)
2. ~6.6GB RAM → 48GB에서 여유롭게 구동, 다른 작업 병행 가능
3. ~80-90 tok/s → Dense 14B(~60-70)보다 빠름
4. MMLU Pro 77.2% → 구 세대 27B(67.6%) 능가
5. Apache 2.0 → MAU 제한 없음 (Llama의 7억 제한 vs 없음)

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
