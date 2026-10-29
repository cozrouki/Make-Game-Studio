# Third-Party Licenses

This repository is an **integration** of assets from several upstream projects.
This file preserves the required copyright and permission notices for the
components that are **redistributed** here (bundled in the tree), and documents
the components that are only **referenced or installed separately** (not
bundled, so no redistribution obligation).

For a per-asset breakdown (what was copied verbatim, mirrored, forked, or only
referenced), see [`.claude/docs/ATTRIBUTION.md`](.claude/docs/ATTRIBUTION.md).

Licenses verified against the GitHub API on **2026-07-20** (items 1–5) and against the
upstream LICENSE files on **2026-10-23** (items 6–8).

---

## Bundled components (redistributed — notices required)

### 1. Claude-Code-Game-Studios — L1 process skills

- Source: https://github.com/Donchitos/Claude-Code-Game-Studios
- License: **MIT**
- Bundled here: 72 skills (`.claude/skills/<name>/`), 39 agents (`.claude/agents/`),
  10 hooks, 10 rules, 6 `gs-*` docs. Some files (`session-*.sh`,
  `gameplay-code.md`, `settings.json` wiring) are local forks/merges.

```
Copyright (c) 2026 Donchitos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 2. Unity-SkillForge — L2 C# code-pattern skills

- Source: https://github.com/nlelouche/Unity-SkillForge
- License: **MIT**
- Bundled here: 102 skills under `.agent/skills/` (SKILL.md + templates/) and
  `skills-index.json`, mirrored offline. The mirror is not modified in place;
  Korean customization lives in `.claude/skills/ko-*` / `sf-*`.

```
Copyright (c) 2025 AntiGravity Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 6. marketingskills — `marketing` external catalog

- Source: https://github.com/coreyhaines31/marketingskills
- License: **MIT**
- Bundled here: 52 skills under `.agent/marketing/skills/` (without `evals/`) and the
  integration docs under `.agent/marketing/tools/` (`*.md` only — the 66 API CLI
  scripts in `tools/clis/` are not included). Unmodified; Korean summaries are a
  separate local file (`.agent/catalogs/marketing.ko.json`).

```
MIT License

Copyright (c) 2025 Corey Haines

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 7. awesome-gamedev-agent-skills — `gamedev` external catalog

- Source: https://github.com/gamedev-skills/awesome-gamedev-agent-skills
- License: **Apache-2.0** — full text in `.agent/gamedev/LICENSE`
- Bundled here: 36 skills under `.agent/gamedev/skills/{disciplines,genres,unity,workflows}/`
  (engine-specific skills for Godot, Unreal, Roblox and web engines, the router,
  and repository scripts/tests are not included). Files are unmodified; Korean
  summaries are a separate local file (`.agent/catalogs/gamedev.ko.json`).
- NOTICE (reproduced as required by Apache-2.0 §4(d)):

```
awesome-gamedev-agent-skills
Copyright 2026 Abhishek Barali and the awesome-gamedev-agent-skills contributors

This product is licensed under the Apache License, Version 2.0 (see LICENSE).

All skills in this repository are original works. They were authored from primary
documentation (engine and framework docs, language references, and platform
specifications). Third-party sources and other skill collections were studied for
general patterns only; no text or code was copied from them.

Game engine, framework, and platform names referenced in this repository
(including but not limited to Godot, Unity, Unreal Engine, Phaser, PixiJS,
three.js, Babylon.js, Bevy, GameMaker, LÖVE, and MonoGame) are trademarks of
their respective owners and are used for identification and descriptive purposes
only. Their use does not imply any affiliation with or endorsement by those owners.
```

### 8. android/skills — `android` external catalog

- Source: https://github.com/android/skills (Google LLC)
- License: **Apache-2.0** — full text in `.agent/android/LICENSE.txt` (the upstream has no NOTICE file)
- Bundled here: 4 skills — `profilers/android-profiler`, `play/play-policy-insights`,
  `performance/anr-audit-and-fix`, `performance/r8-analyzer` (native-app skills for Compose,
  Wear, TV, Cars, CameraX etc. are not included). Files are unmodified, including the
  bundled Perfetto `trace_processor` wrapper (Apache-2.0, The Android Open Source Project);
  Korean summaries are a separate local file (`.agent/catalogs/android.ko.json`).

---

## Referenced / separately installed (NOT bundled — no redistribution)

### 3. MCPForUnity (unity-mcp) — L3 Editor automation backend

- Source: https://github.com/CoplayDev/unity-mcp — License: **MIT**
  (Copyright (c) 2025 CoplayDev)
- Not redistributed here. Installed by the end user as a UPM package
  (`com.coplaydev.unity-mcp`) via `Packages/manifest.json`; its license ships
  inside that package. This repo only adds a usage guide
  (`.claude/docs/mcp-unity-guide.md`).

### 4. antigravity-awesome-skills — L4 packaging format

- Source: https://github.com/sickn33/antigravity-awesome-skills
  (repository appears to have moved/been renamed as of 2026-07-20)
- Only the **schema/format** of `bundles.json` / `workflows.json` was
  referenced when authoring `.claude/data/`. **No skill content was copied**,
  so no redistribution obligation. Credited here for good faith.

### 5. Unity-Skills (Besty0728) — optional reference catalog

- Source: https://github.com/Besty0728/Unity-Skills
- **Not installed / not bundled.** Referenced by URL only as an optional future
  integration. No files copied.

### 8. game-design-skills-bundle — `gamedesign` external catalog (NOT bundled)

- Source: https://github.com/Stanestane/game-design-skills-bundle
- License: **PolyForm Noncommercial 1.0.0**
  (Required Notice: Copyright Stanislav Stankovic (https://www.stane-island.net/)).
  Commercial use — including use inside a company that develops, publishes or
  operates games — and any redistribution or repackaging require a commercial
  licence from the author (see the upstream `COMMERCIAL-LICENSE.md`).
- **Not redistributed here.** No files from this bundle are in this repository.
  A user who qualifies (noncommercial use, or holder of a commercial licence) fetches
  it directly from upstream with
  `python scripts/sync-catalog.py gamedesign --fetch --accept-license <noncommercial|commercial>`;
  the files land in `.agent/gamedesign/`, which is git-ignored and excluded from
  `scripts/install.ps1`. `.agent/catalogs/gamedesign.ko.json` contains only short
  locally written descriptions of the skill names, not upstream text.

---

If you believe a notice is missing or incorrect, please open an issue — it will
be corrected in the next sync cycle.
