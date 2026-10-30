---
applyTo: "Assets/*/Scripts/**/*.cs,Assets/<SharedModule>/Scripts/**/*.cs,Assets/SharedAssets/Scripts/**/*.cs,src/**/*.gd,src/**/*.cs,Source/**/*.cpp,Source/**/*.h"
description: "Gameplay 코드 규칙"
---
<!-- 생성물: scripts/gen-rule-mirrors.py — 직접 편집 금지 · 정본: .claude/rules/gameplay-code.md -->

# Gameplay 코드 규칙

게임플레이 스크립트에 적용되는 코딩 기준. 공통 규칙 다음에 엔진별 절이 있다 — **프로젝트 엔진의 절만** 적용한다 (엔진 판정 · 엔진별 도구: `.claude/docs/engine-layers.md`). 엔진 API 는 `docs/engine-reference/<engine>/` 로 확인한다.

## 공통 규칙 (모든 엔진)

- **매직 넘버 금지**: 튜닝 값은 에디터에 노출하거나 데이터 자산(Unity ScriptableObject · Godot Resource · Unreal Data Asset)에서 읽는다
- **Delta Time 사용**: 이동 · 애니메이션 · 타이머는 프레임 시간(`deltaTime` · `delta` · `DeltaTime`)을 곱한다
- **UI 직접 참조 금지**: 게임플레이 코드는 UI 를 모른다 — 이벤트로 통신 (C# event · Godot signal · Unreal delegate)
- **물리는 물리 틱에서**: 강체 조작은 물리 틱(Unity `FixedUpdate` · Godot `_physics_process` · Unreal 물리 서브스텝/`AsyncPhysicsTick`)에서
- **노드 · 컴포넌트 탐색 캐싱**: 탐색은 초기화 때 한 번, 매 프레임 코드에서 하지 않는다
- **핫 패스 할당 0**: 매 프레임 코드에서 힙 할당 · 문자열 조합 · 컬렉션 생성 금지
- 모든 게임플레이 수치는 외부 config/data 에서 — 코드 하드코딩 금지
- 게임플레이 시스템은 명확한 인터페이스를 구현
- 상태 머신은 명시적 전이 테이블을 가지고 모든 상태를 문서화
- 모든 게임플레이 로직에 단위 테스트 작성 — 로직과 표현 계층 분리
- 코드 주석에 어떤 design doc 을 구현하는지 명시
- 게임 상태를 위한 static 싱글톤 금지 — DI 사용

## Unity (C#)

- 튜닝 값은 `[SerializeField] private` 로 Inspector 노출 (public 필드 금지)
- 물리: Rigidbody 조작은 `FixedUpdate()` 에서만
- `GetComponent` 는 `Awake()` 에서 1회 캐싱, `Update()` 류에서 호출 금지
- `Update()` / `FixedUpdate()` 에서 GC 할당 금지 (LINQ · string 연산 · `new` 금지)
- Animator 파라미터는 해시 캐싱:

```csharp
// ✅ StringToHash 캐싱
private static readonly int SpeedHash = Animator.StringToHash("Speed");

// ❌ 매 프레임 문자열 조회
animator.SetFloat("Speed", value);
```

- **기계 검사**: 위 규칙과 Animator 문자열 · public 튜닝 필드는 `python .agent/tools/lint/unity_lint.py` (UL001~008)와 Unity 공식 분석기(UNT, `prereq.py install unity-analyzers`)가 확인한다. 오탐은 그 줄에 `// unity-lint: ignore ULxxx` 와 이유

네임스페이스 · 어셈블리:

```
{GamePrefix}.{Category}.{Subsystem}
예: YourGame.Gameplay.Player
    YourGame.Core.Stage
    <SharedModule>.Data
```

- 의존 방향: **Game → <SharedModule>** (단방향만 허용, asmdef 로 강제)
- 게임 간 직접 참조 금지
- Editor 코드는 `Scripts/Editor/` + Editor asmdef 에 격리

## Godot (GDScript · C#)

- 정적 타입을 쓴다 (`var speed: float`, `func move(delta: float) -> void`)
- 튜닝 값은 `@export` 하거나 커스텀 `Resource`(`.tres`)에서 읽는다
- 노드 참조는 `@onready var x: Node = $Path` 또는 `%UniqueName` 로 캐싱 — `_process` 에서 `get_node()` · `find_child()` 금지
- 강체 · `CharacterBody` 이동은 `_physics_process(delta)` 에서
- 시스템 간 통신은 signal — 자식이 부모를 직접 호출하지 않는다 ("call down, signal up")
- `_process` 에서 배열 · 딕셔너리 · 문자열 생성을 피한다. 자주 쓰는 이름은 `StringName` 상수(`&"name"`)로
- 전역 상태는 autoload 남용 대신 주입 — autoload 는 진짜 전역 서비스(저장 · 오디오 버스)만
- 기계 검사: 아직 없다 (`.claude/docs/engine-layers.md`) — 리뷰에서 이 절을 확인한다

## Unreal (C++)

- 튜닝 값은 `UPROPERTY(EditDefaultsOnly)` · Data Asset · Data Table — 생성자 리터럴 금지
- UObject 포인터 멤버는 `UPROPERTY()` 를 붙여 GC 에 알린다 (`TObjectPtr<>`). 붙이지 않은 원시 포인터는 수거 후 댕글링이 된다
- `Tick` 은 필요할 때만 켠다 (`PrimaryActorTick.bCanEverTick = false` 기본, 타이머 · 이벤트 우선)
- `Tick` 에서 `GetAllActorsOfClass` · `FindComponentByClass` · `FName` 생성 금지 — `BeginPlay` 에서 캐싱
- 시스템 간 통신은 delegate (`DECLARE_DYNAMIC_MULTICAST_DELEGATE_*`) — UMG 위젯을 게임플레이 클래스가 직접 갖지 않는다
- 모듈 의존 방향은 `*.Build.cs` 로 강제 — 게임 모듈 → 공유 모듈 단방향
- `.uasset` · `.umap` 은 손으로 고치지 않는다 (`scene-files.md`, 설정 deny)
- 기계 검사: 아직 없다 (`.claude/docs/engine-layers.md`) — 리뷰에서 이 절을 확인한다
