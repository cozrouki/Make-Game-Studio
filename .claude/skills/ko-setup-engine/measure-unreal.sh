#!/usr/bin/env bash
# ko-setup-engine 실측 스크립트 — Unreal 프로젝트 루트(*.uproject 가 있는 곳)에서 실행.
# 사용: bash .claude/skills/ko-setup-engine/measure-unreal.sh [모듈-폴더 ...]
#   모듈-폴더 = 프로젝트 자체 C++ 모듈 (예: Source/MyGame). Plugins/ 의 서드파티는 명명 통계에서 뺀다.
#   생략하면 Source/ 하위 모듈 후보(.cpp · .h 수)만 출력하고 종료한다(exit 2).
# 출력: 마크다운 실측 리포트(stdout). 파일을 쓰지 않는다. 측정하지 못한 항목은 "측정 안 함" 으로 적는다.
# Blueprint · 에셋(.uasset)은 바이너리라 내용을 읽지 않는다 — 파일 수와 이름만 본다.

set -u

UPROJECT=$(ls ./*.uproject 2>/dev/null | head -1)
if [ -z "$UPROJECT" ]; then
  echo "ERROR: Unreal 프로젝트 루트가 아님 (*.uproject 없음)" >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "## 모듈 후보 (Source/ 하위, .cpp / .h 수)"
  if [ -d Source ]; then
    for d in Source/*/; do
      c=$(find "$d" -name '*.cpp' 2>/dev/null | wc -l)
      h=$(find "$d" -name '*.h' 2>/dev/null | wc -l)
      [ $((c + h)) -gt 0 ] && printf '%6d cpp %6d h  %s\n' "$c" "$h" "${d%/}"
    done | sort -rn
  else
    echo "- Source/ 없음 — Blueprint 전용 프로젝트일 수 있다 (이 경우 명명 통계 없이 진행)"
  fi
  echo
  echo "→ 프로젝트 자체 모듈 폴더를 인수로 다시 실행하세요."
  exit 2
fi

ROOTS=("$@")
for r in "${ROOTS[@]}"; do
  [ -d "$r" ] || { echo "ERROR: 폴더 없음: $r" >&2; exit 1; }
done

cc() { grep -rhE "$1" --include='*.h' --include='*.cpp' "${ROOTS[@]}" 2>/dev/null | wc -l | tr -d ' '; }
files() { grep -rlE "$1" --include='*.h' --include='*.cpp' "${ROOTS[@]}" 2>/dev/null | wc -l | tr -d ' '; }
findn() { find "${ROOTS[@]}" "$@" 2>/dev/null | wc -l | tr -d ' '; }
ini() { grep -m1 -E "^$2=" "Config/$1" 2>/dev/null | sed -E "s/^$2=//" | tr -d '\r'; }

echo "# ko-setup-engine 실측 리포트 (Unreal)"
echo
echo "- 프로젝트: $UPROJECT"
echo "- 모듈 루트: ${ROOTS[*]}"
echo "- .cpp: $(findn -name '*.cpp') · .h: $(findn -name '*.h')"
echo "- Content/ .uasset: $(find Content -name '*.uasset' 2>/dev/null | wc -l | tr -d ' ') · .umap: $(find Content -name '*.umap' 2>/dev/null | wc -l | tr -d ' ')"
echo "- Blueprint 추정 (BP_ · WBP_ · ABP_ 접두 .uasset): $(find Content \( -name 'BP_*.uasset' -o -name 'WBP_*.uasset' -o -name 'ABP_*.uasset' \) 2>/dev/null | wc -l | tr -d ' ')"
echo

echo "## 엔진"
echo "- EngineAssociation: $(grep -oE '"EngineAssociation"\s*:\s*"[^"]*"' "$UPROJECT" | sed -E 's/.*:\s*"//; s/"$//')"
echo "- 모듈 (.uproject Modules):"
tr -d '\r\n' < "$UPROJECT" | grep -oE '"Modules"\s*:\s*\[[^]]*\]' | grep -oE '"Name"\s*:\s*"[^"]+"' \
  | sed -E 's/.*:\s*"//; s/"$//' | sed 's/^/    /'
echo "- 플러그인 Enabled=true (.uproject Plugins):"
tr -d '\r\n' < "$UPROJECT" | grep -oE '\{[^{}]*"Name"\s*:\s*"[^"]+"[^{}]*"Enabled"\s*:\s*true[^{}]*\}' \
  | grep -oE '"Name"\s*:\s*"[^"]+"' | sed -E 's/.*:\s*"//; s/"$//' | sed 's/^/    /'
echo "- 프로젝트 플러그인 폴더: $(ls -d Plugins/*/ 2>/dev/null | tr '\n' ' ')"
echo

echo "## 렌더 · 물리 (Config/DefaultEngine.ini)"
if [ -f Config/DefaultEngine.ini ]; then
  echo "- r.DynamicGlobalIlluminationMethod: $(ini DefaultEngine.ini r.DynamicGlobalIlluminationMethod) (1 = Lumen)"
  echo "- r.ReflectionMethod: $(ini DefaultEngine.ini r.ReflectionMethod)"
  echo "- r.Shadow.Virtual.Enable: $(ini DefaultEngine.ini r.Shadow.Virtual.Enable)"
  echo "- r.Mobile.* 설정 줄: $(grep -c '^r\.Mobile' Config/DefaultEngine.ini)"
  echo "- DefaultGraphicsRHI: $(ini DefaultEngine.ini DefaultGraphicsRHI)"
  echo "  (값이 비어 있으면 엔진 기본값 — docs/engine-reference/unreal/modules/rendering.md 확인)"
else
  echo "- Config/DefaultEngine.ini 없음 — 측정 안 함"
fi
echo

echo "## 의존 모듈 (*.Build.cs)"
find "${ROOTS[@]}" -name '*.Build.cs' 2>/dev/null | while IFS= read -r b; do
  deps=$(tr -d '\r\n' < "$b" | grep -oE '(Public|Private)DependencyModuleNames\.AddRange\([^;]*\)' | grep -oE '"[A-Za-z0-9_]+"' | tr -d '"' | sort -u | tr '\n' ' ')
  echo "- $b: $deps"
done
echo

echo "## 기능 사용 (C++)"
echo "- GAS (UAbilitySystemComponent · UGameplayAbility): $(files '(UAbilitySystemComponent|UGameplayAbility)')"
echo "- Enhanced Input (UInputAction · UEnhancedInputComponent): $(files '(UInputAction|UEnhancedInputComponent)')"
echo "- UMG (UUserWidget): $(files 'UUserWidget') · CommonUI (UCommonActivatableWidget): $(files 'UCommonActivatableWidget')"
echo "- 복제 (Replicated · DOREPLIFETIME): $(files '(Replicated|DOREPLIFETIME)')"
echo "- Mass (UMassProcessor): $(files 'UMassProcessor') · Niagara (UNiagaraComponent): $(files 'UNiagaraComponent')"
echo "- Tick 켠 클래스 (bCanEverTick = true): $(cc 'bCanEverTick\s*=\s*true')"
echo

echo "## 명명 통계 (Unreal 접두 규칙)"
echo "- UCLASS 다음 class 이름 U/A 접두: $(cc '^\s*class\s+[A-Z0-9_]+_API\s+[UA][A-Z]\w*\s*:')"
echo "- UCLASS 다음 class 접두 위반 의심 (U/A/F/I 아님): $(cc '^\s*class\s+[A-Z0-9_]+_API\s+[^UAFI ][A-Za-z]\w*\s*:')"
echo "- USTRUCT F 접두: $(cc '^\s*struct\s+([A-Z0-9_]+_API\s+)?F[A-Z]\w*')"
echo "- UENUM E 접두: $(cc '^\s*enum\s+class\s+E[A-Z]\w*')"
echo "- bool b 접두: $(cc '^\s*(UPROPERTY\([^)]*\)\s*)?bool\s+b[A-Z]\w*\s*[;=]')"
echo "- bool b 접두 없음: $(cc '^\s*(UPROPERTY\([^)]*\)\s*)?bool\s+[a-ac-zA-Z]\w*\s*[;=]')"
echo "- UPROPERTY 없는 UObject 원시 포인터 멤버 의심: $(cc '^\s*U[A-Z]\w*\s*\*\s*\w+\s*;')"
echo "- TObjectPtr 사용: $(cc 'TObjectPtr<')"
echo

echo "## 에셋 명명 샘플 (Content/)"
find Content -name '*.uasset' 2>/dev/null | sed 's|.*/||' | shuf -n 10 2>/dev/null | sed 's/^/    /'
echo

echo "## 테스트"
echo "- IMPLEMENT_SIMPLE_AUTOMATION_TEST: $(cc 'IMPLEMENT_SIMPLE_AUTOMATION_TEST')"
echo "- BEGIN_DEFINE_SPEC: $(cc 'BEGIN_DEFINE_SPEC')"
echo "- 테스트 이름 루트 샘플:"
grep -rhoE 'IMPLEMENT_SIMPLE_AUTOMATION_TEST\(\s*\w+\s*,\s*"[^".]+\.' --include='*.cpp' "${ROOTS[@]}" 2>/dev/null \
  | grep -oE '"[^".]+\.' | sort | uniq -c | sort -rn | head -3 | sed 's/^/    /'
echo

echo "## 측정 안 함"
echo "- Blueprint 그래프 내용 · 에셋 설정 (.uasset 은 바이너리)"
echo "- 대상 플랫폼 · 목표 fps (질문으로 받는다). Config/*/ 플랫폼 폴더 참고: $(ls -d Config/*/ 2>/dev/null | tr '\n' ' ')"
