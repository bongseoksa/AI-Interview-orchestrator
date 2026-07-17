"""M5 프로그레스 + 취약 맵 — ArchitectCrew + FrontendCrew + QACrew 순차 실행

ArchitectCrew: user_progress CRUD 설계, Auth 연동 패턴, RLS 검증
FrontendCrew: 프로그레스 UI 컴포넌트, 취약 맵 시각화, Auth 상태 관리
QACrew: M5 기능 테스트 전략 + 테스트 케이스
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.architect.crew import ArchitectCrew
from src.crews.frontend.crew import FrontendCrew
from src.crews.qa.crew import QACrew


M5_CONTEXT = """AI Interview Phase 0 — M5 프로그레스 + 취약 맵 설계

[서비스 현재 상태]
- M1(DB+시드) 완료: Supabase에 nodes(138개)/questions/user_progress 테이블 배포, RLS 적용
- M2(UI) 완료: 랜딩, 대시보드(/dashboard), /learn/[category]/[slug] SSG 151페이지
- M3(메타인지 진단) 완료: /diagnosis 페이지 (intro → 질문 → 결과), Zustand 클라이언트 상태
- M4(학습 모듈) 완료: /learn/[category]/[slug] 3단 구조 콘텐츠 (개념정의, 핵심키워드, 면접팁)
- /learn/map 페이지 존재: 카테고리별 노드 수 표시하나 유저 진행도 미연동
- 기술 스택: Next.js 16 (App Router), TypeScript 5.9.x, Tailwind CSS 3.4.x, shadcn/ui, Zustand 5.x, pnpm

[DB 스키마 — 이미 배포됨]
nodes: id, category(ENUM), title, slug, content_body, difficulty, key_keywords, default_tip, is_active
questions: id, node_id, question, answer_guide, is_diagnostic
user_progress: id, user_id, node_id, mastery_level(int 0-100), last_accessed(timestamp)
- user_progress RLS: auth.uid() = user_id (ADR-004)

[Auth 인프라 — 이미 설정됨]
- middleware.ts: Supabase SSR 미들웨어 (세션 갱신)
- lib/supabase/server.ts: 서버 클라이언트 (cookies 기반)
- lib/supabase/client.ts: 브라우저 클라이언트
- .env.local: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

[현재 쿼리 — lib/supabase/queries.ts]
- getAllNodes(), getNodesByCategory(), getNodeBySlug(), getQuestionsByNodeId()
- getDiagnosticQuestions(), getCategoryCounts()
- user_progress 관련 쿼리 없음

[현재 진단 스토어 — store/diagnosis.ts]
- DiagnosisAnswer: { questionId, category, level: "know"|"vague"|"unknown" }
- 진단 결과는 Zustand 클라이언트 상태에만 존재, DB 미연동

[M5 요구사항 — PRD]
1. 지식 상태 트래킹 (US-1.2): 학습 완료 시 실시간 프로그레스 반영, Supabase 동기화
   - 학습 완료 액션 → user_progress upsert → 프로그레스 바/노드 상태 실시간 변경
   - 비정상 종료 후 재진입 시 마지막 완료 지점 데이터 유지
   - 이전 단계로 이동 시 기존 진행도 유지
2. 취약 맵 시각화 (P1): /learn/map에서 카테고리별 이해도 현황 시각화
3. 대시보드 프로그레스 반영: 카테고리별 진행도를 대시보드 카드에 표시

[설계 요청]
1. Auth 연동 패턴: 로그인/비로그인 사용자 분기 처리
   - 비로그인: 학습 콘텐츠 열람 가능, 프로그레스 저장 불가 (로그인 유도 UI)
   - 로그인: user_progress CRUD 가능
2. user_progress CRUD 쿼리 설계:
   - getUserProgress(userId): 전체 진행도 조회
   - getUserProgressByCategory(userId, category): 카테고리별 진행도
   - upsertUserProgress(userId, nodeId, masteryLevel): 학습 완료 시 저장
   - syncDiagnosisResults(userId, answers): 진단 결과 → user_progress 초기화
3. 학습 페이지 (/learn/[category]/[slug]) 변경:
   - "학습 완료" 버튼 추가 → mastery_level 업데이트
   - 현재 mastery 상태 표시 (미시작/학습중/완료)
4. 대시보드 변경: 각 카테고리 카드에 진행도 프로그레스 바 추가
5. 취약 맵 (/learn/map) 변경: 유저 진행도 기반 카테고리별 이해도 히트맵/차트
6. 진단 결과 연동: 진단 완료 시 결과를 user_progress에 초기 mastery로 저장
7. Supabase Auth UI: 로그인/회원가입 모달 또는 페이지 (소셜 로그인 선택)
8. 실시간 반영: Optimistic UI + Supabase 동기화 패턴
"""


def main():
    # 1. ArchitectCrew 실행 — 데이터 흐름 + CRUD 설계
    print("\n" + "=" * 60)
    print("Phase 1: ArchitectCrew — M5 데이터/Auth 설계")
    print("=" * 60)

    architect_context = f"""{M5_CONTEXT}

[ArchitectCrew 설계 포커스]
1. user_progress CRUD 쿼리 및 RLS 패턴 설계
2. Auth 연동: Supabase Auth 로그인/회원가입 플로우
3. 진단 결과 → user_progress 동기화 데이터 흐름
4. Optimistic UI를 위한 데이터 페칭 전략 (TanStack Query vs SWR vs 직접 fetch)
5. mastery_level 계산 로직: 진단(know=80, vague=40, unknown=0) + 학습완료(100)
"""

    architect_result = ArchitectCrew().crew().kickoff(inputs={"topic": architect_context})

    print("\n=== ArchitectCrew 완료 ===")
    print(architect_result)

    # 2. FrontendCrew 실행 — UI 컴포넌트 설계
    print("\n" + "=" * 60)
    print("Phase 2: FrontendCrew — M5 프로그레스 UI 설계")
    print("=" * 60)

    frontend_context = f"""{M5_CONTEXT}

[ArchitectCrew 설계 결과 참조]
위 ArchitectCrew가 설계한 데이터 흐름/CRUD 패턴 기반으로 UI 컴포넌트를 설계한다.

[FrontendCrew 설계 포커스]
1. Auth UI: 로그인/회원가입 컴포넌트 (shadcn/ui Dialog + Supabase Auth)
2. 학습 페이지 프로그레스 UI: 완료 버튼, mastery 상태 뱃지
3. 대시보드 프로그레스: 카테고리 카드 내 진행도 바
4. 취약 맵: 카테고리별 이해도 시각화 (히트맵/도넛차트/프로그레스 바)
5. 진단 결과 → 프로그레스 연동 UI 흐름
6. 비로그인 사용자 로그인 유도 UI
7. 서버 컴포넌트 vs 클라이언트 컴포넌트 분리
"""

    frontend_result = FrontendCrew().crew().kickoff(inputs={"topic": frontend_context})

    print("\n=== FrontendCrew 완료 ===")
    print(frontend_result)

    # 3. QACrew 실행 — 테스트 전략
    print("\n" + "=" * 60)
    print("Phase 3: QACrew — M5 테스트 전략/케이스")
    print("=" * 60)

    qa_context = f"""{M5_CONTEXT}

[설계 결과 참조]
ArchitectCrew + FrontendCrew 설계 결과 기반으로 M5 테스트 전략과 케이스를 작성한다.

[QACrew 테스트 포커스]
1. Auth 플로우: 로그인/로그아웃/세션 만료 시나리오
2. user_progress CRUD: 정상/비정상 케이스
3. RLS 보안: 다른 사용자 데이터 접근 차단 검증
4. 진단 결과 → 프로그레스 동기화 정합성
5. Optimistic UI: 네트워크 지연/실패 시 롤백
6. 비로그인 사용자: 로그인 유도 동작
7. 반응형: 모바일 프로그레스 UI
"""

    qa_result = QACrew().crew().kickoff(inputs={"topic": qa_context})

    print("\n=== QACrew 완료 ===")
    print(qa_result)

    print("\n" + "=" * 60)
    print("M5 설계 완료 — output/ 폴더 확인")
    print("=" * 60)


if __name__ == "__main__":
    main()
