#!/usr/bin/env bash
# studio-pause-notice.sh — 스튜디오 정지(PAUSED)를 작업 중인 세션에 바로 알린다 (PostToolUse)
# 티켓 하나를 처리하는 동안에는 inbox 를 보지 않으므로, 정지(사용량 가드 · 디렉터)를 도구 호출 직후에 주입한다.
# 세션마다 정지 1건당 한 번만 알린다. 정지가 없으면 파일 검사 하나로 끝난다.

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PAUSED="$ROOT/production/studio/PAUSED"
[ -f "$PAUSED" ] || exit 0

INPUT=$(cat)
SID=$(printf '%s' "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
[ -n "$SID" ] || SID="unknown"

SEEN_DIR="$ROOT/production/studio/locks/pause-seen"
STAMP=$(cksum < "$PAUSED" | cut -d' ' -f1)
MARK="$SEEN_DIR/$SID"
if [ -f "$MARK" ] && [ "$(cat "$MARK")" = "$STAMP" ]; then
    exit 0
fi
mkdir -p "$SEEN_DIR"
echo "$STAMP" > "$MARK"

# JSON 문자열에 넣을 수 없는 문자 제거
REASON=$(head -1 "$PAUSED" | tr -d '"\\\r\t')

MSG="[studio] ⏸ 스튜디오 전체 정지 — ${REASON} | 스튜디오 역할 세션이면: 지금 단계를 안전한 지점에서 마치고, 진행 중 티켓에 studio.py update <id> --by <역할> --note '인계: 한 일 / 남은 일 / 미커밋 파일 / 재개 첫 단계' 를 남긴 뒤 멈춘다. 새 티켓에 착수하지 않고, 미완성 작업은 커밋하지 않는다. | 디렉터 세션이면: 사용자에게 알리고 production/studio/HANDOFF.md 를 확인한다. | 상세: .agent/tools/studio/README.md 의 사용량 한도 절"

printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' "$MSG"
