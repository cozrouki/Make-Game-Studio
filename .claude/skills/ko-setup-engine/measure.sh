#!/usr/bin/env bash
# ko-setup-engine 실측 스크립트 — Unity 프로젝트 루트에서 실행.
# 사용: bash .claude/skills/ko-setup-engine/measure.sh [코드-루트 ...]
#   코드-루트 = 프로젝트 자체 코드 폴더 (예: Assets/YourGame). 서드파티 에셋이 명명 통계를 오염시키지 않도록 지정한다.
#   생략하면 Assets/ 하위 후보 폴더(.cs 수)만 출력하고 종료한다(exit 2).
# 출력: 마크다운 실측 리포트(stdout). 파일을 쓰지 않는다.

set -u

if [ ! -f "ProjectSettings/ProjectVersion.txt" ]; then
  echo "ERROR: Unity 프로젝트 루트가 아님 (ProjectSettings/ProjectVersion.txt 없음) — Godot 은 measure-godot.sh, Unreal 은 measure-unreal.sh" >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "## 코드 루트 후보 (Assets/ 하위, .cs 파일 수)"
  for d in Assets/*/; do
    n=$(find "$d" -name '*.cs' 2>/dev/null | wc -l)
    [ "$n" -gt 0 ] && printf '%6d  %s\n' "$n" "${d%/}"
  done | sort -rn
  echo
  echo "→ 프로젝트 자체 코드 폴더를 인수로 다시 실행하세요 (서드파티 제외)."
  exit 2
fi

ROOTS=("$@")
for r in "${ROOTS[@]}"; do
  [ -d "$r" ] || { echo "ERROR: 폴더 없음: $r" >&2; exit 1; }
done

# .cs 내용에서 정규식 매치 줄 수
count() { grep -rhE "$1" --include='*.cs' "${ROOTS[@]}" 2>/dev/null | wc -l | tr -d ' '; }
# 정규식을 포함하는 .cs 파일 수
files() { grep -rlE "$1" --include='*.cs' "${ROOTS[@]}" 2>/dev/null | wc -l | tr -d ' '; }
findn() { find "${ROOTS[@]}" "$@" 2>/dev/null | wc -l | tr -d ' '; }

echo "# ko-setup-engine 실측 리포트"
echo
echo "- 코드 루트: ${ROOTS[*]}"
echo "- .cs 파일: $(findn -name '*.cs')"
echo

echo "## 엔진"
echo "- $(grep -m1 'm_EditorVersion:' ProjectSettings/ProjectVersion.txt | tr -d '\r')"
echo

echo "## 패키지 (Packages/manifest.json)"
if [ -f Packages/manifest.json ]; then
  grep -oE '"com\.[a-z0-9.-]+"\s*:\s*"[^"]+"' Packages/manifest.json \
    | grep -vE '"com\.unity\.(modules|feature)\.' \
    | sed -E 's/"([^"]+)"\s*:\s*"([^"]+)"/- \1 = \2/'
  rp="Built-in"
  grep -q '"com.unity.render-pipelines.universal"' Packages/manifest.json && rp="URP"
  grep -q '"com.unity.render-pipelines.high-definition"' Packages/manifest.json && rp="HDRP"
  echo "- **렌더 파이프라인 판정**: $rp"
else
  echo "- manifest.json 없음"
fi
echo

echo "## 물리 · AI"
echo "- Rigidbody 사용 파일: $(files '\bRigidbody\b')"
echo "- Rigidbody2D 사용 파일: $(files '\bRigidbody2D\b')"
echo "- CharacterController 사용 파일: $(files '\bCharacterController\b')"
echo "- NavMeshAgent 사용 파일: $(files '\bNavMeshAgent\b')"
echo "- ECS(Unity.Entities) 사용 파일: $(files 'using Unity\.Entities')"
echo

echo "## UI"
echo "- UI Toolkit(UnityEngine.UIElements) 파일: $(files 'using UnityEngine\.UIElements')"
echo "- uGUI(UnityEngine.UI) 파일: $(files 'using UnityEngine\.UI;')"
echo "- TextMeshPro 파일: $(files 'using TMPro')"
echo "- .uxml: $(findn -name '*.uxml') · .uss: $(findn -name '*.uss')"
echo

echo "## 입력"
ia=$(find "${ROOTS[@]}" -name '*.inputactions' 2>/dev/null)
if [ -n "$ia" ]; then
  # 파일별로 출력 — _old 같은 미사용 사본이 합계를 부풀리지 않게
  while IFS= read -r f; do
    line="- $f:"
    for dev in Keyboard Mouse Gamepad Touchscreen Joystick XRController; do
      n=$(grep -o "<$dev>" "$f" | wc -l | tr -d ' ')
      [ "$n" -gt 0 ] && line="$line <$dev> $n ·"
    done
    echo "${line% ·}"
  done <<< "$ia"
else
  echo "- .inputactions 없음 (코드 루트 기준)"
fi
echo "- 레거시 Input.GetKey/GetAxis/GetButton 줄: $(count 'Input\.(GetKey|GetAxis|GetButton)')"
echo

echo "## 명명 통계"
echo "- [SerializeField] private camelCase: $(count '\[SerializeField\][^;]*private\s+[^;=]*\s[a-z]\w*\s*[;=]')"
echo "- [SerializeField] private _camelCase: $(count '\[SerializeField\][^;]*private\s+[^;=]*\s_\w+\s*[;=]')"
echo "- [SerializeField] private m_Xxx: $(count '\[SerializeField\][^;]*private\s+[^;=]*\sm_\w+\s*[;=]')"
echo "- 그 외 private _camelCase: $(count '^\s*private\s+(static\s+)?(readonly\s+)?[^;=(]*\s_\w+\s*[;=]')"
echo "- 그 외 private camelCase: $(count '^\s*private\s+(static\s+)?(readonly\s+)?[^;=(]*\s[a-z]\w*\s*[;=]')"
echo "- 그 외 private m_Xxx: $(count '^\s*private\s+(static\s+)?(readonly\s+)?[^;=(]*\sm_\w+\s*[;=]')"
echo "- const PascalCase: $(count '\bconst\s+\w+\s+[A-Z][a-z]\w*\s*=')"
echo "- const UPPER_SNAKE: $(count '\bconst\s+\w+\s+[A-Z][A-Z0-9_]+\s*=')"
echo "- const kXxx: $(count '\bconst\s+\w+\s+k[A-Z]\w*\s*=')"
echo "- event On*: $(count '\bevent\s+[^;]+\sOn[A-Z]\w*\s*;')"
echo "- event 기타(과거형 등): $(( $(count '\bevent\s+[^;]+\s[A-Z]\w*\s*;') - $(count '\bevent\s+[^;]+\sOn[A-Z]\w*\s*;') ))"
echo "- Animator.StringToHash 사용 줄: $(count 'Animator\.StringToHash')"
echo "- namespace 예시:"
grep -rhoE '^\s*namespace\s+[A-Za-z0-9_.]+' --include='*.cs' "${ROOTS[@]}" 2>/dev/null \
  | sed -E 's/^\s*namespace\s+//' | sort | uniq -c | sort -rn | head -5 | sed 's/^/    /'
echo

echo "## 에셋 명명 샘플"
echo "- 프리팹 $(findn -name '*.prefab')개 중 샘플:"
find "${ROOTS[@]}" -name '*.prefab' 2>/dev/null | sed 's|.*/||' | shuf -n 10 2>/dev/null | sed 's/^/    /'
echo "- 씬 $(findn -name '*.unity')개 중 샘플:"
find "${ROOTS[@]}" -name '*.unity' 2>/dev/null | sed 's|.*/||' | shuf -n 6 2>/dev/null | sed 's/^/    /'
echo

echo "## 셰이더"
echo "- .shader/.shadergraph/.shadersubgraph/.hlsl: $(findn \( -name '*.shader' -o -name '*.shadergraph' -o -name '*.shadersubgraph' -o -name '*.hlsl' \))"
echo

echo "## 테스트"
found=0
while IFS= read -r a; do
  [ -z "$a" ] && continue
  if grep -qE 'TestRunner|nunit' "$a"; then
    found=1
    # includePlatforms 배열은 여러 줄일 수 있어 공백을 접어서 검사
    if tr -d ' \t\r\n' < "$a" | grep -q '"includePlatforms":\["Editor"'; then mode="EditMode"; else mode="PlayMode"; fi
    echo "- $mode: $a ($(find "$(dirname "$a")" -name '*.cs' | wc -l | tr -d ' ') .cs)"
  fi
done < <(find "${ROOTS[@]}" -name '*.asmdef' 2>/dev/null)
[ "$found" -eq 0 ] && echo "- 테스트 asmdef 없음"
echo

echo "## Assembly Definition"
find "${ROOTS[@]}" -name '*.asmdef' 2>/dev/null | sed 's/^/- /'
