# /ko-code-review — Korean code review (English reference)

> Reference translation of the wrapper skill. **Canonical:** `.claude/skills/ko-code-review/SKILL.md`.
> Frontmatter: `argument-hint: "<PR-number or branch> [--lean | --solo]"`, `agent: lead-programmer`,
> `allowed-tools: Read, Glob, Grep, Bash`.

> **Engine note (2026-10-30):** the canonical Korean skill is now engine-neutral (Unity · Godot · Unreal — see `.claude/docs/engine-layers.md`). This translation still describes the Unity path only; the Godot / Unreal branches are in the canonical file.

A Korean review that adds multi-game context on top of the Game-Studios `code-review` skill.

## Usage

```
/ko-code-review PR-42
/ko-code-review feature/my-feature-v2
/ko-code-review HEAD --solo   # solo-dev lightweight review
```

## Phase 1: Identify changes

- If `$1` is a PR number (`PR-N` or `#N`) → `gh pr diff $1` (or guide the user).
- If a branch name → `git diff main...$1`.
- If `HEAD` → `git diff HEAD~5 HEAD`.

## Phase 2: Game-tag classification

Extract the game tag from changed file paths (multi-game project):

- `Assets/{GameName}/...` → that game's tag (e.g. `[GAME1]`, `[GAME2]`).
- `Assets/<SharedModule>/...` → `[CORE]`.
- Tag mapping follows the "Game Folder Mapping" table in the project `CLAUDE.md`/`AGENTS.md`.
- Skip this step for single-game projects.

Group output by game in the header.

## Phase 3: Delegate to the base skill

Follow `.claude/skills/code-review/SKILL.md`. Additional checks (report in the project language):

### Unity-specific (gameplay-code compliance)
- [ ] Magic numbers externalized via `[SerializeField] private` or a ScriptableObject?
- [ ] `Time.deltaTime` / `Time.fixedDeltaTime` not missing?
- [ ] No LINQ / string ops / `new` on hot paths (`Update`/`FixedUpdate`)?
- [ ] `GetComponent` cached in `Awake()`?
- [ ] `Animator.StringToHash` cached?

### Multi-game assembly
- [ ] Namespace `{GamePrefix}.{Category}.{Subsystem}` respected.
- [ ] **Game → <SharedModule> one-way** dependency only — no reverse / cross-game references.
- [ ] Editor code under `Scripts/Editor/` + Editor asmdef.

### General (engine-agnostic)
- Apply the base `code-review` skill's ADR-compliance checks.

## Phase 4: Output

```
🔴 CRITICAL N / 🟡 WARNING N / 🔵 INFO N

[GAME1]
  - <file:line> — <issue> — <suggestion>
[GAME2]
  - ...
```

`--lean`: CRITICAL only (omit WARNING/INFO). `--solo`: suggestions only, skip approval flow.

## Related
- Base skill: `/code-review` · Design review: `/design-review` · Performance: `/ko-perf-profile`
