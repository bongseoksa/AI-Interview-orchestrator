"""코드 생성용 파일 도구 — 다른 레포에 안전하게 접근"""

from pathlib import Path

from crewai.tools import tool

# 탐색 시 무시할 디렉토리
IGNORE_DIRS = {
    ".venv", "venv", "node_modules", ".next", ".git",
    "__pycache__", ".cache", "dist", "build", ".turbo",
}

# 허용하는 프로젝트 루트
PROJECT_BASE = Path(__file__).resolve().parent.parent.parent.parent


def _validate_path(path_str: str) -> Path:
    """경로가 프로젝트 범위 내인지 검증한다."""
    p = Path(path_str).resolve()
    if not str(p).startswith(str(PROJECT_BASE)):
        raise ValueError(f"허용 범위 밖 경로: {p}")
    return p


@tool("list_directory")
def list_directory(directory: str) -> str:
    """디렉토리의 파일/폴더 목록을 트리 형태로 반환한다. .venv, node_modules 등은 제외."""
    target = _validate_path(directory)
    if not target.is_dir():
        return f"디렉토리 없음: {target}"

    lines = []
    for item in sorted(target.iterdir()):
        if item.name in IGNORE_DIRS or item.name.startswith("."):
            continue
        prefix = "[DIR]  " if item.is_dir() else "[FILE] "
        lines.append(f"{prefix}{item.name}")
    return "\n".join(lines) if lines else "(빈 디렉토리)"


@tool("list_directory_recursive")
def list_directory_recursive(directory: str, max_depth: int = 3) -> str:
    """디렉토리를 재귀적으로 탐색하여 트리를 반환한다. max_depth로 깊이 제한."""
    target = _validate_path(directory)
    if not target.is_dir():
        return f"디렉토리 없음: {target}"

    lines = []

    def _walk(path: Path, depth: int, indent: str):
        if depth > max_depth:
            return
        try:
            items = sorted(path.iterdir())
        except PermissionError:
            return
        for item in items:
            if item.name in IGNORE_DIRS or item.name.startswith("."):
                continue
            if item.is_dir():
                lines.append(f"{indent}{item.name}/")
                _walk(item, depth + 1, indent + "  ")
            else:
                lines.append(f"{indent}{item.name}")

    _walk(target, 1, "")
    return "\n".join(lines[:500]) if lines else "(빈 디렉토리)"


@tool("read_file")
def read_file(file_path: str) -> str:
    """파일 내용을 읽어 반환한다. 최대 500줄."""
    target = _validate_path(file_path)
    if not target.is_file():
        return f"파일 없음: {target}"
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > 500:
        return "\n".join(lines[:500]) + f"\n\n... ({len(lines) - 500}줄 생략)"
    return text


@tool("write_file")
def write_file(file_path: str, content: str) -> str:
    """파일에 내용을 쓴다. 디렉토리가 없으면 자동 생성한다."""
    target = _validate_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"파일 생성 완료: {target} ({len(content)}자)"
