"""Step 3: 아키텍처 설계 Crew (스키마 + 데이터 흐름)"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Optional, Callable

@CrewBase
class ArchitectCrew:
    """Supabase 스키마 설계 및 데이터 흐름 검토 Crew (Step 3)"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, llm_factory: Optional[Callable] = None):
        """
        의존성 주입을 통해 LLM 생성 로직을 외부에서 제어할 수 있도록 합니다.
        llm_factory: (model_name) -> LLM 인스턴스를 반환하는 함수
        """
        self._llm_factory = llm_factory

    def _get_llm(self, model_type: str = "default"):
        """LLM Factory가 존재하면 사용하고, 없으면 fallback 로직을 수행합니다."""
        if self._llm_factory:
            # 특정 모델 타입에 맞는 LLM을 factory를 통해 획득 (예: HIGH_PERF_MODEL)
            # 실제 구현에서는 model_type 매핑 로직이 필요하나, 인터페이스 표준화를 위해 구조만 잡음
            return self._llm_factory(model_type)
        
        # Fallback: 기존의 전역 설정을 사용하도록 허용 (하위 호환성 유지)
        from src.config.llm import get_llm, HIGH_PERF_MODEL
        return get_llm(HIGH_PERF_MODEL)

    @agent
    def fullstack_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["fullstack_architect"],
            llm=self._get_llm("high_perf"),
            verbose=True,
        )

    @agent
    def backend_senior(self) -> Agent:
        return Agent(
            config=self.agents_config["backend_senior"],
            llm=self._get_llm("high_perf"),
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
