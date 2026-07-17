#!/bin/bash
# sync-agents.sh
# orchestrator의 YAML 정의를 기반으로 각 레포의 .claude/agents/ 서브에이전트를 확인한다.
# 실제 .md 파일은 수동으로 관리하며, 이 스크립트는 배포 현황을 확인하는 용도.

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$BASE_DIR")"

WEB_AGENTS="$PARENT_DIR/AI-Interview-web/.claude/agents"
SERVER_AGENTS="$PARENT_DIR/AI-Interview-server/.claude/agents"
ORCH_AGENTS="$BASE_DIR/.claude/agents"

echo "=== 에이전트 배포 현황 ==="
echo ""

echo "[orchestrator] $ORCH_AGENTS"
if [ -d "$ORCH_AGENTS" ]; then
  ls -1 "$ORCH_AGENTS"/*.md 2>/dev/null | while read f; do echo "  - $(basename "$f")"; done
else
  echo "  (디렉토리 없음)"
fi
echo ""

echo "[web] $WEB_AGENTS"
if [ -d "$WEB_AGENTS" ]; then
  ls -1 "$WEB_AGENTS"/*.md 2>/dev/null | while read f; do echo "  - $(basename "$f")"; done
else
  echo "  (디렉토리 없음)"
fi
echo ""

echo "[server] $SERVER_AGENTS"
if [ -d "$SERVER_AGENTS" ]; then
  ls -1 "$SERVER_AGENTS"/*.md 2>/dev/null | while read f; do echo "  - $(basename "$f")"; done
else
  echo "  (디렉토리 없음)"
fi
echo ""

echo "=== YAML 원본 (orchestrator/agents/) ==="
ls -1 "$BASE_DIR/agents/"*.yaml 2>/dev/null | while read f; do echo "  - $(basename "$f")"; done
