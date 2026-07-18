# Design: Crew 실행 로거 (CrewExecutionLogger)

> 작성일: 2026-07-17
> 상태: 구현 완료 (src/config/crew_logger.py)

## 1. 배경 및 목적

현재 9개 Crew 실행 시 에이전트의 작업 과정은 `verbose=True`로 터미널에만 출력되고,
완료 후에는 `output/` 디렉토리에 최종 산출물만 남는다.

**문제**: 에이전트가 할루시네이션을 발생시키는 시점에 "어떤 에이전트가 무슨 말을 했는지"
추적할 수 없다. 터미널 로그는 휘발되므로 사후 검증이 불가능하다.

**목적**: 모든 Crew 실행 과정을 로컬 파일로 실시간 기록하여,
할루시네이션 발생 시 즉각적인 인지와 긴급 조치를 가능하게 한다.

## 2. 설계 원칙

- **최소 침습**: 기존 crew.py 코드 변경 없음. main.py에 import 1줄만 추가
- **실시간 기록**: 이벤트 발생 즉시 파일에 flush (버퍼링 없음)
- **단순 구현**: 순수 Python 파일 I/O. 외부 의존성 없음
- **실행별 분리**: Crew 실행마다 별도 로그 파일 생성

## 3. 기술 구현

### 3.1 핵심 컴포넌트

```
src/config/crew_logger.py    # BaseEventListener 구현 (완료)
main.py                      # import 1줄 추가 (완료)
logs/                        # 실행 로그 저장 디렉토리 (gitignored)
```

### 3.2 활용할 CrewAI 이벤트

CrewAI v1.15+ `BaseEventListener`를 사용한다. 인스턴스 생성만으로 자동 등록된다.

| 이벤트 | 기록 내용 |
|--------|-----------|
| `CrewKickoffStartedEvent` | Crew 시작 (crew_name) |
| `CrewKickoffCompletedEvent` | Crew 완료 (crew_name, output 요약) |
| `CrewKickoffFailedEvent` | Crew 실패 (crew_name, error) |
| `AgentExecutionStartedEvent` | 에이전트 태스크 시작 (agent.role, task) |
| `AgentExecutionCompletedEvent` | 에이전트 태스크 완료 (agent.role, output 요약) |
| `AgentExecutionErrorEvent` | 에이전트 오류 (agent.role, error) |
| `TaskStartedEvent` | 태스크 시작 |
| `TaskCompletedEvent` | 태스크 완료 (output 전문) |
| `TaskFailedEvent` | 태스크 실패 (error) |
| `ToolUsageStartedEvent` | 도구 호출 시작 (tool_name, input) |
| `ToolUsageFinishedEvent` | 도구 호출 완료 (tool_name, output 요약) |
| `LLMStreamChunkEvent` | LLM 토큰 스트림 (agent별 발화 내용) |

### 3.3 로그 파일 형식

파일명: `logs/{crew_name}_{timestamp}.log`

```
[2026-07-17 22:25:01] [CREW_START] ArchitectCrew
[2026-07-17 22:25:01] [TASK_START] schema_design
[2026-07-17 22:25:01] [AGENT_START] 풀스택 아키텍트 (Fullstack Architect) — schema_design
[2026-07-17 22:25:03] [LLM] 풀스택 아키텍트: Supabase 스키마를 설계하겠습니다. 먼저 questions 테이블...
[2026-07-17 22:25:15] [TOOL_START] 풀스택 아키텍트 — search_web(query="Supabase RLS policy")
[2026-07-17 22:25:18] [TOOL_DONE] 풀스택 아키텍트 — search_web — 결과 512자
[2026-07-17 22:25:30] [AGENT_DONE] 풀스택 아키텍트 — schema_design — 출력 2048자
[2026-07-17 22:25:30] [TASK_DONE] schema_design — output/step3-schema-design.sql
[2026-07-17 22:25:31] [TASK_START] data_flow_review
[2026-07-17 22:25:31] [AGENT_START] 백엔드 시니어 (Backend Senior) — data_flow_review
...
[2026-07-17 22:26:45] [CREW_DONE] ArchitectCrew — 104초 소요
```

### 3.4 LLM 스트림 처리 전략

`LLMStreamChunkEvent`는 토큰 단위로 발생하므로 매 토큰마다 파일에 쓰면 I/O 과부하가 발생한다.

**전략**: 에이전트별 버퍼에 청크를 누적하고, 문장 완성 시점(마침표/줄바꿈) 또는
일정 크기(500자) 도달 시 flush한다. 에이전트 전환 시에도 강제 flush한다.

### 3.5 적용 방법

`main.py`에서 import만 추가하면 모든 Crew에 자동 적용된다:

```python
# main.py 상단에 추가
from src.config.crew_logger import CrewExecutionLogger  # noqa: F401
```

`BaseEventListener`는 인스턴스 생성 시점에 CrewAI 이벤트 버스에 자동 등록되므로,
모듈 로드 시 글로벌 인스턴스를 생성해두면 별도 설정 없이 모든 Crew에 적용된다.

## 4. 디렉토리 변경

```
src/config/
  llm.py              # (기존) Ollama LLM 설정
  crew_logger.py       # (신규) CrewExecutionLogger
logs/                  # (신규) 실행 로그 디렉토리 (gitignored)
```

## 5. 할루시네이션 검증 활용

로그 파일을 통해 다음을 사후 검증할 수 있다:

1. **에이전트 발화 추적**: 어떤 에이전트가 어떤 시점에 무슨 말을 했는지 전문 확인
2. **도구 호출 검증**: 에이전트가 올바른 도구를 올바른 입력으로 호출했는지 확인
3. **태스크 간 컨텍스트 전달**: 선행 태스크의 출력이 후행 태스크에 올바르게 전달되었는지 확인
4. **시간 분석**: 태스크별 소요 시간으로 병목 구간 파악

향후 Phase 1에서는 이 로그를 기반으로 GUI 대시보드(WebSocket 실시간 스트리밍)를 구축할 수 있다.

---

# Design: 서기에이전트 노션 연동 확장

> 작성일: 2026-07-17
> 상태: 구현 완료 (src/crews/documentation/, scripts/sync_notion.py)

## 1. 배경

현재 DocumentationCrew(서기에이전트)는 로컬 파일(`output/`)에만 산출물을 생성한다.
노션 문서 업데이트는 Claude Code가 직접 MCP 도구로 수행하고 있다.

**새 원칙**: 노션 작성 시 서기에이전트 활용 필수.

## 2. 구현 전략

서기에이전트(CrewAI, Ollama)가 직접 Notion API를 호출하는 것은 비효율적이다.
로컬 LLM이 API 호출을 담당하면 할루시네이션 위험 + 실행 시간이 크게 증가한다.

**채택 방안: 2단계 파이프라인**

```
[서기에이전트] → 노션용 마크다운 초안 생성 (output/)
     ↓
[동기화 스크립트] → Notion API로 업로드 (scripts/sync_notion.py)
```

### 2.1 DocumentationCrew 태스크 확장

기존 2개 태스크에 `notion_draft` 태스크를 추가한다:

| 태스크 | 역할 | output_file |
|--------|------|-------------|
| doc_audit | 문서 정합성 검증 (기존) | output/doc-audit-report.md |
| changelog_update | CHANGELOG 갱신 (기존) | output/doc-changelog-sync.md |
| **notion_draft** | **노션 업데이트 초안 생성 (신규)** | **output/notion-update-draft.md** |

### 2.2 동기화 스크립트

`scripts/sync_notion.py` — 서기에이전트가 생성한 초안을 파싱하여 Notion API에 반영.
또는 Claude Code가 서기에이전트 초안을 읽어 MCP 도구로 노션에 반영.

### 2.3 워크플로우

```
1. 의사결정/변경사항 발생
2. python main.py docs  → 서기에이전트가 감사 + 노션 초안 생성
3. 초안 리뷰 후 노션 동기화 실행
```

## 3. 구현 우선순위

| 순서 | 작업 | 근거 |
|------|------|------|
| 1 | CrewExecutionLogger 구현 | 기존 코드 무변경, 즉시 적용 가능 |
| 2 | DocumentationCrew에 notion_draft 태스크 추가 | 서기에이전트 역할 확장 |
| 3 | sync_notion.py 스크립트 구현 | 노션 자동 동기화 |
