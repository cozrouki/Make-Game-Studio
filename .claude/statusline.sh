#!/usr/bin/env bash
# statusline.sh — Claude Code 터미널 상태줄 (TikiProject)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE_FILE="$REPO_ROOT/production/stage.txt"
ACTIVE_FILE="$REPO_ROOT/production/session-state/active.md"

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

echo "$OUTPUT"
