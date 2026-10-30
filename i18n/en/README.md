# English Reference Translations

> **Korean is canonical.** These are reference translations for English-speaking
> contributors. The files the agent actually reads and auto-applies are the
> Korean originals — keep those authoritative and update these when they change.

| English (here) | Canonical source |
|---|---|
| [AGENTS.md](AGENTS.md) | `/AGENTS.md` — persona §1–§7 (tool-neutral) |
| [rules/gameplay-code.md](rules/gameplay-code.md) | `.claude/rules/gameplay-code.md` |
| [rules/doc-writing.md](rules/doc-writing.md) | `.claude/rules/doc-writing.md` |
| [skills/*.md](skills/) | `.claude/skills/ko-*/SKILL.md` — 7 Korean wrappers + 4 mattpocock/skills adaptations (`ko-prereq` not translated) |

Not translated (Korean only): the artgen tool docs (`.agent/tools/artgen/README.md`),
studio mode (`.agent/tools/studio/` — protocol, role charters, templates) and the
`studio-*` skills. The top of the root `README.md` summarizes both in English.

## Why only these files?

The other 10 rules in `.claude/rules/` (`ai-code`, `data-files`, `design-docs`,
`engine-code`, `narrative`, `network-code`, `prototype-code`, `shader-code`,
`test-standards`, `ui-code`) are **already English** — direct copies from
[Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios).
No translation needed.

The `ko-*` skills are thin **Korean wrappers** around English L1 skills
(`/code-review`, `/sprint-plan`, …). English-speaking users can simply invoke the
underlying English skills directly; these translations exist so you can see what
extra steps each wrapper adds.

The four adapted skills (`ko-diagnose`, `ko-tdd`, `ko-grill`, `ko-agent-retro`)
have English originals upstream in [mattpocock/skills](https://github.com/mattpocock/skills);
their pages here link the original and list only the Unity-specific changes.

## Making the agent respond in English

The persona instructs Korean output. To switch:

1. In `AGENTS.md`, change the Communication Style line
   `- **모든 답변은 한국어로 작성한다.**` → `- **Write all responses in English.**`
2. In `.claude/rules/doc-writing.md`, change `- **언어**: 한국어` → `English`.
3. (Claude Code) `CLAUDE.md` inherits the AGENTS.md persona; no separate change needed.

These are reference docs only — they are **not** auto-applied as rules or
invokable as skills (they live outside `.claude/rules/` and `.claude/skills/`).
