# CLAUDE.md — AI-Interview-orchestrator

에이전트 정의 원본 및 워크플로우를 관리하는 오케스트레이터 레포.

## 레포 목적

- 10개 에이전트의 페르소나 정의 원본 (YAML) 관리
- 각 레포(web/server)의 `.claude/agents/` 서브에이전트 생성 스크립트
- Step별 워크플로우 정의
- 향후 자율 에이전트 실행 환경 (Ollama + CrewAI, 무료 모델만)

## 비용 제약

- **Claude API 토큰 사용 불가** — 이 레포에서는 유료 LLM API를 직접 호출하지 않는다
- 자율 에이전트 실행 시 Ollama 로컬 모델만 사용
- Claude Code 서브에이전트(.claude/agents/)는 사용 가능 (기존 구독 활용)

## 디렉토리 구조

```
agents/               # 에이전트 YAML 정의 원본
workflows/            # Step별 워크플로우 정의
scripts/              # 유틸리티 (sync, 변환 등)
.claude/agents/       # 이 레포에서 사용하는 Claude Code 서브에이전트
```

## 관련 레포

- `AI-Interview-web` — 프론트엔드 (Next.js 16, pnpm)
- `AI-Interview-server` — 백엔드 (Python, TBD)
