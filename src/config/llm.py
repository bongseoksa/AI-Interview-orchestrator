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

import json
import sys
import urllib.error
import urllib.request
from typing import Callable, Dict, Any

from crewai import LLM

# 기본 모델: Gemma 4 12B — tool-call 신뢰도 최고, 빠르고 가벼움
DEFAULT_MODEL = "ollama/gemma4:12b"

# 고성능 모델: Gemma 4 26B MoE (4B 활성) — 복잡한 분석/설계 시 사용
HIGH_PERF_MODEL = "ollama/gemma4:26b"

# 빠른 반복 모델: Qwen3 8B — 간단한 태스크, 최고 속도
FAST_MODEL = "ollama/qwen3:8b"

OLLAMA_BASE_URL = "http://localhost:11434"

# Ollama에 설치된 모델 캐시 (프로세스 내 1회 조회)
_available_models: set[str] | None = None


def _get_available_models() -> set[str]:
    """Ollama 서버에서 설치된 모델 목록을 조회한다."""
    global _available_models
    if _available_models is not None:
        return _available_models
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        _available_models = {m["name"] for m in data.get("models", [])}
    except (urllib.error.URLError, OSError):
        print("  [LLM] Ollama 서버 연결 실패 — 로컬 모델 목록 조회 불가", file=sys.stderr)
        _available_models = set()
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [LLM] Ollama 응답 파싱 실패: {e}", file=sys.stderr)
        _available_models = set()
    return _available_models


def _is_model_available(model: str) -> bool:
    """Ollama에 해당 모델이 설치되어 있는지 확인한다."""
    ollama_name = model.removeprefix("ollama/")
    return ollama_name in _get_available_models()


def get_llm(model: str | None = None, model_type_map: Dict[str, str] | None = None) -> LLM:
    """
    Ollama LLM 인스턴스 반환. 
    
    Args:
        model: 요청할 모델명 (e.g., 'ollama/gemma4:12b')
        model_type_map: 특정 타입(high_perf)을 매핑하는 사전. 
                        예: {'high_perf': 'ollama/gemma4:26b'}
    """
    requested = model or DEFAULT_MODEL
    
    # 타입 기반 매핑 처리 (Dependency Injection Interface)
    if model_type_map and not requested.startswith("ollama/"):
        # 만약 요청된 것이 단순 식별자라면(예: 'high_perf') 맵에서 찾음
        requested = model_type_map.get(requested, DEFAULT_MODEL)

    if not _is_model_available(requested) and requested != DEFAULT_MODEL:
        fallback = DEFAULT_MODEL
        ollama_name = requested.removeprefix("ollama/")
        default_name = fallback.removeprefix("ollama/")
        print(f"  [LLM fallback] {ollama_name} 미설치 → {default_name} 사용")
        requested = fallback
        
    return LLM(
        model=requested,
        base_url=OLLAMA_BASE_URL,
    )

def get_llm_factory(model_type_map: Dict[str, str] | None = None) -> Callable[[str], LLM]:
    """
    특정 모델 타입을 주면 LLM을 반환하는 Factory 함수를 생성합니다.
    이 방식은 Crew의 의존성 주입(DI)를 용이하게 합니다.
    """
    def factory(model_type: str) -> LLM:
        # 전달받은 model_type이 맵에 있으면 해당 모델로, 없으면 기본값으로 호출
        return get_llm(model=model_type, model_type_map=model_type_map)
    return factory
