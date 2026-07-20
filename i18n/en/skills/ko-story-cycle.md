# /ko-story-cycle — story implementation cycle (English reference)

> Reference translation. **Canonical:** `.claude/skills/ko-story-cycle/SKILL.md`.
> Frontmatter: `argument-hint: "<story-id> [--skip-review]"`, `agent: lead-programmer`,
> `allowed-tools: Read, Glob, Grep, Write, Edit, Bash, AskUserQuestion`.

Runs one story end to end — readiness → implementation → completion.

## Usage

```
/ko-story-cycle STORY-042
/ko-story-cycle STORY-042 --skip-review   # skip code review (small change)
```

## Phase 1: Intake + context
- `$1` = story ID (e.g. `STORY-042`, `[GAME1]-S012`).
- Find the story doc: `production/stories/$1.md` or a reference inside `doc/*/task.md`.
- Parse the game tag (the project's tag set, e.g. `[GAME1][GAME2][CORE]`).

## Phase 2: Readiness (story-readiness)
Call `.claude/skills/story-readiness/SKILL.md`:
- Presence of the 8 required design-doc sections
- Dependencies stated
- Acceptance Criteria are verifiable
- If blocked, report to the user and offer to stop.

## Phase 3: Implementation (dev-story)
Call `.claude/skills/dev-story/SKILL.md`. Additional steps:
- Confirm the assembly matching the game tag (`{GamePrefix}.{Category}.{Subsystem}`).
- Apply the `gameplay-code` rules (no magic numbers, cache GetComponent, Zero-GC, FixedUpdate).
- Point the user to relevant SkillForge patterns: `/sf-list 02-gameplay`, etc.

## Phase 4: Code review (optional)
If `--skip-review` is absent, call `.claude/skills/code-review/SKILL.md`. Added context:
- Show changed game tags in the output header.
- Extra checks for namespace violations / reversed assembly dependencies.

## Phase 5: Completion (story-done)
Call `.claude/skills/story-done/SKILL.md` plus post-processing:
- Mark the item done in `doc/{ActiveGame}/task.md` (Edit tool, user approval).
- Add a one-line summary to `doc/work_log.md` (with game tag).
- Propose updating the "Completed items" section of `active.md`.

## Related
- Single steps: `/story-readiness`, `/dev-story`, `/code-review`, `/story-done`
- After the cycle: `/sprint-status` for progress.
