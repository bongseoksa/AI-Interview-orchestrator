"""QA Crew (테스트 전략 + 테스트 케이스)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class QACrew:
    """테스트 전략 수립 및 테스트 케이스 작성 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_engineer"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def test_strategy(self) -> Task:
        return Task(
            config=self.tasks_config["test_strategy"],
        )

    @task
    def test_cases(self) -> Task:
        return Task(
            config=self.tasks_config["test_cases"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
