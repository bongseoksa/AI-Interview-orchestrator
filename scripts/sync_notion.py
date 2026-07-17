#!/usr/bin/env python3
"""서기에이전트 노션 동기화 스크립트.

output/notion-update-draft.md를 읽어 Notion 페이지에 반영한다.
서기에이전트가 생성한 초안을 파싱 → 페이지별 미리보기 → 확인 후 반영.

사용법:
    python scripts/sync_notion.py                    # 대화형 (페이지별 확인)
    python scripts/sync_notion.py --dry-run          # 미리보기만 (반영 안 함)
    python scripts/sync_notion.py --auto             # 전체 자동 반영 (확인 생략)

환경변수:
    NOTION_TOKEN  — Notion Integration 토큰 (필수)
                    .env 파일에서도 읽음
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFT_PATH = PROJECT_ROOT / "output" / "notion-update-draft.md"
ENV_PATH = PROJECT_ROOT / ".env"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# 페이지 이름 → Notion 페이지 ID 매핑
PAGE_ID_MAP: dict[str, str] = {
    "메인 허브": "3a0141f8-c327-80eb-ba18-d9637ff76f63",
    "AI Interview": "3a0141f8-c327-80eb-ba18-d9637ff76f63",
    "기획서": "3a0141f8-c327-81fe-bfbf-e35fd03e8c19",
    "사업계획서": "3a0141f8-c327-8186-9810-c8c025aa943b",
    "프로젝트 진행 가이드": "3a0141f8-c327-81ba-9d0e-e7444b9d2df8",
    "진행 가이드": "3a0141f8-c327-81ba-9d0e-e7444b9d2df8",
    "에이전트 조직 구조": "3a0141f8-c327-81e1-8d29-d4698f6e6161",
    "의사결정 기록": "3a0141f8-c327-81fd-8884-e1a9447b1fc0",
    "Step 1 시장 조사 보고서": "3a0141f8-c327-8189-8d69-dbc5531fff9a",
    "Step 2 PRD": "3a0141f8-c327-8111-a9bd-f62a1d4a92b9",
    "Step 3 Handoff": "3a0141f8-c327-8153-bd9f-ce64916fda71",
    "시드 데이터 뱅크": "3a0141f8-c327-81a8-9d4e-e9aaeb3665a3",
}


@dataclass
class PageUpdate:
    """하나의 Notion 페이지에 대한 업데이트 정보."""

    page_name: str
    page_id: str | None
    raw_content: str
    changes: list[str] = field(default_factory=list)


# ── Notion API 호출 ──


def _get_notion_token() -> str:
    """환경변수 또는 .env 파일에서 NOTION_TOKEN을 가져온다."""
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("NOTION_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _notion_request(
    method: str, path: str, body: dict | None = None, token: str = ""
) -> dict:
    """Notion API에 요청을 보낸다."""
    url = f"{NOTION_API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _markdown_to_blocks(markdown: str) -> list[dict]:
    """간단한 마크다운을 Notion 블록 객체 리스트로 변환한다.

    지원 요소: h3, h4, 불릿 리스트, 일반 단락, 코드블록.
    """
    blocks: list[dict] = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # 빈 줄 건너뛰기
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
            i += 1  # 닫는 ``` 건너뛰기
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang or "plain text",
                },
            })
            continue

        # h3 (### )
        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}],
                },
            })
            i += 1
            continue

        # h4 (#### )
        if line.startswith("#### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[5:].strip()}}],
                },
            })
            i += 1
            continue

        # 불릿 리스트 (- 또는 * )
        if re.match(r"^[\-\*]\s", line.strip()):
            text = re.sub(r"^[\-\*]\s", "", line.strip())
            # 볼드 처리: **text** → Notion rich_text with bold annotation
            rich_text = _parse_inline_formatting(text)
            block: dict = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text},
            }
            # 하위 불릿 (탭/2스페이스 들여쓰기) → children
            children = []
            while i + 1 < len(lines) and re.match(r"^(\t|  +)[\-\*]\s", lines[i + 1]):
                i += 1
                child_text = re.sub(r"^(\t|  +)[\-\*]\s", "", lines[i])
                child_rich = _parse_inline_formatting(child_text)
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": child_rich},
                })
            if children:
                block["bulleted_list_item"]["children"] = children
            blocks.append(block)
            i += 1
            continue

        # 일반 단락
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": _parse_inline_formatting(line.strip()),
            },
        })
        i += 1

    return blocks


def _parse_inline_formatting(text: str) -> list[dict]:
    """인라인 볼드(**text**)를 Notion rich_text 배열로 변환한다."""
    parts: list[dict] = []
    pattern = re.compile(r"\*\*(.+?)\*\*")
    last_end = 0

    for match in pattern.finditer(text):
        # 볼드 앞 일반 텍스트
        if match.start() > last_end:
            parts.append({
                "type": "text",
                "text": {"content": text[last_end : match.start()]},
            })
        # 볼드 텍스트
        parts.append({
            "type": "text",
            "text": {"content": match.group(1)},
            "annotations": {"bold": True},
        })
        last_end = match.end()

    # 나머지 일반 텍스트
    if last_end < len(text):
        parts.append({
            "type": "text",
            "text": {"content": text[last_end:]},
        })

    if not parts:
        parts.append({"type": "text", "text": {"content": text}})

    return parts


def append_to_page(page_id: str, blocks: list[dict], token: str) -> dict:
    """Notion 페이지 하단에 블록을 추가한다."""
    return _notion_request(
        "PATCH",
        f"/blocks/{page_id}/children",
        body={"children": blocks},
        token=token,
    )


# ── 초안 파싱 ──


def parse_draft(draft_text: str) -> list[PageUpdate]:
    """notion-update-draft.md를 파싱하여 페이지별 업데이트 목록을 반환한다."""
    updates: list[PageUpdate] = []

    # ## 페이지명 으로 분할
    sections = re.split(r"^## ", draft_text, flags=re.MULTILINE)

    for section in sections[1:]:  # 첫 번째는 헤더/메타 정보
        lines = section.strip().split("\n", 1)
        page_name_raw = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        if not content:
            continue

        # "업데이트 불필요" 계열 문구 감지
        if re.search(r"(업데이트\s*불필요|변경\s*없음|건너뛰)", content[:100]):
            continue

        # 페이지 이름에서 괄호 안 내용도 매칭 시도
        # 예: "메인 허브 (AI Interview)" → "메인 허브" 및 "AI Interview" 둘 다
        page_id = None
        for name, pid in PAGE_ID_MAP.items():
            if name in page_name_raw:
                page_id = pid
                break

        # 변경 사항 추출 (### 변경 N: ...)
        changes = re.findall(r"###\s+변경\s*\d*[:\s]*(.*)", content)

        updates.append(PageUpdate(
            page_name=page_name_raw,
            page_id=page_id,
            raw_content=content,
            changes=changes,
        ))

    return updates


# ── 메인 실행 ──


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    auto = "--auto" in sys.argv

    # 1. 초안 파일 확인
    if not DRAFT_PATH.exists():
        print(f"초안 파일이 없습니다: {DRAFT_PATH}")
        print("먼저 `python main.py docs`를 실행하여 서기에이전트가 초안을 생성하도록 하세요.")
        sys.exit(1)

    # 2. 토큰 확인
    token = _get_notion_token()
    if not token and not dry_run:
        print("NOTION_TOKEN이 설정되지 않았습니다.")
        print("환경변수 또는 .env 파일에 NOTION_TOKEN=<your_token>을 추가하세요.")
        print("--dry-run 옵션으로 미리보기만 할 수 있습니다.")
        sys.exit(1)

    # 3. 초안 파싱
    draft_text = DRAFT_PATH.read_text(encoding="utf-8")
    updates = parse_draft(draft_text)

    if not updates:
        print("노션 업데이트 항목이 없습니다 (업데이트 불필요 또는 파싱 실패).")
        sys.exit(0)

    print(f"\n{'=' * 60}")
    print(f"  노션 동기화 — {len(updates)}개 페이지 업데이트 감지")
    print(f"  초안: {DRAFT_PATH}")
    if dry_run:
        print("  모드: DRY-RUN (미리보기만)")
    elif auto:
        print("  모드: AUTO (전체 자동 반영)")
    else:
        print("  모드: 대화형 (페이지별 확인)")
    print(f"{'=' * 60}\n")

    applied = 0
    skipped = 0
    failed = 0

    for i, update in enumerate(updates, 1):
        print(f"\n--- [{i}/{len(updates)}] {update.page_name} ---")

        if update.page_id:
            print(f"  페이지 ID: {update.page_id}")
        else:
            print("  [경고] 페이지 ID를 찾을 수 없습니다. 수동 반영이 필요합니다.")
            skipped += 1
            continue

        if update.changes:
            for j, change in enumerate(update.changes, 1):
                print(f"  변경 {j}: {change}")
        else:
            print("  (변경 사항 헤더를 파싱하지 못했습니다. 원본 내용을 확인하세요)")

        # 변경 내용 미리보기 (최대 500자)
        preview = update.raw_content[:500]
        if len(update.raw_content) > 500:
            preview += f"\n  ... (+{len(update.raw_content) - 500}자)"
        print(f"\n  [미리보기]")
        for line in preview.split("\n"):
            print(f"  | {line}")

        if dry_run:
            print("  -> DRY-RUN: 건너뜀")
            skipped += 1
            continue

        # 확인 프롬프트
        if not auto:
            answer = input("\n  반영하시겠습니까? [y/n/q(종료)] ").strip().lower()
            if answer == "q":
                print("  동기화를 중단합니다.")
                break
            if answer != "y":
                print("  -> 건너뜀")
                skipped += 1
                continue

        # Notion API로 반영
        try:
            blocks = _markdown_to_blocks(update.raw_content)
            if not blocks:
                print("  [경고] 변환할 블록이 없습니다.")
                skipped += 1
                continue

            result = append_to_page(update.page_id, blocks, token)
            block_count = len(result.get("results", []))
            print(f"  -> 반영 완료 ({block_count}개 블록 추가)")
            applied += 1

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.readable() else str(e)
            print(f"  [오류] Notion API 실패: {e.code} — {error_body[:200]}")
            failed += 1
        except Exception as e:
            print(f"  [오류] {e}")
            failed += 1

    # 결과 요약
    print(f"\n{'=' * 60}")
    print(f"  동기화 완료: 반영 {applied} / 건너뜀 {skipped} / 실패 {failed}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
