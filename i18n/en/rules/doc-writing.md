# Documentation Rules (English reference)

> Reference translation. **Canonical auto-applied rule:** `.claude/rules/doc-writing.md`.
> Auto-applies to: `doc/**/*.md`, `production/**/*.md`.

## Common rules

- **Language**: Korean (including comments in code blocks) in the canonical template.
  Switch to your team's language as needed — see `i18n/en/README.md`.
- **Game tag**: every `work_log.md` entry must carry one (multi-game projects).
  - The tag set is defined per project, e.g. `[GAME1]`, `[GAME2]`, `[CORE]` (shared module, e.g. `<SharedModule>`).
  - Single-game projects may omit tags or use just `[GAME]` / `[CORE]`.
- **Date format**: `YYYY-MM-DD`.

## task.md format

```markdown
# {GameName} Tasks

## In progress
- [ ] Task description (YYYY-MM-DD)

## Done
- [x] Task description (done: YYYY-MM-DD)

## Backlog
- [ ] Task description
```

## work_log.md format

Keep only the current month in `doc/work_log.md`, prepend new entries (newest first), and move past months to `doc/work_log/YYYY-MM.md` (AGENTS.md §6).

```markdown
## YYYY-MM-DD

### [TAG] Work title
- Summary of changes
- Decisions and rationale
```

## active.md rules

- Keep the `<!-- STATUS -->` block current at all times.
- Update the `_last updated:` date before ending a session.
- "Next up" items must be described as concrete actions.
- Stay within 3–5KB — current state, recent completions, next steps, and blockers only (AGENTS.md §6-1).

## architecture.md required sections

1. `## File structure`
2. `## Architecture patterns`
3. `## Core systems`
4. `## Known issues`
5. `## Design-decision log`
