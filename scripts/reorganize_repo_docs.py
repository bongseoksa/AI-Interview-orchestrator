"""레포지토리 문서 재정리 — 서기에이전트 + 외부인사 검증

목적: 3개 레포(orchestrator, web, server)의 문서를 감사하고 재정리한다.
참여 에이전트: 서기관리(감사+재작성), 외부인사(검증)

실행: source .venv/bin/activate && python scripts/reorganize_repo_docs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Crew, Process, Task
from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory_recursive, read_file, write_file

# === 3개 레포 경로 ===
BASE = "/Users/bongseok.sa/Desktop/workspace/personal/AI-Interview"
ORCH = f"{BASE}/AI-Interview-orchestrator"
WEB = f"{BASE}/AI-Interview-web"
SERVER = f"{BASE}/AI-Interview-server"

# === 현황 분석 + 문제점 + 목표 컨텍스트 ===
AUDIT_CONTEXT = f"""
[프로젝트 개요]
AI Interview — 프론트엔드 엔지니어를 위한 AI 기반 모의 인터뷰 연습 서비스
3개 레포: orchestrator (CrewAI + Ollama), web (Next.js 16), server (Python, 미착수)

[현재 문서 현황 — 3개 레포]

== orchestrator ({ORCH}) ==
루트 문서 (3개):
- CLAUDE.md (267줄): 에이전트 컨텍스트, 디렉토리 구조, 실행 명령어, 커스텀 도구, 비용 제약, 역할 분담
- ONBOARDING.md (170줄): 설치/실행/종료 가이드, 프로젝트 구조, AI 모델 요약
- README.md (95줄): 간략 개요, Getting Started, Agents 목록, 구조

docs/ (1개):
- docs/design-crew-logger.md (167줄): CrewExecutionLogger 설계 + 서기에이전트 노션 연동 설계

.claude/agents/ (7개):
- strategy-manager.md, product-manager.md, project-manager.md
- fullstack-architect.md, infra-expert.md, doc-secretary.md, external-advisor.md

scripts/ (18개 .py + 1개 .sh): sync-agents.sh, sync_notion.py, sync_artifacts.py, sync_meeting_notes.py 등
output/ (35+ .md): Crew 실행 산출물 (gitignored)

== web ({WEB}) ==
루트 문서 (3개):
- CLAUDE.md (101줄): 기술 스택, 컨벤션, i18n, 역할 분담
- ONBOARDING.md (117줄): 설치/실행 가이드, 프로젝트 구조, 기술 스택
- README.md (68줄): Tech Stack, Getting Started, 구조, Security

docs/ (9개):
- docs/README.md: 문서 관리 허브 (레포별 배치, 역할 구분, Notion 맵)
- docs/CHANGELOG.md (156줄): 전체 문서 변경 이력
- docs/agents/secretary.md: 서기관리 에이전트 정의 및 운영 가이드
- docs/sync/notion-sync-log.md: Notion 동기화 이력
- docs/sync/document-registry.md: 전체 문서 레지스트리
- docs/templates/ (4개): competitor-analysis.md, prd.md, user-story.md, adr.md — 모두 빈 템플릿

.claude/agents/ (3개): frontend-senior.md, qa-engineer.md, doc-secretary.md

== server ({SERVER}) ==
루트 문서 (3개):
- CLAUDE.md (55줄): 미착수 상태, AI 모델 전략, 비용 제약, 역할 분담
- ONBOARDING.md (92줄): 미착수 반영, 예상 설치 흐름
- README.md (50줄): 미착수 상태, Planned Stack

.claude/agents/ (3개): backend-senior.md, data-engineer.md, qa-engineer.md (qa-engineer 불완전)

[발견된 문제점]

A. 3개 레포 공통:
1. CLAUDE.md / ONBOARDING.md / README.md 간 정보 중복 (기술 스택, 프로젝트 구조, 명령어)
2. 3개 파일의 역할 경계가 모호 — 어디서 뭘 찾아야 하는지 불명확
3. 용어 불일치: "Step" vs "Phase" 혼용 (ONBOARDING.md, CHANGELOG.md, docs/README.md 등)

B. orchestrator 고유:
4. docs/ 에 설계 문서 1개만 존재 — 23개 커스텀 도구의 API 문서 없음
5. README.md에 "9 Crews"로 오래된 정보 (실제 11 Crew)
6. CHANGELOG.md가 없음 (web에만 있음)
7. output/ 산출물 35+개가 인덱스 없이 산재
8. design-crew-logger.md 상태가 "구현 대기"이나 이미 구현됨 (crew_logger.py 존재)

C. web 고유:
9. docs/templates/ 4개 모두 빈 껍데기 — 실제 산출물은 orchestrator output/에 존재
10. docs/sync/document-registry.md 의 Notion 페이지 ID와 구조가 구 구조 기준
11. docs/README.md의 Notion 문서 맵이 구 구조 기준 (사업계획서 등 이미 아카이브됨)
12. docs/CHANGELOG.md의 "Step" 용어 — Phase로 통일 필요

D. server 고유:
13. qa-engineer.md 내용 불완전 (다른 레포의 서브에이전트보다 현저히 짧음)
14. 전체적으로 ~40% 플레이스홀더 — 미착수 상태이므로 불필요한 중복 제거하고 미착수 상태에 맞게 경량화 필요

[3개 파일의 역할 재정의 — 중복 제거 원칙]

| 파일 | 대상 | 목적 | 포함 내용 |
|------|------|------|-----------|
| CLAUDE.md | Claude Code (AI) | AI 에이전트가 코드 작업 시 참조하는 컨텍스트 | 프로젝트 목적, 아키텍처 결정, 컨벤션, 금지사항, 역할 분담 |
| README.md | 사람 (GitHub 방문자) | 레포 개요 + 빠른 시작 | 프로젝트 소개, Getting Started, 간략 구조, 링크 |
| ONBOARDING.md | 사람 + AI (신규 참여자) | 상세 온보딩 (독립적 시작) | 필수 개념, 사전 요구사항, 설치, 실행, 종료, 구조, 도구, 비용 |

중복 제거 규칙:
- 기술 스택 상세 → ONBOARDING.md (SSOT). CLAUDE.md는 핵심만 언급, README.md는 테이블 요약만
- 프로젝트 구조 → CLAUDE.md (AI가 코드 탐색에 사용). ONBOARDING.md는 참조만
- 실행 명령어 → ONBOARDING.md가 상세, README.md가 Getting Started 최소 명령어만
- 역할 분담/금지사항 → CLAUDE.md에만 (사람은 CLAUDE.md 참조 안내만)
- 모델 전략 → orchestrator CLAUDE.md에만 상세. web/server는 "orchestrator 참조" 1줄
"""

# === 에이전트 정의 ===
llm = get_llm(HIGH_PERF_MODEL)

doc_secretary = Agent(
    role="서기관리 에이전트 (Documentation Secretary)",
    goal="3개 레포의 문서를 감사하고, 중복 제거 + 역할 명확화 + 용어 통일하여 재작성한다",
    backstory=(
        "6년차 테크니컬 라이터. 멀티 레포 프로젝트에서 문서 관리 체계를 여러 차례 재구성한 경험이 있다. "
        "'같은 정보를 두 곳에 쓰면 반드시 하나는 틀어진다'는 원칙으로 SSOT를 철저히 지킨다. "
        "각 문서의 대상 독자(AI vs 사람 vs 신규 참여자)에 맞는 정보 수준을 설계한다."
    ),
    llm=llm,
    tools=[list_directory_recursive, read_file, write_file],
    allow_delegation=False,
    verbose=True,
)

reviewer = Agent(
    role="외부인사 (External Advisor)",
    goal="재작성된 문서가 실제 독자(신규 개발자, AI 에이전트, GitHub 방문자)에게 유용한지 비판적으로 검증한다",
    backstory=(
        "15년차 스타트업 자문위원. 수십 개의 오픈소스 프로젝트 문서를 리뷰한 경험이 있다. "
        "'README만 보고 3분 안에 프로젝트를 이해할 수 없으면 실패'라는 기준으로 평가한다. "
        "호의적이지 않으며, 실제 독자 관점에서 빠짐없이 문제를 지적한다."
    ),
    llm=llm,
    tools=[read_file],
    allow_delegation=False,
    verbose=True,
)

# === 태스크 정의 ===

task1_audit = Task(
    description=f"""3개 레포의 모든 문서를 읽고, 문제점을 분석하여 재정리 계획을 수립한다.

{AUDIT_CONTEXT}

[수행 사항]
1. 3개 레포의 루트 문서를 모두 읽는다:
   - {ORCH}/CLAUDE.md, {ORCH}/ONBOARDING.md, {ORCH}/README.md
   - {WEB}/CLAUDE.md, {WEB}/ONBOARDING.md, {WEB}/README.md
   - {SERVER}/CLAUDE.md, {SERVER}/ONBOARDING.md, {SERVER}/README.md

2. orchestrator 추가 문서를 읽는다:
   - {ORCH}/docs/design-crew-logger.md
   - {ORCH}/src/config/crew_logger.py (구현 상태 확인)

3. web 추가 문서를 읽는다:
   - {WEB}/docs/README.md
   - {WEB}/docs/CHANGELOG.md
   - {WEB}/docs/sync/document-registry.md
   - {WEB}/docs/agents/secretary.md

4. 각 파일별 문제점을 정리하고, 역할 재정의에 따라 내용 이동/삭제/수정 계획을 작성한다.
5. "Phase"로 용어 통일 대상 파일 목록을 작성한다.
6. 파일별 수정 우선순위를 매긴다 (High/Medium/Low).

반드시 모든 파일을 실제로 읽어서 정확한 내용 기반으로 분석할 것.""",
    expected_output="""재정리 계획서 (마크다운):
1. 파일별 문제점 분석 (현재 내용 요약 + 문제점)
2. 역할 재정의에 따른 내용 이동 매핑 (어떤 정보가 어디로 이동/삭제되는지)
3. 용어 통일 대상 목록
4. 파일별 수정 우선순위 (High/Medium/Low)
5. 실행 순서""",
    agent=doc_secretary,
    output_file="output/repo-docs-audit.md",
)

task2_rewrite = Task(
    description=f"""감사 결과를 기반으로, 3개 레포의 문서를 재작성한다.

{AUDIT_CONTEXT}

[재작성 대상 — 파일별 가이드]

=== orchestrator 레포 ({ORCH}) ===

1. CLAUDE.md — AI 에이전트 컨텍스트로 최적화
   - 레포 목적 (간결하게)
   - 디렉토리 구조 (AI가 코드 탐색에 사용)
   - 실행 명령어 (전체 목록 — AI가 실행해야 하므로)
   - Crew-에이전트 매핑 테이블
   - 커스텀 도구 테이블 (src/tools/)
   - 개발 역할 분담 + 금지사항
   - AI 모델 2-Tier 전략 상세
   - Notion API 안전 마진
   - 비용 제약
   - 관련 레포
   ※ 기술 스택 상세(버전, 비교표, 선정 근거)는 ONBOARDING.md로 이동

2. ONBOARDING.md — 신규 참여자 독립 시작 가이드
   - 필수 개념 (CrewAI, Ollama, YAML 에이전트, Crew, MoE)
   - 사전 요구사항
   - 설치 (환경 변수, 모델 다운로드, 가상환경)
   - 실행 / 종료
   - 주요 명령어 (빠른 참조 테이블)
   - 프로젝트 구조 (CLAUDE.md 참조 안내)
   - AI 모델 상세 (비교표, 선정 근거 — CLAUDE.md에서 이동)
   - 비용 제약
   - 관련 문서 링크
   ※ "Step" → "Phase" 통일

3. README.md — GitHub 방문자용 경량 개요
   - 프로젝트 소개 (1-2문장)
   - AI Model Strategy (테이블 요약)
   - Getting Started (최소 명령어 3줄)
   - Crew Overview (11 Crew 간략 테이블, "9 Crews" 수정)
   - Project Structure (간략)
   - Security
   - Related Repositories
   ※ 상세 정보 → ONBOARDING.md 링크

4. docs/design-crew-logger.md — 상태 업데이트
   - "구현 대기" → "구현 완료" 변경 (crew_logger.py 존재 확인)
   - 실제 구현 위치 기록

=== web 레포 ({WEB}) ===

5. CLAUDE.md — AI 에이전트 컨텍스트
   - Package Manager (간결)
   - Architecture Overview (Tech Stack, Path Aliases, Conventions)
   - i18n 상세 (next-intl — AI가 번역 키 관리에 사용)
   - 개발 역할 분담 + 금지사항
   - AI 모델 전략: "orchestrator 참조" 1줄로 변경 (상세 제거)
   ※ 기술 스택 버전 상세는 ONBOARDING.md 참조로 변경

6. ONBOARDING.md — 신규 참여자 가이드
   - 필수 개념 (Next.js 16 App Router, Turbopack, shadcn/ui, Path Alias, Zod 4)
   - 사전 요구사항
   - 설치 / 실행 / 종료
   - 주요 명령어 테이블
   - 프로젝트 구조 (CLAUDE.md 참조)
   - 기술 스택 상세 (버전 테이블 — SSOT)
   - 컨벤션 (CLAUDE.md 참조 안내)
   - 관련 문서

7. README.md — GitHub 방문자용
   - Tech Stack (테이블 요약)
   - Getting Started (3-4줄)
   - Project Structure (간략)
   - Scripts 테이블
   - Security
   - Related Repositories

8. docs/README.md — 문서 허브 최신화
   - Notion 문서 맵: 새 구조(5 섹션, 15 페이지)로 업데이트
   - 역할 구분 섹션 유지
   ※ 사업계획서, 프로젝트 진행 가이드 → 새 구조 반영

9. docs/CHANGELOG.md — 용어 통일
   - "Step" → "Phase" 치환
   - 이번 재정리 작업 항목 추가

10. docs/sync/document-registry.md — 최신화
    - Notion 페이지 ID를 새 구조 기준으로 업데이트
    - 새 섹션/페이지 반영
    - 최종 확인일 갱신

=== server 레포 ({SERVER}) ===

11. CLAUDE.md — 미착수 맞춤 경량화
    - 레포 목적
    - 상태: 미착수
    - 개발 역할 분담 + 금지사항
    - AI 모델 전략: "orchestrator 참조" 1줄
    - 관련 레포
    ※ 기존 내용 중복 제거, 미착수에 맞게 간결하게

12. ONBOARDING.md — 미착수 맞춤
    - 필수 개념
    - 사전 요구사항
    - 설치 (예상 흐름)
    - 현재 상태
    - 확정 예정 사항
    - 관련 문서
    ※ "Step" → "Phase" 통일

13. README.md — 미착수 맞춤
    - Status (미착수)
    - Planned Stack
    - Getting Started (예상 흐름)
    - Related Repositories

[작성 규칙]
- 각 파일을 "=== 파일 경로 ===" 구분자로 분리하여 출력
- 각 파일의 전체 내용을 마크다운으로 작성 (부분 수정 아닌 전체 재작성)
- 기존 내용을 최대한 보존하되, 역할에 맞지 않는 정보는 이동/제거
- "Phase" 용어 통일 (Step 표기 제거)
- 정보 중복 금지: 한 곳에만 작성하고 다른 곳은 참조 링크

반드시 모든 대상 파일을 실제로 read_file로 읽어서 기존 내용 기반으로 재작성할 것.
기존 내용을 임의로 제거하거나 축소하지 말 것 — 역할에 따라 적절한 파일로 이동할 것.""",
    expected_output="""13개 파일의 전체 재작성 콘텐츠.
각 파일은 "=== 파일 경로 ===" 구분자로 분리.
모든 파일이 빠짐없이 포함되어야 한다.""",
    agent=doc_secretary,
    context=[task1_audit],
    output_file="output/repo-docs-rewrite.md",
)

task3_review = Task(
    description=f"""서기에이전트가 재작성한 문서를 비판적으로 검증한다.

output/repo-docs-rewrite.md 파일을 읽어서 재작성된 문서를 확인한다.
기존 문서도 읽어서 비교한다.

[검증 기준]

1. README 3분 테스트:
   - 각 README.md만 읽고 3분 안에 "이 레포가 뭐고, 어떻게 시작하는지" 이해 가능한가?

2. ONBOARDING 독립성 테스트:
   - ONBOARDING.md만으로 환경 설정 → 실행 → 종료까지 독립적으로 가능한가?
   - 누락된 단계나 불명확한 지시는 없는가?

3. CLAUDE.md 완전성 테스트:
   - AI 에이전트가 코드 작업 시 필요한 모든 컨텍스트(구조, 컨벤션, 금지사항)가 포함되었는가?
   - 불필요한 정보(사람용 설명, 상세 비교표)가 포함되지 않았는가?

4. 중복 제거 검증:
   - 같은 정보가 2개 이상의 파일에 반복되는 곳이 있는가?
   - 중복이 발견되면 어느 파일에 남기고 어디서 제거해야 하는지 제안

5. 용어 통일 검증:
   - "Step" 표기가 남아있는 곳이 있는가?
   - 다른 용어 불일치가 있는가?

6. 정보 누락 검증:
   - 기존 문서에 있던 중요 정보가 재작성 과정에서 유실되지 않았는가?
   - 특히: 커스텀 도구 목록, Notion API 마진, 보안 훅, i18n 상세 등

7. 정합성 검증:
   - 3개 레포 간 크로스 참조가 정확한가?
   - Crew 수, 에이전트 수, 버전 정보 등이 일관되는가?

각 기준별로 Pass/Fail + 구체적 문제점을 기록한다.
문제 발견 시 수정 제안을 포함한다.

반드시 output/repo-docs-rewrite.md와 기존 원본 파일을 모두 읽어서 비교 검증할 것.""",
    expected_output="""검증 보고서 (마크다운):
- 7개 기준별 Pass/Fail + 상세 사유
- 발견된 문제점 목록 (Critical/High/Medium/Low)
- 수정 제안 목록
- 최종 승인 여부
- 종합 점수 (/10)""",
    agent=reviewer,
    context=[task1_audit, task2_rewrite],
    output_file="output/repo-docs-review.md",
)

# === Crew 실행 ===
crew = Crew(
    agents=[doc_secretary, reviewer],
    tasks=[task1_audit, task2_rewrite, task3_review],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("레포지토리 문서 재정리 — 서기에이전트 + 외부인사 검증")
    print("=" * 60)
    print(f"모델: {HIGH_PERF_MODEL}")
    print(f"대상 레포: orchestrator, web, server")
    print("태스크: 1) 감사 + 계획 → 2) 재작성 → 3) 외부인사 검증")
    print("=" * 60)
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("완료! 산출물:")
    print("  - output/repo-docs-audit.md (감사 + 계획)")
    print("  - output/repo-docs-rewrite.md (재작성된 문서)")
    print("  - output/repo-docs-review.md (외부인사 검증)")
    print("=" * 60)
