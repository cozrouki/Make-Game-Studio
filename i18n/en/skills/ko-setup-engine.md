# /ko-setup-engine — measured engine setup (English reference)

> Reference translation. **Canonical:** `.claude/skills/ko-setup-engine/SKILL.md`.
> Frontmatter: `argument-hint: "[code-root ...]  e.g. Assets/YourGame"`,
> `allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion`.

Upstream `/setup-engine` targets new projects and fills engine and naming fields with **defaults**. On a project that already has code, those defaults diverge from the real conventions and `/code-review` then flags existing code en masse. This skill **measures the project** to fill both files and asks only what code cannot reveal (platforms, target fps).

Files it fills:
- `CLAUDE.md` → `## Technology Stack` (`/gate-check` checks it for `[CHOOSE]`)
- `.claude/docs/technical-preferences.md` (~20 L1 skills read engine, performance budgets, naming, and **specialist routing** from it)

## Usage

```
/ko-setup-engine                       # show code-root candidates and let the user pick
/ko-setup-engine Assets/YourGame       # explicit code root
/ko-setup-engine Assets/GameA Assets/SharedModule
```

## Phase 1: Decide the code root(s)

Measure **only the project's own code** so third-party assets don't skew naming stats.

1. Use the arguments if given.
2. Otherwise, if the `AGENTS.md` §6 game-folder mapping table is filled in (not `[GAME1]` placeholders), propose `Assets/<GameName>` + the shared-module folder.
3. Otherwise run `bash .claude/skills/ko-setup-engine/measure.sh` with no arguments to get candidates by `.cs` count, and let the user pick via `AskUserQuestion` (multiSelect). Leave likely third-party folders (asset-store vendor names, `Plugins`, `ThirdParty`) unselected by default.

## Phase 2: Measure

```bash
bash .claude/skills/ko-setup-engine/measure.sh <code-root...>
```

- Use the Markdown report as evidence for the next steps. The script writes no files.
- **If there are 0 `.cs` files**, there is nothing to measure → tell the user to use `/setup-engine` (new project) and stop.

## Phase 3: Two questions (one AskUserQuestion call)

1. **Target platforms** (multiSelect): PC / Console (Switch·PS·Xbox) / Mobile / Web — allow Other so "current + planned" can be stated.
2. **Target framerate**: 60fps (recommended) / 30fps / 120fps+.

## Phase 4: Derivation rules

- **Engine & Language**: `m_EditorVersion`; render pipeline + version; physics 2D if Rigidbody2D > 0 else PhysX 3D (note CharacterController / NavMeshAgent).
- **Input & Platform**: upstream `/setup-engine` table (PC only → Gamepad Partial; Console → Full; Mobile → Touch Full; Web → Partial/Partial). If Console is a planned expansion, write "Partial → Full target" and add "no hover-only UI, all menus D-pad navigable" to Platform Notes. Count bindings from **files in use** only (skip `_old` / `_backup` copies). Note 0 gamepad bindings and any legacy `Input.Get*` usage.
- **Naming — majority vote**, listing the minority too if ≥ 20%: `[SerializeField] private` and other private fields are judged **separately**; constants (PascalCase / UPPER_SNAKE / `kXxx`); events (`On*` if majority); namespaces summarized as `{Root}.{Category}.{Subsystem}`; scene/prefab patterns from the samples. Keep the measured counts as an HTML comment.
- **Performance**: framerate from the answer (60 → 16.6ms, 30 → 33.3ms, 120 → 8.3ms); Draw Calls / Memory Ceiling stay `[TO BE CONFIGURED — measure once target hardware is fixed]` (never guess); hot path = zero GC.
- **Testing**: test asmdefs from the report (EditMode / PlayMode, location); none → recommend `/test-setup`.
- **Forbidden Patterns**: one-line summaries of `.claude/rules/gameplay-code.md`, pointing to it. Add nothing else.
- **Allowed Libraries**: packages actually used from the manifest (exclude IDE, learning, device-simulator dev tools). No speculative additions.
- **Engine Specialists**: standard Unity routing (same as upstream). UI note: "UI Toolkit (UXML/USS)" if UI Toolkit files > uGUI files, else "uGUI (Canvas)". DOTS specialist "(only when adopting ECS/Jobs/Burst)" if no ECS files. Drop the Addressables line if the package is absent.
- **CLAUDE.md Technology Stack**: Engine / Language / Render Pipeline / Key Packages / Build System / Asset Pipeline.

## Phase 5: Preview → approve → write

1. Show **complete drafts** of both files (diff only the changed lines if they exist).
2. Write only after approval.
3. If `technical-preferences.md` exists, **preserve human-written Forbidden Patterns, Allowed Libraries, and Architecture Decisions Log**; refresh only measured sections.
4. If `CLAUDE.md` has no `## Technology Stack`, add it after the first `---` separator.

Keep the section titles used by upstream skills (Engine & Language, Input & Platform, Naming Conventions, Performance Budgets, Testing, Forbidden Patterns, Allowed Libraries / Addons, Architecture Decisions Log, Engine Specialists, File Extension Routing) and the `- **Engine**: value` line format — the `detect-gaps.sh` hook reads `^- **Engine**:`.

## Phase 6: Follow-up

- Propose a one-line entry at the top of `doc/work_log.md`: `[<tag>] /ko-setup-engine — <engine> · <RP> · measured naming · platforms <answer>`
- Tell the user to rerun after engine or package upgrades (human-written sections are preserved).

## Related

- New project (no code): `/setup-engine`
- Test framework scaffold: `/test-setup`
- Phase gate: `/gate-check`
