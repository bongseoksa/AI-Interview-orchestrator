# Orchestrator GUI — "에이전트 사무실" 계획

> 작성일: 2026-07-31
> 브랜치: `feature/orchestrator-gui`
> 상태: 계획 수립 (구현 전)

## 한 줄 요약

11개 CrewAI 에이전트가 일하는 과정을 **실제 사무실처럼** 실시간으로 시각화하는
크로스플랫폼(macOS · Windows) 데스크톱 앱을 만든다.

## 왜 만드는가 (목적)

현재 에이전트의 작업 과정은 `verbose=True`로 터미널에 흘러가거나
`logs/*.log` 파일에 텍스트로만 남는다. **"누가 지금 무슨 일을 하는지"**를
한눈에 보기 어렵고, 비개발자에게 이 시스템의 가치를 전달하기 어렵다.

이 GUI는 오케스트레이터를 **투명한 유리 사무실**로 바꾼다:

- 각 에이전트 = 자기 책상에서 일하는 직원 (전략 관리자, PM, 아키텍트, 서기, 외부인사…)
- Crew 실행 = 팀이 회의실에 모여 프로젝트를 수행
- 도구 호출 = 웹서치·노션 문서·파일 캐비닛을 사용하는 동작
- LLM 사고 = 머리 위 생각 풍선 + 실제 발화 자막
- 완료/실패 = 산출물이 책상에 쌓이거나 빨간 경고

관전(monitoring)과 통제(control, 사무실에서 직접 Crew를 출근시키기)를 모두 지원한다.

## 핵심 설계 인사이트

이 기능은 백지에서 시작하지 않는다. [`docs/design-crew-logger.md`](../design-crew-logger.md)가
이미 예고한 대로 —

> "향후 Phase 1에서는 이 로그를 기반으로 GUI 대시보드(WebSocket 실시간 스트리밍)를 구축할 수 있다."

기존 [`src/config/crew_logger.py`](../../src/config/crew_logger.py)의
`CrewExecutionLogger(BaseEventListener)`가 이미 CrewAI 이벤트 버스의 12종 이벤트를
가로채고 있다. GUI는 **같은 이벤트 스트림을 파일 대신 WebSocket으로도 흘려보내는 것**이
전부다. 기존 코드는 손대지 않고 형제(sibling) 리스너를 추가한다.

```
CrewAI 이벤트 버스
   ├── CrewExecutionLogger  → logs/*.log      (기존, 유지)
   └── GUIEventListener     → WebSocket        (신규)  → 사무실 UI
```

## 비용 제약 준수

- GUI 자체는 **LLM을 호출하지 않는다** (순수 시각화 계층). `CLAUDE.md`의
  "Claude API 토큰 사용 불가" 원칙에 영향 없음.
- Crew 실행은 기존과 동일하게 Ollama 로컬 모델만 사용.
- 데스크톱 스택 후보는 모두 오픈소스/무료 (PyWebView, Tauri, Electron).

## 문서 구성

| 문서 | 내용 |
|------|------|
| [`01-vision-and-metaphor.md`](01-vision-and-metaphor.md) | 사무실 은유 상세 설계 — 직원 캐스트, 이벤트→시각 상태 매핑, 화면 레이아웃 |
| [`02-architecture.md`](02-architecture.md) | 이벤트 파이프라인, 기술 스택, 이벤트 스키마, 모듈 구조 |
| [`03-roadmap.md`](03-roadmap.md) | 단계별 마일스톤, 리스크, 미결정 사항 |

## 확정해야 할 결정 (요약)

상세 논의는 [`03-roadmap.md`](03-roadmap.md) 참조. 현재 권고안:

| 결정 | 권고안 | 대안 |
|------|--------|------|
| 데스크톱 셸 | **PyWebView + PyInstaller** (Python 단일 언어) | Tauri(최소 용량) / Electron(친숙) |
| 프론트 렌더링 | **DOM/CSS 아바타** (MVP) | Phaser·PixiJS (게임형 픽셀 사무실) |
| 범위 | **관전 + 통제** (UI에서 Crew 실행) | 관전 전용 |
| 착수 방식 | **로컬 웹 MVP → 데스크톱 패키징** 2단계 | 처음부터 데스크톱 |

> 레포 원칙(`CLAUDE.md`)상 UI 상세 설계는 **FrontendCrew**, 아키텍처는 **ArchitectCrew**가
> 주도 검증하는 것이 정석이다. 이 문서는 그 Crew 실행을 위한 입력(설계 초안) 역할을 겸한다.
