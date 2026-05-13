---
globs:
  - "Assets/*/Scripts/**/*.cs"
  - "Assets/SharedCore/Scripts/**/*.cs"
  - "Assets/SharedAssets/Scripts/**/*.cs"
  - "src/gameplay/**"
---

# Gameplay 코드 규칙 (TikiProject)

Unity C# 스크립트에 적용되는 코딩 기준.

## 필수 규칙

- **매직 넘버 금지**: 튜닝 값은 `[SerializeField] private`로 Inspector 노출
- **Delta Time 사용**: 이동/애니메이션은 `Time.deltaTime` / `Time.fixedDeltaTime` 사용
- **UI 직접 참조 금지**: Gameplay 코드에서 UI 컴포넌트 직접 참조 금지 — 이벤트로 통신
- **물리는 FixedUpdate**: Rigidbody 조작은 `FixedUpdate()`에서만
- **GetComponent 캐싱**: `Awake()`에서 1회 캐싱, Hot Path에서 호출 금지
- **Zero GC in Hot Paths**: `Update()` / `FixedUpdate()`에서 GC 할당 금지 (LINQ, string 연산, new 호출 금지)

## Animator 파라미터

```csharp
// ✅ StringToHash 캐싱
private static readonly int SpeedHash = Animator.StringToHash("Speed");

// ❌ 매 프레임 문자열 조회
animator.SetFloat("Speed", value);
```

## 네임스페이스 규칙

```
{GamePrefix}.{Category}.{Subsystem}
예: KickleCubicle.Gameplay.Player
    ElevatorAction.Core.Stage
    SharedCore.Data
```

## Assembly Definition

- 의존 방향: **Game → SharedCore** (단방향만 허용)
- 게임 간 직접 참조 금지
- Editor 코드는 `Scripts/Editor/` + Editor asmdef에 격리

## 일반 원칙 (Game-Studios에서 통합)

- 모든 게임플레이 수치는 외부 config/data에서 — 코드 하드코딩 금지
- 게임플레이 시스템은 명확한 인터페이스를 구현
- 상태 머신은 명시적 전이 테이블을 가지고 모든 상태를 문서화
- 모든 게임플레이 로직에 단위 테스트 작성 — 로직과 표현 계층 분리
- 코드 주석에 어떤 design doc을 구현하는지 명시
- 게임 상태를 위한 static 싱글톤 금지 — DI 사용
