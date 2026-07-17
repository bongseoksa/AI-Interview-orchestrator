"""서기관리 Crew (문서 감사 + CHANGELOG 동기화 + 노션 초안 생성)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class DocumentationCrew:
    """문서 정합성 검증, 변경 이력 관리, 노션 업데이트 초안 생성 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def doc_secretary(self) -> Agent:
        return Agent(
            config=self.agents_config["doc_secretary"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def doc_audit(self) -> Task:
        return Task(
            config=self.tasks_config["doc_audit"],
        )

    @task
    def changelog_update(self) -> Task:
        return Task(
            config=self.tasks_config["changelog_update"],
        )

    @task
    def notion_draft(self) -> Task:
        return Task(
            config=self.tasks_config["notion_draft"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
