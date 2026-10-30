#!/usr/bin/env bash
# ko-setup-engine 실측 스크립트 — Godot 프로젝트 루트(project.godot 가 있는 곳)에서 실행.
# 사용: bash .claude/skills/ko-setup-engine/measure-godot.sh [코드-루트 ...]
#   코드-루트 = 프로젝트 자체 스크립트 폴더 (예: src). addons/ 는 서드파티라 명명 통계에서 뺀다.
#   생략하면 최상위 폴더 후보(.gd · .cs 수)만 출력하고 종료한다(exit 2).
# 출력: 마크다운 실측 리포트(stdout). 파일을 쓰지 않는다. 측정하지 못한 항목은 "측정 안 함" 으로 적는다.

set -u

if [ ! -f "project.godot" ]; then
  echo "ERROR: Godot 프로젝트 루트가 아님 (project.godot 없음)" >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "## 코드 루트 후보 (최상위 폴더, .gd / .cs 파일 수 — addons/ · .godot/ 제외)"
  for d in */; do
    case "$d" in addons/|.godot/) continue ;; esac
    g=$(find "$d" -name '*.gd' 2>/dev/null | wc -l)
    c=$(find "$d" -name '*.cs' 2>/dev/null | wc -l)
    [ $((g + c)) -gt 0 ] && printf '%6d gd %6d cs  %s\n' "$g" "$c" "${d%/}"
  done | sort -rn
  echo
  echo "→ 프로젝트 자체 코드 폴더를 인수로 다시 실행하세요 (addons/ 제외)."
  exit 2
fi

ROOTS=("$@")
for r in "${ROOTS[@]}"; do
  [ -d "$r" ] || { echo "ERROR: 폴더 없음: $r" >&2; exit 1; }
done

# project.godot 는 [섹션] 아래 키를 둔다 (예: [physics] 의 3d/physics_engine). ini <섹션> <키>
ini() {
  awk -v sec="[$1]" -v key="$2" '
    { sub(/\r$/, "") }
    /^\[/ { insec = ($0 == sec); next }
    insec && index($0, key "=") == 1 { v = substr($0, length(key) + 2); gsub(/^"|"$/, "", v); print v; exit }
  ' project.godot 2>/dev/null
}
gd() { grep -rhE "$1" --include='*.gd' "${ROOTS[@]}" 2>/dev/null | wc -l | tr -d ' '; }
gdfiles() { grep -rlE "$1" --include='*.gd' --include='*.tscn' "${ROOTS[@]}" 2>/dev/null | wc -l | tr -d ' '; }
findn() { find "${ROOTS[@]}" "$@" 2>/dev/null | wc -l | tr -d ' '; }

echo "# ko-setup-engine 실측 리포트 (Godot)"
echo
echo "- 코드 루트: ${ROOTS[*]}"
echo "- .gd 파일: $(findn -name '*.gd') · .cs 파일: $(findn -name '*.cs') · .tscn: $(findn -name '*.tscn') · .tres: $(findn -name '*.tres')"
echo

echo "## 엔진"
feat=$(ini application 'config/features')
echo "- config/features: ${feat:-없음}"
echo "- 버전 판정: $(echo "$feat" | grep -oE '[0-9]+\.[0-9]+' | head -1)"
echo "- 렌더러 (rendering/renderer/rendering_method): $(ini rendering 'renderer/rendering_method' || true)"
[ -z "$(ini rendering 'renderer/rendering_method')" ] && echo "  (설정 없음 = 기본 Forward+)"
echo "- 3D 물리 엔진 (physics/3d/physics_engine): $(ini physics '3d/physics_engine')"
[ -z "$(ini physics '3d/physics_engine')" ] && echo "  (설정 없음 = 버전 기본값 — docs/engine-reference/godot/modules/physics.md 확인)"
echo "- .NET (C#) 사용: $( [ -n "$(ls ./*.csproj 2>/dev/null)" ] && echo '예 (*.csproj 있음)' || echo '아니오')"
echo

echo "## 2D / 3D 판정 근거"
echo "- 2D 노드 사용 파일 (Node2D · CharacterBody2D · RigidBody2D · Sprite2D · TileMap): $(gdfiles '(Node2D|CharacterBody2D|RigidBody2D|Sprite2D|TileMap)')"
echo "- 3D 노드 사용 파일 (Node3D · CharacterBody3D · RigidBody3D · MeshInstance3D): $(gdfiles '(Node3D|CharacterBody3D|RigidBody3D|MeshInstance3D)')"
echo

echo "## 애드온 · 오토로드"
if [ -d addons ]; then
  for a in addons/*/; do
    v=$(grep -m1 '^version=' "$a/plugin.cfg" 2>/dev/null | sed 's/version=//; s/"//g' | tr -d '\r')
    echo "- ${a%/}${v:+ = $v}"
  done
else
  echo "- addons/ 없음"
fi
echo "- 활성 플러그인 ([editor_plugins]): $(sed -n '/^\[editor_plugins\]/,/^\[/p' project.godot | grep -m1 '^enabled=' | tr -d '\r' || true)"
echo "- 오토로드:"
sed -n '/^\[autoload\]/,/^\[/p' project.godot | grep -E '^[A-Za-z_]' | tr -d '\r' | sed 's/^/    /'
echo

echo "## 입력 ([input] 액션)"
acts=$(sed -n '/^\[input\]/,/^\[/p' project.godot | grep -cE '^[A-Za-z_][A-Za-z0-9_]*=' )
echo "- 액션 수: $acts"
echo "- 키보드 이벤트: $(sed -n '/^\[input\]/,/^\[/p' project.godot | grep -o 'InputEventKey' | wc -l | tr -d ' ')"
echo "- 마우스 이벤트: $(sed -n '/^\[input\]/,/^\[/p' project.godot | grep -o 'InputEventMouseButton' | wc -l | tr -d ' ')"
echo "- 게임패드 이벤트: $(sed -n '/^\[input\]/,/^\[/p' project.godot | grep -oE 'InputEventJoypad(Button|Motion)' | wc -l | tr -d ' ')"
echo "- 터치 이벤트: $(sed -n '/^\[input\]/,/^\[/p' project.godot | grep -oE 'InputEventScreen(Touch|Drag)' | wc -l | tr -d ' ')"
echo

echo "## 명명 통계 (GDScript)"
echo "- class_name PascalCase: $(gd '^class_name\s+[A-Z][A-Za-z0-9]*')"
echo "- class_name 기타: $(( $(gd '^class_name\s+') - $(gd '^class_name\s+[A-Z][A-Za-z0-9]*') ))"
echo "- func snake_case: $(gd '^\s*(static\s+)?func\s+_?[a-z][a-z0-9_]*\s*\(')"
echo "- func camelCase: $(gd '^\s*(static\s+)?func\s+_?[a-z]+[A-Z]\w*\s*\(')"
echo "- signal 과거형(-ed): $(gd '^\s*signal\s+\w+ed\b')"
echo "- signal 전체: $(gd '^\s*signal\s+\w+')"
echo "- const UPPER_SNAKE: $(gd '^\s*const\s+[A-Z][A-Z0-9_]*\s*[:=]')"
echo "- const 기타: $(( $(gd '^\s*const\s+\w+') - $(gd '^\s*const\s+[A-Z][A-Z0-9_]*\s*[:=]') ))"
echo "- private 접두 _ 변수: $(gd '^\s*var\s+_[a-z]\w*')"
echo "- 정적 타입 var (var x: T): $(gd '^\s*(@\w+\s+)*var\s+\w+\s*:\s*[A-Za-z]')"
echo "- 타입 없는 var: $(gd '^\s*(@\w+\s+)*var\s+\w+\s*=')"
echo "- @onready: $(gd '@onready')"
echo "- _process 안 get_node · find_child 의심 줄: $(gd '(get_node|find_child)\(')"
echo

echo "## 파일 명명 샘플"
echo "- .gd 파일명 snake_case: $(find "${ROOTS[@]}" -name '*.gd' 2>/dev/null | sed 's|.*/||' | grep -cE '^[a-z0-9_]+\.gd$')  · PascalCase: $(find "${ROOTS[@]}" -name '*.gd' 2>/dev/null | sed 's|.*/||' | grep -cE '^[A-Z][A-Za-z0-9]*\.gd$')"
echo "- 씬 샘플:"
find "${ROOTS[@]}" -name '*.tscn' 2>/dev/null | sed 's|.*/||' | shuf -n 8 2>/dev/null | sed 's/^/    /'
echo

echo "## 셰이더"
echo "- .gdshader: $(findn -name '*.gdshader') · .gdshaderinc: $(findn -name '*.gdshaderinc') · VisualShader(.tres 내): $(gdfiles 'VisualShader')"
echo

echo "## 테스트"
if [ -f addons/gdUnit4/bin/GdUnitCmdTool.gd ]; then
  echo "- gdUnit4: 설치됨 (addons/gdUnit4)"
else
  echo "- gdUnit4: 없음 — /test-setup 권장"
fi
[ -d addons/gut ] && echo "- GUT: 설치됨 (addons/gut) — 상류 test-run.sh 는 gdUnit4 기준"
tests=$(find . -path ./addons -prune -o -path ./.godot -prune -o -name '*_test.gd' -print 2>/dev/null | wc -l | tr -d ' ')
echo "- *_test.gd 파일: $tests"
echo

echo "## 측정 안 함"
echo "- 대상 플랫폼 · 목표 fps (코드로 알 수 없음 — 질문으로 받는다)"
echo "- export_presets.cfg 의 플랫폼은 참고만 한다: $( [ -f export_presets.cfg ] && grep -E '^platform=' export_presets.cfg | sed 's/platform=//; s/"//g' | tr -d '\r' | sort -u | tr '\n' ' ' || echo '파일 없음')"
echo "- C# 명명 통계 (.cs 가 있으면 measure.sh 의 Unity 통계 항목을 참고하되 Godot 규칙은 PascalCase 메서드 · _camelCase 필드가 기본)"
