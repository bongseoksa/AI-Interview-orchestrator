# 04 — 레퍼런스 벤치마킹

> 웹서치로 수집한 "AI 에이전트 사무실" 오픈소스 사례 정리 (2026-07-31).
> 구현 내용은 상이하나 **레이아웃·상호작용 패턴**을 벤치마킹한다.
> 사용자 제시 레퍼런스: [DeskRPG 블로그](https://javaexpert.tistory.com/1720) · [OpenClaw 메타버스 오피스 영상](https://www.youtube.com/watch?v=hLh5K0IWk5E)

## 1. 생태계 지형 — 3개 계열

수집 결과 이 분야는 세 갈래로 나뉜다. **우리 프로젝트의 위치를 먼저 못박는 것이 중요하다.**

| 계열 | 성격 | 대표 | 우리와의 관계 |
|------|------|------|--------------|
| ① 소셜 시뮬레이션 | 에이전트가 자율적으로 살아감(대화·연애·파티) | AI Town, Generative Agents(Smallville) | 참고만 — 우리는 자율 생활이 아님 |
| ② 코딩 에이전트 시각화 | **실제** 코딩 에이전트 활동을 실시간 반영 | pixel-agents, AgentRoom, agents-in-the-office, claude-office | **레이아웃·행동 매핑 직접 벤치마킹** |
| ③ 협업 멀티에이전트 오피스 | 팀이 태스크를 분담·수행 | **DeskRPG**, **AgentOffice**, agent-town | **오피스 은유·태스크보드·회의실 벤치마킹** |

> **우리의 위치 = ② + ③ 하이브리드.** CrewAI가 실제 실행하는 작업을 실시간 반영(②)하되,
> 11개 에이전트가 Crew 단위로 협업하는 조직을 오피스로 표현(③)한다.
> AI Town류(①)의 "자율 배회"는 채택하지 않는다 — 우리 에이전트는 이벤트에 따라 움직인다.

## 2. 핵심 벤치마크 (우리와 가장 가까운 순)

### 🥇 AgentOffice — `harishkotra/agent-office` (MIT)
**우리와 제약이 거의 동일: Ollama 로컬 LLM + 오피스 시각화.**
- 스택: **Phaser.js(게임 캔버스) + React 오버레이(Vite)** — 캔버스 위에 HTML UI 패널 얹음
- 동기화: **Colyseus(WebSocket) + delta 압축** — 변경된 바이트만 전송, 스프라이트 tween
- UI 패널: **Chat / TaskBoard / SystemLog / ActivityLog / Inspector / LayoutEditor**
- 에이전트 행동: move / talk / use_tool(코드 실행·웹검색·파일 IO) / hire
- LLM 추상화: `InferenceAdapter`로 Ollama·OpenAI·Anthropic 교체 가능
- 배포: Docker Compose
- **차용 포인트**: 패널 구성(특히 Inspector=직원 프로필, LayoutEditor), Phaser+React 오버레이 방식, Ollama 어댑터 패턴, MIT라 코드 학습 자유

### 🥈 AgentRoom — `liuyixin-louis/agentroom`
**이벤트 파이프라인 + 데스크톱 패키징의 정석.**
- 스택: **Tauri(데스크톱) + Rust 파일워처 + React + Canvas 2D**, BFS 경로탐색, 캐릭터 상태머신
- 동작: 코딩 에이전트가 디스크에 쓰는 **JSONL 트랜스크립트를 감시** → 구조화 이벤트로 변환 → 프론트
- 공간: **Work Room(활성=책상 착석) vs Break Room(유휴=이동/배회)**, 프로젝트별 오피스 분리
- 부가: 세션 검색, 트랜스크립트 뷰어, **서브에이전트를 별도 캐릭터로 스폰**
- **차용 포인트**: 활성/유휴 공간 분리, 상태머신+경로탐색, 데스크톱은 Tauri 선택지, 원본 로그 뷰어(=우리 회의록 원문 링크)

### 🥉 agents-in-the-office — `gukosowa/agents-in-the-office`
**행동→오브젝트 매핑의 교과서.**
- 스택: Vue 3 + Pinia + Vite + **Tauri 2**, 커스텀 타일 렌더러(A* 경로), RPG Maker 타일셋 지원
- 이벤트: `sessionId/timestamp/type/agentType/payload` JSON → Rust `notify` 워처 → Pinia 스토어 → 에이전트별 드라이버
- **행동 매핑**:
  - 코드 작성 → 컴퓨터로 이동
  - 파일 읽기 → 책장으로 이동
  - 도구 호출 → 해당 오브젝트(Bash/Read/Edit…)로 이동
  - **승인 대기 → 경고 표시 + 붉은 비네트**
  - 유휴 → 배회 + 대화 시도
- 지원: Claude Code, Gemini CLI
- **차용 포인트**: 우리 `01-vision §4-2` 도구 아이콘 매핑을 "이동+상호작용"으로 승격, 대기 상태의 강한 시각 신호

### DeskRPG — `dandacompany/deskrpg` · [deskrpg.com](https://www.deskrpg.com) *(사용자 원본 레퍼런스)*
**멀티플레이어 오피스 + 태스크보드 + 회의실의 완성형.**
- LPC 기반 아바타 커스터마이즈, 채널(공유 맵) 실시간 멀티플레이 이동
- **OpenClaw** 게이트웨이로 AI NPC 연결 → 대화로 업무 위임
- **태스크 상태: 대기 → 진행중 → 중단 → 완료** (칸반), NPC가 걸어와 in-world 리포트 전달
- **전용 회의실 + 회의록 저장**(헤더에서 열람), 다중 에이전트 AI 미팅
- Tiled 스타일 맵 에디터, SQLite/PostgreSQL, Docker
- **차용 포인트**: 칸반 태스크 상태 4단계, 회의실+회의록(우리 CrewKickoff=회의, `logs`=회의록과 1:1), NPC가 결과를 "가져다주는" 연출

## 3. 그 밖의 참고 사례

| 프로젝트 | 한줄 | 차용 포인트 |
|----------|------|------------|
| **pixel-agents** (`pablodelucca`) | 코딩에이전트 시각화 계열의 원조. 터미널 에이전트를 오피스 캐릭터로. VS Code 확장 + `npx` 로컬 서버 | "편집 중=타이핑, 검색 중=읽기, 막힘=시각 플래그" 상태 표현의 표준 |
| **agent-town** (`rafapetter`) | **의존성 0**, 프레임워크 불문 TS, HTML5 Canvas 2D **절차적 렌더링(스프라이트시트 없음)**, 7개 테마(오피스 포함), 칸반 | **저의존 MVP 경로** — 무거운 빌드 없이 시작 가능 |
| **claude-office** (`paulrobello`) | Claude Code 작업을 실시간 픽셀 오피스로 | 단일 에이전트 실시간 반영 레퍼런스 |
| **pixel-office-openclaw** (`neomatrix25`) | OpenClaw 에이전트 픽셀 오피스, 캐릭터 클릭 시 대화 | 클릭→상호작용 UX |
| **my-virtual-office** (`eliautobot`) | self-hosted 2D 워크스페이스, 책상 이동·커피·미팅 | "로그 대신 물리적 현존감" 카피 방향 |
| **AI Town** (`a16z-infra`) | 소셜 시뮬 앵커. Convex 엔진, Generative Agents(Stanford/Google) 논문 재현 | 계열①, 아키텍처보다 무드 참고 |
| **AgentVerse** (`OpenBMB`) | 멀티에이전트 프레임워크(task-solving + simulation) | 프레임워크 관점 참고 |

## 4. 우리 설계에 반영할 결론

### 4-1. 검증된 것 (기존 계획 유지 근거)
- **이벤트 구동 시각화는 정석 패턴이다.** AgentRoom·agents-in-the-office 모두
  `구조화 이벤트 → 상태머신 → 캔버스`로 동작. 우리 `crew_logger → OfficeEvent → WebSocket → UI`와 동일.
- **Ollama + 오피스 시각화 조합은 이미 실증됐다** (AgentOffice). 스택 리스크 낮음.

### 4-2. 우리만의 강점 (레퍼런스보다 유리한 점)
- 레퍼런스 대부분(AgentRoom·agents-in-the-office)은 코딩 에이전트가 디스크에 남긴
  **JSONL을 역으로 감시**하는 우회 방식이다. **우리는 CrewAI 이벤트 버스를 직접 소유**하므로
  파일워처·폴링 없이 구조화된 이벤트를 바로 얻는다 → 더 풍부하고 정확하다.
- 11개 에이전트의 `role/goal/backstory/tools`가 이미 정의돼 있어 **직원 프로필·성격이 공짜**다
  (AgentOffice는 성격을 LLM으로 생성).

### 4-3. 새로 흡수할 패턴 (문서 반영)
1. **공간 분리**: 활성=책상(Work), 유휴=휴게 공간(Break) — AgentRoom
2. **행동→이동 매핑 승격**: 도구 호출을 "해당 오브젝트로 걸어가 상호작용"으로 (AgentRoom·agents-in-the-office) → `01-vision §4-2` 확장
3. **대기/오류 강조**: 승인·입력 대기 시 붉은 비네트+경고 (agents-in-the-office)
4. **칸반 태스크보드**: 대기/진행중/중단/완료 (DeskRPG) → Task 이벤트를 칸반으로
5. **회의실+회의록**: CrewKickoff=회의 소집, `logs/*.log`=회의록 (DeskRPG)
6. **Inspector/프로필 카드**: 에이전트 클릭 → 상태·이력 (AgentOffice)
7. **NPC 결과 배달 연출**: 완료 산출물을 캐릭터가 "가져다주는" 모션 (DeskRPG) — 선택

### 4-4. 스택 결정 보강 (기존 후보 + 레퍼런스 실증)
| 레이어 | 레퍼런스 실증 | 우리 채택안 (`02-architecture`) |
|--------|--------------|------------------------------|
| 캔버스 | Phaser(AgentOffice) / Canvas2D+절차적(agent-town) | MVP: DOM·CSS 또는 **agent-town식 저의존 Canvas2D**, 고도화 시 Phaser |
| UI 오버레이 | React 오버레이(AgentOffice) | 프레임워크 무관 오버레이 유지 |
| 실시간 동기화 | Colyseus/WebSocket(AgentOffice), Tauri 이벤트(AgentRoom) | **WebSocket**(기존안 유지) |
| 데스크톱 | **Tauri**(AgentRoom·agents-in-the-office) | PyWebView(권고) ↔ **Tauri**(강력한 실증 대안) |
| 태스크 UI | 칸반(DeskRPG·agent-town) | 태스크보드 추가 |

> 결론: 기존 `02-architecture.md`의 방향은 레퍼런스로 검증됐다. 다만 **데스크톱 셸에서
> Tauri가 이 분야의 사실상 표준**(AgentRoom·agents-in-the-office·다수)임이 확인되어,
> `03-roadmap` 미결정 D1의 유력 대안으로 격상한다.

## 5. 라이선스 메모
- 다수가 **MIT**(AgentOffice, agent-town 등) → 코드 학습·부분 차용 자유. 채택 시 개별 라이선스 재확인 필수.
- 에셋(스프라이트/타일셋)은 별도 라이선스(LPC, RPG Maker 타일셋 등) — 상용/배포 시 반드시 확인.

## Sources
- [DeskRPG (블로그, 원본 레퍼런스)](https://javaexpert.tistory.com/1720) · [DeskRPG GitHub](https://github.com/dandacompany/deskrpg) · [deskrpg.com](https://www.deskrpg.com)
- [OpenClaw 메타버스 오피스 영상](https://www.youtube.com/watch?v=hLh5K0IWk5E)
- [AgentOffice — DEV 글](https://dev.to/harishkotra/how-i-built-agentoffice-self-growing-ai-teams-in-a-pixel-art-virtual-office-4o0p) · [agent-office GitHub](https://github.com/harishkotra/agent-office)
- [AgentRoom](https://github.com/liuyixin-louis/agentroom) · [agents-in-the-office](https://github.com/gukosowa/agents-in-the-office)
- [agent-town (rafapetter)](https://github.com/rafapetter/agent-town) · [claude-office](https://github.com/paulrobello/claude-office) · [pixel-office-openclaw](https://github.com/neomatrix25/pixel-office-openclaw) · [my-virtual-office](https://github.com/eliautobot/my-virtual-office)
- [AI Town (a16z-infra)](https://github.com/a16z-infra/ai-town) · [AgentVerse (OpenBMB)](https://github.com/OpenBMB/AgentVerse)
