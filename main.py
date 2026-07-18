"""AI Interview Orchestrator — CrewAI 실행 엔트리포인트"""

import sys

from src.config.crew_logger import crew_logger  # noqa: F401 — 이벤트 버스 자동 등록

from src.crews.research.crew import ResearchCrew
from src.crews.planning.crew import PlanningCrew
from src.crews.architect.crew import ArchitectCrew
from src.crews.frontend.crew import FrontendCrew
from src.crews.qa.crew import QACrew
from src.crews.infra.crew import InfraCrew
from src.crews.data.crew import DataCrew
from src.crews.documentation.crew import DocumentationCrew
from src.crews.review.crew import ReviewCrew
from src.crews.codegen.crew import CodegenCrew, REPO_PATHS
from src.crews.notion_edit.crew import NotionEditCrew
from src.tools.notion_tools import (
    list_notion_pages,
    _read_page_raw,
    append_to_notion_page,
    search_notion_blocks,
    update_notion_block,
    delete_notion_block,
    insert_after_notion_block,
    PAGE_ID_MAP,
)


def run_research():
    """Step 1: 시장 조사 실행"""
    inputs = {"topic": "CS 면접 준비 / 기술 면접 학습 서비스"}
    result = ResearchCrew().crew().kickoff(inputs=inputs)
    print("\n=== Step 1 완료 ===")
    print(result)
    return result


def run_planning():
    """Step 2-4: 기획 (PRD -> 기능 스펙 -> 유저 스토리) 실행"""
    inputs = {"topic": "AI Interview — CS 면접 준비 서비스"}
    result = PlanningCrew().crew().kickoff(inputs=inputs)
    print("\n=== Step 2-4 완료 ===")
    print(result)
    return result


def run_architect():
    """Step 3: 아키텍처 설계 (스키마 + 데이터 흐름) 실행"""
    inputs = {"topic": "AI Interview Phase 0 — Supabase 스키마 및 데이터 파이프라인"}
    result = ArchitectCrew().crew().kickoff(inputs=inputs)
    print("\n=== Step 3 아키텍처 설계 완료 ===")
    print(result)
    return result


def run_frontend():
    """프론트엔드 설계 (컴포넌트 + 페이지 구조) 실행"""
    inputs = {"topic": "AI Interview Phase 0 — 개념 학습 MVP"}
    result = FrontendCrew().crew().kickoff(inputs=inputs)
    print("\n=== 프론트엔드 설계 완료 ===")
    print(result)
    return result


def run_qa():
    """QA (테스트 전략 + 테스트 케이스) 실행"""
    inputs = {"topic": "AI Interview Phase 0 — 개념 학습 MVP"}
    result = QACrew().crew().kickoff(inputs=inputs)
    print("\n=== QA 완료 ===")
    print(result)
    return result


def run_infra():
    """인프라 (CI/CD + 배포 전략) 실행"""
    inputs = {"topic": "AI Interview — web/server/orchestrator 3개 레포"}
    result = InfraCrew().crew().kickoff(inputs=inputs)
    print("\n=== 인프라 설계 완료 ===")
    print(result)
    return result


def run_data():
    """데이터 (스키마 최적화 + 파이프라인) 실행"""
    inputs = {"topic": "AI Interview Phase 0 — Supabase 스키마 및 시드 파이프라인"}
    result = DataCrew().crew().kickoff(inputs=inputs)
    print("\n=== 데이터 설계 완료 ===")
    print(result)
    return result


def run_documentation():
    """서기관리 (문서 감사 + CHANGELOG + 노션 초안) 실행"""
    inputs = {"topic": "AI Interview 프로젝트 전체 문서"}
    result = DocumentationCrew().crew().kickoff(inputs=inputs)
    print("\n=== 문서 감사 + 노션 초안 완료 ===")
    print("노션 초안: output/notion-update-draft.md")
    print(result)
    return result


def run_review():
    """외부인사 리뷰 (Devil's Advocate + 경쟁력 분석) 실행"""
    inputs = {"topic": "AI Interview 서비스 전체"}
    result = ReviewCrew().crew().kickoff(inputs=inputs)
    print("\n=== 외부인사 리뷰 완료 ===")
    print(result)
    return result


def run_codegen():
    """코드 생성 — 설계 문서 기반으로 대상 레포에 코드 파일 생성"""
    if len(sys.argv) < 4:
        print("사용법: python main.py codegen <repo> <task_description>")
        print(f"  repo: {', '.join(REPO_PATHS.keys())}")
        print('  예시: python main.py codegen web "학습 페이지 컴포넌트 생성"')
        sys.exit(1)

    repo_key = sys.argv[2]
    if repo_key not in REPO_PATHS:
        print(f"알 수 없는 레포: {repo_key}")
        print(f"사용 가능: {', '.join(REPO_PATHS.keys())}")
        sys.exit(1)

    target_repo = str(REPO_PATHS[repo_key])
    task_desc = " ".join(sys.argv[3:])

    print(f"  대상 레포: {target_repo}")
    print(f"  작업: {task_desc}")

    inputs = {
        "task_description": task_desc,
        "target_repo": target_repo,
    }
    result = CodegenCrew().crew().kickoff(inputs=inputs)
    print("\n=== 코드 생성 완료 ===")
    print(result)
    return result


def run_notion():
    """노션 페이지 직접 조작"""
    if len(sys.argv) < 3:
        print("사용법:")
        print("  python main.py notion list                                # 페이지 목록")
        print('  python main.py notion read <페이지>                       # 페이지 읽기')
        print('  python main.py notion write <페이지> <내용>               # 페이지에 추가')
        print('  python main.py notion search <페이지> <키워드>            # 블록 검색')
        print('  python main.py notion update <블록ID> <새내용>            # 블록 수정')
        print('  python main.py notion delete <블록ID>                     # 블록 삭제')
        print('  python main.py notion insert <페이지> <기준블록ID> <내용> # 블록 뒤에 삽입')
        sys.exit(1)

    action = sys.argv[2]

    if action == "list":
        print(list_notion_pages.run())
        return

    if action == "read":
        if len(sys.argv) < 4:
            print("페이지 이름 또는 ID를 지정하세요.")
            print(f"사용 가능: {', '.join(PAGE_ID_MAP.keys())}")
            sys.exit(1)
        page = sys.argv[3]
        print(_read_page_raw(page))
        return

    if action == "write":
        if len(sys.argv) < 5:
            print('사용법: python main.py notion write <페이지> "마크다운 내용"')
            sys.exit(1)
        page = sys.argv[3]
        content = " ".join(sys.argv[4:])
        print(append_to_notion_page.run(page=page, markdown_content=content))
        return

    if action == "search":
        if len(sys.argv) < 5:
            print('사용법: python main.py notion search <페이지> <키워드>')
            sys.exit(1)
        page = sys.argv[3]
        keyword = " ".join(sys.argv[4:])
        print(search_notion_blocks.run(page=page, keyword=keyword))
        return

    if action == "update":
        if len(sys.argv) < 5:
            print('사용법: python main.py notion update <블록ID> "새 내용"')
            sys.exit(1)
        block_id = sys.argv[3]
        content = " ".join(sys.argv[4:])
        print(update_notion_block.run(block_id=block_id, new_content=content))
        return

    if action == "delete":
        if len(sys.argv) < 4:
            print('사용법: python main.py notion delete <블록ID>')
            sys.exit(1)
        block_id = sys.argv[3]
        print(delete_notion_block.run(block_id=block_id))
        return

    if action == "insert":
        if len(sys.argv) < 6:
            print('사용법: python main.py notion insert <페이지> <기준블록ID> "마크다운 내용"')
            sys.exit(1)
        page = sys.argv[3]
        after_id = sys.argv[4]
        content = " ".join(sys.argv[5:])
        print(insert_after_notion_block.run(page=page, after_block_id=after_id, markdown_content=content))
        return

    print(f"알 수 없는 액션: {action}")
    print("사용 가능: list, read, write, search, update, delete, insert")


def run_notion_edit():
    """AI 기반 노션 편집 — 검색 결과를 AI가 검증하여 정확한 블록 편집"""
    if len(sys.argv) < 4:
        print("사용법: python main.py notion-edit <페이지> <편집 지시>")
        print('  예시: python main.py notion-edit 의사결정 "Step 4 상태를 완료로 변경"')
        print('  예시: python main.py notion-edit 기획서 "카테고리 수를 9개에서 10개로 수정"')
        sys.exit(1)

    page = sys.argv[2]
    instruction = " ".join(sys.argv[3:])

    print(f"  대상 페이지: {page}")
    print(f"  편집 지시: {instruction}")

    inputs = {
        "page": page,
        "edit_instruction": instruction,
    }
    result = NotionEditCrew().crew().kickoff(inputs=inputs)
    print("\n=== 노션 편집 완료 ===")
    print(result)
    return result


def run_artifacts():
    """산출물 레지스트리 동기화 — 로컬 산출물 스캔 → 분류 → 노션 기록"""
    from scripts.sync_artifacts import main as sync_main
    return sync_main()


def run_meetings():
    """에이전트 회의록 동기화 — 3개 레포 검토 → 로그 분석 → 노션 기록"""
    from scripts.sync_meeting_notes import main as meetings_main
    return meetings_main()


COMMANDS = {
    "research": ("Step 1: 시장 조사", run_research),
    "planning": ("Step 2-4: 기획", run_planning),
    "architect": ("아키텍처 설계", run_architect),
    "frontend": ("프론트엔드 설계", run_frontend),
    "qa": ("QA 테스트 전략", run_qa),
    "infra": ("인프라 CI/CD", run_infra),
    "data": ("데이터 파이프라인", run_data),
    "docs": ("문서 감사 + 노션 초안", run_documentation),
    "review": ("외부인사 리뷰", run_review),
    "codegen": ("코드 생성 (codegen <repo> <task>)", run_codegen),
    "notion": ("노션 조작 (notion list|read|write|search|...)", run_notion),
    "notion-edit": ("AI 노션 편집 (notion-edit <페이지> <지시>)", run_notion_edit),
    "artifacts": ("산출물 레지스트리 동기화 (로컬→노션)", run_artifacts),
    "meetings": ("에이전트 회의록 동기화 (3개 레포→노션)", run_meetings),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("사용법: python main.py <command>")
        print("\n사용 가능한 명령어:")
        for cmd, (desc, _) in COMMANDS.items():
            print(f"  {cmd:12s} — {desc}")
        sys.exit(1)

    cmd = sys.argv[1]
    desc, func = COMMANDS[cmd]
    print(f"\n{desc} 시작...")
    func()


if __name__ == "__main__":
    main()
