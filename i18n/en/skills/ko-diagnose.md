# /ko-diagnose — bug diagnosis loop (English reference)

> **Canonical:** `.claude/skills/ko-diagnose/SKILL.md`. Adapted from
> [mattpocock/skills `diagnosing-bugs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs) (MIT) —
> read the upstream for the full English text. Same six phases: build a red-capable
> feedback loop → reproduce + minimise → 3–5 falsifiable hypotheses → instrument →
> fix + regression test → cleanup.

## Unity-specific changes

- **Feedback-loop ladder**: failing EditMode test → failing PlayMode test → temporary
  `[MenuItem]` editor harness read via `read_console` → replayed recordings → seeded
  random loops → `git bisect run` → differential runs → human-in-the-loop as a numbered
  Play-mode checklist (instead of the upstream bash template).
- Tests run through `mcp__UnityMCP__run_tests` or `Unity -batchmode -runTests`.
- Determinism levers: `Random.InitState`, injected time / deltaTime, fixed physics step.
- Perf branch: baseline with `mcp__UnityMCP__manage_profiler` / `Stopwatch`, then hand
  off to `/ko-perf-profile` and `.agent/skills/06-performance/`.
- No correct test seam (logic locked in MonoBehaviour, static singletons, direct
  time/random calls) is recorded as a finding for `/ko-code-review` or `/tech-debt`.
- The correct hypothesis goes into the commit message or `doc/work_log.md`.
