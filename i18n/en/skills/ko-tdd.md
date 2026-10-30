# /ko-tdd — test-driven development (English reference)

> **Canonical:** `.claude/skills/ko-tdd/SKILL.md` + `tests.md`. Adapted from
> [mattpocock/skills `tdd`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd) (MIT) —
> read the upstream for the full English text. Same rules: test behaviour through
> public interfaces, only at seams agreed with the user, vertical slices (one test →
> one implementation), red before green, refactoring belongs to review.

## Unity-specific changes

- **Seams**: prefer EditMode tests on plain C# logic extracted from MonoBehaviours
  (humble object); PlayMode only when lifecycle / physics / coroutines / scene loading
  is itself under test. Separate test asmdefs (`Tests/EditMode`, `Tests/PlayMode`).
- Time, random, input, and storage are injected interfaces (matches
  `gameplay-code.md`: no static singletons, use DI) — these are the only mock points.
- A compile error is not red: check `read_console` first.
- Done = agreed seams green **and** the game's full test suite green; report the count.
- `tests.md` merges upstream `tests.md` + `mocking.md` with NUnit C# examples.
- Setup / helpers: `/test-setup`, `/test-helpers`. Refactor in `/ko-code-review`.
