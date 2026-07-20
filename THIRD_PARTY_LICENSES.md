# Third-Party Licenses

This repository is an **integration** of assets from several upstream projects.
This file preserves the required copyright and permission notices for the
components that are **redistributed** here (bundled in the tree), and documents
the components that are only **referenced or installed separately** (not
bundled, so no redistribution obligation).

For a per-asset breakdown (what was copied verbatim, mirrored, forked, or only
referenced), see [`.claude/docs/ATTRIBUTION.md`](.claude/docs/ATTRIBUTION.md).

Licenses verified against the GitHub API on **2026-07-20**.

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

---

If you believe a notice is missing or incorrect, please open an issue — it will
be corrected in the next sync cycle.
