#!/usr/bin/env bash
# session-start.sh — 세션 시작 시 컨텍스트 요약 출력 (한국어 fork)
#
# 상류(Claude-Code-Game-Studios v1.2.0) session-start.sh 의 판정을 가져오고 출력은 한국어로 한다.
#   상류에서 가져온 것: 프로젝트 루트 판정 · project.yaml 스키마 검사 · 단계 출처 불일치 경고 ·
#                       엔진별 코드 루트(resolve_code_root) · 엔진 레퍼런스 불일치 경고 · CHECKPOINT 미리보기
#   이 템플릿 것:       배너 · active.md 의 <!-- STATUS --> 블록 · 다음 할 것 · 블로커 · 엔진 표시
#   빼 둔 것:           update-check (상류 템플릿 릴리스 알림 — 이 템플릿 사용자에게는 맞지 않는다)
# 10초 예산 안에 끝나야 한다 — 끊기면 세션 상태가 컨텍스트에 닿지 않는다. 읽기는 모두 줄 수 제한.

if [ -f "project.yaml" ] || { [ -d ".claude" ] && [ "${PWD##*/}" != ".claude" ]; }; then
  REPO_ROOT="$PWD"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ] && case "${CLAUDE_PROJECT_DIR%/}" in */.claude|*\\.claude) false ;; *) true ;; esac; then
  REPO_ROOT="$CLAUDE_PROJECT_DIR"
else
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
fi
cd "$REPO_ROOT" 2>/dev/null || true

PROJECT_NAME="$(basename "$REPO_ROOT")"
ACTIVE_FILE="production/session-state/active.md"
[ -f .claude/hooks/yaml-helper.sh ] && . .claude/hooks/yaml-helper.sh 2>/dev/null

echo ""
echo "╔══════════════════════════════════════════════════════╗"
printf "║  %-50s║\n" "${PROJECT_NAME} — 세션 시작"
echo "╚══════════════════════════════════════════════════════╝"

# ── 1. 브랜치 & 최근 커밋 ────────────────────────────────────
BRANCH=""
if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    echo ""
    echo "📌 Git 브랜치: $BRANCH"
    echo ""
    echo "🕐 최근 커밋 (3개):"
    git log --oneline -3 2>/dev/null | sed 's/^/   /'
fi

# ── 2. 엔진 · 설정 검사 ───────────────────────────────────────
ENGINE=""
if [ -f project.yaml ] && command -v get_yaml_key >/dev/null 2>&1; then
    ENGINE=$(get_yaml_key project.yaml engine.name 2>/dev/null)
    EVER=$(get_yaml_key project.yaml engine.version 2>/dev/null)
    [ -n "$ENGINE" ] && echo "" && echo "🛠️  엔진: $ENGINE ${EVER}"
fi
if [ -z "$ENGINE" ]; then
    echo ""
    echo "🛠️  엔진: 미설정 — 기존 프로젝트면 /ko-setup-engine, 새 프로젝트면 /setup-engine"
fi
if command -v validate_local_yaml_base >/dev/null 2>&1; then
    BASE_ERR=$(validate_local_yaml_base 2>&1) || echo "[!] $BASE_ERR"
    for y in project.yaml project.local.yaml; do
        if [ -f "$y" ]; then
            ERRS=$(validate_yaml_enum "$y" 2>&1)
            [ -n "$ERRS" ] && echo "[!] $y 스키마 오류:" && echo "$ERRS" | sed 's/^/    /'
        fi
    done
fi
# 엔진 레퍼런스 import 줄과 설정 엔진이 다르면 매 세션 다른 엔진 문서를 읽는다 (관찰만 — 고치지 않는다)
if [ -n "$ENGINE" ] && [ -f CLAUDE.md ]; then
    ERI=$(grep -m1 -E '^@docs/engine-reference/[a-z]+/VERSION\.md' CLAUDE.md 2>/dev/null \
          | sed -n 's|^@docs/engine-reference/\([a-z]*\)/VERSION\.md.*|\1|p')
    CFG=$(printf '%s' "$ENGINE" | awk '{print tolower($1)}')
    if [ -n "$ERI" ] && [ "$ERI" != "$CFG" ]; then
        echo "!! 엔진 레퍼런스 불일치: project.yaml=$CFG, CLAUDE.md import=$ERI — /setup-engine 재실행 또는 ENGINE-REFERENCE-IMPORT 줄 수정"
    fi
fi

# ── 3. 활성 세션 상태 ─────────────────────────────────────────
echo ""
if [ -f "$ACTIVE_FILE" ]; then
    STATUS_BLOCK=$(sed -n '/<!-- STATUS -->/,/<!-- \/STATUS -->/p' "$ACTIVE_FILE" 2>/dev/null | head -40)
    CHECKPOINT=$(sed -n '/^[[:space:]]*<!-- CHECKPOINT -->[[:space:]]*$/,/^[[:space:]]*<!-- \/CHECKPOINT -->[[:space:]]*$/p' "$ACTIVE_FILE" 2>/dev/null \
                 | grep -v 'CHECKPOINT -->' | head -25)

    # 3,000자 상한: 훅 출력이 10,000자를 넘으면 미리보기로 잘려 아래 줄(다음 할 것 · 블로커)이 사라진다
    cap() { awk '{ c += length($0) + 1; if (c > 3000) { print "   … (잘림 — active.md 를 읽는다)"; exit } print }'; }
    if [ -n "$STATUS_BLOCK" ]; then
        echo "🎮 이전 세션 상태:"
        echo "$STATUS_BLOCK" | grep -v "<!--" | grep -v "^$" | sed 's/^/   /' | cap
    elif [ -n "$CHECKPOINT" ]; then
        # 상류 스킬은 .claude/docs/templates/session-state.md 의 CHECKPOINT 블록을 쓴다
        echo "🎮 이전 세션 체크포인트:"
        echo "$CHECKPOINT" | sed 's/^/   /' | cap
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
    TOTAL=$(wc -l < "$ACTIVE_FILE" | tr -d ' ')
    echo "   (active.md ${TOTAL}줄 — 이어서 하려면 파일 전체를 읽는다)"
else
    echo "🎮 세션 상태: active.md 없음"
fi

# ── 4. 개발 단계 (project.yaml 이 정본, stage.txt 는 예전 미러) ──
STAGE_YAML=""
[ -f project.yaml ] && command -v get_yaml_key >/dev/null 2>&1 && STAGE_YAML=$(get_yaml_key project.yaml project.stage 2>/dev/null)
STAGE_TXT=""
[ -f production/stage.txt ] && STAGE_TXT=$(head -1 production/stage.txt | tr -d '\r' | sed 's/[[:space:]]*$//')
STAGE="${STAGE_YAML:-$STAGE_TXT}"
[ -n "$STAGE" ] && echo "" && echo "🚀 개발 단계: $STAGE"
if [ -n "$STAGE_YAML" ] && [ -n "$STAGE_TXT" ] && [ "$STAGE_YAML" != "$STAGE_TXT" ]; then
    echo "[!] 단계 출처 불일치: project.yaml=$STAGE_YAML, production/stage.txt=$STAGE_TXT — 단계는 /gate-check 만 바꾼다 (손으로 맞추지 말 것)"
fi

# ── 5. 스프린트 · 마일스톤 · 버그 ─────────────────────────────
LATEST_SPRINT=$(ls -t production/sprints/sprint-*.md 2>/dev/null | head -1)
[ -n "$LATEST_SPRINT" ] && echo "🏃 진행 스프린트: $(basename "$LATEST_SPRINT" .md)"
LATEST_MS=$(ls -t production/milestones/*.md 2>/dev/null | head -1)
[ -n "$LATEST_MS" ] && echo "🎯 마일스톤: $(basename "$LATEST_MS" .md)"
if [ -f .claude/scripts/bug-stats.sh ]; then
    BUG_OPEN=$(bash .claude/scripts/bug-stats.sh --root . tests/playtest production 2>/dev/null | awk -F'\t' '$1 == "open" { print $2 }')
    [ -n "$BUG_OPEN" ] && [ "$BUG_OPEN" -gt 0 ] 2>/dev/null && echo "🐛 오픈 버그: ${BUG_OPEN}개"
fi

# ── 6. 코드 헬스 (엔진별 코드 루트 — Unity Assets/ · Godot src/ · Unreal Source/) ──
CODE_ROOT=""
command -v resolve_code_root >/dev/null 2>&1 && CODE_ROOT=$(resolve_code_root 2>/dev/null | cut -f1)
if [ -n "$CODE_ROOT" ] && [ -d "$CODE_ROOT" ]; then
    SRC=(--include='*.gd' --include='*.cs' --include='*.cpp' --include='*.h' --include='*.hpp')
    TODO=$(grep -rI "${SRC[@]}" "TODO" "$CODE_ROOT/" 2>/dev/null | wc -l | tr -d ' ')
    FIXME=$(grep -rI "${SRC[@]}" "FIXME" "$CODE_ROOT/" 2>/dev/null | wc -l | tr -d ' ')
    echo "🩺 코드 헬스: TODO ${TODO}개 / FIXME ${FIXME}개 (${CODE_ROOT}/)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
exit 0
