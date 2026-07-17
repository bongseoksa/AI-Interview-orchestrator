#!/usr/bin/env python3
"""Notion 중간 편집 엣지 케이스 테스트

리스크가 높은 시나리오를 검증:
1. 동일 키워드 다수 매치 → 정확한 블록 선별
2. 부분 키워드 매치 → 유사 내용 구분
3. 연속 블록 수정 → 순서 보존
4. 삽입 후 재삽입 → 위치 정확성
5. 삭제 후 검증 → 잔여 확인
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.notion_tools import (
    _api_request,
    _read_page_raw,
    append_to_notion_page,
    search_notion_blocks,
    update_notion_block,
    delete_notion_block,
    insert_after_notion_block,
    PAGE_ID_MAP,
)

MAIN_PAGE_ID = PAGE_ID_MAP["메인"]
PASS = 0
FAIL = 0


def log(status: str, msg: str):
    global PASS, FAIL
    if status == "PASS":
        PASS += 1
    elif status == "FAIL":
        FAIL += 1
    print(f"  [{status}] {msg}")


def create_test_page() -> str:
    resp = _api_request("POST", "/pages", {
        "parent": {"page_id": MAIN_PAGE_ID},
        "properties": {
            "title": {"title": [{"text": {"content": "[TEST] 중간 편집 엣지 케이스"}}]}
        },
    })
    page_id = resp["id"]
    print(f"  테스트 페이지: {page_id}")
    return page_id


def setup_content(page_id: str):
    """동일 키워드가 여러 곳에 있는 복잡한 구조를 생성."""
    content = """## 프로젝트 상태
- 현재 단계: Step 4 진행 중
- 완료된 단계: Step 1, Step 2, Step 3

## 기술 스택
- 프레임워크: Next.js 16
- 언어: TypeScript 5.9
- 상태 관리: Zustand 5.x

## 에이전트 현황
- 전체 에이전트 수: 11개
- 활성 에이전트: 11개
- 에이전트 프레임워크: CrewAI

## 카테고리 정보
- 카테고리 수: 9개
- HTML, CSS, JavaScript, React, Next.js
- 인프라/보안/네트워크, 형상관리(Git/CI-CD)
- 성능/SEO, AI/LLM 통합

## 마일스톤 진행
- M1 온보딩: 완료
- M2 학습 카드: 완료
- M3 메타인지 진단: 진행 중
- M4 대시보드: 대기
- M5 진행 추적: 대기

## 비용 정보
- 서버 비용: 무료 (Supabase Free Tier)
- AI 모델 비용: 무료 (Ollama 로컬)
- 총 비용: $0/월
"""
    append_to_notion_page.run(page=page_id, markdown_content=content)


def test_1_multi_match_select(page_id: str):
    """테스트 1: 동일 키워드 다수 매치 → 맥락으로 정확한 블록 선별"""
    print("\n--- 테스트 1: 동일 키워드 다수 매치 ---")
    print("  '에이전트'가 여러 블록에 존재 → '에이전트 프레임워크' 블록만 수정")

    result = search_notion_blocks.run(page=page_id, keyword="에이전트")
    match_count = result.count("=== 매치")
    print(f"  검색 결과: {match_count}건 매치")

    if match_count < 3:
        log("FAIL", f"최소 3건 이상 매치 기대, 실제 {match_count}건")
        return

    # "에이전트 프레임워크: CrewAI" 블록만 찾아서 수정
    # 정확한 블록을 찾기 위해 더 구체적으로 검색
    result2 = search_notion_blocks.run(page=page_id, keyword="에이전트 프레임워크")
    if "매치 1" not in result2:
        log("FAIL", "'에이전트 프레임워크' 검색 실패")
        return

    # 블록 ID 추출
    import re
    bid_match = re.search(r">>> \[([0-9a-f-]+)\]", result2)
    if not bid_match:
        log("FAIL", "블록 ID 추출 실패")
        return

    block_id = bid_match.group(1)
    result3 = update_notion_block.run(block_id=block_id, new_content="에이전트 프레임워크: CrewAI v1.15.4 (업그레이드됨)")

    if "수정 완료" in result3:
        # 검증: 다른 "에이전트" 블록은 변경되지 않았는지
        verify = search_notion_blocks.run(page=page_id, keyword="전체 에이전트 수")
        if "11개" in verify:
            log("PASS", "정확한 블록만 수정, 다른 블록 무변경 확인")
        else:
            log("FAIL", "다른 에이전트 블록이 변경됨")
    else:
        log("FAIL", f"수정 실패: {result3}")


def test_2_partial_keyword(page_id: str):
    """테스트 2: 부분 키워드 → 유사 내용 구분"""
    print("\n--- 테스트 2: 부분 키워드로 유사 내용 구분 ---")
    print("  'Step'으로 검색 → 여러 매치 중 'Step 4' 블록만 수정")

    result = search_notion_blocks.run(page=page_id, keyword="Step 4")
    import re
    bid_match = re.search(r">>> \[([0-9a-f-]+)\]", result)
    if not bid_match:
        log("FAIL", "Step 4 블록 검색 실패")
        return

    block_id = bid_match.group(1)
    result2 = update_notion_block.run(block_id=block_id, new_content="현재 단계: Step 4 완료")

    if "수정 완료" in result2:
        # Step 1,2,3 은 변경되지 않았는지
        verify = search_notion_blocks.run(page=page_id, keyword="Step 1, Step 2, Step 3")
        if "매치" in verify:
            log("PASS", "Step 4만 수정, Step 1/2/3 무변경 확인")
        else:
            log("FAIL", "다른 Step 블록이 변경됨")
    else:
        log("FAIL", f"수정 실패: {result2}")


def test_3_insert_at_position(page_id: str):
    """테스트 3: 특정 위치에 삽입 → 정확한 위치 확인"""
    print("\n--- 테스트 3: 특정 위치에 삽입 ---")
    print("  '기술 스택' 섹션 제목 바로 아래에 새 항목 삽입")

    result = search_notion_blocks.run(page=page_id, keyword="기술 스택")
    import re
    bid_match = re.search(r">>> \[([0-9a-f-]+)\]", result)
    if not bid_match:
        log("FAIL", "'기술 스택' 블록 검색 실패")
        return

    heading_id = bid_match.group(1)
    result2 = insert_after_notion_block.run(
        page=page_id,
        after_block_id=heading_id,
        markdown_content="- 패키지 매니저: pnpm 10.17.1 (삽입 테스트)"
    )

    if "삽입 완료" in result2:
        # 삽입된 내용이 기술 스택 바로 아래에 있는지 확인
        verify = search_notion_blocks.run(page=page_id, keyword="pnpm 10.17.1")
        if "이전" in verify and "기술 스택" in verify:
            log("PASS", "기술 스택 바로 아래에 삽입 확인")
        else:
            log("FAIL", "삽입 위치가 잘못됨")
    else:
        log("FAIL", f"삽입 실패: {result2}")


def test_4_delete_and_verify(page_id: str):
    """테스트 4: 삭제 후 검증 → 삭제된 블록이 실제로 사라졌는지"""
    print("\n--- 테스트 4: 삭제 후 검증 ---")
    print("  '총 비용: $0/월' 블록 삭제 → 검색으로 부재 확인")

    result = search_notion_blocks.run(page=page_id, keyword="총 비용")
    import re
    bid_match = re.search(r">>> \[([0-9a-f-]+)\]", result)
    if not bid_match:
        log("FAIL", "'총 비용' 블록 검색 실패")
        return

    block_id = bid_match.group(1)
    result2 = delete_notion_block.run(block_id=block_id)

    if "삭제 완료" in result2:
        time.sleep(1)
        verify = search_notion_blocks.run(page=page_id, keyword="총 비용")
        if "없습니다" in verify:
            log("PASS", "삭제된 블록이 검색되지 않음 확인")
        else:
            log("FAIL", "삭제된 블록이 여전히 검색됨")
    else:
        log("FAIL", f"삭제 실패: {result2}")


def test_5_consecutive_updates(page_id: str):
    """테스트 5: 연속 수정 → 순서 보존"""
    print("\n--- 테스트 5: 연속 수정 (마일스톤 3개 동시 변경) ---")
    print("  M3, M4, M5 상태를 동시에 변경")

    import re
    changes = [
        ("M3 메타인지 진단", "M3 메타인지 진단: 완료 (테스트)"),
        ("M4 대시보드", "M4 대시보드: 진행 중 (테스트)"),
        ("M5 진행 추적", "M5 진행 추적: 설계 중 (테스트)"),
    ]

    all_ok = True
    for keyword, new_content in changes:
        result = search_notion_blocks.run(page=page_id, keyword=keyword)
        bid_match = re.search(r">>> \[([0-9a-f-]+)\]", result)
        if not bid_match:
            log("FAIL", f"'{keyword}' 검색 실패")
            all_ok = False
            continue

        block_id = bid_match.group(1)
        result2 = update_notion_block.run(block_id=block_id, new_content=new_content)
        if "수정 완료" not in result2:
            log("FAIL", f"'{keyword}' 수정 실패")
            all_ok = False

    if all_ok:
        # 순서 확인: M3 → M4 → M5 순서가 유지되는지
        text = _read_page_raw(page_id)
        m3_pos = text.find("M3 메타인지 진단: 완료")
        m4_pos = text.find("M4 대시보드: 진행 중")
        m5_pos = text.find("M5 진행 추적: 설계 중")

        if m3_pos < m4_pos < m5_pos:
            log("PASS", "3개 블록 수정 완료, 순서 보존 확인")
        else:
            log("FAIL", f"순서 깨짐: M3={m3_pos}, M4={m4_pos}, M5={m5_pos}")


def main():
    print("=" * 60)
    print("  Notion 중간 편집 엣지 케이스 테스트")
    print("=" * 60)

    print("\n[준비] 테스트 페이지 생성 + 콘텐츠 설정")
    page_id = create_test_page()
    time.sleep(1)
    setup_content(page_id)
    time.sleep(1)

    test_1_multi_match_select(page_id)
    test_2_partial_keyword(page_id)
    test_3_insert_at_position(page_id)
    test_4_delete_and_verify(page_id)
    test_5_consecutive_updates(page_id)

    # 정리 생략 — 노션에서 확인
    print(f"\n[정리 생략] 테스트 페이지 유지: {page_id}")

    print(f"\n{'=' * 60}")
    print(f"  결과: PASS {PASS} / FAIL {FAIL}")
    print(f"{'=' * 60}")

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
