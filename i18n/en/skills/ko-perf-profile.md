# /ko-perf-profile — Korean performance profiling (English reference)

> Reference translation. **Canonical:** `.claude/skills/ko-perf-profile/SKILL.md`.
> Frontmatter: `argument-hint: "<scope: scene | system | full> [game-tag]"`, `agent: performance-analyst`,
> `allowed-tools: Read, Glob, Grep, Bash, mcp__UnityMCP__manage_profiler`.

Diagnoses Unity performance bottlenecks and matches them to SkillForge catalog fixes.

## Usage

```
/ko-perf-profile scene             # active scene only
/ko-perf-profile system GAME1      # one game (multi-game project)
/ko-perf-profile full              # whole project
```

## Phase 1: Scope + context
- `$1` = scope. `$2` = game tag (optional) — restricts to `Assets/<Game>/`.

## Phase 2: Collect profiler data
Use MCPForUnity `manage_profiler` if available:
- CPU frame time (Main / Render / Physics / Scripts)
- GC allocation amount / frequency
- Draw call / batch count
- Memory (Managed / Native / Texture / Mesh)

If MCP is unavailable, guide the user to capture the Profiler and paste results.

## Phase 3: Bottleneck analysis
Follow `.claude/skills/perf-profile/SKILL.md`. Additional suspicion patterns per metric:
- **High GC** → suspect a `gameplay-code` Zero-GC violation. Check LINQ, string concat, `new` in `Update`.
- **High draw calls** → static batching not applied / Material instance splits.
- **Physics overhead** → FixedUpdate frequency / leftover inactive Rigidbodies.
- **Script CPU** → uncached `GetComponent`, inefficient `Find` calls.

## Phase 4: SkillForge pattern recommendations
Recommend a skill from `.agent/skills/06-performance/` per bottleneck type:
- GC / hot path → `jobs-burst-optimization`, `csharp-gc-best-practices`
- Rendering / draw call → `gpu-instancing-expert`, `lod-system`
- Memory / texture → `texture-streaming-expert`, `addressables-management`
- Profiling itself → `profiling-analysis`

```
🔍 Bottleneck: <category> (<value>)
   → SkillForge: /sf-info 06-performance/<skill>
   → Apply:      /sf-add 06-performance/<skill>
```

## Phase 5: Save
Save to `production/perf-reports/perf-<YYYYMMDD>.md` (after user approval).

## Related
- Base skill: `/perf-profile` · Tech debt: `/tech-debt` · Catalog: `/sf-list 06-performance`
