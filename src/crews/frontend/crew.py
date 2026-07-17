"""프론트엔드 설계 Crew (컴포넌트 + 페이지 구조)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class FrontendCrew:
    """프론트엔드 컴포넌트 설계 및 페이지 구조 정의 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def frontend_senior(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_senior"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def component_design(self) -> Task:
        return Task(
            config=self.tasks_config["component_design"],
        )

    @task
    def page_structure(self) -> Task:
        return Task(
            config=self.tasks_config["page_structure"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
