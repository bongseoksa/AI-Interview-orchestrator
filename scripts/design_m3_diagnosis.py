"""M3 메타인지 진단 — FrontendCrew + QACrew 순차 실행

FrontendCrew: M3 진단 UI 컴포넌트 설계 + 페이지 구조
QACrew: M3 진단 기능 테스트 전략 + 테스트 케이스
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.frontend.crew import FrontendCrew
from src.crews.qa.crew import QACrew


M3_CONTEXT = """AI Interview Phase 0 — M3 메타인지 진단 기능 설계

[서비스 현재 상태]
- M1(DB+시드) 완료: Supabase에 nodes(138개)/questions/user_progress 테이블 배포
- M2(UI) 완료: 랜딩, 대시보드, /learn/[category]/[slug] SSG 151페이지 빌드 성공
- 기술 스택: Next.js 16 (App Router), TypeScript 5.9.x, Tailwind CSS 3.4.x, shadcn/ui, Zustand 5.x, pnpm
- DB: Supabase (PostgreSQL + Auth), RLS 정책 적용

[M3 요구사항 — PRD US-2.1]
메타인지 진단: 사용자가 학습 시작 전 간단한 진단으로 취약 분야를 파악하여 효율적으로 집중할 영역을 정한다.

Acceptance Criteria:
1. '진단 시작' 클릭 시, CS 질문(5~10개)이 하나씩 노출되고 답변 시, 결과 리포트에서 '취약 지점' 강조
2. 질문 건너뛰기 시 '모름/답변 없음'으로 처리, 취약 포인트 반영
3. 재시험 시 기존 기록 초기화 (MVP)

[진단 질문 방식 — OQ-2 확정]
- 정적 세트: questions 테이블의 is_diagnostic=true 질문 사용 (LLM 비용 0원)
- 138개 Q&A 중 카테고리당 1~2개 진단용 질문 선별 (총 8~16개)
- 사용자는 각 질문에 대해 "안다 / 애매하다 / 모른다" 3단계로 자기 점검

[DB 스키마]
questions 테이블: id, node_id, question, answer_guide, is_diagnostic, created_at
nodes 테이블: id, category, title, slug, content_body, difficulty, key_keywords, default_tip, is_active

[기존 페이지 구조]
- / (랜딩)
- /dashboard (커리큘럼 대시보드 — 8개 카테고리 카드)
- /learn/[category] (카테고리별 개념 목록)
- /learn/[category]/[slug] (개념 상세 — 3단 구조)
- /learn/map (취약 맵 — 카테고리별 분포)

[설계 요청]
1. /diagnosis 페이지: 진단 시작 → 질문 하나씩 → 결과 리포트
2. 진단 결과를 대시보드와 취약 맵에 반영하는 방법
3. 클라이언트 컴포넌트 vs 서버 컴포넌트 분리
4. 상태 관리: 진단 진행 상태 (현재 질문 인덱스, 답변 배열) — Zustand 활용
5. shadcn/ui 컴포넌트 선택 (Card, Button, Progress, RadioGroup, Badge 등)
6. 접근성: 키보드 내비게이션, 스크린 리더 지원
7. 반응형: 모바일 퍼스트 설계
8. 진단 완료 후 CTA: "취약 개념 학습하기" → /learn/[category] 연결
"""


def main():
    # 1. FrontendCrew 실행
    print("\n" + "=" * 60)
    print("Phase 1: FrontendCrew — M3 컴포넌트/페이지 설계")
    print("=" * 60)

    frontend_result = FrontendCrew().crew().kickoff(inputs={"topic": M3_CONTEXT})

    print("\n=== FrontendCrew 완료 ===")
    print(frontend_result)

    # 2. QACrew 실행
    print("\n" + "=" * 60)
    print("Phase 2: QACrew — M3 테스트 전략/케이스")
    print("=" * 60)

    qa_context = f"""AI Interview Phase 0 — M3 메타인지 진단 테스트

{M3_CONTEXT}

[FrontendCrew 설계 결과 참조]
위 컨텍스트 기반으로 설계된 M3 메타인지 진단 기능의 테스트 전략과 테스트 케이스를 작성한다.
"""

    qa_result = QACrew().crew().kickoff(inputs={"topic": qa_context})

    print("\n=== QACrew 완료 ===")
    print(qa_result)

    print("\n" + "=" * 60)
    print("M3 설계 완료 — output/ 폴더 확인")
    print("=" * 60)


if __name__ == "__main__":
    main()
