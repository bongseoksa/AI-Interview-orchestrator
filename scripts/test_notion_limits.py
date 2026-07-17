#!/usr/bin/env python3
"""Notion 도구 대용량 읽기/쓰기/수정 테스트 (3만자 내외)

테스트 페이지를 생성 → 대량 쓰기 → 읽기 검증 → 추가 쓰기 → 재읽기 → 정리
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.notion_tools import (
    _api_request,
    _read_page_raw,
    append_to_notion_page,
    read_notion_page,
    read_notion_page_full,
    PAGE_ID_MAP,
)

MAIN_PAGE_ID = PAGE_ID_MAP["메인"]


def create_test_page() -> str:
    """메인 허브 아래에 테스트 페이지를 생성한다."""
    resp = _api_request("POST", "/pages", {
        "parent": {"page_id": MAIN_PAGE_ID},
        "properties": {
            "title": {
                "title": [{"text": {"content": "[TEST] 노션 도구 대용량 테스트"}}]
            }
        },
    })
    if "error" in resp:
        print(f"  [실패] 페이지 생성 오류: {resp['error']}")
        sys.exit(1)
    page_id = resp["id"]
    print(f"  [OK] 테스트 페이지 생성: {page_id}")
    return page_id


def delete_test_page(page_id: str):
    """테스트 페이지를 아카이브(삭제)한다."""
    resp = _api_request("PATCH", f"/pages/{page_id}", {"archived": True})
    if "error" in resp:
        print(f"  [실패] 페이지 삭제 오류: {resp['error']}")
    else:
        print(f"  [OK] 테스트 페이지 삭제 완료")


def generate_content(target_chars: int, label: str) -> str:
    """target_chars 길이의 마크다운 콘텐츠를 생성한다."""
    sections = []
    char_count = 0
    section_num = 0

    while char_count < target_chars:
        section_num += 1
        section = f"""## {label} 섹션 {section_num}

### 개요
이 섹션은 오케스트레이터 Notion 도구의 대용량 쓰기/읽기 테스트를 위한 더미 콘텐츠입니다.
섹션 번호 {section_num}, 라벨 {label}. 총 목표 글자수: {target_chars}자.

### 기술 스택 상세
- **프레임워크**: Next.js 16 (App Router) — React Server Components, Streaming SSR, Partial Prerendering 지원
- **언어**: TypeScript 5.9.x — 엄격한 타입 체킹, satisfies 연산자, const type parameters 활용
- **스타일링**: Tailwind CSS 3.4.x — JIT 컴파일, 커스텀 디자인 토큰, 반응형 브레이크포인트 전략
- **UI 컴포넌트**: shadcn/ui — Radix UI 기반, 접근성 내장, CSS 변수 테마링
- **상태 관리 (클라이언트)**: Zustand 5.x — 경량, devtools 지원, persist 미들웨어
- **상태 관리 (서버)**: TanStack Query 5.x — 캐시 무효화, 낙관적 업데이트, 무한 스크롤
- **폼 관리**: React Hook Form 7.x + Zod 4.x — 서버/클라이언트 통합 검증
- **국제화**: next-intl 4.x — URL prefix 라우팅, 서버 컴포넌트 네이티브 지원

### 아키텍처 설계 원칙
1. 서버 컴포넌트를 기본으로 사용하고, 인터랙티브 요소만 클라이언트 컴포넌트로 분리한다
2. 데이터 페칭은 서버 컴포넌트에서 수행하고, 클라이언트에서는 캐시된 데이터를 활용한다
3. 코드 스플리팅은 라우트 단위로 자동 적용되며, 동적 임포트로 추가 최적화한다
4. CSS-in-JS를 사용하지 않고, Tailwind CSS 유틸리티 클래스로 스타일링한다
5. 접근성(a11y)은 시맨틱 마크업, ARIA 속성, 키보드 내비게이션을 기본으로 포함한다

### 데이터 모델
```typescript
interface Category {{
  id: string;
  name: string;
  slug: string;
  description: string;
  questionCount: number;
  iconEmoji: string;
}}

interface Question {{
  id: string;
  categoryId: string;
  title: string;
  difficulty: 'junior' | 'mid' | 'senior';
  content: string;
  answer: string;
  explanation: string;
  relatedQuestionIds: string[];
  tags: string[];
  createdAt: string;
  updatedAt: string;
}}
```

### 성능 최적화 전략
- **Core Web Vitals 목표**: LCP < 2.5s, INP < 200ms, CLS < 0.1
- **이미지 최적화**: next/image 컴포넌트, WebP/AVIF 자동 변환, lazy loading
- **폰트 최적화**: next/font, 로컬 폰트 파일, font-display: swap
- **번들 사이즈**: 동적 임포트, tree-shaking, barrel export 금지

"""
        sections.append(section)
        char_count += len(section)

    content = "\n".join(sections)
    return content[:target_chars]


def test_write(page_id: str, content: str, label: str) -> bool:
    """쓰기 테스트."""
    print(f"\n--- 쓰기 테스트: {label} ({len(content)}자) ---")
    start = time.time()
    result = append_to_notion_page.run(page=page_id, markdown_content=content)
    elapsed = time.time() - start
    print(f"  결과: {result}")
    print(f"  소요: {elapsed:.1f}초")
    success = "완료" in result
    print(f"  {'[OK]' if success else '[FAIL]'}")
    return success


def test_read(page_id: str, expected_min_chars: int, label: str) -> tuple[bool, int]:
    """읽기 테스트 (CLI — 전체 읽기)."""
    print(f"\n--- 읽기 테스트: {label} (최소 {expected_min_chars}자 기대) ---")
    start = time.time()
    text = _read_page_raw(page_id)
    elapsed = time.time() - start
    actual = len(text)
    print(f"  읽은 글자수: {actual}자")
    print(f"  소요: {elapsed:.1f}초")
    success = actual >= expected_min_chars
    print(f"  {'[OK]' if success else '[FAIL]'} (기대 >= {expected_min_chars})")
    return success, actual


def test_agent_read(page_id: str, label: str) -> bool:
    """에이전트 읽기 테스트 (8000자 제한 + 구간 읽기)."""
    print(f"\n--- 에이전트 읽기 테스트: {label} ---")

    # 기본 읽기 (8000자 제한)
    result = read_notion_page.run(page=page_id)
    print(f"  read_notion_page: {len(result)}자 (8000자 제한)")
    if len(result) < 7000:
        print("  [FAIL] 제한된 읽기가 너무 짧음")
        return False

    # 구간 읽기
    result_full = read_notion_page_full.run(page=page_id, offset=8000, limit=5000)
    print(f"  read_notion_page_full(offset=8000, limit=5000): {len(result_full)}자")
    if len(result_full) < 1000:
        print("  [FAIL] 구간 읽기 결과가 너무 짧음")
        return False

    print("  [OK]")
    return True


def main():
    print("=" * 60)
    print("  Notion 도구 대용량 테스트 (3만자 내외)")
    print("=" * 60)

    # 1. 테스트 페이지 생성
    print("\n[1/7] 테스트 페이지 생성")
    page_id = create_test_page()
    time.sleep(1)

    results: dict[str, bool] = {}

    try:
        # 2. 1차 쓰기 — 10,000자
        content_1 = generate_content(10000, "1차")
        results["쓰기_10K"] = test_write(page_id, content_1, "1차 10,000자")
        time.sleep(1)

        # 3. 1차 읽기 — 10,000자 확인
        success, actual_1 = test_read(page_id, 8000, "1차 10K 확인")
        results["읽기_10K"] = success

        # 4. 2차 쓰기 — 추가 10,000자 (누적 ~20K)
        content_2 = generate_content(10000, "2차")
        results["쓰기_20K"] = test_write(page_id, content_2, "2차 추가 10,000자")
        time.sleep(1)

        # 5. 2차 읽기 — 20,000자 확인
        success, actual_2 = test_read(page_id, 16000, "2차 20K 확인")
        results["읽기_20K"] = success

        # 6. 3차 쓰기 — 추가 12,000자 (누적 ~32K)
        content_3 = generate_content(12000, "3차")
        results["쓰기_32K"] = test_write(page_id, content_3, "3차 추가 12,000자")
        time.sleep(1)

        # 7. 3차 읽기 — 30,000자+ 확인
        success, actual_3 = test_read(page_id, 25000, "3차 30K+ 확인")
        results["읽기_32K"] = success

        # 8. 에이전트 읽기 테스트 (제한+구간)
        results["에이전트_읽기"] = test_agent_read(page_id, "에이전트 구간 읽기")

    finally:
        # 정리 생략 — 노션에서 직접 확인용
        print(f"\n[정리 생략] 테스트 페이지 유지: {page_id}")
        print(f"  노션에서 직접 확인 후 수동 삭제하세요.")

    # 결과 요약
    print(f"\n{'=' * 60}")
    print("  테스트 결과 요약")
    print(f"{'=' * 60}")
    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:20s} — {status}")
        if not passed:
            all_pass = False
    print(f"{'=' * 60}")
    print(f"  전체: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print(f"{'=' * 60}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
