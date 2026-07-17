"""i18n (국제화) 설계 — FrontendCrew + QACrew 순차 실행

FrontendCrew: i18n 디렉토리 구조, JSON 스키마, 컴포넌트 적용 패턴 설계
QACrew: 번역 누락/일관성 테스트 전략
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.frontend.crew import FrontendCrew
from src.crews.qa.crew import QACrew


I18N_CONTEXT = """AI Interview — i18n (국제화) 설계

[서비스 현재 상태]
- Next.js 16 (App Router), TypeScript 5.9.x, Tailwind CSS 3.4.x, shadcn/ui, Zustand 5.x, pnpm
- 9개 카테고리, 151개 노드, SSG 기반 학습 페이지
- 현재 모든 UI 텍스트가 한국어 하드코딩
- 기본 언어: ko (한국어), 추가 지원: en (영어)

[현재 프로젝트 구조]
app/
  layout.tsx                    # 루트 레이아웃
  page.tsx                      # 랜딩 페이지
  dashboard/page.tsx            # 대시보드
  diagnosis/page.tsx            # 메타인지 진단
  learn/
    map/page.tsx                # 학습 맵
    [category]/page.tsx         # 카테고리별 목록
    [category]/[slug]/page.tsx  # 개념 학습 상세
  actions/progress.ts           # Server Actions
components/
  auth/auth-modal.tsx           # 로그인/회원가입 모달
  common/user-nav.tsx           # 사용자 네비게이션
  diagnosis/                    # 진단 관련 컴포넌트들
  learn/completion-button.tsx   # 학습 완료 버튼
  ui/                           # shadcn/ui 컴포넌트
constants/categories.ts         # 카테고리 매핑 (label, description, icon)
store/diagnosis.ts              # Zustand 진단 스토어
providers/
  auth-provider.tsx             # Auth 상태 관리
  query-provider.tsx            # TanStack Query

[하드코딩된 한국어 텍스트 유형]
1. 페이지 제목/설명 (metadata.title, metadata.description)
2. UI 라벨 (버튼, 헤더, 네비게이션)
3. 에러/상태 메시지 ("데이터를 불러올 수 없습니다", "처리 중...")
4. 카테고리 이름/설명 (constants/categories.ts의 label, description)
5. 진단 관련 텍스트 (질문 안내, 결과 라벨)
6. Auth 관련 텍스트 (로그인, 회원가입, 이메일, 비밀번호)

[DB 콘텐츠는 i18n 대상 아님]
- nodes 테이블의 title, content_body, key_keywords, default_tip → DB 콘텐츠는 현재 한국어 전용
- questions 테이블의 question, answer_guide → DB 콘텐츠는 현재 한국어 전용
- i18n은 UI 텍스트(Chrome)만 대상

[설계 요청]
1. i18n 라이브러리 선택: next-intl vs 커스텀 솔루션 (App Router 호환성 필수)
2. 디렉토리 구조 설계:
   - 번역 파일 위치 (messages/, locales/, i18n/ 등)
   - JSON 파일 구조 (네임스페이스 분리 전략)
   - 라우팅 전략: URL prefix (/en/, /ko/) vs cookie/header 기반
3. JSON 스키마 설계:
   - 키 네이밍 컨벤션 (dot notation vs nested object)
   - 네임스페이스 분류 (common, dashboard, diagnosis, learn, auth 등)
   - 복수형, 변수 삽입(interpolation), 포맷팅 패턴
4. 컴포넌트 적용 패턴:
   - Server Component에서 번역 사용법
   - Client Component에서 번역 사용법
   - metadata (title, description)에서 번역 적용
   - Zustand store 내 텍스트 처리
5. 언어 전환 UI:
   - 언어 선택 컴포넌트 위치 및 디자인
   - 기본 언어 감지 로직 (Accept-Language vs localStorage)
6. 기존 코드 마이그레이션 가이드:
   - 하드코딩된 텍스트를 번역 키로 교체하는 패턴
   - constants/categories.ts 처리 방안
"""


def main():
    # 1. FrontendCrew — i18n 아키텍처 + 컴포넌트 설계
    print("\n" + "=" * 60)
    print("Phase 1: FrontendCrew — i18n 디렉토리/JSON/컴포넌트 설계")
    print("=" * 60)

    frontend_context = f"""{I18N_CONTEXT}

[FrontendCrew 설계 포커스]
1. i18n 라이브러리 비교 및 선택 (next-intl 권장, App Router 호환)
2. 디렉토리 구조: 번역 파일 위치, 네임스페이스 분리
3. JSON 스키마: 키 네이밍, 네임스페이스별 구조
4. Server Component / Client Component 각각의 번역 적용 패턴
5. metadata i18n (generateMetadata에서 번역)
6. 언어 전환 UI 컴포넌트 설계
7. constants/categories.ts 국제화 방안
8. 라우팅 전략: /[locale]/ prefix vs middleware 기반
"""

    frontend_result = FrontendCrew().crew().kickoff(inputs={"topic": frontend_context})

    print("\n=== FrontendCrew 완료 ===")
    print(frontend_result)

    # 2. QACrew — i18n 테스트 전략
    print("\n" + "=" * 60)
    print("Phase 2: QACrew — i18n 테스트 전략/케이스")
    print("=" * 60)

    qa_context = f"""{I18N_CONTEXT}

[FrontendCrew 설계 결과 참조]
위 FrontendCrew가 설계한 i18n 아키텍처 기반으로 테스트 전략을 수립한다.

[QACrew 테스트 포커스]
1. 번역 키 누락 검증: ko에 있는 키가 en에도 존재하는지
2. 언어 전환 시 UI 깨짐 테스트
3. 텍스트 길이 차이로 인한 레이아웃 이슈 (영어가 한국어보다 길 수 있음)
4. SSG 페이지의 locale별 빌드 검증
5. metadata (SEO) 언어별 정확성
6. 브라우저 언어 감지 → 기본 언어 설정 동작
"""

    qa_result = QACrew().crew().kickoff(inputs={"topic": qa_context})

    print("\n=== QACrew 완료 ===")
    print(qa_result)

    print("\n" + "=" * 60)
    print("i18n 설계 완료 — output/ 폴더 확인")
    print("=" * 60)


if __name__ == "__main__":
    main()
