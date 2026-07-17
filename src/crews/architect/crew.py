"""Step 3: 아키텍처 설계 Crew (스키마 + 데이터 흐름)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class ArchitectCrew:
    """Supabase 스키마 설계 및 데이터 흐름 검토 Crew (Step 3)"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def fullstack_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["fullstack_architect"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @agent
    def backend_senior(self) -> Agent:
        return Agent(
            config=self.agents_config["backend_senior"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def schema_design(self) -> Task:
        return Task(
            config=self.tasks_config["schema_design"],
        )

    @task
    def data_flow_review(self) -> Task:
        return Task(
            config=self.tasks_config["data_flow_review"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
