# Gameplay Code Rules (English reference)

> Reference translation. **Canonical auto-applied rule:** `.claude/rules/gameplay-code.md`.
> Auto-applies (via that file's frontmatter) to:
> `Assets/*/Scripts/**/*.cs`, `Assets/<SharedModule>/Scripts/**/*.cs`,
> `Assets/SharedAssets/Scripts/**/*.cs`, `src/gameplay/**`.

Coding standards for Unity C# scripts.

## Mandatory rules

- **No magic numbers**: expose tuning values via `[SerializeField] private` in the Inspector.
- **Use delta time**: drive movement/animation with `Time.deltaTime` / `Time.fixedDeltaTime`.
- **No direct UI references**: gameplay code must not reference UI components directly — communicate via events.
- **Physics in FixedUpdate**: manipulate Rigidbodies only in `FixedUpdate()`.
- **Cache GetComponent**: cache once in `Awake()`; never call it on a hot path.
- **Zero GC in hot paths**: no GC allocation in `Update()` / `FixedUpdate()` (no LINQ, string ops, or `new`).

## Animator parameters

```csharp
// ✅ Cache with StringToHash
private static readonly int SpeedHash = Animator.StringToHash("Speed");

// ❌ String lookup every frame
animator.SetFloat("Speed", value);
```

## Namespace convention

```
{GamePrefix}.{Category}.{Subsystem}
e.g. YourGame.Gameplay.Player
     YourGame.Core.Stage
     <SharedModule>.Data
```

## Assembly Definition

- Dependency direction: **Game → <SharedModule>** (one-way only).
- No direct references between games.
- Isolate Editor code under `Scripts/Editor/` with an Editor asmdef.

## General principles (merged from Game-Studios)

- All gameplay values come from external config/data — no hardcoding in code.
- Gameplay systems implement clear interfaces.
- State machines have an explicit transition table and document every state.
- Write unit tests for all gameplay logic — separate logic from presentation.
- In code comments, state which design doc a piece implements.
- No static singletons for game state — use DI.
