"""M5 진단 버그 수정 검증 — QACrew 실행

진단 완료 후 무한 루프 에러 수정 검증:
- Zustand selector 무한 루프 (getSnapshot should be cached)
- computed 함수를 store 외부 helper + useMemo로 전환
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.qa.crew import QACrew

VERIFY_CONTEXT = """AI Interview M5 — 진단 결과 페이지 버그 수정 검증

[발견된 버그]
1. diagnosis-result.tsx에서 Zustand store의 computed 함수를 selector 안에서 호출
   → useDiagnosisStore((s) => s.getCategoryResults())
   → 매 렌더마다 새 객체 반환 → useSyncExternalStore 무한 루프
   → "The result of getSnapshot should be cached to avoid an infinite loop"

[수정 내용]
1. store/diagnosis.ts: getCategoryResults(), getWeakCategories()를 store 외부 순수 함수로 이동
2. diagnosis-result.tsx: useMemo로 computed 값 캐싱
3. 8개 → 9개 카테고리 텍스트 업데이트 (diagnosis-intro.tsx, diagnosis/page.tsx)

[검증 항목]
1. Zustand selector가 매번 새 참조를 반환하지 않는지 확인
2. useMemo 의존성 배열이 올바른지 확인
3. 진단 완료 → 결과 페이지 전환이 에러 없이 이루어지는지 로직 검토
4. user_progress 저장 로직(useEffect)이 React 19 Strict Mode에서 안전한지 확인
5. 빌드가 정상적으로 완료되는지 확인 (166 pages)
"""


def main():
    print("=" * 60)
    print("QACrew — M5 진단 버그 수정 검증")
    print("=" * 60)

    result = QACrew().crew().kickoff(inputs={"topic": VERIFY_CONTEXT})

    print("\n=== QACrew 검증 완료 ===")
    print(result)


if __name__ == "__main__":
    main()
