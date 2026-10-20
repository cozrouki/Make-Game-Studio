# /ko-art-gen — make graphics that match the design intent (English reference)

> Reference translation. **Canonical:** `.claude/skills/ko-art-gen/SKILL.md`. Tool docs (Korean): `.agent/tools/artgen/README.md`.

Turns the specs written by `/asset-spec` into real images, reviews them against the art bible, and brings the approved ones into Unity.
Deterministic work (generate · store · promote) is done by the `.agent/tools/artgen/artgen.py` CLI. Judgment (writing the request, visual review, deciding how to regenerate) is done by this skill.

## Usage

```
/ko-art-gen ASSET-012                 single asset
/ko-art-gen spec:combat               every Needed asset in design/assets/specs/combat-assets.md
/ko-art-gen next                      first Needed asset in the manifest
/ko-art-gen ASSET-012 --variants 6 --rounds 2
/ko-art-gen spec:combat --auto        skip per-asset confirmation (still confirms the final promote list)
```

## Backend-neutral by design

The image backend (local ComfyUI, a commercial API, an in-house server, …) is **an adapter chosen later**:

- `mock` (default) — placeholder PNGs, so the whole flow (request → generate → review → promote → Unity import) can be exercised before a backend is chosen. Visual review is skipped; technical checks still run.
- `command` — run any external program via an argv template (`{job_file}`, `{out_dir}`, …). No Python required.
- Python adapter — copy `artgen_lib/providers/_template.py`, implement `check()` / `generate()`. It is auto-discovered.

## Phases

0. **Pre-check** — requires the art bible, the asset manifest, and the spec file. Runs `artgen providers` and tells the user when `mock` is active.
1. **Target & context** — resolves the assets (Audio and 3D are out of scope). Reads the art bible (identity, shape language, color system, prohibitions, §8 standards), `technical-preferences.md` (naming, budgets), and the game-folder mapping in `AGENTS.md` §6.
2. **Generation request** — writes `design/assets/requests/ASSET-NNN.json` (`artgen-request/1`). Style tokens are defined once in `_style-tokens.json` and shared by every asset, because shared tokens are what keep the assets consistent. Then runs `validate` and `prompt`, and the user confirms.
3. **Generate** — runs `artgen generate`. Errors are reported verbatim. The manifest status becomes `In Progress`.
4. **Review** — Claude views each PNG and scores five axes (style, shape, color, readability at in-game size, technical) from 1 to 5. Every score cites the art bible. Results go to `review.md`. If no variant passes, the skill edits subject/composition/negative only (style tokens stay fixed), logs the edit in `history`, and regenerates, up to `maxRounds`.
5. **Select** — the user picks: promote / choose another variant / regenerate with a new direction / reject.
6. **Promote** — installs the Editor-only import postprocessor once (with confirmation). Then runs `artgen promote`, which writes `import-map.json` first and then copies into `Assets/`, so the TextureImporter settings apply on the first import. The manifest becomes `Done`. Placeholder results stay `In Progress (placeholder)`.
7. **Wrap-up** — shows a summary table, writes a `work_log` entry, and suggests `/ko-art-gen next` or `/asset-audit`.

## Principles

- The design docs are the source of truth. Nothing that isn't in the spec goes into the prompt.
- Every generation is kept as a new version. Nothing is overwritten (`promote --force` backs up first).
- No secrets in requests, config, or logs.
- Nothing is written to `Assets/` without the user's approval.
