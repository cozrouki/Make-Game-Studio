# Gameplay Code Rules (English reference)

> Reference translation. **Canonical auto-applied rule:** `.claude/rules/gameplay-code.md`.
> Auto-applies (via that file's frontmatter) to:
> `Assets/*/Scripts/**/*.cs`, `Assets/<SharedModule>/Scripts/**/*.cs`,
> `Assets/SharedAssets/Scripts/**/*.cs`, `src/**/*.gd`, `src/**/*.cs`,
> `Source/**/*.cpp`, `Source/**/*.h`.

Coding standards for gameplay scripts. Common rules first, then one section per
engine — **apply only the project engine's section** (engine detection and
per-engine tools: `.claude/docs/engine-layers.md`). Check engine APIs against
`docs/engine-reference/<engine>/`.

## Common rules (all engines)

- **No magic numbers**: expose tuning values in the editor or read them from data
  assets (Unity ScriptableObject · Godot Resource · Unreal Data Asset)
- **Use delta time**: multiply movement, animation and timers by frame time
  (`deltaTime` · `delta` · `DeltaTime`)
- **No direct UI references**: gameplay code does not know the UI — communicate
  through events (C# events · Godot signals · Unreal delegates)
- **Physics on the physics tick**: rigid-body work happens on the physics tick
  (Unity `FixedUpdate` · Godot `_physics_process` · Unreal physics substep /
  `AsyncPhysicsTick`)
- **Cache node / component lookups**: look up once at initialisation, never in
  per-frame code
- **Zero allocations in hot paths**: no heap allocation, string building or
  collection creation in per-frame code
- All gameplay values come from external config/data — no hardcoding
- Gameplay systems implement clear interfaces
- State machines have explicit transition tables with every state documented
- Unit tests for all gameplay logic — separate logic from presentation
- Code comments name the design doc they implement
- No static singletons for game state — use dependency injection

## Unity (C#)

- Tuning values are `[SerializeField] private` (no public fields)
- Physics: touch Rigidbody only in `FixedUpdate()`
- Cache `GetComponent` once in `Awake()`, never call it from `Update()`-style methods
- No GC allocation in `Update()` / `FixedUpdate()` (no LINQ, string ops, `new`)
- Cache Animator parameters as hashes:

```csharp
// ✅ cached StringToHash
private static readonly int SpeedHash = Animator.StringToHash("Speed");

// ❌ string lookup every frame
animator.SetFloat("Speed", value);
```

- **Machine checks**: the rules above plus Animator strings and public tuning
  fields are checked by `python .agent/tools/lint/unity_lint.py` (UL001–008) and
  Unity's official analyzers (UNT, `prereq.py install unity-analyzers`). For a
  false positive, put `// unity-lint: ignore ULxxx` and the reason on that line.

Namespaces and assemblies:

```
{GamePrefix}.{Category}.{Subsystem}
e.g. YourGame.Gameplay.Player
     YourGame.Core.Stage
     <SharedModule>.Data
```

- Dependency direction: **Game → <SharedModule>** only (enforced by asmdefs)
- No direct references between games
- Editor code isolated in `Scripts/Editor/` + an Editor asmdef

## Godot (GDScript · C#)

- Use static typing (`var speed: float`, `func move(delta: float) -> void`)
- Tuning values are `@export`ed or read from a custom `Resource` (`.tres`)
- Cache node references with `@onready var x: Node = $Path` or `%UniqueName` —
  no `get_node()` / `find_child()` in `_process`
- Move rigid bodies and `CharacterBody` in `_physics_process(delta)`
- Systems communicate through signals — children do not call parents directly
  ("call down, signal up")
- Avoid building arrays, dictionaries and strings in `_process`; keep frequently
  used names as `StringName` constants (`&"name"`)
- Prefer injection over autoload sprawl — autoloads only for true global services
  (save, audio buses)
- Machine checks: none yet (`.claude/docs/engine-layers.md`) — reviewers check
  this section

## Unreal (C++)

- Tuning values via `UPROPERTY(EditDefaultsOnly)`, Data Assets or Data Tables —
  no literals in constructors
- Mark UObject pointer members `UPROPERTY()` so the GC knows them (`TObjectPtr<>`);
  an unmarked raw pointer dangles after collection
- Enable `Tick` only when needed (`PrimaryActorTick.bCanEverTick = false` by
  default; prefer timers and events)
- No `GetAllActorsOfClass`, `FindComponentByClass` or `FName` construction in
  `Tick` — cache in `BeginPlay`
- Systems communicate through delegates (`DECLARE_DYNAMIC_MULTICAST_DELEGATE_*`) —
  gameplay classes do not own UMG widgets
- Module dependency direction is enforced in `*.Build.cs` — game modules → shared
  modules only
- Never hand-edit `.uasset` / `.umap` (`scene-files.md`, denied in settings)
- Machine checks: none yet (`.claude/docs/engine-layers.md`) — reviewers check
  this section
