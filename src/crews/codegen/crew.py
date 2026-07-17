"""코드 생성 Crew — 설계 문서 기반으로 대상 레포에 실제 코드 파일 생성"""

from pathlib import Path
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import (
    list_directory,
    list_directory_recursive,
    read_file,
    write_file,
)

# 프로젝트 루트 (orchestrator 기준)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# 대상 레포 경로 매핑
REPO_PATHS = {
    "web": PROJECT_ROOT.parent / "AI-Interview-web",
    "server": PROJECT_ROOT.parent / "AI-Interview-server",
    "orchestrator": PROJECT_ROOT,
}


@CrewBase
class CodegenCrew:
    """설계 문서를 기반으로 대상 레포에 코드를 생성하는 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def codegen_developer(self) -> Agent:
        return Agent(
            config=self.agents_config["codegen_developer"],
            llm=get_llm(HIGH_PERF_MODEL),
            tools=[
                list_directory,
                list_directory_recursive,
                read_file,
                write_file,
            ],
            allow_delegation=False,
            verbose=True,
        )

    @task
    def analyze_codebase(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_codebase"],
        )

    @task
    def generate_code(self) -> Task:
        return Task(
            config=self.tasks_config["generate_code"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
