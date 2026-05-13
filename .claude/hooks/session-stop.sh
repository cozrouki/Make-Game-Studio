#!/usr/bin/env bash
# session-stop.sh — 세션 종료 시 체크리스트 출력 (TikiProject)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ACTIVE_FILE="$REPO_ROOT/production/session-state/active.md"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║            TikiProject — 세션 종료                    ║"
echo "╚══════════════════════════════════════════════════════╝"

# ── active.md 업데이트 상태 확인 ─────────────────────────────
if [ -f "$ACTIVE_FILE" ]; then
    LAST_UPDATED=$(grep "_마지막 업데이트:" "$ACTIVE_FILE" | tail -1 | sed 's/.*_마지막 업데이트: //' | tr -d '_')
    TODAY=$(date '+%Y-%m-%d')
    echo ""
    echo "📋 active.md 마지막 업데이트: ${LAST_UPDATED:-'없음'}"

    if [[ "$LAST_UPDATED" != "$TODAY"* ]]; then
        echo ""
        echo "⚠️  active.md가 오늘 업데이트되지 않았습니다."
        echo "   세션 종료 전 업데이트하세요:"
        echo "   - 완료된 항목 / 다음 할 것 / 미완료·블로커"
    fi
fi

# ── 이번 세션 변경 요약 ───────────────────────────────────────
if command -v git &>/dev/null && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
    echo ""
    echo "📝 변경된 파일:"
    git -C "$REPO_ROOT" status --short 2>/dev/null | head -10 | sed 's/^/   /'

    COMMIT_COUNT=$(git -C "$REPO_ROOT" log --oneline --since="8 hours ago" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$COMMIT_COUNT" -gt 0 ]; then
        echo ""
        echo "✅ 이번 세션 커밋 ($COMMIT_COUNT개):"
        git -C "$REPO_ROOT" log --oneline --since="8 hours ago" 2>/dev/null | sed 's/^/   /'
    fi
fi

# ── 세션 아카이브 (Game-Studios) ─────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SESSION_LOG_DIR="$REPO_ROOT/production/session-logs"
mkdir -p "$SESSION_LOG_DIR" 2>/dev/null
if [ -f "$ACTIVE_FILE" ]; then
    {
        echo "## 아카이브된 세션 상태: $TIMESTAMP"
        cat "$ACTIVE_FILE"
        echo ""
        echo "---"
        echo ""
    } >> "$SESSION_LOG_DIR/session-log.md" 2>/dev/null
    echo ""
    echo "📦 세션 로그: production/session-logs/session-log.md"
fi

# ── 체크리스트 ────────────────────────────────────────────────
echo ""
echo "📌 세션 종료 체크리스트:"
echo "   [ ] active.md — 다음 할 것, 미완료/블로커 업데이트"
echo "   [ ] doc/work_log.md — 작업 내용 기록 (게임 태그 포함)"
echo "   [ ] doc/{GameName}/task.md — 태스크 현황 업데이트"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
