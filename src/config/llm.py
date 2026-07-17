"""LLM 설정 — Ollama 로컬 모델만 사용 (무료)"""

from crewai import LLM

# 기본 모델: Qwen3 14B (M4 Pro 48GB에서 쾌적하게 구동)
# 대안: qwen3:8b (가벼움), qwen3:32b (고성능), llama3.3 (범용)
DEFAULT_MODEL = "ollama/qwen3:14b"
OLLAMA_BASE_URL = "http://localhost:11434"


def get_llm(model: str | None = None) -> LLM:
    """Ollama LLM 인스턴스 반환"""
    return LLM(
        model=model or DEFAULT_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
