"""외부인사 리뷰 Crew (Devil's Advocate + 경쟁력 분석)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL


@CrewBase
class ReviewCrew:
    """Devil's Advocate 리뷰 및 경쟁력 취약점 분석 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def external_advisor(self) -> Agent:
        return Agent(
            config=self.agents_config["external_advisor"],
            llm=get_llm(HIGH_PERF_MODEL),
            verbose=True,
        )

    @task
    def devils_advocate(self) -> Task:
        return Task(
            config=self.tasks_config["devils_advocate"],
        )

    @task
    def competitiveness_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["competitiveness_analysis"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
