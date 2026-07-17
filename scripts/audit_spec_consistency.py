"""문서 정합성 검토 — PlanningCrew(PM) + DocumentationCrew(서기) 순차 실행

PM: 핵심 스펙 크로스 체크 (카테고리 수, Q&A 수, 마일스톤 등)
서기: 문서 간 정합성 감사 + CHANGELOG 동기화 계획
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.planning.crew import PlanningCrew
from src.crews.documentation.crew import DocumentationCrew


AUDIT_CONTEXT = """AI Interview 프로젝트 문서 정합성 크로스 체크

[현재 확인된 불일치 사항]
1. 카테고리 수: 노션 시드 데이터 뱅크는 9개(AI/LLM 통합 포함), PRD/Handoff/코드/DB는 8개
2. Q&A 수: 노션 시드 데이터 뱅크는 151개, Handoff는 138개, Supabase DB는 138개
3. 마일스톤: Handoff에서 M3(메타인지 진단) 상태가 아직 "🔲 대기"로 표기되어 있으나 실제 구현 완료

[검토 대상 문서]
- PRD (Notion): 제품 요구사항 문서 — 카테고리 8개, Phase 0 기능 정의
- Handoff (Notion): Step 3→4 핸드오프 — Task 목록, 마일스톤 상태
- 시드 데이터 뱅크 (Notion): Q&A DB 현황 — 9개 카테고리, 151개
- 진행 가이드 (Notion): 프로젝트 진행 현황
- CLAUDE.md (3개 레포): 기술 스택, 에이전트 구성
- types/database.ts: CategoryType ENUM — 8개
- constants/categories.ts: CATEGORIES 배열 — 8개
- Supabase DB: category_type ENUM — 8개 값

[정본(Source of Truth) 기준]
- 카테고리 목록/수: 시드 데이터 뱅크가 정본 (실제 데이터 기반)
- Q&A 수: 시드 데이터 뱅크가 정본
- 마일스톤 상태: 실제 코드/빌드 결과가 정본
- 기술 스택: package.json이 정본

[기대 산출물]
1. 불일치 항목 목록 + 심각도
2. 각 불일치별 수정 대상 문서와 구체적 수정 내용
3. 작업 리스트(Action Items) 형태로 정리
"""


def main():
    # 1. PlanningCrew — PM의 스펙 정합성 크로스 체크
    print("\n" + "=" * 60)
    print("Phase 1: PlanningCrew(PM) — 스펙 정합성 검토")
    print("=" * 60)

    # spec_consistency_review 태스크만 실행하기 위해 직접 kickoff
    pm_result = PlanningCrew().crew().kickoff(inputs={"topic": AUDIT_CONTEXT})

    print("\n=== PlanningCrew 완료 ===")
    print(pm_result)

    # 2. DocumentationCrew — 서기의 문서 감사 + CHANGELOG
    print("\n" + "=" * 60)
    print("Phase 2: DocumentationCrew(서기) — 문서 감사")
    print("=" * 60)

    doc_context = f"""{AUDIT_CONTEXT}

[PM 검토 결과 참조]
위 PlanningCrew의 스펙 정합성 검토 결과를 참조하여, 문서 감사 및 동기화 계획을 수립한다.
"""

    doc_result = DocumentationCrew().crew().kickoff(inputs={"topic": doc_context})

    print("\n=== DocumentationCrew 완료 ===")
    print(doc_result)

    print("\n" + "=" * 60)
    print("문서 정합성 검토 완료 — output/ 폴더 확인")
    print("  - output/spec-consistency-review.md (PM 검토)")
    print("  - output/doc-audit-report.md (서기 감사)")
    print("  - output/doc-changelog-sync.md (동기화 계획)")
    print("=" * 60)


if __name__ == "__main__":
    main()
