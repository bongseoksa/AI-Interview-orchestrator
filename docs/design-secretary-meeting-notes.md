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

## 6. 충실도(fidelity) — 3계층 원칙 (절단은 표시용일 뿐)

300자 절단은 하드 리밋이 아니라 **표시용 자기 제한**이다. `logs/*.log`(사람이 읽는 표시 계층)만
절단하고, **저장·노션 계층은 무절단**으로 간다 → 속기록의 "가감 없이"를 실제로 충족한다.

| 계층 | 절단 | 처리 |
|------|------|------|
| 표시 — `logs/*.log`, GUI 라이브 피드 | 300자 유지 | `crew_logger` 무변경 |
| 저장 — `gui_data/sessions/<run_id>.jsonl`, `output/meeting-notes/*.md` | **무절단** | 파일은 길이 제한 없음 |
| 노션 — 회의록 페이지 | **무절단 + 청킹** | `_chunk_text`가 1860자 단위 **split**(자르지 않음) → 손실 0 |

- **전제(중요)**: 무절단 원문은 **소스에서 캡처**해야 한다. `logs/*.log`는 이미 절단돼 있어
  복원 불가 → `GUIEventListener`(또는 속기 전용 스트림)가 `event.output`/`event.response`
  **원문 그대로**를 세션 JSONL에 적재하고, 속기록은 이 무절단 소스로 생성한다.
- **단일 소스 권장**: 이 무절단 세션 JSONL을 [`gui/05`](gui/05-human-review-and-docs.md) §B의
  트랜스크립트·리플레이와 **동일 소스로 통합** → 속기록·GUI·회의록이 한 원본을 공유한다.

> 결정: 03 §4 **D8 채택**. MVP도 무절단 저장을 기본으로 한다(파일 크기는 텍스트라 부담 작음).

## 7. 노션 반영 — 토글 방식 (확정)

Notion의 블록 100개/요청·rich_text 2000자는 **콘텐츠 제한이 아니라 전송 단위 제한**이다.
`_chunk_text`/`_parse_inline_formatting`가 1860자 단위로 **나눠 담고**(자르지 않음),
`_markdown_to_blocks` + `MAX_BLOCKS_PER_REQUEST`가 블록을 페이지네이션한다 →
**속기록 전문을 손실 없이 노션에 저장 가능**하다. 남는 것은 가독성이며, **토글 방식으로 확정**한다.

### 7-1. 노션 페이지 구조 (확정)
```
## 기본 정보
## 정리 요약            ← 펼침 상태(항상 노출)
   ### 안건 / 주요 논의 / 결정사항 / 산출물
▸ 속기록 (발언 전문) N발화   ← 토글 블록(기본 접힘). 펼치면 아래 자식 블록
     ### [22:25:03] 풀스택 아키텍트
     > (발화 원문)
     ### [22:25:15] 풀스택 아키텍트 — 🔧 WebSearch(...)
     …
```
- 정리 요약은 **항상 노출**, 속기록은 **토글로 접어** 삽입 → 길어도 페이지가 지저분하지 않다.
- 로컬 `output/meeting-notes/<page_title>.md`에는 토글 없이 전문을 그대로 무손실 저장.

### 7-2. 구현 제약 — 현재 `notion_tools.py`는 토글 미지원 ★
- `_markdown_to_blocks`(쓰기)는 heading/list/code/paragraph만 만들고 **토글 블록을 생성하지 않는다.**
  (`toggle`은 읽기 함수 `_block_text`·업데이트 허용 목록에만 존재)
- 노션 토글은 내용을 **자식(children)으로** 품는 구조라 **평면 블록 리스트로는 불가** →
  **토글+자식 생성 헬퍼를 새로 추가**해야 한다(§8-4).
- 자식 블록 처리 시 유의:
  - 한 요청의 중첩 깊이 제한(약 2단계) → 토글 블록을 먼저 만들고, 자식은
    `PATCH /blocks/{toggle_id}/children`로 **93개 단위 청킹** 추가.
  - 속기록의 `### 헤더 + > 인용`을 토글 자식으로 넣으므로 depth 관리 필요.
  - 대안: `heading_3` + `is_toggleable: true` + children (토글형 헤더).
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

### 8-4. `src/tools/notion_tools.py` — 토글 블록 지원 추가 (필수)
현재 미지원(§7-2). 아래를 신설한다:
```python
def _toggle_block(summary_text: str, children: list[dict]) -> dict:
    """접히는 토글 블록 생성. children은 별도 PATCH로 추가할 수도 있음."""
    return {
        "object": "block", "type": "toggle",
        "toggle": {
            "rich_text": _parse_inline_formatting(summary_text),
            # children은 2단계 초과 시 인라인 금지 → 생성 후 PATCH로 청킹 추가
        },
    }
```
- `create_meeting_page`(sync_meeting_notes.py)에서: ① 정리 요약 블록 생성 →
  ② 속기록 토글 블록 생성 → ③ `build_stenograph` 결과를 `_markdown_to_blocks`로 변환해
  `PATCH /blocks/{toggle_id}/children`에 **93개 단위**로 추가.
- 회귀 방지: 기존 `_markdown_to_blocks` 시그니처·동작은 건드리지 않고 헬퍼만 추가.

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
- [ ] **노션 토글 블록 지원** `notion_tools._toggle_block` 신설 + 자식 93개 청킹 PATCH (§7-2·§8-4)
- [ ] 노션 회의록: 정리 요약(펼침) + 속기록(토글 접힘) 구조로 반영 (§7-1)
- [ ] `doc-secretary.yaml` constraints 보강 (§8-2)
- [ ] (선택) 무절단 캡처 — GUI 세션 로그(GM0)와 통합 (§6)

## 11. GUI 연계

이 속기록은 [`gui/05`](gui/05-human-review-and-docs.md) §B "에이전트 회의록 조회"의
트랜스크립트·리플레이 소스와 동일하다. **속기록 데이터 소스를 GUI 세션 JSONL로 일원화**하면
회의록(노션) · 트랜스크립트(GUI) · 리플레이가 하나의 원본을 공유한다.
