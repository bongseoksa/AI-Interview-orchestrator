# 03 — 로드맵 · 리스크 · 미결정

## 1. 단계별 마일스톤

각 마일스톤은 독립적으로 "보여줄 수 있는" 산출물을 남긴다.

### GM0 — 이벤트 백본 (기반)
- `src/gui/events.py`, `listener.py`, `bus.py` 구현
- `GUIEventListener`를 이벤트 버스에 등록 → 콘솔로 OfficeEvent(JSON) 출력 검증
- **DoD**: 아무 Crew나 실행하면 구조화 이벤트가 실시간으로 찍힌다 (`crew_logger`와 병존)

### GM1 — 로컬 웹 대시보드 (관전)
- FastAPI 서버 + `/ws/office` + `/api/agents` + `/api/crews`
- 프론트 MVP: 11개 책상 + 상태 아이콘 + 회의록 피드 (DOM/CSS)
- `main.py gui` 명령으로 기동 → 브라우저 자동 오픈
- **DoD**: 터미널에서 `python main.py architect` 실행 시, 브라우저 사무실에서
  아키텍트 팀이 일하는 모습이 실시간으로 보인다

### GM2 — 통제 + 산출물 (상호작용)
- `POST /api/run/{crew}` + 통제 바 버튼 (codegen/notion-edit 인자 모달)
- 산출물 선반(`output/` 목록·미리보기), 직원 프로필 카드
- 세션 상태·경과·토큰 카운터
- **DoD**: 사무실 UI 버튼만으로 Crew를 실행하고 산출물까지 열람한다

### GM3 — 사무실 연출 고도화 (몰입)
- 아바타·이동·도구 애니메이션, 회의실 클로즈업 (필요 시 Phaser)
- LLM 스트리밍 자막(옵션), 사운드(옵션), 픽셀/대시보드 뷰 토글
- **DoD**: 비개발자가 봐도 "직원들이 일하는 사무실"로 읽힌다

### GM4 — 데스크톱 패키징 (배포)
- PyWebView 셸로 백엔드+웹뷰 단일 프로세스화
- PyInstaller로 macOS `.app` / Windows `.exe` 빌드, 실행 가이드
- **DoD**: Mac·Windows에서 더블클릭 한 번으로 사무실 앱이 뜬다

## 2. 의존성·순서

```
GM0 ──▶ GM1 ──▶ GM2 ──▶ GM3
                  └──────▶ GM4 (GM2 이후 언제든 병행 가능)
```

GM0→GM1이 가치의 80%. GM3(연출)와 GM4(패키징)는 우선순위에 따라 순서 교체 가능.

## 3. 리스크 · 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| CrewAI 이벤트 필드가 버전마다 다름 | 리스너 파싱 깨짐 | `getattr` 방어적 접근(기존 로거와 동일 패턴), 이벤트 스냅샷 테스트 |
| kickoff 블로킹으로 서버 멈춤 | UI 프리즈 | worker thread 실행, 이벤트 버스 전역 수신 활용 |
| LLM 스트리밍 이벤트 I/O 과부하 | 프론트 렉 | `design-crew-logger.md §3.4` 버퍼링(문장/500자 flush) 재사용, 스트림은 옵션 |
| PyInstaller가 CrewAI/Ollama 의존성 누락 | 빌드 실패 | hidden-import 목록 관리, GM4 초반에 최소 빌드 스파이크 선행 |
| 게임형 연출 과투자 | 일정 지연 | GM1(정보 전달) 먼저 확정 후 GM3 연출은 선택적 |
| Ollama 미기동 상태에서 실행 | Crew 실패 이벤트만 | UI에 "Ollama 오프라인" 배너 + 헬스체크 |

## 4. 미결정 사항 (사용자 확인 필요)

| # | 결정 | 권고 | 비고 |
|---|------|------|------|
| D1 | 데스크톱 셸 | PyWebView + PyInstaller | Python 단일 언어. Tauri(경량)·Electron(친숙) 대안 |
| D2 | 프론트 렌더링 | DOM/CSS MVP → 필요 시 Phaser | 게임형 픽셀 사무실을 처음부터 원하면 Phaser 선착수 |
| D3 | 범위 | 관전 + 통제 | 관전 전용이면 GM2 축소 |
| D4 | 착수 방식 | 로컬 웹 MVP 먼저 | 처음부터 데스크톱 앱을 원하면 GM4를 앞으로 |
| D5 | 시각 톤 | 스타일라이즈드(깔끔) | 픽셀 도트 감성 vs 미니멀 대시보드 감성 |
| D6 | 사운드/알림 | 옵션(기본 OFF) | 완료·오류 사운드 넣을지 |

## 5. 레포 원칙과의 정합

`CLAUDE.md`의 개발 역할 분담 원칙에 따라, **구현 착수 전 다음 Crew 실행을 권장**한다:

1. **ArchitectCrew** — 이벤트 파이프라인·모듈 구조 검증 (`02-architecture.md`를 입력으로)
2. **FrontendCrew** — 사무실 UI 컴포넌트·상태 머신 상세 설계 (`01-vision-and-metaphor.md` 입력)
3. **QACrew** — 이벤트 리스너·WebSocket 브로드캐스트 테스트 전략
4. **ReviewCrew(외부인사)** — "이 GUI가 실사용될 가치가 있는가" 냉정한 검증

이 `docs/gui/` 문서 자체가 위 Crew들에 넘길 **설계 초안(input)** 역할을 한다.
Notion 반영이 필요하면 **서기에이전트(DocumentationCrew)** 경유 원칙을 따른다.

## 6. 다음 액션 (제안)

- [ ] D1~D6 결정 확정
- [ ] GM0 스파이크: `GUIEventListener`로 이벤트 JSON 콘솔 출력 (반나절)
- [ ] ArchitectCrew·FrontendCrew 설계 검증 실행
- [ ] GM1 착수
