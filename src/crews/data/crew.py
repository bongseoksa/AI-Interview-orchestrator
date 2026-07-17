"""데이터 Crew (스키마 최적화 + 데이터 파이프라인)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class DataCrew:
    """스키마 최적화 및 데이터 파이프라인 설계 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def data_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["data_engineer"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def schema_optimization(self) -> Task:
        return Task(
            config=self.tasks_config["schema_optimization"],
        )

    @task
    def data_pipeline(self) -> Task:
        return Task(
            config=self.tasks_config["data_pipeline"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
