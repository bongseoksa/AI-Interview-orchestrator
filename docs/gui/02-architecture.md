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

| 후보 | 장점 | 단점 | 판정 |
|------|------|------|------|
| **DOM/CSS + 경량 상태관리** | 접근성·저사양 유리, 빌드 단순 | 화려한 연출 한계 | **MVP 권장** |
| Phaser / PixiJS | 게임형 픽셀 사무실, 풍부한 애니메이션 | 번들 큼, 접근성 추가 작업 | Phase 2 옵션 |
| React + Framer Motion | 컴포넌트화·애니메이션 균형 | Node 빌드 필요 | 중간 절충안 |

권고: **바닐라 또는 경량 프레임워크 + CSS 트랜지션으로 MVP**, 반응이 좋으면
회의실 클로즈업만 Phaser로 고도화. (web 레포는 Next.js지만 이 GUI는 독립 앱이므로
스택을 강제 공유하지 않는다.)

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

## 3. 이벤트 스키마 (OfficeEvent)

WebSocket으로 흐르는 단일 메시지 포맷. 프론트는 `type`으로 분기한다.

```jsonc
{
  "type": "agent.started",        // crew.started/completed/failed, task.*, agent.*, tool.*, llm.*
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
| GET | `/api/session/{id}/status` | 실행 상태·경과·토큰 |
| GET | `/api/outputs` | `output/` 산출물 목록 |
| GET | `/api/outputs/{name}` | 산출물 내용 미리보기 |
| GET | `/api/logs/{run}` | 원본 `logs/*.log` (회의록 원문 링크용) |
| WS | `/ws/office` | 실시간 OfficeEvent 스트림 |

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
  web/            # 프론트엔드 (정적 산출물 또는 소스)
    index.html
    office.(js|ts)
    assets/       # 아바타·도구 아이콘·사운드(옵션)
main.py           # (+) "gui" 명령 추가 — uvicorn 기동 + 브라우저/웹뷰 오픈
pyproject.toml    # (+) fastapi, uvicorn, (Phase2) pywebview 의존성
```

`main.py` 확장 (기존 `COMMANDS` 딕셔너리에 1줄):

```python
"gui": ("에이전트 사무실 GUI 실행", run_gui),
```

## 6. 기존 코드 영향 범위

- **무변경**: `crew_logger.py`, 11개 `crews/*/crew.py`, `tools/*`, `agents/*.yaml`.
- **추가만**: `src/gui/` 신규 패키지, `main.py`에 `gui` 명령 1개, `pyproject.toml` 의존성.
- 리스크 낮음: 이벤트 리스너는 read-only 관찰자. 실패해도 Crew 실행 자체엔 영향 최소화
  (리스너 예외를 삼키는 방어 코드 포함).

## 7. 보안·범위

- 로컬 전용 바인딩(`127.0.0.1`) 기본. 원격 관전이 필요하면 인증 계층은 별도 논의.
- 통제 API(`/api/run`)는 로컬 앱에서만 노출. 외부 공개 시 CSRF/인증 필수(범위 밖).
