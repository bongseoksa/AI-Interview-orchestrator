# 02 — 아키텍처

> 기존 코드 무변경 원칙(최소 침습)을 지키면서, 이벤트 스트림을 WebSocket으로 확장한다.

## 1. 전체 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│  Python 프로세스 (오케스트레이터 + GUI 백엔드)                  │
│                                                               │
│   main.py / API가 Crew.kickoff() 실행                         │
│        │                                                      │
│        ▼                                                      │
│   CrewAI 이벤트 버스 (프로세스 전역)                           │
│        ├── CrewExecutionLogger  ──▶ logs/*.log   (기존, 유지) │
│        └── GUIEventListener     ──▶ OfficeEvent(JSON)         │
│                                        │                      │
│                                        ▼                      │
│                                   EventBus (asyncio fan-out)  │
│                                        │                      │
│                     FastAPI: WebSocket /ws/office ◀───────────┤
│                             REST /api/*                       │
│                                        │                      │
└────────────────────────────────────────┼─────────────────────┘
                                          ▼
                            사무실 UI (webview / 브라우저)
```

핵심: CrewAI 이벤트 버스는 **프로세스 전역 싱글턴**이라, 리스너 인스턴스를 하나 더
등록하면 별도 배선 없이 모든 Crew의 이벤트를 받는다 (`crew_logger.py`가 이미 그렇게 동작).

## 2. 기술 스택

### 2.1 백엔드 (Python, 기존 레포에 추가)

| 계층 | 선택 | 근거 |
|------|------|------|
| 웹 프레임워크 | **FastAPI + uvicorn** | 비동기 WebSocket 네이티브, server 레포와 동일 스택(학습비용↓) |
| 이벤트 모델 | **pydantic** | FastAPI 내장, 직렬화·검증 일원화 |
| Crew 실행 | **worker thread** (`concurrent.futures`) | kickoff은 블로킹 → 스레드로 서버 응답성 유지. 이벤트 버스는 전역이라 스레드에서도 수신됨 |
| 정적 서빙 | FastAPI `StaticFiles` | 프론트 빌드 산출물 서빙 |

> 대안: Crew를 **subprocess**로 격리하면 크래시 격리·병렬성이 좋아지지만, 이벤트를
> stdout/IPC로 직렬화해야 한다. MVP는 thread, 확장 시 subprocess 검토(03 로드맵 참조).

### 2.2 프론트엔드 (사무실 UI)

| 후보 | 장점 | 단점 | 판정 | 레퍼런스 실증 |
|------|------|------|------|--------------|
| **DOM/CSS + 경량 상태관리** | 접근성·저사양 유리, 빌드 단순 | 화려한 연출 한계 | **MVP 권장** | — |
| **Canvas 2D 절차적**(스프라이트시트 없음) | 저의존, 빌드 가벼움, 경로탐색 자유 | 픽셀아트 감성은 별도 에셋 필요 | MVP 대안 | agent-town(rafapetter, 의존성 0) |
| Phaser / PixiJS | 게임형 픽셀 사무실, 풍부한 애니메이션 | 번들 큼, 접근성 추가 작업 | Phase 2 옵션 | AgentOffice(Phaser+React 오버레이) |
| React + Framer Motion | 컴포넌트화·애니메이션 균형 | Node 빌드 필요 | 중간 절충안 | AgentRoom(React+Canvas2D) |

권고: **바닐라/경량 프레임워크 + CSS 트랜지션으로 MVP**(또는 agent-town식 저의존 Canvas2D),
반응이 좋으면 회의실 클로즈업만 Phaser로 고도화. 여러 레퍼런스가 **캔버스(게임 엔진) + HTML UI
오버레이** 구조를 공통 채택하므로(AgentOffice·AgentRoom), 오버레이 방식을 기본 골격으로 삼는다.
(web 레포는 Next.js지만 이 GUI는 독립 앱이므로 스택을 강제 공유하지 않는다.)

### 2.3 데스크톱 셸 (macOS + Windows)

백엔드가 Python이라 셸은 반드시 Python 프로세스를 띄우거나 함께 배포해야 한다.

| 후보 | 배포물 | 런타임 | 판정 |
|------|--------|--------|------|
| **PyWebView + PyInstaller** | `.app`(mac) / `.exe`(win) 단일 | OS 내장 웹뷰 | **권장** — Python 단일 언어, 백엔드와 한 프로세스에 번들 |
| Tauri | 초경량 바이너리 | OS 웹뷰 + Rust | 배포 최적이나 Rust 툴체인 + Python 사이드카 배선 필요 |
| Electron | 큰 바이너리 | 번들 Chromium | 친숙하나 무겁고 Python 사이드카 별도 |

권고: **Phase 1은 셸 없이 로컬 웹**(`python main.py gui` → 브라우저 오픈)으로 검증하고,
**Phase 2에서 PyWebView로 감싸** Mac/Windows 바이너리를 만든다. 초경량 배포가 중요해지면
Tauri로 전환(프론트/이벤트 프로토콜은 그대로 재사용 가능).

> **레퍼런스 주의**: 이 분야 데스크톱 앱(AgentRoom·agents-in-the-office)은 대부분 **Tauri**를
> 채택했다. 다만 그들은 프론트가 이미 JS/TS이고 백엔드도 Rust다. **우리는 백엔드가 Python(CrewAI)**
> 이라 Tauri를 쓰면 Python을 사이드카로 배선해야 한다. 그래서 1차 권고는 PyWebView이되,
> JS 프론트를 본격 구축하기로 하면 Tauri가 강력한 대안이다 (`03-roadmap` D1).

## 3. 이벤트 스키마 (OfficeEvent)

WebSocket으로 흐르는 단일 메시지 포맷. 프론트는 `type`으로 분기한다.

```jsonc
{
  "type": "agent.started",        // crew.*, task.*, agent.*, tool.*, llm.* + 파생: review.requested, human.input_requested, alert.raised
  "ts": "2026-07-31T22:25:03.120",
  "crew": "ArchitectCrew",
  "agent": "풀스택 아키텍트 (Fullstack Architect)",
  "task": "schema_design",
  "tool": null,                    // tool.* 이벤트에서만
  "payload": {                     // 이벤트별 부가 정보
    "text": "Supabase 스키마를 설계하겠습니다…",  // 발화/응답 요약
    "output_len": 2048,
    "output_file": "output/step3-schema-design.sql",
    "tokens": { "prompt": 512, "completion": 1024 },
    "from_cache": false,
    "error": null,
    "elapsed_sec": 104.0
  }
}
```

- 필드 명세는 `crew_logger.py`가 각 이벤트에서 이미 추출하는 값과 1:1 대응
  (agent_role, task_name, tool_name, tool_args, output_file, usage, total_tokens 등).
- 초기 접속 시 서버는 **현재 스냅샷**(로스터 + 진행 중 상태)을 먼저 보내고, 이후 델타 스트림.

## 4. REST API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/agents` | 직원 로스터 (`agents/*.yaml` + 인라인 2종 파싱) |
| GET | `/api/crews` | 실행 가능한 Crew/명령 목록 (`main.py`의 `COMMANDS` 재사용) |
| POST | `/api/run/{crew}` | Crew 백그라운드 실행 (codegen/notion-edit은 body에 인자) |
| GET | `/api/session/{run_id}/status` | 실행 상태·경과·토큰 (run_id는 §8-3) |
| GET | `/api/logs/{run_id}` | 원본 `logs/*.log` (회의록 트랜스크립트 원문 점프용 — 유지) |
| WS | `/ws/office` | 실시간 OfficeEvent 스트림 |
| — | **확인함·문서·회의록 API** | 아래는 [`05-human-review-and-docs.md`](05-human-review-and-docs.md) §E |
| GET/POST | `/api/review`, `/api/review/count`, `/api/review/{id}/preview`, `/api/review/{id}/resolve` | 사람 확인함(승인·반려·답변·dry-run) |
| GET | `/api/docs/artifacts`, `/api/docs/artifacts/{id}` | 작업결과문서 목록·내용 (기존 `/api/outputs` 흡수) |
| GET | `/api/meetings`, `/api/meetings/{run_id}`, `/api/meetings/{run_id}/replay` | 회의(실행) 목록·트랜스크립트·리플레이 |

## 5. 모듈 구조 (신규 `src/gui/`)

```
src/gui/
  __init__.py
  events.py       # OfficeEvent pydantic 모델 + 이벤트 타입 상수
  listener.py     # GUIEventListener(BaseEventListener) — CrewAI 이벤트 → OfficeEvent
  bus.py          # EventBus: asyncio 큐 fan-out, WS 클라이언트 브로드캐스트
  roster.py       # agents/*.yaml 로드 + 인라인 에이전트 메타 보강
  runner.py       # Crew를 worker thread로 kickoff, 세션 상태 추적
  server.py       # FastAPI 앱 (REST + WebSocket + StaticFiles)
  review/         # 사람 확인함 — 05 §F
    models.py     #   ReviewItem(pydantic)
    store.py      #   확인함 CRUD(SQLite/JSON) + 뱃지 카운트
    actions.py    #   승인 후속 동작(sync_notion dry-run/실행) 어댑터
  archive/        # 문서·회의록 — 05 §F
    sessions.py   #   세션 JSONL append/read, 트랜스크립트 재구성
    artifacts.py  #   output/ 스캔 + 메타 인덱싱
  web/            # 프론트엔드 (정적 산출물 또는 소스)
    index.html
    office.(js|ts)
    assets/       # 아바타·도구 아이콘·사운드(옵션)
gui_data/         # (신규, gitignored) review.db, sessions/<run_id>.jsonl, index.json
main.py           # (+) "gui" 명령 추가 — uvicorn 기동 + 브라우저/웹뷰 오픈
pyproject.toml    # (+) fastapi, uvicorn, (Phase2) pywebview 의존성
```

> `listener.py`는 WebSocket 브로드캐스트와 **동시에** ① 세션 JSONL 적재(회의록·리플레이 소스)와
> ② 확인함 항목 자동 파생(초안=유형1, 실패=유형5)을 수행한다. 상세: [`05`](05-human-review-and-docs.md).

`main.py` 확장 (기존 `COMMANDS` 딕셔너리에 1줄):

```python
"gui": ("에이전트 사무실 GUI 실행", run_gui),
```

## 6. 기존 코드 영향 범위

- **무변경**: `crew_logger.py`, 11개 `crews/*/crew.py`, `tools/*`, `agents/*.yaml`.
- **추가만**: `src/gui/` 신규 패키지, `main.py`에 `gui` 명령 1개, `pyproject.toml` 의존성,
  `.gitignore`에 `gui_data/` 추가.
- 리스크 낮음: 이벤트 리스너는 read-only 관찰자. 실패해도 Crew 실행 자체엔 영향 최소화
  (리스너 예외를 삼키는 방어 코드 포함).
- **단, 확인함 승인 동작**(예: `sync_notion` 실행)은 read-only가 아니다 — 반드시
  dry-run 미리보기 후 사람 확정 클릭으로만 실행하며, 노션 쓰기는 서기 초안 경유 원칙을 지킨다.

## 7. 보안·범위

- 로컬 전용 바인딩(`127.0.0.1`) 기본. 원격 관전이 필요하면 인증 계층은 별도 논의.
- 통제 API(`/api/run`)는 로컬 앱에서만 노출. 외부 공개 시 CSRF/인증 필수(범위 밖).

## 8. 실구현 정합성 — 반드시 짚을 4가지 (구현 전 확정)

설계 검토에서 드러난, 코드로 옮길 때 걸리는 핵심 지점들이다. **모두 GM0 스파이크에서 검증**한다.

### 8-1. 프로세스 경계 — "이벤트 버스 전역"은 *한 프로세스 안*에서만 성립 ★가장 중요
CrewAI 이벤트 버스는 **프로세스 전역 싱글턴**이지 *머신 전역*이 아니다. 따라서
`python main.py gui`(GUI 서버 프로세스)와 `python main.py architect`(별도 터미널 프로세스)는
**서로 다른 프로세스**라 GUI가 그 크루의 이벤트를 직접 받지 못한다. 두 실행 모드로 정리한다:

| 모드 | 실행 방식 | 이벤트 경로 | 용도 |
|------|-----------|------------|------|
| **인프로세스(주력)** | GUI가 `/api/run`으로 크루를 **자기 프로세스 안에서** kickoff | 이벤트 버스 직접 수신 → 가장 풍부 | GM2 이후 통제·관전 |
| **사이드카/테일** | 크루를 별도 CLI로 실행, 그 프로세스의 리스너가 `gui_data/sessions/<run_id>.jsonl` 기록 → GUI가 파일 **tail** | 파일 경유(레퍼런스 AgentRoom식) | CLI 병행 관전 |

> **GM1 DoD 정정**: "터미널에서 `python main.py architect` 실행 시 보인다"는 **사이드카/테일 모드**를
> 전제로 한다(세션 JSONL을 tail). GUI 버튼 실행(인프로세스)은 GM2부터. 이 구분을 GM0에서 확정한다.

### 8-2. 스레드 → asyncio 핸드오프 (블로킹 kickoff)
`runner.py`가 kickoff를 **worker thread**에서 돌리면, `GUIEventListener` 콜백도 그 워커 스레드에서
실행된다. 반면 WebSocket 브로드캐스트는 **asyncio 루프 스레드**에서 일어난다. 스레드 경계를
넘을 때는 반드시 `loop.call_soon_threadsafe(...)` 또는 `asyncio.run_coroutine_threadsafe(...)`로
큐에 넣는다(직접 `await`/`queue.put_nowait` 금지). → `bus.py`의 핵심 계약.

### 8-3. run_id 상관관계 (세션 JSONL·확인함 파생)
CrewAI 이벤트에는 run_id가 없고, `CrewKickoffStartedEvent.crew_name`도 `None`인 경우가 있다
(`crew_logger`가 `"unknown"`으로 처리 중). 따라서 **run_id는 `runner`가 kickoff 시점에 생성**해
"현재 실행"으로 리스너에 주입하고, 리스너가 그 값으로 세션 파일·확인함 항목을 태깅한다.

### 8-4. 순차 실행 전제 (동시성 범위)
`crew_logger`는 단일 파일 핸들·인스턴스 상태(`_crew_name`, `_file`)를 공유해 **동시 실행 시 상태가
섞인다**. GUI도 같은 제약이므로 **MVP는 순차 실행**(통제 바 버튼 잠금, 01 §5)으로 못박는다.
동시 다중 크루는 범위 밖 — 필요 시 run_id별 리스너 인스턴스 분리로 확장.

### 8-5. 발화 충실도 — 3계층 원칙 (절단은 표시용일 뿐) ★D8 채택
300자 절단은 하드 리밋이 아니라 **표시용 자기 제한**이다. 계층별로 다르게 적용한다:

| 계층 | 절단 | 근거 |
|------|------|------|
| 표시 (터미널 로그 `logs/*.log`, GUI 라이브 피드) | 300자 유지 | 가독성·IO. 클릭 시 원문 펼침 |
| 저장 (`gui_data/sessions/<run_id>.jsonl`, `output/meeting-notes/*.md`) | **무절단** | 로컬 파일은 길이 제한 없음 |
| 노션 | **무절단 + 청킹** | `_chunk_text`/`_parse_inline_formatting`가 1860자 단위로 **split**(자르지 않음) → 콘텐츠 손실 0 |

- **전제**: 무절단 원문은 **소스에서 캡처**해야 한다. `logs/*.log`는 이미 절단돼 있으니
  `GUIEventListener`가 `event.output`/`event.response` **원문을 그대로** 세션 JSONL에 적재.
  `crew_logger`의 300자 로그는 표시용으로 유지(무변경).
- **노션 유의**(제한 아님, UX): 매우 긴 회의는 블록 수↑ → PATCH 다회·페이지 무거움.
  속기록은 **토글로 접어** 삽입 권장. 상세:
  [`../design-secretary-meeting-notes.md`](../design-secretary-meeting-notes.md) §6·§7.
