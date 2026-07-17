"""서기관리 Crew (문서 감사 + CHANGELOG 동기화 + 노션 읽기/쓰기)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from src.config.llm import get_llm, HIGH_PERF_MODEL
from src.tools.file_tools import list_directory_recursive, read_file, write_file
from src.tools.notion_tools import (
    list_notion_pages,
    read_notion_page,
    read_notion_page_full,
    append_to_notion_page,
    query_notion_database,
)


@CrewBase
class DocumentationCrew:
    """문서 정합성 검증, 변경 이력 관리, 노션 직접 읽기/쓰기 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def doc_secretary(self) -> Agent:
        return Agent(
            config=self.agents_config["doc_secretary"],
            llm=get_llm(HIGH_PERF_MODEL),
            tools=[
                list_directory_recursive,
                read_file,
                write_file,
                list_notion_pages,
                read_notion_page,
                read_notion_page_full,
                append_to_notion_page,
                query_notion_database,
            ],
            allow_delegation=False,
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
