#!/usr/bin/env bash
# studio-write-guard.sh — 스튜디오 역할 세션이 자기 쓰기 영역 밖을 고치려 하면 막는다 (PreToolUse: Write|Edit|MultiEdit|NotebookEdit)
# 커밋 때의 영역 검사(studio.py commit · audit)를 쓰기 순간으로 앞당긴 장치다 (하네스: 결정적 제약).
# 역할은 launch 가 남긴 세션 ID(production/studio/locks/launch.json) 또는 STUDIO_ROLE 로 정한다. 역할을 모르면 막지 않는다.
# 스튜디오 모드가 아닌 프로젝트에서는 파일 하나 확인하고 끝난다.

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[ -f "$ROOT/production/studio/roster.json" ] || exit 0
[ -f "$ROOT/.agent/tools/studio/studio.py" ] || exit 0

# 가드가 쓰는 표준 입력(훅 JSON)을 그대로 넘긴다. 종료 코드 2 = 차단 (stderr 가 에이전트에게 전달됨)
python "$ROOT/.agent/tools/studio/studio.py" --root "$ROOT" guard --hook
