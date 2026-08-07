"""확인함 — 승인 후 노션 반영 (docs/gui/07 §7, docs/gui/05 §A)

큐를 DB로 만들지 않는다. output/_review/<run_id>.json 파일 존재 자체가 대기 상태다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DIR = PROJECT_ROOT / "output" / "_review"

# 회의록·결정사항이 붙는 부모 페이지 (07 §6 — 형제 페이지로 둔다)
MEETING_PARENT = "에이전트 회의록"


def _path(run_id: str) -> Path:
    return REVIEW_DIR / f"{run_id}.json"


def enqueue(run_id: str, agenda: str, date: str, docs: list[dict[str, str]]) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    _path(run_id).write_text(
        json.dumps({"run_id": run_id, "agenda": agenda, "date": date, "docs": docs},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pending() -> list[dict[str, Any]]:
    if not REVIEW_DIR.exists():
        return []
    items = []
    for p in sorted(REVIEW_DIR.glob("*.json")):
        try:
            items.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return items


def preview(run_id: str) -> dict[str, Any]:
    p = _path(run_id)
    if not p.exists():
        return {"error": "대기 항목 없음"}
    item = json.loads(p.read_text(encoding="utf-8"))
    for d in item["docs"]:
        f = Path(d["path"])
        d["content"] = f.read_text(encoding="utf-8") if f.exists() else "(초안 파일 없음)"
    return item


def approve(run_id: str) -> dict[str, Any]:
    """노션에 child page 2건 생성. 페이지 제목 = 파일명 (doc_name 동일 소스)."""
    from src.tools.notion_tools import create_notion_child_page

    p = _path(run_id)
    if not p.exists():
        return {"error": "대기 항목 없음"}
    item = json.loads(p.read_text(encoding="utf-8"))

    results = []
    for d in item["docs"]:
        f = Path(d["path"])
        if not f.exists():
            results.append({"title": d["title"], "error": "초안 파일 없음"})
            continue
        try:
            msg = create_notion_child_page.run(
                parent_page=MEETING_PARENT,
                title=d["title"],
                markdown_content=f.read_text(encoding="utf-8"),
            )
            results.append({"title": d["title"], "result": str(msg)})
        except Exception as e:
            results.append({"title": d["title"], "error": str(e)})

    if any("error" in r for r in results):
        # 큐를 남긴다 — 재시도 가능
        return {"ok": False, "results": results}

    p.unlink()  # md는 남긴다 (노션 장애 시 재시도 원본)
    return {"ok": True, "results": results}


def reject(run_id: str) -> dict[str, Any]:
    p = _path(run_id)
    if not p.exists():
        return {"error": "대기 항목 없음"}
    item = json.loads(p.read_text(encoding="utf-8"))
    for d in item["docs"]:
        Path(d["path"]).unlink(missing_ok=True)
    p.unlink()
    return {"ok": True}
