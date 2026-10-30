# /ko-grill — design interview (English reference)

> **Canonical:** `.claude/skills/ko-grill/SKILL.md`. Adapted from
> [mattpocock/skills `grilling` + `grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling) (MIT) —
> read the upstream for the full English text. Same method: treat the topic as a
> design tree, ask the whole frontier per round (numbered, each with a recommended
> answer), look up facts yourself via sub-agents, put only decisions to the user, and
> act only after the user confirms shared understanding.

## Project-specific changes

- Fact sources to check first: `doc/{GameName}/architecture.md` · `task.md`, GDDs in
  `design/`, ADRs, AGENTS.md standards.
- Ends with a numbered summary of decisions; hard-to-reverse technical choices are
  proposed for an ADR via `/architecture-decision`.
