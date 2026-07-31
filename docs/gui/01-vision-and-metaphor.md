# 01 — 사무실 은유 설계

> "오케스트레이터를 유리 사무실로." 이벤트 로그를 사람이 이해하는 장면으로 번역한다.

## 1. 직원 캐스트 (11 Crew · 13 에이전트)

각 에이전트의 `agents/*.yaml`에 있는 `role` / `goal` / `backstory` / `deploy_to.tools`가
사무실 직원의 **직함 · 담당 업무 · 성격 · 사용 도구**로 그대로 매핑된다.

| 자리(책상) | 에이전트 | 소속 Crew | 성격 힌트 (backstory) |
|-----------|----------|-----------|----------------------|
| 리서치 데스크 | 전략 관리자 | Research | 10년차 전략 컨설턴트, 근거 없는 제안 안 함 |
| 기획 데스크 | PM / PjM | Planning | 제품 방향 결정 · 타임라인 관리 |
| 아키텍처 데스크 | 풀스택 아키텍트 / 백엔드 시니어 | Architect | 스키마·데이터 흐름 설계 |
| 프론트 데스크 | FE 시니어 | Frontend | 컴포넌트·페이지 구조 |
| QA 데스크 | QA 엔지니어 | QA | 테스트 전략·케이스 |
| 인프라 데스크 | 인프라 전문가 | Infra | CI/CD·배포 |
| 데이터 데스크 | 데이터 엔지니어 | Data | 스키마 최적화·파이프라인 |
| 서기실 | 서기관리 | Documentation | 문서 감사·노션 초안 (노션 반출 담당) |
| 자문 코너 | 외부인사 | Review | 15년차 자문·엔젤, "왜 실패하는가"부터 묻는 Devil's Advocate |
| 개발실 | 코드 생성 개발자 *(인라인)* | Codegen | 타 레포에 코드 파일 생성 |
| 편집 데스크 | 노션 편집 에이전트 *(인라인)* | NotionEdit | 검색→AI 검증→정확 편집 |

> 캐스트 데이터는 하드코딩하지 않고 **`agents/*.yaml`을 런타임에 로드**해 자동 구성한다.
> 인라인 2개(Codegen·NotionEdit)는 YAML이 없으므로 `src/gui/roster.py`에 최소 메타만 보강.

## 2. 조직 구조 = 사무실 공간

> 공간 구성은 [`04-references.md`](04-references.md)의 검증된 패턴을 차용한다
> (Work/Break 분리 = AgentRoom, 회의실+회의록 = DeskRPG, 칸반 = DeskRPG·agent-town).

- **오픈 플로어(Work Room)**: 11개 책상이 항상 보인다. 활성 에이전트만 책상에 앉아 조명이 켜진다.
- **휴게 공간(Break Room)**: 유휴 상태 에이전트는 책상을 떠나 휴게 공간으로 이동/배회한다
  → "지금 누가 일하고 누가 쉬는지"가 공간만으로 읽힌다 (AgentRoom의 Work/Break 분리).
- **회의실**: Crew 하나가 kickoff되면, 소속 에이전트들이 회의실 슬롯으로 이동/강조.
  다중 에이전트 Crew(Planning=PM+PjM, Architect=아키텍트+백엔드)는 함께 앉는다.
  회의 종료 시 회의록이 저장되고 헤더에서 열람(= 기존 `logs/*.log`와 1:1).
- **태스크보드(칸반)**: `대기 → 진행중 → 중단 → 완료` 4단계. Task 이벤트가 카드로 이동한다.
- **산출물 선반**: Task 완료 시 `output/*.md`·`*.sql` 문서 아이콘이 선반에 쌓인다.
  (선택) 담당 에이전트가 선반까지 걸어가 결과물을 "가져다 놓는" 연출(DeskRPG).
- **회의록 벽보(Activity Feed)**: 우측 사이드에 이벤트가 시간순 자막으로 흐른다
  (기존 `logs/*.log` 한 줄 = 벽보 한 줄, 의미 동일).

## 3. 이벤트 → 시각 상태 매핑 (핵심)

CrewAI 이벤트 버스가 쏘는 12종 이벤트를 직원의 **애니메이션 상태**로 번역한다.
아래 이벤트는 이미 `crew_logger.py`가 구독 중인 것과 동일하다.

| CrewAI 이벤트 | 사무실 장면 | 직원 상태 |
|--------------|------------|----------|
| `CrewKickoffStarted` | 팀이 회의실에 소집, 프로젝트 배너 게시 | 팀 활성화 |
| `CrewKickoffCompleted` | 회의 종료, 결과 발표 + 소요시간·토큰 표시 | 팀 해산 |
| `CrewKickoffFailed` | 회의실 빨간 경고등 | 팀 오류 |
| `TaskStarted` | 새 업무 카드가 담당 책상에 도착 | — |
| `TaskCompleted` | 산출물 선반에 문서 추가 (`→ output/…` 표시) | — |
| `TaskFailed` | 업무 카드 빨갛게 뒤집힘 | — |
| `AgentExecutionStarted` | 해당 직원 책상 조명 ON, 타이핑 시작 | working |
| `AgentExecutionCompleted` | 발화 자막(요약 300자) + 출력 분량 배지 | speaking→idle |
| `AgentExecutionError` | 직원 머리 위 물음표/경고 | error |
| `ToolUsageStarted` | 도구 아이콘 활성 (아래 4-2 참조) | using-tool |
| `ToolUsageFinished` | 도구 결과 분량 배지, 캐시 여부 표시 | using-tool→working |
| `ToolUsageError` | 도구 아이콘 빨강 | tool-error |
| `LLMCallCompleted` | 생각 풍선 사라지고 발화, 토큰 카운터 증가 | thinking→speaking |
| `LLMCallFailed` | 생각 풍선 터짐 | error |

> 참고: 현재 로거는 스트리밍(`LLMStreamChunkEvent`)이 아닌 `LLMCallCompleted`를 쓴다.
> 실시간 "타이핑되는 자막"을 원하면 스트림 이벤트 구독을 GUI 리스너에서 선택적으로 켠다
> (설계 초안 `design-crew-logger.md` §3.4의 버퍼링 전략 재사용).

### 4-1. 직원 상태 머신

```
idle ──AgentStart──▶ working ──ToolStart──▶ using-tool ──ToolFinish──▶ working
                        │                                                 │
                        └──LLMCall(진행)──▶ thinking ──LLMCompleted──▶ speaking
                        │                                                 │
                     AgentError                                      AgentDone
                        ▼                                                 ▼
                      error ◀──────────────────────────────────────── idle
```

### 4-2. 도구별 오브젝트 & 이동 (walk-to-object)

레퍼런스(AgentRoom·agents-in-the-office)의 검증된 패턴: 도구 호출은 단순 아이콘 점등이 아니라
**해당 오브젝트로 걸어가 상호작용**하는 이동으로 표현한다 → 무엇을 하는지 공간으로 즉시 읽힌다.
`deploy_to.tools` 및 커스텀 도구(`src/tools/`) 기준:

| 도구 | 오브젝트 / 이동 |
|------|----------------|
| `WebSearch` / `WebFetch` | 창가 검색 단말로 이동 → 돋보기로 인터넷 검색 |
| `read_file` / `write_file` | 서류 캐비닛으로 이동 → 열기/철하기 |
| `read_notion_page` / `append_to_notion_page` / `update_notion_block` … | 노션 문서함으로 걸어가 열람/수정 |
| `search_notion_blocks` | 문서함에서 특정 페이지 뒤적임 |
| `query_notion_database` | Q&A 데이터베이스 단말 조회 |
| `Bash` / `Grep` / `Glob` | 터미널 단말기로 이동 → 작업 |

> **대기/오류 강조**: 입력·승인 대기나 오류 시 화면에 **붉은 비네트 + 경고 표시**로 강하게 알린다
> (agents-in-the-office). 저사양 모드에서도 텍스트 경고는 항상 노출.

## 4. 화면 레이아웃 (와이어프레임)

```
┌────────────────────────────────────────────────────────────────┐
│ …사무실  ⏱00:42  🎫12.3k   🔔 확인함(3)   📚 문서·회의록           │  ← 상단바
├──────────────────────────────────────────┬─────────────────────┤
│                                            │  회의록(Feed)        │
│   [리서치] [기획] [아키텍처] [프론트]       │  22:25 CREW_START    │
│     💡        ⌨️       💤        💤          │  Architect          │
│                                            │  22:25 아키텍트:     │
│   [QA]   [인프라] [데이터] [서기]           │  스키마 설계…        │
│    💤      💤       ⌨️       💤              │  22:25 TOOL 웹서치   │
│                                            │  …                  │
│   ┌── 회의실: Architect Crew ──┐            │                     │
│   │  풀스택아키텍트  백엔드시니어 │  📄 output/ │                     │
│   │     💭 thinking   working    │  schema.sql │                     │
│   └────────────────────────────┘            │                     │
├──────────────────────────────────────────┴─────────────────────┤
│  ▶ Research  ▶ Planning  ▶ Architect  …  (Crew 실행 버튼)          │  ← 통제 바
└────────────────────────────────────────────────────────────────┘
```

- **상단바**: 현재 Crew, 경과 시간, 누적 토큰(`LLMCallCompleted.usage` 합산 / `total_tokens`),
  **🔔 확인함 뱃지**(사람이 처리할 항목 수), **📚 문서·회의록** 진입.
- **플로어**: 11개 책상, 상태 아이콘/애니메이션.
- **회의실 패널**: 활성 Crew의 에이전트 발화·산출물 클로즈업.
- **회의록 피드**: 이벤트 자막 스트림 (기존 로그와 1:1).
- **통제 바**: 각 Crew 실행 버튼. codegen/notion-edit처럼 인자가 필요한 명령은 입력 모달.
- **🔔 확인함 / 📚 문서·회의록**: 사람 개입·기록 열람 기능 — 상세 설계는
  [`05-human-review-and-docs.md`](05-human-review-and-docs.md).

## 5. 상호작용 (통제 기능)

- Crew 실행 버튼 → 백엔드 `POST /api/run/{crew}` → 백그라운드 실행, 이벤트가 사무실에 흐름.
- 실행 중 버튼 잠금(순차 실행 원칙). 완료 시 산출물 선반 클릭으로 `output/` 파일 미리보기.
- 직원 클릭 → 프로필 카드(goal/backstory/tools) + 해당 세션 발화 이력.
- **확인함(🔔)**: 노션 초안 승인·코드젠 리뷰·에이전트 질문·오류 조치를 한 곳에서 처리.
  승인 시 dry-run 미리보기 후 후속 동작(예: `sync_notion`) 실행 — [`05`](05-human-review-and-docs.md) §A.
- **문서·회의록(📚)**: 작업결과문서(마크다운/코드) 열람 + 과거 실행을 "회의"로 보고
  트랜스크립트/리플레이 — [`05`](05-human-review-and-docs.md) §B.
- 회의록 피드 클릭 → 원본 `logs/*.log` 라인으로 스크롤(할루시네이션 검증 동선 유지).

## 6. 접근성·현실성 원칙

- 애니메이션은 **정보 전달이 우선**, 장식은 그 다음. 색·아이콘만으로도 상태 판별 가능.
- 텍스트 자막은 항상 제공(스크린리더/저사양 대비). 게임형 픽셀 연출은 옵션 토글.
- 저사양·원격 상황을 위해 "간단 대시보드 모드"(아바타 없이 카드 리스트) 폴백 제공.
