# /ko-sprint-plan — sprint planning (English reference)

> Reference translation. **Canonical:** `.claude/skills/ko-sprint-plan/SKILL.md`.
> Frontmatter: `argument-hint: "<sprint-number> [duration-days=14]"`, `agent: producer`,
> `allowed-tools: Read, Glob, Grep, Write, AskUserQuestion`.

Wraps the Game-Studios `sprint-plan` skill. Output saved to `production/sprints/sprint-<N>.md`.

## Usage

```
/ko-sprint-plan 7
/ko-sprint-plan 7 10         # 10-day sprint
/ko-sprint-plan 7 14 --solo  # solo mode
```

## Phase 1: Parse args
- `$1` = sprint number (required).
- `$2` = duration in days (default 14).
- `--solo` = solo-developer mode (simplified review).

## Phase 2: Gather context
Read and assemble context from:
- `doc/work_log.md` top ~50 lines (newest first) — recent work flow
- `doc/{ActiveGame}/task.md` — current game's task status
- `production/session-state/active.md` — active game/Epic/Feature
- Previous sprint's retro section, if any: `production/sprints/sprint-<N-1>.md`

## Phase 3: Delegate to base skill
Follow `.claude/skills/sprint-plan/SKILL.md`, and output (in the project language):
- Sprint goal (one line)
- Work grouped by game tag (the project's tag set, e.g. `[GAME1][GAME2][CORE]`)
- Capacity estimate for the given duration
- Risks / dependencies

## Phase 4: Save and confirm
- Output path: `production/sprints/sprint-$1.md`.
- Ask for approval before writing (project language).
- After saving, propose linking the sprint ID in `active.md` "Next up".

## Related
- Base skill: `/sprint-plan` (Game-Studios) · Status: `/sprint-status` · Cycle: `/ko-story-cycle`
