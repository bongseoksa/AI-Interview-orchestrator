# 07 — 지시 채팅 & 회의 (GM7)

> 사내 메신저처럼 지시하고 보고받는다. `scripts/design_*.py` 작성을 대체한다.

**상태: 구현 완료 (2026-08-07)** — 실행 `python main.py gui` → 메신저 하단 입력창.
검증 `python tests/test_dispatch.py` (13 pass, LLM·노션 호출 없음).

## 1. 문제

새 업무를 시키려면 매번 스크립트를 짜야 한다. 원인은 두 군데 하드코딩이다.

| # | 위치 | 증상 |
|---|------|------|
| 1 | `main.py`의 `run_research()` 등 11개 | `inputs={"topic": "..."}` 하드코딩 — Crew는 있는데 **주제를 못 바꾼다** |
| 2 | `scripts/design_m5_m6.py` | 임의 참석자 조합 회의는 `Agent`/`Task`를 **코드로 직접 조립**해야 한다 |

GUI도 이 둘을 못 뚫는다. `POST /api/run/{crew}`는 crew 이름만 받고 인자 경로가 없다.
`office.js`는 WS **수신 전용** — 사용자→에이전트 방향 채널이 아예 없다.

## 2. 소통 3종 → 실행 모델

| 소통 종류 | 주체 | 트리거 | 산출 |
|-----------|------|--------|------|
| 작업 지시 | 사용자 | 메신저 입력 | 라우터 → 실행 |
| 현황 공유 | 에이전트 | crew/agent/task 이벤트 | 메신저 말풍선 (기존) |
| 미팅 실시간 과정 | 에이전트 | 회의실 존 이벤트 (기존) | 화면 |
| 미팅 회의록 | 서기 | 회의 종료 | 노션 `에이전트 회의록` 하위 페이지 |
| 미팅 결정사항 보고서 | 서기 | 회의 종료 | 노션 `회의 결정사항` 하위 페이지 (신규) |

**핵심 규칙 — 참석자 수가 곧 모드다.**

```
라우터가 뽑은 참석자 1명  → 채팅 답변.       회의록/보고서 없음
라우터가 뽑은 참석자 2명+ → 회의.            회의록 + 결정사항 보고서 생성
```

`mode` 필드를 따로 두지 않는다. 참석자 목록 하나로 분기한다.

## 3. 재사용 / 신규 / 삭제

**재사용 (새로 만들지 않는다)**

| 기존 자산 | 새 용도 |
|-----------|---------|
| `roster.load_roster()` | 라우터 프롬프트의 에이전트 카탈로그 + Agent 조립 재료 (동일 소스) |
| `get_llm(FAST_MODEL)` (Tier 2 `gemma4:12b`) | 라우터 판정 |
| `gui_data/sessions/<run_id>.jsonl` | 속기록 원본 (무절단 — D8) |
| `sync_meeting_notes.analyze_meeting_with_llm()` | 회의록 생성 |
| `create_notion_child_page()` | 페이지 생성 + 부모 그룹화 |
| `OfficeEvent` / `event_bus` | 사용자 메시지도 같은 포맷으로 흐른다 |
| `ThreadPoolExecutor(max_workers=1)` | 이미 큐다 |

**신규 (2 파일)**

- `src/gui/dispatch.py` (~180줄) — 라우터 + ad-hoc Crew 조립
- `src/gui/review.py` (~60줄) — 확인함

**삭제**

- `runner.py`의 `is_busy` 거절. `ThreadPoolExecutor(1)`이 이미 순차 큐인데 거절만 하고 있다.
  거절을 빼면 메신저처럼 지시가 쌓이고 순서대로 처리된다. **큐 구현 불필요.**

## 4. 라우터 — 3단 폴백

```
사용자 메시지
  │
  ├─ 1) @멘션 있음?  "@fullstack-architect 스키마 봐줘"
  │      → 정규식으로 agent_id 추출, LLM 스킵
  │
  ├─ 2) LLM 라우팅 (gemma4:12b)
  │      입력: roster 13명 요약 + 최근 대화 10턴 + 메시지
  │      출력: {"agents": [...], "agenda": "...", "repo": "web|server|orchestrator|null"}
  │
  └─ 3) 파싱 실패 / agents 빈 배열
         → 실행하지 않고 되묻는다
           "누구한테 시킬까요? [PM] [아키텍트] [FE 시니어] ..."
```

- **대화 맥락**: 최근 10턴을 프롬프트에 넣는다. CrewAI Memory / 벡터 DB 안 쓴다.
  "그거 다시 해줘"가 안 먹히기 시작하면 그때 올린다.
- **오분류 방어**: 판정 결과를 먼저 메신저에 띄우고 실행한다.
  `[회의] M1 서비스 LLM 선정 — product-manager, fullstack-architect, infra-expert`
  Ollama 로컬이라 오분류 비용은 시간뿐. **취소 버튼은 미구현** — 큐 대기 항목은
  `Future.cancel()`로 가능하지만 실행 중인 Crew는 CrewAI에 중단 API가 없다.
  반쪽 취소(대기분만)를 만들면 "취소했는데 계속 돈다"가 되므로 넣지 않았다.

## 5. Ad-hoc 회의 조립

```python
# dispatch.py 핵심 (의사코드)
def build_meeting(agent_ids, agenda, context):
    roster = {a["agent_id"]: a for a in load_roster()}
    members = [Agent(role=r["role"], goal=r["goal"], backstory=r["backstory"],
                     llm=get_llm(HIGH_PERF_MODEL), allow_delegation=False)
               for r in (roster[i] for i in agent_ids)]

    # 참석자별 Task = 순차 릴레이 (앞 발언이 context로 들어간다)
    tasks = [Task(description=f"안건: {agenda}\n{context}\n당신의 관점에서 검토·주장하라.",
                  expected_output="근거를 갖춘 의견과 권고안", agent=m)
             for m in members]

    # 서기 Task 고정 추가 — 결정사항 추출 담당
    tasks.append(Task(description="위 논의에서 결정사항/미결/액션아이템을 추출하라.",
                      expected_output="## 결정사항 / ## 미결 / ## 액션아이템",
                      agent=secretary, context=tasks[:]))

    return Crew(agents=members + [secretary], tasks=tasks, process=Process.sequential)
```

- `Process.sequential` 고정. `hierarchical`은 manager LLM 호출이 추가로 붙고,
  로컬 모델의 위임 판단 품질이 불안하다.
- 참석자 1명이면 서기 Task를 붙이지 않는다 → 그냥 답변 1건.

## 5-1. 권한 (도구)

| 에이전트 | 도구 |
|----------|------|
| 전원 | `list_directory`, `list_directory_recursive`, `read_file` — 읽기 전용. 회의는 논의지 실행이 아니다 |
| `codegen-developer` | \+ `write_file`. `file_tools`의 `PROJECT_BASE`가 `AI-Interview/`라 web/server 크로스 레포 쓰기가 열린다 (CLI `CodegenCrew`와 동일 권한). 태스크도 '의견'이 아니라 '실행'으로 분기한다 |
| `notion-editor` | \+ `read_notion_page`, `search_notion_blocks`. **수정·삭제는 주지 않는다** — 채팅 오타 한 번에 지식베이스가 지워지면 안 된다. `main.py notion-edit` CLI 전용 |

## 6. 문서 명명 규칙 (파일 · 노션 페이지 공통)

```
{일자}_{타이틀}_{종류}

2026-08-07_M1-서비스-LLM-선정_회의록
2026-08-07_M1-서비스-LLM-선정_결정사항
```

| 필드 | 규칙 |
|------|------|
| `{일자}` | `YYYY-MM-DD`. 정렬이 곧 일자별 정리다 |
| `{타이틀}` | 라우터가 뽑은 `agenda`를 slug화 — 공백→`-`, `/`·`_` 제거, 40자 |
| `{종류}` | `회의록` \| `결정사항` \| (확장: `보고서` \| `초안`) |
| 충돌 | 같은 일자·타이틀·종류가 이미 있으면 `_2` 접미 (시간 안 붙인다 — 이름이 길어진다) |

**단일 소스**: `dispatch.py`의 `doc_name(date, agenda, kind)` 하나가 파일명과 노션 페이지 제목을 **동시에** 만든다. 두 군데에서 각각 조립하지 않는다.

**절단도 단일 소스** — `trim()`. 40자 절단은 `route()`(안건 확정)와 `slugify()`(파일명) 두 군데에서 걸리는데, 서로 다르게 자르면 이중 절단으로 어긋난다. 절단은 항상 어절 경계에서 한다 — 이 문자열이 그대로 노션 페이지 제목이라 어절 중간에서 끊기면 안 읽힌다(`...최소-테스트배포-준비가`). 경계가 제목 절반보다 앞이면 그냥 자른다(빈 제목 방지).

적용 범위 — 로컬 파일도 같은 이름을 쓴다:

```
output/meetings/2026-08-07_M1-서비스-LLM-선정_회의록.md
output/meetings/2026-08-07_M1-서비스-LLM-선정_결정사항.md
output/_review/<run_id>.json          ← 큐 파일만 run_id 유지 (내부용)
```

### 노션 배치

```
회의록 (섹션)
├── 에이전트 회의록                                    ← 기존, 그대로 사용
│   ├── 2026-08-07_M1-서비스-LLM-선정_회의록
│   ├── 2026-08-07_M1-서비스-LLM-선정_결정사항
│   ├── 2026-08-07_Phase5-M3-면접UI-범위_회의록
│   └── 2026-08-07_Phase5-M3-면접UI-범위_결정사항
```

- 회의록과 결정사항은 **형제 페이지**다. 부모를 나누지 않는다 — 이름의 `{일자}_{타이틀}` 접두가 이미 둘을 묶고, 정렬하면 일자별·회의별로 붙어 나온다. 부모 페이지 추가 = `notion_pages.json` 항목 추가 + 탐색 1클릭 증가인데 얻는 게 없다.
- 월별 폴더는 안 만든다 — 이름 정렬로 충분. 회의 100건 넘으면 그때.
- **기존 27건은 소급 개명하지 않는다** (`YYYY-MM-DD HH:MM — CrewName 주제` 유지). 신규분부터 적용. 혼재가 거슬리면 `scripts/rename_meeting_pages.py` 별건.

## 7. 확인함 — 승인 후 반영 (최소 GM5)

`CLAUDE.md` 2단계 파이프라인(초안 → 리뷰 → 동기화) 준수. Ollama 환각이 검토 없이 노션에 박히는 걸 막는다.

**큐를 DB로 만들지 않는다.** `output/_review/<run_id>.json` 파일 자체가 큐다
(`05-human-review-and-docs.md` §38의 "경량 컨벤션" 그대로).

```
회의 종료
  → 서기가 초안 2건 생성 → output/meetings/{일자}_{타이틀}_{종류}.md
  → output/_review/<run_id>.json 저장 (초안 경로 2개 참조)
  → WS: review.pending 이벤트
  → 메신저에 승인 카드
       [미리보기] [노션 반영] [반려]
  → 승인: create_notion_child_page ×2 (페이지 제목 = 파일명, doc_name() 동일 소스)
          → json 삭제 (md는 남긴다 — 노션 장애 시 재시도 원본)
  → 반려: json 삭제 + md 삭제
```

sqlite(`gui_data/review.db`) 스킵. 파일 몇 개 안 쌓인다.

## 8. API — 3개 추가

| Method | Path | 응답 |
|--------|------|------|
| POST | `/api/message` `{text}` | `{run_id, agents, agenda}` 또는 `{ask: "누구한테..."}` |
| GET | `/api/review` | 대기 항목 목록 |
| POST | `/api/review/{run_id}/{approve\|reject}` | `{ok}` |

기존 `POST /api/run/{crew}`는 유지 — 버튼 = 프리셋 지시.

## 9. 이벤트 타입 — 3개 추가

`user.message` / `router.decided` / `review.pending`

`OfficeEvent` 스키마는 그대로 쓴다 (`payload.text`). 새 Pydantic 모델 안 만든다.

## 10. 프론트 (office.js, +~120줄)

- 메신저 하단 입력창 (Enter 전송, Shift+Enter 줄바꿈)
- `user.message` → 우측 정렬 말풍선
- `router.decided` → 시스템 라인
- `review.pending` → 승인 카드 (미리보기 모달 / 노션 반영 / 반려)
- 헤더에 `대기 N건` (큐 깊이), 메신저 제목에 `확인함 N`
- 실행 중에도 Crew 버튼을 막지 않는다 — 큐가 열렸으므로

**미처리**: `CREW_MAP` 하드코딩 제거. `agents/*.yaml`에 `crew` 필드가 없어서 roster API가 crew를 못 준다. 고칠 자리는 `office.js`가 아니라 `roster.py`이고(crew 디렉토리 → agent 매핑), 이 작업 범위 밖이다.

### UX 보완 (2026-08-07)

팔레트를 Claude 디자인(따뜻한 뉴트럴 + 코랄)으로 교체하고, 스크린샷으로 확인한 문제를 고쳤다.
**구조 검증(엔드포인트·함수 존재)만으로는 아래를 하나도 못 잡았다 — 렌더링을 봐야 보였다.**

| 문제 | 조치 |
|------|------|
| `@멘션`을 쓰려면 `agent_id`를 외워야 함 | `@` 입력 시 자동완성 팝업 (방향키·Enter·Tab·Esc). `쓰기` 배지로 코드젠 표시 |
| 발언이 500자에서 잘려 회의 내용을 못 읽음 | 8줄 클램프 + `전문 보기 (N자)` 토글. 원문은 DOM에 그대로 |
| 빈 메신저에 안내가 없어 첫 지시를 못 씀 | 빈 상태 안내 (동작 설명만) |
| 아바타 색이 랜덤 HSL(형광 초록·분홍)이라 팔레트와 충돌 | 채도 낮춘 고정 팔레트 13색에서 해시 선택 |
| 메신저 360px(화면 25%)이라 입력창이 좁음 | 패널을 `clamp(440px, 44vw, 760px)`로 확대 — 입력창은 대화 안에 두고 **패널 폭을 넓힌다**. 입력창만 하단 전폭으로 빼봤으나 대화와 분리돼 되돌렸다 |
| 보내기 버튼이 프리셋 바와 따로 놈 | 같은 radius 계열로 맞추고 `Enter` 힌트 추가. 프리셋은 외곽선(보조), 보내기는 채움(주 액션) |
| placeholder가 1줄 textarea에서 잘림 | 문구 축약 + `rows=2` |
| 대시보드 13장이 가로로 잘림 | 기본 접힘 + 접힘 시 `display:none` (max-height 추정 대신) |
| 라우터 판정이 회의/작업 구분 없이 같은 회색 | 배지 분리 — 회의=코랄, 작업=초록, 되묻기=주황 |
| **새로고침하면 승인 카드가 사라져 승인 불가** | 접속 시 `/api/review`로 대기 항목 복원 (기능 결함) |

**제거**: 하드코딩된 예시 지시 버튼 3개. 프로젝트 상태를 읽어 다음 작업을 제안하는 게 아니라
고정 문자열이었다 — 자동으로 갱신되지 않는 '추천'은 오해만 만든다.

검증: 헤드리스 Chrome 스크린샷(다크/라이트) + `node`로 DOM 스텁 위에서 렌더 함수 스모크
(클램프·XSS 이스케이프·배지 분기·멘션 팝업 필터/선택).

## 11. 안 하는 것

| 스킵 | 추가 시점 |
|------|-----------|
| CrewAI Memory / 벡터 RAG | 최근 10턴 주입으로 대화가 안 이어질 때 |
| 동시 실행 | Ollama 로컬이라 어차피 GPU 직렬. 원격 LLM 전환 시 |
| LLM 스트리밍 자막 | `LLMCallStartedEvent` 확인 후 (handoff 문서 별건) |
| 월별 폴더 / sqlite 확인함 / 세션 리플레이 | 회의 100건, 확인함 20건 넘으면 |

## 12. 검증

### 자가검증 — `python tests/test_dispatch.py` (13 pass)

LLM·노션 호출 없음. 라우터는 스텁, 확인함은 임시 디렉토리.
pytest를 붙이지 않았다 — 이 레포에 테스트 인프라가 없어서 의존성 한 줄을 위해 프레임워크를 들이지 않는다.

| 검증 | 내용 |
|------|------|
| `slug` / `doc_name` | slug화, 40자, `_` 구분자 2개, 충돌 시 `_2`·`_3` |
| `trim_at_word_boundary` | 어절 경계 절단 + **route/slugify 절단 일치** (이중 절단 회귀 방지) |
| `mention` / `route_mention_skips_llm` | @멘션 추출, 멘션 있으면 LLM 호출 안 함(스텁이 raise) |
| `route_llm` | 잡설 섞인 응답에서 JSON 추출 |
| `route_filters` | 없는 id·서기 제외 |
| `route_fallback_asks` | JSON 파싱 실패·빈 배열·LLM 예외 → 실행 안 하고 되묻기 |
| `solo_is_not_meeting` | 1명 → Task 1개, 서기 없음 |
| `meeting_appends_secretary` | 3명 → Agent 4·Task 4, 참석자 순서 유지, 서기 context 3개 |
| `bad_ids` | 유효 0명 → ValueError |
| `transcript` | 3000자 발언 무절단 저장 (D8) |
| `review_roundtrip` | enqueue→pending→preview→reject, 반려 시 초안 md도 삭제 |

### 실행 중 잡은 결함 (자가검증만으로는 안 잡혔다)

| 결함 | 증상 | 원인 · 조치 |
|------|------|-------------|
| **지시 원문 소실** | 코드젠이 파일을 안 쓰고 "무엇을 하라는 건지 알려달라"고 답함 | `agenda`가 제목과 태스크 지시를 겸했다. 40자 절단으로 조건이 날아감 → `instruction`(원문 무절단)을 태스크에 따로 넣는다. 코드젠뿐 아니라 **모든 에이전트**가 제약을 잃고 있었다 |
| **참석자 에코** | 외부인사가 PM 발언을 통째로 고쳐 씀 (Devil's Advocate 소실) | `external-advisor.yaml`이 `- "좋다/괜찮다"는...`에서 YAML 파싱 실패 → `roster.py`가 **조용히** `role=agent_id`로 폴백 → 페르소나 없는 빈 에이전트. YAML 수정 + 폴백 시 경고 출력 + 전 에이전트 goal/backstory 검사 테스트 |
| 릴레이 지시 동일 | 뒤 발언자가 앞 발언을 요약/반복 | 첫 발언자와 이후 발언자의 지시를 분리 — "이미 나온 논거를 다시 쓰지 마라, 동의/반박부터 밝혀라" |
| 회의록 화자 구분 소실 | 화자 3명이 본문 헤딩 11개에 섞여 읽을 수 없음 | 발언 본문의 `#`를 h4 이하로 강등 + `---` 구분선 |
| `notion-editor` 페르소나 없음 | (위 테스트가 잡음) | backstory 추가. 노션 **조회 도구만** 부여 — 수정·삭제는 CLI 전용 |

### 실행 검증 (2026-08-07, gemma4:26b)

| 단계 | 결과 |
|------|------|
| 라우터 실전 | "PM·아키텍트·인프라 불러서 회의" → 3인 **회의** / "테스트 추가해줘" → 1인 **작업**. 둘 다 정확 |
| 2인 회의 | QA → 인프라 → 서기 릴레이 완주 (약 2분 35초), 결정사항 추출됨 |
| 큐 개방 | 실행 중 2번째 지시 투입 → 거절 대신 `queued:1`, 순서대로 처리 |
| 1인 작업 | 회의록·결정사항 **미생성** (참석자 수 = 모드 규칙 검증) |
| 문서 생성 | `2026-08-07_..._회의록.md` (12KB) / `..._결정사항.md` (2.3KB) |
| 확인함 승인 | 노션 자식 페이지 2건 생성, 95블록·26블록, **마지막 줄까지 전달 확인** |

## 13. 리스크

| 리스크 | 대응 |
|--------|------|
| 라우터 오분류 → 엉뚱한 크루가 몇 분 실행 | 판정 선표시로 즉시 인지. **중단 불가**(§4) — 확실할 땐 `@멘션`을 쓴다 |
| `gemma4:12b` JSON 준수율 | 파싱 실패·예외 → 실행 안 하고 되묻기 (§4 폴백 3). 실측 2/2 정상 |
| 프로세스 경계 — CLI 실행분이 GUI에 안 보임 | 기존 미해결 항목(handoff §1). 채팅은 인프로세스라 무관 |
| 회의 결과가 노션에 안 남음 | 승인 실패 시 큐 json을 지우지 않는다 → 재승인 가능. 초안 md는 승인 후에도 남긴다 |

## 14. 레포 원칙 정합

`CLAUDE.md` 개발 역할 분담에 따라 **구현 착수 전 Crew 검증 권장**:

1. **ArchitectCrew** — 라우터 3단 폴백 + ad-hoc 조립 구조 검증 (이 문서를 입력으로)
2. **ReviewCrew** — "라우터 오분류 비용 vs 스크립트 작성 비용" 냉정한 검증
3. 노션 반영은 **DocumentationCrew** 경유 (확인함이 이 규칙의 구현체다)
