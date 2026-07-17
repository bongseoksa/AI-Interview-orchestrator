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


def _chunk_text(text: str, max_len: int = 1860) -> list[str]:
    """텍스트를 max_len 이하 청크로 분할한다 (Notion rich_text 제한 2000자, 7% 마진)."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # 줄바꿈 기준으로 자르기 시도
        cut = text.rfind("\n", 0, max_len)
        if cut <= 0:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks


def _parse_inline_formatting(text: str) -> list[dict]:
    """인라인 볼드(**text**)를 Notion rich_text 배열로 변환한다.
    2000자 초과 시 자동 분할."""
    # 1860자(2000 - 7% 마진) 이하면 기존 로직
    if len(text) <= 1860:
        return _parse_inline_simple(text)
    # 초과: 청크 분할 후 각각 파싱
    parts: list[dict] = []
    for chunk in _chunk_text(text, 1860):
        parts.extend(_parse_inline_simple(chunk))
    return parts


def _parse_inline_simple(text: str) -> list[dict]:
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
            code_text = "\n".join(code_lines)
            # 2000자 초과 시 여러 코드블록으로 분할
            for chunk in _chunk_text(code_text, 2000):
                blocks.append({
                    "object": "block", "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}],
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


def _read_page_raw(page: str) -> str:
    """Notion 페이지 전체 내용을 마크다운으로 반환한다 (글자수 제한 없음)."""
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
    header = f"# {title}\n\n" if title else ""
    return header + text


# CrewAI 에이전트용 글자수 제한 (LLM 컨텍스트 보호)
AGENT_READ_LIMIT = 8000


@tool("read_notion_page")
def read_notion_page(page: str) -> str:
    """Notion 페이지 내용을 읽어 마크다운 텍스트로 반환한다. page는 페이지 이름(예: 기획서) 또는 페이지 ID. LLM 컨텍스트 보호를 위해 8000자로 제한된다."""
    text = _read_page_raw(page)
    if len(text) > AGENT_READ_LIMIT:
        text = text[:AGENT_READ_LIMIT] + f"\n\n... (총 {len(text)}자 중 {AGENT_READ_LIMIT}자까지 표시. 나머지는 read_notion_page_full 도구로 offset 지정하여 읽기)"
    return text


@tool("read_notion_page_full")
def read_notion_page_full(page: str, offset: int = 0, limit: int = 8000) -> str:
    """Notion 페이지를 offset/limit으로 구간 읽기한다. 긴 페이지를 나눠 읽을 때 사용. offset은 시작 글자 위치, limit은 읽을 글자수."""
    text = _read_page_raw(page)
    total = len(text)
    chunk = text[offset:offset + limit]
    remaining = total - offset - len(chunk)
    footer = ""
    if remaining > 0:
        footer = f"\n\n... ({remaining}자 남음. offset={offset + len(chunk)}으로 다음 구간 읽기)"
    return f"[{offset}~{offset + len(chunk)} / 총 {total}자]\n\n{chunk}{footer}"


# Notion API 1회 요청당 최대 블록 수 (제한 100, 7% 마진 적용)
MAX_BLOCKS_PER_REQUEST = 93


@tool("append_to_notion_page")
def append_to_notion_page(page: str, markdown_content: str) -> str:
    """Notion 페이지 하단에 마크다운 내용을 추가한다. page는 페이지 이름 또는 ID. 100블록 초과 시 자동 분할 전송."""
    page_id = _resolve_page_id(page)
    if not page_id:
        return f"페이지를 찾을 수 없습니다: {page}\n사용 가능한 페이지: {', '.join(PAGE_ID_MAP.keys())}"

    blocks = _markdown_to_blocks(markdown_content)
    if not blocks:
        return "변환할 블록이 없습니다. 마크다운 내용을 확인하세요."

    # 100블록씩 청크로 분할 전송
    total_added = 0
    for i in range(0, len(blocks), MAX_BLOCKS_PER_REQUEST):
        chunk = blocks[i:i + MAX_BLOCKS_PER_REQUEST]
        resp = _api_request("PATCH", f"/blocks/{page_id}/children", {"children": chunk})
        if "error" in resp:
            return f"블록 {i}~{i+len(chunk)} 전송 중 오류: {resp['error']} (이전 {total_added}개 블록은 이미 반영됨)"
        total_added += len(resp.get("results", []))

    chunks_sent = (len(blocks) + MAX_BLOCKS_PER_REQUEST - 1) // MAX_BLOCKS_PER_REQUEST
    chunk_info = f" ({chunks_sent}회 분할 전송)" if chunks_sent > 1 else ""
    return f"Notion 페이지에 {total_added}개 블록 추가 완료{chunk_info} (page_id: {page_id})"


# ── 중간 편집 도구 ──


def _get_all_blocks(page_id: str) -> list[dict]:
    """페이지의 모든 블록을 페이지네이션하여 가져온다."""
    all_blocks: list[dict] = []
    cursor = None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        resp = _api_request("GET", path)
        if "error" in resp:
            return []
        all_blocks.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return all_blocks


def _block_text(block: dict) -> str:
    """블록에서 plain_text를 추출한다."""
    btype = block.get("type", "")
    data = block.get(btype, {})
    rich_text = data.get("rich_text", [])
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def _block_summary(block: dict) -> str:
    """블록을 한 줄 요약으로 반환한다."""
    btype = block.get("type", "")
    text = _block_text(block)
    bid = block.get("id", "")
    prefix = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### ",
              "bulleted_list_item": "- ", "numbered_list_item": "1. ",
              "code": "```", "paragraph": ""}.get(btype, f"[{btype}] ")
    preview = text[:120] + ("..." if len(text) > 120 else "")
    return f"[{bid}] {prefix}{preview}"


@tool("search_notion_blocks")
def search_notion_blocks(page: str, keyword: str) -> str:
    """Notion 페이지에서 keyword가 포함된 블록을 검색한다. 블록 ID, 타입, 내용, 전후 맥락을 반환한다. page는 페이지 이름 또는 ID."""
    page_id = _resolve_page_id(page)
    if not page_id:
        return f"페이지를 찾을 수 없습니다: {page}"

    blocks = _get_all_blocks(page_id)
    if not blocks:
        return "블록을 가져올 수 없습니다."

    matches: list[str] = []
    keyword_lower = keyword.lower()

    for idx, block in enumerate(blocks):
        text = _block_text(block)
        if keyword_lower not in text.lower():
            continue

        lines = [f"\n=== 매치 {len(matches) + 1} ==="]

        # 이전 블록 (맥락)
        if idx > 0:
            lines.append(f"  이전: {_block_summary(blocks[idx - 1])}")

        # 매치 블록
        bid = block.get("id", "")
        btype = block.get("type", "")
        lines.append(f"  >>> [{bid}] type={btype}")
        lines.append(f"      내용: {text[:500]}")

        # 다음 블록 (맥락)
        if idx < len(blocks) - 1:
            lines.append(f"  다음: {_block_summary(blocks[idx + 1])}")

        matches.append("\n".join(lines))

    if not matches:
        return f"'{keyword}'를 포함하는 블록이 없습니다."

    header = f"'{keyword}' 검색 결과: {len(matches)}건 (전체 {len(blocks)}블록 중)"
    return header + "\n".join(matches)


@tool("update_notion_block")
def update_notion_block(block_id: str, new_content: str) -> str:
    """특정 블록의 텍스트 내용을 교체한다. block_id는 search_notion_blocks로 찾은 ID. 블록 타입은 유지되고 내용만 바뀐다."""
    # 기존 블록 가져오기
    resp = _api_request("GET", f"/blocks/{block_id}")
    if "error" in resp:
        return f"블록 조회 실패: {resp['error']}"

    btype = resp.get("type", "")
    old_text = _block_text(resp)

    # 지원하는 블록 타입
    supported = {
        "paragraph", "heading_1", "heading_2", "heading_3",
        "bulleted_list_item", "numbered_list_item", "to_do", "code",
        "toggle", "callout", "quote",
    }
    if btype not in supported:
        return f"수정 불가능한 블록 타입: {btype}"

    # 새 rich_text 생성
    rich_text = _parse_inline_formatting(new_content)

    # 블록 업데이트
    update_body: dict = {btype: {"rich_text": rich_text}}

    # 코드블록은 language 유지
    if btype == "code":
        old_lang = resp.get("code", {}).get("language", "plain text")
        update_body["code"]["language"] = old_lang

    resp = _api_request("PATCH", f"/blocks/{block_id}", update_body)
    if "error" in resp:
        return f"블록 수정 실패: {resp['error']}"

    return f"블록 수정 완료 (id: {block_id}, type: {btype})\n  이전: {old_text[:200]}\n  이후: {new_content[:200]}"


@tool("delete_notion_block")
def delete_notion_block(block_id: str) -> str:
    """특정 블록을 삭제한다. block_id는 search_notion_blocks로 찾은 ID."""
    # 삭제 전 내용 확인
    resp = _api_request("GET", f"/blocks/{block_id}")
    if "error" in resp:
        return f"블록 조회 실패: {resp['error']}"

    btype = resp.get("type", "")
    old_text = _block_text(resp)

    # 삭제 실행
    resp = _api_request("DELETE", f"/blocks/{block_id}")
    if "error" in resp:
        return f"블록 삭제 실패: {resp['error']}"

    return f"블록 삭제 완료 (id: {block_id}, type: {btype})\n  삭제된 내용: {old_text[:200]}"


@tool("insert_after_notion_block")
def insert_after_notion_block(page: str, after_block_id: str, markdown_content: str) -> str:
    """특정 블록 뒤에 새 블록을 삽입한다. page는 페이지 이름/ID, after_block_id는 기준 블록 ID."""
    page_id = _resolve_page_id(page)
    if not page_id:
        return f"페이지를 찾을 수 없습니다: {page}"

    blocks = _markdown_to_blocks(markdown_content)
    if not blocks:
        return "변환할 블록이 없습니다."

    # 93블록씩 분할 전송 (after 파라미터 사용)
    total_added = 0
    current_after = after_block_id
    for i in range(0, len(blocks), MAX_BLOCKS_PER_REQUEST):
        chunk = blocks[i:i + MAX_BLOCKS_PER_REQUEST]
        resp = _api_request("PATCH", f"/blocks/{page_id}/children", {
            "children": chunk,
            "after": current_after,
        })
        if "error" in resp:
            return f"삽입 실패: {resp['error']} (이전 {total_added}개는 반영됨)"
        results = resp.get("results", [])
        total_added += len(results)
        # 다음 청크는 마지막으로 삽입된 블록 뒤에
        if results:
            current_after = results[-1]["id"]

    return f"블록 {after_block_id} 뒤에 {total_added}개 블록 삽입 완료"


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
