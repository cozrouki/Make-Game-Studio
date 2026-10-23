#!/usr/bin/env bash
# statusline.sh — Claude Code 터미널 상태줄

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE_FILE="$REPO_ROOT/production/stage.txt"
ACTIVE_FILE="$REPO_ROOT/production/session-state/active.md"
STUDIO_PY="$REPO_ROOT/.agent/tools/studio/studio.py"

# ── Claude 주간 사용량 가드 (스튜디오 모드) ──────────────────
# stdin JSON 의 rate_limits.seven_day 를 studio.py usage 에 넘긴다. 임계값(usageGuard) 이상이면 전체 정지 + 인계 기록.
INPUT=$(cat)
USAGE=""
if [ -f "$STUDIO_PY" ] && [ -d "$REPO_ROOT/production/studio" ]; then
    USAGE=$(printf '%s' "$INPUT" | python "$STUDIO_PY" --root "$REPO_ROOT" usage --stdin 2>/dev/null | head -1)
    [ "$USAGE" = "기록 안 함" ] && USAGE=""
fi
if [ -f "$REPO_ROOT/production/studio/PAUSED" ]; then
    USAGE="⏸ 스튜디오 정지${USAGE:+ · $USAGE}"
fi

# ── 개발 단계 ────────────────────────────────────────────────
if [ -f "$STAGE_FILE" ]; then
    STAGE=$(cat "$STAGE_FILE" | tr -d '[:space:]' | tr -d '\n')
else
    STAGE="Production"
fi

# ── 활성 세션 상태 ────────────────────────────────────────────
GAME=""
FEATURE=""
TASK=""

if [ -f "$ACTIVE_FILE" ]; then
    GAME=$(sed -n '/<!-- STATUS -->/,/<!-- \/STATUS -->/p' "$ACTIVE_FILE" | grep "^게임:" | sed 's/게임: *//')
    FEATURE=$(sed -n '/<!-- STATUS -->/,/<!-- \/STATUS -->/p' "$ACTIVE_FILE" | grep "^Feature:" | sed 's/Feature: *//')
    TASK=$(sed -n '/<!-- STATUS -->/,/<!-- \/STATUS -->/p' "$ACTIVE_FILE" | grep "^Task:" | sed 's/Task: *//')
fi

# ── 출력 조합 ────────────────────────────────────────────────
OUTPUT="$STAGE"

if [ -n "$GAME" ] && [ "$GAME" != "-" ]; then
    OUTPUT="$OUTPUT | $GAME"
    if [ -n "$FEATURE" ] && [ "$FEATURE" != "-" ]; then
        OUTPUT="$OUTPUT > $FEATURE"
        if [ -n "$TASK" ] && [ "$TASK" != "-" ]; then
            OUTPUT="$OUTPUT > $TASK"
        fi
    fi
fi

if [ -n "$USAGE" ]; then
    OUTPUT="$OUTPUT | $USAGE"
fi

echo "$OUTPUT"
