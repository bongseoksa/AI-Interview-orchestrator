"""AI Interview Orchestrator — CrewAI 실행 엔트리포인트"""

import sys

from src.crews.research.crew import ResearchCrew
from src.crews.planning.crew import PlanningCrew


def run_research():
    """Step 1: 시장 조사 실행"""
    inputs = {"topic": "CS 면접 준비 / 기술 면접 학습 서비스"}
    result = ResearchCrew().crew().kickoff(inputs=inputs)
    print("\n=== Step 1 완료 ===")
    print(result)
    return result


def run_planning():
    """Step 2-4: 기획 (PRD → 기능 스펙 → 유저 스토리) 실행"""
    inputs = {"topic": "AI Interview — CS 면접 준비 서비스"}
    result = PlanningCrew().crew().kickoff(inputs=inputs)
    print("\n=== Step 2-4 완료 ===")
    print(result)
    return result


COMMANDS = {
    "research": ("Step 1: 시장 조사", run_research),
    "planning": ("Step 2-4: 기획", run_planning),
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
