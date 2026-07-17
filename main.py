"""AI Interview Orchestrator — CrewAI 실행 엔트리포인트"""

import sys

from src.crews.research.crew import ResearchCrew
from src.crews.planning.crew import PlanningCrew
from src.crews.architect.crew import ArchitectCrew
from src.crews.frontend.crew import FrontendCrew
from src.crews.qa.crew import QACrew
from src.crews.infra.crew import InfraCrew
from src.crews.data.crew import DataCrew
from src.crews.documentation.crew import DocumentationCrew
from src.crews.review.crew import ReviewCrew


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
    """서기관리 (문서 감사 + CHANGELOG) 실행"""
    inputs = {"topic": "AI Interview 프로젝트 전체 문서"}
    result = DocumentationCrew().crew().kickoff(inputs=inputs)
    print("\n=== 문서 감사 완료 ===")
    print(result)
    return result


def run_review():
    """외부인사 리뷰 (Devil's Advocate + 경쟁력 분석) 실행"""
    inputs = {"topic": "AI Interview 서비스 전체"}
    result = ReviewCrew().crew().kickoff(inputs=inputs)
    print("\n=== 외부인사 리뷰 완료 ===")
    print(result)
    return result


COMMANDS = {
    "research": ("Step 1: 시장 조사", run_research),
    "planning": ("Step 2-4: 기획", run_planning),
    "architect": ("아키텍처 설계", run_architect),
    "frontend": ("프론트엔드 설계", run_frontend),
    "qa": ("QA 테스트 전략", run_qa),
    "infra": ("인프라 CI/CD", run_infra),
    "data": ("데이터 파이프라인", run_data),
    "docs": ("문서 감사", run_documentation),
    "review": ("외부인사 리뷰", run_review),
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
