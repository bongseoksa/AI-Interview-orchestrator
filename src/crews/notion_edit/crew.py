"""노션 편집 Crew — AI 모델이 검색 결과를 검증하여 정확한 블록을 편집"""

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.notion_tools import (
    read_notion_page,
    read_notion_page_full,
    append_to_notion_page,
    search_notion_blocks,
    update_notion_block,
    delete_notion_block,
    insert_after_notion_block,
)


@CrewBase
class NotionEditCrew:
    """AI 모델이 검색 결과를 분석하여 정확한 노션 블록을 편집하는 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def notion_editor(self) -> Agent:
        return Agent(
            config=self.agents_config["notion_editor"],
            llm=get_llm(HIGH_PERF_MODEL),
            tools=[
                read_notion_page,
                read_notion_page_full,
                append_to_notion_page,
                search_notion_blocks,
                update_notion_block,
                delete_notion_block,
                insert_after_notion_block,
            ],
            allow_delegation=False,
            verbose=True,
        )

    @task
    def edit_notion(self) -> Task:
        return Task(
            config=self.tasks_config["edit_notion"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
