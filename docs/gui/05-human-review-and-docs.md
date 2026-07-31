# 05 — 사람 확인함(Human Review) & 문서·회의록 조회

> 사무실을 "보기만" 하는 것을 넘어, **사람이 개입·확인·기록 열람**하는 두 기능.
> 이 저장소의 필수 원칙 — 2단계 리뷰(서기 초안 → 리뷰 → 노션 반영), 코드젠 리뷰 후 커밋,
> 회의록/산출물 관리 — 를 GUI 위에서 그대로 운영한다.

---

## A. 사람 확인함 (Human Review Queue / "결재함")

### A-1. 왜 필요한가

에이전트는 자율 실행되지만, **사람만 내릴 수 있는 결정**이 있다. 지금은 이런 항목이
터미널 로그·`output/` 파일에 흩어져 있어 "지금 내가 뭘 확인/승인해야 하는지"가 안 보인다.
확인함은 이 항목들을 **한 곳에 모아 뱃지로 알리고, 그 자리에서 처리**하게 한다.

이것은 새 원칙이 아니라 `CLAUDE.md`가 이미 요구하는 게이트를 UI로 구현하는 것이다:
> "서기에이전트가 노션용 초안을 생성 → **리뷰 후** 노션에 반영하는 2단계 워크플로우"
> "생성된 파일은 **리뷰 후** 커밋"

### A-2. 확인함에 들어오는 항목 (Source → Item)

| # | 유형 | 발생 계기 | 사람이 할 일 | 승인 시 동작 |
|---|------|-----------|-------------|-------------|
| 1 | **노션 반영 승인** | 서기(DocumentationCrew)가 `output/notion-update-draft.md` 등 초안 생성 | 초안 검토 | `sync_notion.py`(해당 초안) 실행 → 노션 반영 |
| 2 | **코드젠 리뷰** | CodegenCrew가 타 레포(web/server)에 파일 생성 | diff 검토 | 체크 표시(커밋은 사람이 별도 수행) |
| 3 | **다음 단계 진행 승인** | Crew 완료 → 다음 마일스톤/Crew 진입 전 | 결과 확인 | 다음 Crew 실행 트리거(선택) |
| 4 | **에이전트 질문/승인 요청** | CrewAI human-in-the-loop(태스크 `human_input`) — **실행 블로킹** | 답변 입력 | 답변을 에이전트에 반환 → 실행 재개 |
| 5 | **오류·실패 조치** | `CrewKickoffFailed` / `AgentExecutionError` / `ToolUsageError` | 원인 확인·재실행 결정 | 재실행 또는 보류 |
| 6 | **할루시네이션 의심 플래그** | 로그 이상 패턴(선택, 후순위) | 발화 검증 | 표시/무시 |

> 1·2번은 이 저장소의 **명시적 리뷰 게이트**라 최우선 구현 대상.
> 4번(CrewAI `human_input`)은 실행을 멈추는 항목이라 최상단·강조 노출.

### A-3. 항목 수집 방식 (기존 코드 무변경 우선)

- **이벤트 파생(무변경)**: `TaskCompleted`의 `output_file`이 초안 패턴(`*notion*draft*`, `output/_review/*`)이면 유형1, `Failed/Error` 이벤트면 유형5로 자동 생성. (`GUIEventListener`가 판정)
- **경량 컨벤션(선택)**: Crew가 사람 확인이 필요할 때 `output/_review/<id>.json`을 남기면 확인함이 픽업. 크루 코드에 한 줄 헬퍼만 추가하는 수준.
- **CrewAI human_input 후킹(유형4)**: 태스크에 `human_input=True`가 설정된 경우, 표준 입력 대신 확인함으로 라우팅하는 어댑터. (Phase 후반, 별도 설계)

### A-4. 항목 수명주기 & 처리

```
open ──(사람 열람)──▶ in_review ──┬─ approve  ─▶ resolved  (+ 후속 동작 실행)
                                    ├─ reject   ─▶ resolved  (사유 기록)
                                    ├─ answer   ─▶ resolved  (에이전트에 반환)
                                    └─ dismiss  ─▶ resolved  (보류/무시)
```

- 처리 결과는 **의사결정 기록과 연동 가능**: 승인/반려 사유는 필요 시 노션 의사결정 로그
  초안으로 넘긴다(역시 서기 경유가 원칙, 긴급 시 예외).
- 확인함은 **영속 저장**(재시작·재접속에도 유지) → 로컬 스토어 필요(§C).

### A-5. 안전·권한 원칙 (중요)

- 노션 반영·외부 반영은 **"게시(publish)" 성격**이므로 반드시 사람 승인 후에만 실행된다.
  확인함이 바로 그 승인 게이트다 — GUI가 임의로 노션에 쓰지 않는다.
- 승인 동작이 트리거하는 스크립트(`sync_notion.py` 등)는 **미리보기(dry-run)를 먼저 보여주고**
  확정 클릭 시 실행한다.
- 노션 쓰기 경로는 원칙대로 **서기에이전트 초안 → 승인 → 반영**을 유지(직접 쓰기 금지).

---

## B. 작업결과문서 & 회의록 조회

두 아카이브를 탭으로 제공한다: **① 작업결과문서(산출물)** · **② 에이전트 회의록**.

### B-1. 작업결과문서 (Artifacts)

- **대상**: `output/*.md|*.sql|…` 산출물, 서기 노션 초안, (참조) CodegenCrew가 타 레포에
  생성한 파일 경로.
- **표시**: 마크다운 렌더링 + 코드 하이라이트, 메타데이터(생성 Crew/Task/에이전트/시각 —
  `TaskCompleted` 이벤트에서 획득), **"이 문서를 만든 회의로 가기"** 링크(B-2와 연결).
- **연동**: 기존 `scripts/sync_artifacts.py`(산출물 레지스트리)의 분류 개념 재사용.
  "노션 레지스트리에 반영"은 확인함(A) 항목으로 승인 후 실행.

### B-2. 에이전트 회의록 (Meeting Notes)

핵심 관점: **Crew 실행 1회 = 회의 1건.** 에이전트들이 태스크를 주고받으며 논의한 전 과정이
회의록이다.

- **목록**: 과거 실행을 `일자 + Crew + 주제`로 나열, Crew/에이전트/키워드/기간 필터·검색
  (레퍼런스 AgentRoom의 session search 패턴).
- **상세(트랜스크립트)**: 회의 한 건을 열면 시간순으로 —
  - 에이전트별 발화(`AGENT_OUTPUT`/`LLM_RESPONSE`), 도구 호출(`TOOL_*`),
    태스크 전환(`TASK_*`), 산출물(`→ output/…`) 을 대화록 형태로 재구성.
  - 각 라인은 **원본 `logs/*.log`로 점프**(할루시네이션 검증 동선 유지).
- **리플레이(선택·고도화)**: 회의 이벤트를 다시 흘려보내 **사무실이 그 회의를 재연**.
  타임라인 스크럽으로 되감기/빨리감기.
- **기존 자산 연동**: `docs/meeting-notes/*.md`(정제본), 노션 "에이전트 회의록"(일자+주제별
  하위 페이지), `scripts/sync_meeting_notes.py`. GUI는 **로컬 우선**으로 보여주고, 노션 반영은
  확인함(A) 경유.
- **속기록 연계**: 서기에이전트의 회의록은 "정리 요약 + 속기록(가감 없는 발언 전문)" 2계층으로
  보완된다 — [`../design-secretary-meeting-notes.md`](../design-secretary-meeting-notes.md).
  이 트랜스크립트 뷰어의 발언 원문 소스와 **동일 데이터(세션 JSONL)로 일원화**하는 것을 권장.

### B-3. 데이터 소스 — 구조화 세션 로그 신설

현재 `logs/*.log`는 사람이 읽는 텍스트라 트랜스크립트/리플레이 재구성이 번거롭다.
GUI는 **실행별 구조화 이벤트(JSONL)를 함께 적재**한다:

```
gui_data/sessions/<run_id>.jsonl     # OfficeEvent 원본(구조화) — 트랜스크립트·리플레이 소스
logs/<crew>_<ts>.log                 # (기존) 사람이 읽는 로그 — 유지, 원문 점프용
```

- `GUIEventListener`가 WebSocket 브로드캐스트와 **동시에** 세션 파일에 append(파일 = 진실원본).
- 기존 `CrewExecutionLogger`(텍스트 로그)는 그대로 병존 — 무변경 원칙 유지.

---

## C. 저장소(Persistence)

두 기능 모두 재시작에도 유지돼야 하므로 로컬 스토어를 둔다.

```
gui_data/                    # gitignored
  review.db (또는 review.json)   # 확인함 항목 + 처리 이력
  sessions/<run_id>.jsonl        # 회의별 구조화 이벤트
  index.json                     # 산출물/회의 메타 인덱스(빠른 목록)
```

- 기본 **SQLite**(server 레포와 동일 계열, 동시성·쿼리 유리). 초기엔 JSON도 무방.
- `.gitignore`에 `gui_data/` 추가(로그·output과 동일 정책).

---

## D. 화면 반영 (레이아웃 추가)

`01-vision §4` 상단바에 **확인함 뱃지**, 좌측에 **문서함/회의록** 진입을 추가한다.

```
┌───────────────────────────────────────────────────────────┐
│ …사무실   ⏱00:42  🎫12.3k   🔔 확인함(3)   📚 문서·회의록      │  ← 상단바(+확인함/문서)
├──────────────────────────────────────────┬────────────────┤
│  (플로어 · 회의실 · 태스크보드)             │  회의록 Feed     │
├──────────────────────────────────────────┴────────────────┤
│  ▶ Research  ▶ Planning  …                  (통제 바)          │
└───────────────────────────────────────────────────────────┘

🔔 확인함 패널                       📚 문서·회의록 패널
┌───────────────────────────┐      ┌───────────────────────────┐
│ [!] 에이전트 질문 대기 (1) │      │ [탭] 작업결과문서 | 회의록  │
│ [•] 노션 초안 승인 대기 (2)│      │ ─ 2026-07-31 Architect      │
│ [•] 코드젠 리뷰 (1)        │      │   schema.sql · 논의 12발화   │
│  └ 승인 | 반려 | 미리보기  │      │ ─ 2026-07-18 Planning …      │
└───────────────────────────┘      │  └ 열기 → 트랜스크립트/리플레이│
                                    └───────────────────────────┘
```

---

## E. API 추가 (→ `02-architecture §4`에 반영)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/review` | 확인함 항목 목록(open/in_review) |
| GET | `/api/review/count` | 미처리 개수(뱃지) |
| POST | `/api/review/{id}/preview` | 승인 시 실행될 동작 미리보기(dry-run) |
| POST | `/api/review/{id}/resolve` | 처리(body: `approve`/`reject`/`answer`/`dismiss` + 사유·답변) |
| GET | `/api/docs/artifacts` | 작업결과문서 목록(+메타) |
| GET | `/api/docs/artifacts/{id}` | 문서 내용(렌더용) |
| GET | `/api/meetings` | 회의(실행) 목록(필터·검색) |
| GET | `/api/meetings/{run_id}` | 회의 트랜스크립트(구조화 이벤트) |
| GET | `/api/meetings/{run_id}/replay` | 리플레이 스트림(선택) |

기존 `/api/outputs`, `/api/logs/{run}`는 위 `docs`/`meetings`로 흡수·정리.

## F. 모듈 추가 (→ `02-architecture §5`에 반영)

```
src/gui/
  review/
    models.py     # ReviewItem(pydantic): id, type, status, source, payload, resolution
    store.py      # 확인함 CRUD(SQLite/JSON), 뱃지 카운트
    actions.py    # 승인 후속 동작(sync_notion dry-run/실행 등) 어댑터
  archive/
    sessions.py   # 세션 JSONL append/read, 트랜스크립트 재구성
    artifacts.py  # output/ 스캔 + 메타 인덱싱
  listener.py     # (+) 세션 파일 적재 + review 항목 자동 파생(유형1·5)
```

## G. 마일스톤 (→ `03-roadmap`에 반영)

- **GM5 — 확인함(Human Review)**: 유형1·5 자동 파생 + 목록/승인·반려 + 노션 초안 dry-run→반영
- **GM6 — 문서·회의록 조회**: 세션 JSONL 적재 → 작업결과문서 뷰어 + 회의 트랜스크립트
- **(고도화)** CrewAI `human_input` 라우팅(유형4), 회의 리플레이, 할루시네이션 플래그(유형6)

## H. 레퍼런스 연계 (`04-references`)

- **세션 검색·트랜스크립트 뷰어**: AgentRoom(session search + transcript browsing)
- **회의실 + 회의록 저장·열람**: DeskRPG(meeting notes from header)
- **승인 대기 강조**: agents-in-the-office(붉은 비네트) → 확인함 유형4를 최상단·강조로
- **NPC가 결과를 가져다주는 연출**: DeskRPG → 산출물 생성 시 담당 에이전트가 문서함으로 배달(선택)
