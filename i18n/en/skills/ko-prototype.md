# /ko-prototype — concept to prototype (English reference)

> Reference translation. **Canonical:** `.claude/skills/ko-prototype/SKILL.md`.
> Frontmatter: `argument-hint: "<game-tag> <one-line concept>"`, `agent: prototyper`,
> `allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion`.

Takes a one-line idea from brainstorm → quick design → prototype folder in one pass.

## Usage

```
/ko-prototype GAME1 "evasive action when meeting an enemy in the elevator"
/ko-prototype GAME2 "environment-adaptive reaction on cube rotation"
/ko-prototype NEW "new game concept: time-reversal puzzle"
```

## Phase 1: Intake
- `$1` = game tag (from the project's Game Folder Mapping) or `NEW` (new game).
- `$2..` = free-form concept description.

## Phase 2: Brainstorm
Call `.claude/skills/brainstorm/SKILL.md`. Produce:
- 3–5 idea variants
- Core mechanic of each variant
- Player fantasy (one line)
- 1–2 reference games

Ask the user to pick a preferred variant (AskUserQuestion).

## Phase 3: Quick design
For the chosen variant, call `.claude/skills/quick-design/SKILL.md`:
- Core loop (one paragraph)
- Input → system → feedback flow
- The single riskiest assumption (to validate via prototype)
- Success criteria (quantified if possible)

Output path: `prototypes/$1-<slug>/CONCEPT.md`

## Phase 4: Create prototype folder
Call `.claude/skills/prototype/SKILL.md`.

```
prototypes/$1-<slug>/
├── CONCEPT.md           (Phase 3 output)
├── README.md            (Phase 4, project language)
└── (optional) PROBE.md  (assumption-validation plan from Phase 3)
```

### Unity integration
- `$1 == NEW` → propose a new assembly dir `Assets/<NewGame>/Scripts/Prototype/`.
- Existing game → its `Scripts/Prototype/` or `Scripts/Experiments/`.
- Apply the `prototype-code` rule (relaxed standards, README required).

### SkillForge references
- Combat/action → `/sf-info 02-gameplay/combat-system-pro` or `ability-skill-system`
- Puzzle → `/sf-info 02-gameplay/grid-puzzle-mechanics`
- AI/enemy → `/sf-info 02-gameplay/ai-behavior-trees`

## Phase 5: Post
- Propose adding a prototype-validation item to `active.md` "Next up".
- Add a one-line `doc/work_log.md` entry (`[<tag>] /ko-prototype: <slug>`).

## Related
- Single steps: `/brainstorm`, `/quick-design`, `/prototype`
- Playtest: `/playtest-report` · Move to implementation: `/ko-story-cycle`
