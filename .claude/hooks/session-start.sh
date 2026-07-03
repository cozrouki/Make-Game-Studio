#!/usr/bin/env bash
# session-start.sh — 세션 시작 시 컨텍스트 요약 출력

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_NAME="$(basename "$REPO_ROOT")"
ACTIVE_FILE="$REPO_ROOT/production/session-state/active.md"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
printf "║  %-50s║\n" "${PROJECT_NAME} — 세션 시작"
echo "╚══════════════════════════════════════════════════════╝"

# ── 1. 브랜치 & 최근 커밋 ────────────────────────────────────
if command -v git &>/dev/null && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
    BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)
    echo ""
    echo "📌 Git 브랜치: $BRANCH"
    echo ""
    echo "🕐 최근 커밋 (3개):"
    git -C "$REPO_ROOT" log --oneline -3 2>/dev/null | sed 's/^/   /'
fi

# ── 2. 활성 세션 상태 ─────────────────────────────────────────
echo ""
if [ -f "$ACTIVE_FILE" ]; then
    STATUS_BLOCK=$(sed -n '/<!-- STATUS -->/,/<!-- \/STATUS -->/p' "$ACTIVE_FILE" 2>/dev/null)

    if [ -n "$STATUS_BLOCK" ]; then
        echo "🎮 이전 세션 상태:"
        echo "$STATUS_BLOCK" | grep -v "<!--" | grep -v "^$" | sed 's/^/   /'
    fi

    NEXT=$(awk '/\*\*다음 할 것\*\*/{found=1; next} found && /^$/{exit} found{print}' "$ACTIVE_FILE" 2>/dev/null | head -5)
    if [ -n "$NEXT" ]; then
        echo ""
        echo "➡️  다음 할 것:"
        echo "$NEXT" | sed 's/^/   /'
    fi

    BLOCKER=$(awk '/\*\*미완료 \/ 블로커\*\*/{found=1; next} found && /^---/{exit} found && /^$/{exit} found{print}' "$ACTIVE_FILE" 2>/dev/null | grep -v "^$" | head -5)
    if [ -n "$BLOCKER" ]; then
        echo ""
        echo "⚠️  미완료 / 블로커:"
        echo "$BLOCKER" | sed 's/^/   /'
    fi
else
    echo "🎮 세션 상태: active.md 없음"
fi

# ── 3. 개발 단계 ──────────────────────────────────────────────
STAGE_FILE="$REPO_ROOT/production/stage.txt"
if [ -f "$STAGE_FILE" ]; then
    STAGE=$(cat "$STAGE_FILE" | tr -d '[:space:]')
    echo ""
    echo "🚀 개발 단계: $STAGE"
fi

# ── 4. 스프린트/마일스톤 (Game-Studios) ──────────────────────
if [ -d "$REPO_ROOT/production/sprints" ]; then
    LATEST_SPRINT=$(ls -t "$REPO_ROOT"/production/sprints/sprint-*.md 2>/dev/null | head -1)
    [ -n "$LATEST_SPRINT" ] && echo "🏃 진행 스프린트: $(basename "$LATEST_SPRINT" .md)"
fi
if [ -d "$REPO_ROOT/production/milestones" ]; then
    LATEST_MS=$(ls -t "$REPO_ROOT"/production/milestones/*.md 2>/dev/null | head -1)
    [ -n "$LATEST_MS" ] && echo "🎯 마일스톤: $(basename "$LATEST_MS" .md)"
fi

# ── 5. 오픈 버그 (Game-Studios) ──────────────────────────────
BUG_COUNT=$(find "$REPO_ROOT/tests" "$REPO_ROOT/production" -name "BUG-*.md" 2>/dev/null | wc -l | tr -d ' ')
[ "$BUG_COUNT" -gt 0 ] && echo "🐛 오픈 버그: ${BUG_COUNT}개"

# ── 6. 코드 헬스 (Game-Studios, Assets/ 한정) ────────────────
if [ -d "$REPO_ROOT/Assets" ]; then
    TODO=$(grep -rI --include="*.cs" -c "TODO" "$REPO_ROOT/Assets" 2>/dev/null | awk -F: '{s+=$2}END{print s+0}')
    FIXME=$(grep -rI --include="*.cs" -c "FIXME" "$REPO_ROOT/Assets" 2>/dev/null | awk -F: '{s+=$2}END{print s+0}')
    echo "🩺 코드 헬스: TODO ${TODO}개 / FIXME ${FIXME}개"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
