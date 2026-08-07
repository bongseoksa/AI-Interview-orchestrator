# Handoff: GUI 이벤트 파이프라인 완성

## 날짜
2026-07-31

## 브랜치
feature/orchestrator-gui

---

## 완료된 작업

### GM0: GUI 기본 인프라 (fc01308)
- `src/gui/events.py` — OfficeEvent 단일 메시지 포맷 (Pydantic)
- `src/gui/bus.py` — asyncio EventBus, WebSocket fan-out + call_soon_threadsafe
- `src/gui/listener.py` — GUIEventListener (BaseEventListener 상속), CrewAI 14종 이벤트 캡처
- `src/gui/runner.py` — CrewRunner, ThreadPoolExecutor(max_workers=1) 순차 실행
- `src/gui/server.py` — FastAPI 서버 (REST 4종 + WebSocket 1종 + 정적파일)
- `src/gui/roster.py` — agents/*.yaml + 인라인 2종 로스터 로드
- `main.py` — `gui` 커맨드 등록, gui_listener import 자동 등록
- pyproject.toml — fastapi 의존성 추가

### GM0+: UX 보완 (94e3bdb ~ ac4df06)
- Phase A: Activity Feed → Office Messenger 전환 (채팅 UI)
- Phase B: Agent Dashboard 하단 패널 (per-agent 통계 바)
- Phase C-1: 공간형 레이아웃 (Work Room / Meeting Room / Lounge 3존) + 파일 분리
- Phase D: 인터랙션 강화 (프로필 모달, 도구 하이라이트, 에러 비네트)
- Phase E: 비주얼 톤 조정 (라이트/다크 테마, 가구 인디케이터)

### 검증 완료
- 9개 crew 전체 순차 실행 성공 (research → planning → architect → frontend → qa → infra → data → docs → review)
- API 엔드포인트 4종 정상 (`/api/agents`, `/api/crews`, `/api/status`, `/api/run/{crew}`)
- WebSocket 실시간 이벤트 스트리밍 정상

---

## 해야 할 작업

### 1. 이벤트 파이프라인 갭 보완

| 항목 | 현황 | 해야 할 것 |
|------|------|-----------|
| **GUI 비활성화 시 동작** | `_broadcast`가 None이면 콘솔+JSONL만 출력 — 이미 동작 | 없음 (검증만) |
| **CLI 실행과 GUI 분리** | `python main.py research` (CLI)와 `python main.py gui` (서버)는 별도 프로세스 → CLI 이벤트가 GUI에 안 보임 | CLI 모드에서도 GUI가 떠 있으면 이벤트를 전달할지 결정 필요. 옵션: (a) 무시 (현행 유지), (b) JSONL 파일 tail → WebSocket relay |
| **LLMCallStartedEvent** | 미캡처 (CrewAI에 해당 이벤트 존재 여부 확인 필요) | crewai.events에서 확인 후 있으면 추가 |
| **세션 히스토리** | JSONL 파일(`gui_data/sessions/`)에 적재만 함, GUI에서 과거 세션 조회 불가 | `/api/sessions` + `/api/sessions/{run_id}` 엔드포인트 추가, 프론트에서 리플레이 |

### 2. 이벤트 파이프라인 안정성

| 항목 | 설명 |
|------|------|
| **WebSocket 재연결 시 상태 복원** | 현재 reconnect 시 빈 화면. `/api/status`로 현재 crew 상태는 복원 가능하나, 진행 중 이벤트 히스토리 유실 |
| **느린 클라이언트 처리** | `QueueFull` 시 클라이언트 drop (ponytail 주석). backpressure 또는 ring buffer 전환 검토 |
| **동시 crew 실행 방어** | `CrewRunner.is_busy` 체크 존재하나 race condition 가능성 — `_lock` 범위 재검토 |

### 3. 프론트엔드 보완

| 항목 | 설명 |
|------|------|
| **에이전트-Crew 매핑 정확도** | `CREW_MAP` 하드코딩 → roster API에서 crew 필드를 받아오도록 동적화 |
| **codegen/notion-edit 지원** | 인자 필요한 crew는 버튼에서 제외됨 → 입력 폼 추가 또는 별도 UI |
| **에러 시 상세 표시** | crew.failed 시 에러 메시지만 표시 → 스택트레이스 또는 마지막 에이전트 상태 표시 |

---

## 참고 사항

### 아키텍처 핵심 흐름
```
CrewAI Event Bus
  | (BaseEventListener.setup_listeners)
GUIEventListener._emit()
  |-- 1) stderr 콘솔 출력 (항상)
  |-- 2) JSONL 파일 적재 (항상, gui_data/sessions/)
  +-- 3) EventBus.broadcast_threadsafe() (GUI 활성화 시만)
       | call_soon_threadsafe
     EventBus._broadcast_sync()
       | Queue.put_nowait
     WebSocket /ws/office -> 브라우저
```

### GUI 활성화/비활성화 메커니즘
- **비활성화**: `gui_listener._broadcast`가 `None` → `_emit()`에서 3번 분기 스킵 → 콘솔+JSONL만
- **활성화**: `server.py`의 `_bind_bus()`에서 `gui_listener._broadcast = event_bus.broadcast_threadsafe` 주입
- **전환 조건**: `python main.py gui` 실행 여부 (uvicorn startup 이벤트에서 주입)

### 파일 구조
```
src/gui/
  __init__.py          # 빈 패키지
  events.py            # OfficeEvent, OfficePayload (Pydantic)
  bus.py               # EventBus (asyncio Queue fan-out)
  listener.py          # GUIEventListener (CrewAI 14종 이벤트 -> OfficeEvent)
  runner.py            # CrewRunner (ThreadPoolExecutor, 순차 실행)
  server.py            # FastAPI app (REST + WS + static)
  roster.py            # 에이전트 로스터 로드
  web/
    index.html         # SPA 엔트리
    office.js          # 이벤트 핸들러 + UI 로직
    office.css          # 스타일 (다크/라이트 테마)
```

### 의존성
- `fastapi>=0.115.0` (pyproject.toml에 추가됨)
- `uvicorn` — fastapi의 의존성으로 자동 설치
- `pydantic` — crewai의 의존성으로 이미 존재

### 우선순위 제안
1. **LLMCallStartedEvent 확인 + 추가** — 최소 작업, 파이프라인 완성도 향상
2. **WebSocket 재연결 시 상태 복원** — UX 안정성
3. **세션 히스토리 조회** — 과거 실행 결과 확인 가능
4. **codegen/notion-edit 입력 폼** — 모든 crew GUI에서 실행 가능
