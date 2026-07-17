"""인프라 Crew (CI/CD + 배포 전략)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class InfraCrew:
    """CI/CD 파이프라인 설계 및 배포/운영 전략 수립 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def infra_expert(self) -> Agent:
        return Agent(
            config=self.agents_config["infra_expert"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def cicd_pipeline(self) -> Task:
        return Task(
            config=self.tasks_config["cicd_pipeline"],
        )

    @task
    def deploy_strategy(self) -> Task:
        return Task(
            config=self.tasks_config["deploy_strategy"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
