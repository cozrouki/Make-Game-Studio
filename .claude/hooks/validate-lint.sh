#!/bin/bash
# validate-lint.sh — PreToolUse(Bash|PowerShell): git commit 직전 엔진별 정적 검사 (이 템플릿 자체 훅)
#
# 상류 validate-commit.sh 는 그대로 미러하고, 엔진별 검사만 여기서 한다.
#   Unity  → .agent/tools/lint/unity_lint.py --staged (gameplay-code.md 규칙 UL001~)
#            lint.config.json 의 blocking 규칙만 커밋을 막고(exit 2) 나머지는 경고
#   Godot · Unreal → 아직 정적 검사기가 없다. 해당 소스가 스테이징되면 "검사 안 함" 을 알린다
# 엔진 판정: project.yaml engine.name → 없으면 프로젝트 표지 파일 (.claude/docs/engine-layers.md)

if [ -f "project.yaml" ] || { [ -d ".claude" ] && [ "${PWD##*/}" != ".claude" ]; }; then
  ROOT="$PWD"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ]; then
  ROOT="$CLAUDE_PROJECT_DIR"
else
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
fi
cd "$ROOT" 2>/dev/null || exit 0

INPUT=$(cat)
# git commit 이 아닌 호출은 바로 통과 (모든 Bash 호출에서 돈다)
case "$INPUT" in *'"tool_input"'*[Gg][Ii][Tt]*[Cc][Oo][Mm][Mm][Ii][Tt]*) ;; *) exit 0 ;; esac

ENGINE=""
if [ -f project.yaml ]; then
  ENGINE=$(awk '/^engine:/ { e = 1; next } e && /^[^[:space:]#]/ { exit }
                e && /^[[:space:]]+name:/ { sub(/^[[:space:]]+name:[[:space:]]*/, ""); gsub(/["'"'"']/, "");
                                            split($0, w, /[[:space:]#]/); print w[1]; exit }' project.yaml 2>/dev/null \
           | tr '[:upper:]' '[:lower:]')
fi
case "$ENGINE" in unity|godot|unreal) ;; *)
  if [ -f ProjectSettings/ProjectVersion.txt ]; then ENGINE=unity
  elif [ -f project.godot ]; then ENGINE=godot
  elif ls ./*.uproject >/dev/null 2>&1; then ENGINE=unreal
  else ENGINE=""
  fi ;;
esac

STAGED=$(git diff --cached --name-only 2>/dev/null)
[ -z "$STAGED" ] && exit 0

case "$ENGINE" in
  unity)
    echo "$STAGED" | grep -qE '\.cs$' || exit 0
    LINT=".agent/tools/lint/unity_lint.py"
    if [ ! -f "$LINT" ]; then
      echo "unity-lint 검사 안 함: $LINT 없음" >&2
      exit 0
    fi
    for cmd in python python3 py; do
      if command -v "$cmd" >/dev/null 2>&1; then
        LINT_OUT=$("$cmd" "$LINT" --staged 2>&1)
        LINT_CODE=$?
        if [ $LINT_CODE -eq 1 ]; then
          echo "BLOCKED: unity-lint 차단 규칙 위반 (오탐이면 그 줄에 // unity-lint: ignore ULxxx 와 이유)" >&2
          echo "$LINT_OUT" >&2
          exit 2
        fi
        if echo "$LINT_OUT" | grep -q ': UL'; then
          echo "=== unity-lint 경고 ===" >&2
          echo "$LINT_OUT" | grep -E ': UL' | head -20 >&2
        fi
        exit 0
      fi
    done
    echo "unity-lint 검사 안 함: python 없음" >&2
    ;;
  godot)
    echo "$STAGED" | grep -qE '\.(gd|cs)$' && \
      echo "정적 검사 안 함: Godot 용 검사기는 아직 없다 (gameplay-code.md Godot 절을 리뷰에서 확인)" >&2
    ;;
  unreal)
    echo "$STAGED" | grep -qE '\.(cpp|h)$' && \
      echo "정적 검사 안 함: Unreal 용 검사기는 아직 없다 (gameplay-code.md Unreal 절을 리뷰에서 확인)" >&2
    ;;
  *)
    echo "$STAGED" | grep -qE '\.(cs|gd|cpp|h)$' && \
      echo "정적 검사 안 함: 엔진을 판정하지 못함 (project.yaml engine.name 없음 · 엔진 표지 파일 없음) — /ko-setup-engine" >&2
    ;;
esac
exit 0
