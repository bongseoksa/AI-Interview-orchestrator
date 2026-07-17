"""LLM 설정 — Ollama 로컬 모델만 사용 (무료, 전부 Apache 2.0)

모델 선정 기준 (M4 Pro 48GB, 273 GB/s 대역폭):
- 라이선스: Apache 2.0 (상업적 사용 무제한)
- Tool-call 신뢰도: 에이전트 프레임워크 호환성
- 응답 속도: Ollama+MLX 기준 tok/s
- RAM 사용량: 48GB 내에서 여유 확보

모델 비교 (2026-07):
| 모델              | 타입  | 활성   | RAM    | 속도       | Tool-call | 용도           |
|-------------------|-------|--------|--------|------------|-----------|----------------|
| gemma4:12b        | Dense | 12B    | ~6.6GB | ~80-90t/s  | ~90%      | 기본 (추천)    |
| gemma4:26b        | MoE   | 4B     | ~15GB  | ~70-80t/s  | ~90%      | 고성능 분석    |
| qwen3:8b          | Dense | 8B     | ~5.2GB | ~120+t/s   | ~85%      | 빠른 반복      |
| qwen3.5:35b-a3b   | MoE   | 3B     | ~20GB  | ~70-80t/s  | 85%       | 코딩 특화      |
| qwen3:14b         | Dense | 14B    | ~9GB   | ~60-70t/s  | 85-90%    | 범용 대안      |

참고: https://huggingface.co/blog/daya-shankar/open-source-llms
"""

from crewai import LLM

# 기본 모델: Gemma 4 12B — tool-call 신뢰도 최고, 빠르고 가벼움
# Gemma 4는 네이티브 function calling 내장 (Google 설계)
DEFAULT_MODEL = "ollama/gemma4:12b"

# 고성능 모델: Gemma 4 26B MoE (4B 활성) — 복잡한 분석/설계 시 사용
HIGH_PERF_MODEL = "ollama/gemma4:26b"

# 빠른 반복 모델: Qwen3 8B — 간단한 태스크, 최고 속도
FAST_MODEL = "ollama/qwen3:8b"

OLLAMA_BASE_URL = "http://localhost:11434"


def get_llm(model: str | None = None) -> LLM:
    """Ollama LLM 인스턴스 반환"""
    return LLM(
        model=model or DEFAULT_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
