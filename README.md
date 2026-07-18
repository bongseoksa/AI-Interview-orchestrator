# AI Interview - Orchestrator

프론트엔드 엔지니어를 위한 AI 기반 모의 인터뷰 연습 서비스의 에이전트 오케스트레이션 레포지토리.

## Overview

11개 에이전트 페르소나(YAML)를 정의하고, CrewAI + Ollama로 자율 실행하는 멀티에이전트 시스템.

- **Framework**: CrewAI v1.15 (MIT, self-hosted)
- **LLM**: Ollama local (Gemma 4 26B / 12B)
- **Cost**: $0 (fully local inference)

## AI Model 2-Tier Strategy

| Tier | Model | Type | RAM | Speed | Purpose |
|------|-------|------|-----|-------|---------|
| **Tier 1** | gemma4:26b | MoE | ~15GB | ~70-80 t/s | Research, planning, architecture |
| **Tier 2** | gemma4:12b | Dense | ~6.6GB | ~80-90 t/s | User-facing content |

Hardware: Apple M4 Pro 48GB (273 GB/s)

## Getting Started

```bash
# Git pre-commit 훅 활성화 (최초 1회)
git config core.hooksPath .githooks

# Python 가상환경
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ollama 모델 다운로드 (최초 1회)
ollama pull gemma4:26b    # Tier 1 (~15GB)
ollama pull gemma4:12b    # Tier 2 (~6.6GB)
```

## Crew Execution

```bash
source .venv/bin/activate

python main.py research      # Phase 1: 시장 조사
python main.py planning      # Phase 2-4: 기획 (PRD/스펙/유저스토리)
python main.py architect     # 아키텍처 설계
python main.py frontend      # 프론트엔드 설계
python main.py qa            # QA 테스트 전략
python main.py infra         # 인프라 CI/CD
python main.py data          # 데이터 파이프라인
python main.py docs          # 문서 감사
python main.py review        # 외부인사 리뷰
```

## Agents (11)

| Agent | Role | Crew |
|-------|------|------|
| Strategy Manager | 시장조사, 경쟁사 분석 | ResearchCrew |
| Product Manager | PRD, 기능 기획 | PlanningCrew |
| Project Manager | 스프린트 계획, 태스크 분배 | PlanningCrew |
| Fullstack Architect | 시스템 아키텍처 설계 | ArchitectCrew |
| Backend Senior | API 서버, AI/LLM 파이프라인 | ArchitectCrew |
| Frontend Senior | FE 아키텍처, 컴포넌트 설계 | FrontendCrew |
| QA Engineer | 테스트 전략, 테스트 케이스 | QACrew |
| Infrastructure Expert | CI/CD, 배포 전략 | InfraCrew |
| Data Engineer | 스키마 최적화, 데이터 파이프라인 | DataCrew |
| Doc Secretary | 문서 관리, CHANGELOG 동기화 | DocumentationCrew |
| External Advisor | 외부 관점 리뷰, Devil's Advocate | ReviewCrew |

## Project Structure

```
agents/               # Agent YAML definitions (11, SSOT)
src/
  config/llm.py       # Ollama LLM config (2-Tier)
  crews/              # 11 Crews (each: config/agents.yaml + tasks.yaml + crew.py)
scripts/              # Utilities (sync-agents.sh)
.claude/agents/       # Claude Code sub-agents
main.py               # CrewAI entry point
output/               # Crew execution results (gitignored)
```

## Security

`.githooks/pre-commit` 훅이 커밋 시 민감 파일과 시크릿 패턴을 자동 차단합니다.

```bash
# 훅 활성화 (최초 1회)
git config core.hooksPath .githooks
```

## Related Repositories

- [AI-Interview-web](https://github.com/bongseoksa/AI-Interview-web) - Frontend (Next.js 16)
- [AI-Interview-server](https://github.com/bongseoksa/AI-Interview-server) - Backend (Python)
