"""노션 API 도구 — CrewAI 에이전트가 Notion 페이지를 직접 읽기/쓰기

환경변수:
    NOTION_TOKEN — Notion Integration 토큰 (필수)
                   .env 파일에서도 읽음
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path

from crewai.tools import tool

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# 페이지 이름 → Notion 페이지 ID 매핑
PAGE_ID_MAP: dict[str, str] = {
    "메인": "3a0141f8-c327-80eb-ba18-d9637ff76f63",
    "메인 허브": "3a0141f8-c327-80eb-ba18-d9637ff76f63",
    "AI Interview": "3a0141f8-c327-80eb-ba18-d9637ff76f63",
    "기획서": "3a0141f8-c327-81fe-bfbf-e35fd03e8c19",
    "사업계획서": "3a0141f8-c327-8186-9810-c8c025aa943b",
    "진행 가이드": "3a0141f8-c327-81ba-9d0e-e7444b9d2df8",
    "프로젝트 진행 가이드": "3a0141f8-c327-81ba-9d0e-e7444b9d2df8",
    "에이전트 조직 구조": "3a0141f8-c327-81e1-8d29-d4698f6e6161",
    "의사결정 기록": "3a0141f8-c327-81fd-8884-e1a9447b1fc0",
    "Step 1 시장 조사 보고서": "3a0141f8-c327-8189-8d69-dbc5531fff9a",
    "Step 2 PRD": "3a0141f8-c327-8111-a9bd-f62a1d4a92b9",
    "Step 3 Handoff": "3a0141f8-c327-8153-bd9f-ce64916fda71",
    "시드 데이터 뱅크": "3a0141f8-c327-81a8-9d4e-e9aaeb3665a3",
    "Q&A DB": "3a0141f8-c327-81dd-a1a2-f103d25b61bc",
}


def _get_token() -> str:
    """환경변수 또는 .env에서 NOTION_TOKEN을 가져온다."""
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("NOTION_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _api_request(
    method: str, path: str, body: dict | None = None
) -> dict:
    """Notion API에 요청을 보낸다."""
    token = _get_token()
    if not token:
        return {"error": "NOTION_TOKEN이 설정되지 않았습니다. .env 파일에 NOTION_TOKEN=<token>을 추가하세요."}

    url = f"{NOTION_API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.readable() else str(e)
        return {"error": f"Notion API {e.code}: {error_body[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def _resolve_page_id(page_name_or_id: str) -> str | None:
    """페이지 이름 또는 ID를 Notion 페이지 ID로 변환한다."""
    # UUID 형식이면 그대로 반환
    if re.match(r"^[0-9a-f-]{32,36}$", page_name_or_id):
        return page_name_or_id
    # 이름으로 매핑
    for name, pid in PAGE_ID_MAP.items():
        if name in page_name_or_id or page_name_or_id in name:
            return pid
    return None


def _blocks_to_text(blocks: list[dict], indent: str = "") -> str:
    """Notion 블록 리스트를 읽기 쉬운 텍스트로 변환한다."""
    lines: list[str] = []
    for block in blocks:
        btype = block.get("type", "")
        data = block.get(btype, {})

        # rich_text 추출
        rich_text = data.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich_text)

        if btype == "heading_1":
            lines.append(f"{indent}# {text}")
        elif btype == "heading_2":
            lines.append(f"{indent}## {text}")
        elif btype == "heading_3":
            lines.append(f"{indent}### {text}")
        elif btype == "bulleted_list_item":
            lines.append(f"{indent}- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"{indent}1. {text}")
        elif btype == "to_do":
            checked = data.get("checked", False)
            mark = "x" if checked else " "
            lines.append(f"{indent}- [{mark}] {text}")
        elif btype == "code":
            lang = data.get("language", "")
            lines.append(f"{indent}```{lang}")
            lines.append(text)
            lines.append(f"{indent}```")
        elif btype == "toggle":
            lines.append(f"{indent}> {text}")
        elif btype == "divider":
            lines.append(f"{indent}---")
        elif btype == "callout":
            icon = block.get("callout", {}).get("icon", {})
            emoji = icon.get("emoji", "") if icon else ""
            lines.append(f"{indent}{emoji} {text}")
        elif btype == "table_row":
            cells = data.get("cells", [])
            row = " | ".join(
                "".join(c.get("plain_text", "") for c in cell)
                for cell in cells
            )
            lines.append(f"{indent}| {row} |")
        elif text:
            lines.append(f"{indent}{text}")

        # has_children 처리
        if block.get("has_children") and btype not in ("child_page", "child_database"):
            child_resp = _api_request("GET", f"/blocks/{block['id']}/children")
            if "results" in child_resp:
                lines.append(_blocks_to_text(child_resp["results"], indent + "  "))

    return "\n".join(lines)


def _parse_inline_formatting(text: str) -> list[dict]:
    """인라인 볼드(**text**)를 Notion rich_text 배열로 변환한다."""
    parts: list[dict] = []
    pattern = re.compile(r"\*\*(.+?)\*\*")
    last_end = 0
    for match in pattern.finditer(text):
        if match.start() > last_end:
            parts.append({"type": "text", "text": {"content": text[last_end:match.start()]}})
        parts.append({
            "type": "text",
            "text": {"content": match.group(1)},
            "annotations": {"bold": True},
        })
        last_end = match.end()
    if last_end < len(text):
        parts.append({"type": "text", "text": {"content": text[last_end:]}})
    if not parts:
        parts.append({"type": "text", "text": {"content": text}})
    return parts


def _markdown_to_blocks(markdown: str) -> list[dict]:
    """마크다운 텍스트를 Notion 블록 리스트로 변환한다."""
    blocks: list[dict] = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        # 코드블록
        if line.strip().startswith("```"):
            lang = line.strip().removeprefix("```").strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang or "plain text",
                },
            })
            continue

        # h1
        if line.startswith("# ") and not line.startswith("## "):
            blocks.append({
                "object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]},
            })
            i += 1
            continue

        # h2
        if line.startswith("## ") and not line.startswith("### "):
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]},
            })
            i += 1
            continue

        # h3
        if line.startswith("### "):
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]},
            })
            i += 1
            continue

        # 불릿
        if re.match(r"^[\-\*]\s", line.strip()):
            text = re.sub(r"^[\-\*]\s", "", line.strip())
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _parse_inline_formatting(text)},
            })
            i += 1
            continue

        # 일반 단락
        blocks.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _parse_inline_formatting(line.strip())},
        })
        i += 1

    return blocks


# ── CrewAI 도구 정의 ──


@tool("list_notion_pages")
def list_notion_pages() -> str:
    """사용 가능한 Notion 페이지 목록과 ID를 반환한다."""
    seen: dict[str, list[str]] = {}
    for name, pid in PAGE_ID_MAP.items():
        seen.setdefault(pid, []).append(name)
    lines = []
    for pid, names in seen.items():
        lines.append(f"- {' / '.join(names)}: {pid}")
    return "\n".join(lines)


@tool("read_notion_page")
def read_notion_page(page: str) -> str:
    """Notion 페이지 내용을 읽어 마크다운 텍스트로 반환한다. page는 페이지 이름(예: 기획서) 또는 페이지 ID."""
    page_id = _resolve_page_id(page)
    if not page_id:
        return f"페이지를 찾을 수 없습니다: {page}\n사용 가능한 페이지: {', '.join(PAGE_ID_MAP.keys())}"

    # 페이지 제목 가져오기
    page_info = _api_request("GET", f"/pages/{page_id}")
    if "error" in page_info:
        return page_info["error"]

    title = ""
    props = page_info.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title = "".join(
                rt.get("plain_text", "")
                for rt in prop.get("title", [])
            )
            break

    # 블록 내용 가져오기 (페이지네이션)
    all_blocks: list[dict] = []
    cursor = None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        resp = _api_request("GET", path)
        if "error" in resp:
            return resp["error"]
        all_blocks.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    text = _blocks_to_text(all_blocks)

    # 최대 길이 제한 (LLM 컨텍스트 보호)
    if len(text) > 8000:
        text = text[:8000] + f"\n\n... (총 {len(text)}자 중 8000자까지 표시)"

    header = f"# {title}\n\n" if title else ""
    return header + text


@tool("append_to_notion_page")
def append_to_notion_page(page: str, markdown_content: str) -> str:
    """Notion 페이지 하단에 마크다운 내용을 추가한다. page는 페이지 이름 또는 ID."""
    page_id = _resolve_page_id(page)
    if not page_id:
        return f"페이지를 찾을 수 없습니다: {page}\n사용 가능한 페이지: {', '.join(PAGE_ID_MAP.keys())}"

    blocks = _markdown_to_blocks(markdown_content)
    if not blocks:
        return "변환할 블록이 없습니다. 마크다운 내용을 확인하세요."

    resp = _api_request("PATCH", f"/blocks/{page_id}/children", {"children": blocks})
    if "error" in resp:
        return resp["error"]

    count = len(resp.get("results", []))
    return f"Notion 페이지에 {count}개 블록 추가 완료 (page_id: {page_id})"


@tool("query_notion_database")
def query_notion_database(database_id: str, filter_json: str = "") -> str:
    """Notion 데이터베이스를 쿼리한다. filter_json은 Notion filter 객체의 JSON 문자열 (선택)."""
    body: dict = {"page_size": 20}
    if filter_json:
        try:
            body["filter"] = json.loads(filter_json)
        except json.JSONDecodeError:
            return f"filter_json 파싱 실패: {filter_json}"

    resp = _api_request("POST", f"/databases/{database_id}/query", body)
    if "error" in resp:
        return resp["error"]

    results = resp.get("results", [])
    if not results:
        return "검색 결과가 없습니다."

    lines = [f"총 {len(results)}건 (최대 20건 표시)\n"]
    for item in results:
        props = item.get("properties", {})
        parts = []
        for prop_name, prop_data in props.items():
            ptype = prop_data.get("type", "")
            val = ""
            if ptype == "title":
                val = "".join(rt.get("plain_text", "") for rt in prop_data.get("title", []))
            elif ptype == "rich_text":
                val = "".join(rt.get("plain_text", "") for rt in prop_data.get("rich_text", []))
            elif ptype == "select":
                sel = prop_data.get("select")
                val = sel.get("name", "") if sel else ""
            elif ptype == "multi_select":
                val = ", ".join(s.get("name", "") for s in prop_data.get("multi_select", []))
            elif ptype == "number":
                val = str(prop_data.get("number", ""))
            elif ptype == "checkbox":
                val = str(prop_data.get("checkbox", ""))
            if val:
                parts.append(f"{prop_name}: {val}")
        lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)
