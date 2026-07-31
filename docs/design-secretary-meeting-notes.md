# Design: 서기에이전트 회의록 보완 — "정리 요약 + 속기록"

> 작성일: 2026-07-31
> 상태: 설계 (구현 전)
> 관련: [`design-crew-logger.md`](design-crew-logger.md), [`gui/05-human-review-and-docs.md`](gui/05-human-review-and-docs.md) §B(회의록 조회)
> 대상 코드: [`scripts/sync_meeting_notes.py`](../scripts/sync_meeting_notes.py), [`agents/doc-secretary.yaml`](../agents/doc-secretary.yaml)

## 1. 배경 & 목적

현재 서기에이전트가 회의록을 작성할 때는 **요약만** 남긴다.
`sync_meeting_notes.py`의 `analyze_meeting_with_llm`이 LLM에게 이렇게 지시한다:

> "로그 전체를 복사하지 말고 핵심만 추출한다 / 각 섹션은 2~4줄 이내로 간결하게"

**문제**
- 에이전트들이 **실제로 무슨 말·분석을 했는지 원문이 회의록에 남지 않는다.**
- 요약 과정에서 정보가 손실되고, LLM이 재서술하며 뉘앙스가 왜곡될 수 있다.
- 이는 크루 로거의 본래 목적(할루시네이션 **사후 검증**)과도 어긋난다 —
  검증하려면 "무슨 말을 했는지" 원문이 있어야 한다.

**목적**: 회의록을 2계층으로 만든다.
1. **정리 요약** — 빠르게 파악하는 층 (기존 요약 유지·개선, LLM 담당)
2. **속기록(발언 전문)** — 속기사처럼 **가감 없이** 발언을 기록하는 층 (신규, Python 담당)

## 2. 현재 구조 (as-is)

```
logs/<crew>_<ts>.log   ── parse(Python) ──▶ analyze_meeting_with_llm(LLM 요약)
                                                     │  4섹션(안건/주요논의/결정사항/산출물)
                                                     ▼
                                            create_meeting_page ──▶ Notion 하위 페이지
```

- 원문 발화는 **`logs/*.log`에만** 존재하고 회의록에는 반영되지 않는다.
- 로거는 발화를 축약 저장한다: `AGENT_OUTPUT`(300자), `LLM_RESPONSE`(300자),
  초과분은 `…(+N자)`로 표기 → **완전 무절단은 아님**(§6에서 다룸).

## 3. 목표 회의록 구조 (to-be)

```markdown
# 2026-07-18 22:25 — ArchitectCrew 스키마 설계

## 기본 정보
- 일시 / Crew / 참석자 / 로그 파일

## 정리 요약            ← LLM (서기)  — 기존 4섹션을 이 상위 헤더 아래로
### 안건
### 주요 논의
### 결정사항
### 산출물

## 속기록 (발언 전문)   ← Python 결정론적 추출 (가감 없음)
### [22:25:03] 풀스택 아키텍트 — 발언
> Supabase 스키마를 설계하겠습니다. 먼저 questions 테이블을…
### [22:25:15] 풀스택 아키텍트 — 🔧 WebSearch(query="Supabase RLS policy")
### [22:25:18]   ↳ 결과 512자
### [22:25:30] 백엔드 시니어 — 발언
> 데이터 흐름 관점에서 RLS 정책은…
```

- **정리 요약**을 먼저(빠른 열람), **속기록**을 뒤(감사·검증용)에 배치.

## 4. 설계 원칙 (핵심 결정)

| # | 원칙 | 근거 |
|---|------|------|
| P1 | **속기록은 LLM이 아니라 Python이 로그에서 결정론적으로 추출한다** | LLM 속기는 패러프레이즈·할루시네이션 위험 → "가감 없이"와 정면 충돌. 저장소 철학 "Python이 구조 보장, LLM은 분석만"과 정합 |
| P2 | 정리 요약은 계속 LLM(서기)이 담당 | 요약·결정 도출은 LLM의 강점 |
| P3 | 속기록은 **편집 금지** — 발화 원문 그대로(오타·표현 포함) 인용 | 속기사의 본분. 검증 가능성 확보 |
| P4 | 2계층 분리 — 요약(위) / 속기록(아래) | 빠른 열람과 원문 보존을 동시에 |
| P5 | 노션 반영은 기존 원칙 유지 — 서기 경유 + 사람 리뷰(2단계) | `CLAUDE.md` 노션 작성 원칙 |

## 5. 속기록 생성 로직 (Python, 신규 `build_stenograph`)

`logs/*.log`의 발언성 이벤트 라인을 파싱하여 화자별·시간순 마크다운으로 재구성한다.

| 로그 태그 | 속기록 표현 |
|-----------|------------|
| `[AGENT_START] <역할> — task: <태스크>` | 화자 전환 헤더 `### [시각] <역할>` |
| `[AGENT_OUTPUT] <역할>: <발화>` | 발언 본문 (blockquote 인용) |
| `[LLM_RESPONSE] <응답>` | 발언 본문 (직전 화자에 귀속) |
| `[TOOL_START] <역할> — <도구>(<인자>)` | `🔧 <도구>(<인자>)` 행동 라인 |
| `[TOOL_DONE] <역할> — <도구> — <N>자` | `↳ 결과 <N>자` |
| `[TASK_START] / [TASK_DONE]` | 안건 전환 구분선 |
| `[AGENT_ERROR] / [TOOL_ERROR] / [LLM_FAIL]` | `⚠️ 이슈` 라인 |

**규칙**
- 시간순 유지, 화자 전환 시 새 헤더. 연속 발화는 한 화자 블록으로 묶음.
- 원문 그대로 인용(`> `). 로거가 이미 붙인 `…(+N자)` 절단 표기도 **그대로 보존**(가공 금지).
- LLM 호출 없음 → 비용 0, 재현성 100%.

## 6. 충실도(fidelity) 개선 — 선택 (로거 연동)

현 로거는 발화를 300자로 절단하므로 "완전 무절단 속기"는 불가능하다. 필요 시:

- **(a) 속기 전용 무절단 캡처** *(권고)*: `crew_logger`가 `AGENT_OUTPUT`/`LLM_RESPONSE`를
  절단 없이 별도 스트림에 적재 → `logs/<crew>_<ts>.transcript.jsonl`.
  속기록은 이 파일을 우선 사용, 없으면 기존 `.log`로 폴백.
- **(b) 절단 한도 상향**: `_truncate` 기본값을 속기 대상 태그에 한해 상향(300→2000).
- **GUI 통합**: [`gui/05`](gui/05-human-review-and-docs.md) §B의
  `gui_data/sessions/<run_id>.jsonl`(구조화 이벤트)와 **동일 소스로 통합**하면
  속기록·GUI 트랜스크립트·리플레이가 하나의 진실원본을 공유한다 → **가장 권장**.

> 트레이드오프: 파일 크기·노션 용량 ↑ vs 충실도 ↑. MVP는 기존 `.log` 기반으로 시작하고,
> 무절단 캡처는 GUI 세션 로그(GM0)와 함께 도입하는 것이 효율적이다.

## 7. 노션 반영 고려 (분량 대응)

속기록은 길어질 수 있어 Notion 제약(블록 93개/요청, rich_text 1860자)에 걸린다.
`_markdown_to_blocks` + `MAX_BLOCKS_PER_REQUEST` 자동 청킹이 이미 있으나, 다음 전략을 권고:

- **노션**: `## 정리 요약` 전문 + `## 속기록`은 **토글(heading toggle)로 접어서** 삽입하거나
  "속기록 요지 + 전체는 로컬/로그 링크"로 축약.
- **로컬**: 전체 속기록은 항상 `output/meeting-notes/<page_title>.md`에 무손실 보관.
- 원칙: 노션 쓰기는 서기 초안 → 사람 리뷰 → 반영(2단계) 유지.

## 8. 변경 지점 (구현 가이드)

### 8-1. `scripts/sync_meeting_notes.py`
- **신규** `build_stenograph(meeting: dict) -> str`: §5 로직. LLM 미사용.
- `analyze_meeting_with_llm`: 출력 상단에 `## 정리 요약` 헤더 추가(기존 4섹션은 그 하위로).
  프롬프트의 "로그 전체를 복사하지 말라"는 **요약 층에만 적용**됨을 명확화.
- `create_meeting_page`: 본문 구성을
  `기본 정보 + {LLM 요약} + "\n## 속기록 (발언 전문)\n" + {build_stenograph()}` 로 변경.
- 로컬 무손실 저장 경로 추가(§7).

### 8-2. `agents/doc-secretary.yaml` (페르소나 명문화)
`constraints`에 추가:
```yaml
  - 회의록 작성 시 "정리 요약"을 먼저 쓰고, 이어서 속기사처럼 각 에이전트의 발언을
    가감 없이 기록한 "속기록" 섹션을 반드시 포함한다
  - 속기록은 발화 원문을 편집·재서술하지 않는다 (요약은 요약 섹션에만 한정한다)
```
> 인라인 서기 Agent(`analyze_meeting_with_llm` 내부)의 `backstory`/`goal`에도 동일 취지 반영.

### 8-3. (선택) `src/config/crew_logger.py`
- §6-(a) 무절단 속기 스트림 캡처 옵션.

## 9. Before / After

**Before** (요약만)
```markdown
## 주요 논의
- Supabase 스키마와 RLS 정책을 설계함
```

**After** (요약 + 속기록)
```markdown
## 정리 요약
### 주요 논의
- Supabase 스키마와 RLS 정책을 설계함

## 속기록 (발언 전문)
### [22:25:03] 풀스택 아키텍트
> Supabase 스키마를 설계하겠습니다. 먼저 questions 테이블에 RLS를 적용하고…
### [22:25:15] 풀스택 아키텍트 — 🔧 WebSearch(query="Supabase RLS policy")
### [22:25:18]   ↳ 결과 512자
### [22:25:30] 백엔드 시니어
> 데이터 흐름상 anon 역할은 SELECT만 허용해야 합니다…
```

## 10. 구현 체크리스트

- [ ] `build_stenograph` Python 파서 구현 (§5)
- [ ] `create_meeting_page`에 속기록 섹션 결합
- [ ] `analyze_meeting_with_llm` 출력을 `## 정리 요약` 하위로 재구성
- [ ] 로컬 무손실 저장(`output/meeting-notes/`)
- [ ] 노션 분량 대응(토글/요지, §7)
- [ ] `doc-secretary.yaml` constraints 보강 (§8-2)
- [ ] (선택) 무절단 캡처 — GUI 세션 로그(GM0)와 통합 (§6)

## 11. GUI 연계

이 속기록은 [`gui/05`](gui/05-human-review-and-docs.md) §B "에이전트 회의록 조회"의
트랜스크립트·리플레이 소스와 동일하다. **속기록 데이터 소스를 GUI 세션 JSONL로 일원화**하면
회의록(노션) · 트랜스크립트(GUI) · 리플레이가 하나의 원본을 공유한다.
