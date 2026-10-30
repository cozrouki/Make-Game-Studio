#!/usr/bin/env bash
# session-stop.sh — 세션 종료 시 체크리스트 출력 (한국어 fork — 상류 v1.2.0 의 해시 중복 방지만 가져옴)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_NAME="$(basename "$REPO_ROOT")"
ACTIVE_FILE="$REPO_ROOT/production/session-state/active.md"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
printf "║  %-50s║\n" "${PROJECT_NAME} — 세션 종료"
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
# Stop 은 매 턴 실행된다 — active.md 가 바뀌었을 때만 덧붙인다 (상류 v1.2.0 의 해시 중복 방지).
# 읽는 도구가 없는 사람용 기록이라 월별 파일로 나누고 최근 KEEP_MONTHS 개월만 남긴다 (하나에 쌓으면 수백 MB 가 된다).
# 오래 남길 이력은 git 커밋 · doc/work_log.md 가 맡는다.
KEEP_MONTHS=3
MONTH_LOG="$SESSION_LOG_DIR/session-log-$(date +%Y-%m).md"
HASH_FILE="$SESSION_LOG_DIR/.state.hash"
if [ -f "$ACTIVE_FILE" ]; then
    STATE_HASH=$(git -C "$REPO_ROOT" hash-object -- "$ACTIVE_FILE" 2>/dev/null)
    if [ -z "$STATE_HASH" ] || [ "$STATE_HASH" != "$(cat "$HASH_FILE" 2>/dev/null)" ]; then
        {
            echo "## 아카이브된 세션 상태: $TIMESTAMP"
            cat "$ACTIVE_FILE"
            echo ""
            echo "---"
            echo ""
        } >> "$MONTH_LOG" 2>/dev/null
        [ -n "$STATE_HASH" ] && printf '%s\n' "$STATE_HASH" > "$HASH_FILE" 2>/dev/null
        echo ""
        echo "📦 세션 로그: production/session-logs/$(basename "$MONTH_LOG")"
    fi
fi
# 보관 기간이 지난 월별 로그 정리 — 파일 이름(YYYY-MM)순으로 최근 KEEP_MONTHS 개만 남긴다
OLD_LOGS=$(ls -1 "$SESSION_LOG_DIR"/session-log-[0-9][0-9][0-9][0-9]-[0-9][0-9].md 2>/dev/null | sort -r | tail -n +$((KEEP_MONTHS + 1)))
if [ -n "$OLD_LOGS" ]; then
    echo "$OLD_LOGS" | while IFS= read -r old; do rm -f -- "$old"; done
    echo "🧹 오래된 세션 로그 정리: $(echo "$OLD_LOGS" | xargs -n1 basename | tr '\n' ' ')"
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
