"""시드 데이터 뱅크 문서 검증 — DocumentationCrew 활용"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.documentation.crew import DocumentationCrew


AUDIT_CONTEXT = """
시드 데이터 뱅크 문서 (Notion) 의 '데이터 규모' 섹션이 실제 Q&A DB와 불일치합니다.
아래 실제 DB 조회 결과를 기반으로, 문서의 어떤 부분이 잘못되었는지 분석하고 수정안을 마크다운으로 작성해주세요.

=== 현재 문서 (데이터 규모 테이블) ===
| 카테고리 | Q&A 수 |
|---------|--------|
| 소프트 면접 (행동/인성) | ~15 |
| 프론트엔드 전반 | 100 |
| JavaScript/TypeScript | 100 + 실전 답변 10 |
| React/Next.js/Vue | 100 |
| Git/CI-CD (형상관리) | 100 |
| SEO | 100 |
| 합계 | ~515 |

문서 주석: "Phase 0 메타인지 Q&A DB에는 위 515개에서 정제한 138개 + AI/LLM 통합 13개 = 총 151개"

=== 실제 Notion Q&A DB 조회 결과 (2026-07-17) ===
총 151개 Q&A, 9개 카테고리:
| 카테고리 | Q&A 수 |
|---------|--------|
| JavaScript | 25 |
| CSS | 20 |
| HTML | 20 |
| React | 17 |
| 인프라/보안/네트워크 | 16 |
| 성능/SEO | 14 |
| Next.js | 14 |
| AI/LLM 통합 | 13 |
| 형상관리(Git/CI-CD) | 12 |
| 합계 | 151 |

난이도 분포:
| 난이도 | Q&A 수 | 비율 |
|-------|--------|------|
| 주니어 | 70 | 46.4% |
| 미드 | 49 | 32.5% |
| 시니어 | 32 | 21.2% |

DB 속성: 질문(title), 카테고리(select), 난이도(select), 답변가이드(rich_text), 핵심키워드(rich_text)

=== 추가 불일치: 오케스트레이터 코드 ===
src/crews/data/config/tasks.yaml의 schema_optimization 태스크:
- "카테고리: 8개" → 실제 9개
- "시드 데이터: 138개 Q&A" → 실제 151개

=== 요청 사항 ===
1. 문서의 '데이터 규모' 섹션의 정확한 수정안을 마크다운 테이블로 작성
2. 원본 시드 데이터(515개)와 정제된 DB 데이터(151개)의 관계를 명확히 설명하는 문구 제안
3. 오케스트레이터 코드의 수정 필요 항목 목록
4. 심각도 분류 (Critical/Warning/Info)
"""


def main():
    inputs = {"topic": AUDIT_CONTEXT}
    result = DocumentationCrew().crew().kickoff(inputs=inputs)
    print("\n=== 시드 데이터 문서 감사 완료 ===")
    print(result)
    return result


if __name__ == "__main__":
    main()
