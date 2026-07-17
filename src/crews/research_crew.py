"""Step 1: Discovery & 시장 조사 Crew"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm


@CrewBase
class ResearchCrew:
    """시장 조사 및 경쟁사 분석 Crew (Step 1)"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "src/config/agents.yaml"
    tasks_config = "src/config/tasks.yaml"

    @agent
    def strategy_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["strategy_manager"],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def market_research(self) -> Task:
        return Task(
            config=self.tasks_config["market_research"],
        )

    @task
    def competitor_deep_dive(self) -> Task:
        return Task(
            config=self.tasks_config["competitor_deep_dive"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
