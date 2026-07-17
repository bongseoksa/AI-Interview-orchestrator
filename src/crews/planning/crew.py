"""Step 2-4: 기획 Crew (PRD → 기능 스펙 → 유저 스토리)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm


@CrewBase
class PlanningCrew:
    """PRD, 기능 스펙, 유저 스토리 작성 Crew (Step 2-4)"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def product_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["product_manager"],
            llm=get_llm(),
            verbose=True,
        )

    @agent
    def project_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["project_manager"],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def prd_draft(self) -> Task:
        return Task(
            config=self.tasks_config["prd_draft"],
        )

    @task
    def feature_spec(self) -> Task:
        return Task(
            config=self.tasks_config["feature_spec"],
        )

    @task
    def user_stories(self) -> Task:
        return Task(
            config=self.tasks_config["user_stories"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
