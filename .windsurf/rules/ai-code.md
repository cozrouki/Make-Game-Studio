---
trigger: glob
globs: src/ai/**, Assets/**/AI/**/*.cs, Assets/**/Ai/**/*.cs, Assets/**/ai/**/*.cs, Source/**/AI/**/*.h, Source/**/AI/**/*.cpp, Source/**/Ai/**/*.h, Source/**/Ai/**/*.cpp, Source/**/ai/**/*.h, Source/**/ai/**/*.cpp
description: AI Code Rules
---
<!-- 생성물: scripts/gen-rule-mirrors.py — 직접 편집 금지 · 정본: .claude/rules/ai-code.md -->

# AI Code Rules

- AI update budget: 2ms per frame maximum — profile to verify
- All AI parameters must be tunable from data files (behavior tree weights, perception ranges, timers)
- AI must be debuggable: implement visualization hooks for all AI state (paths, perception cones, decision trees)
- AI should telegraph intentions — players need time to read and react
- Prefer utility-based or behavior tree approaches over hard-coded if/else chains
- Group AI must support formation, flanking, and role assignment from data
- All AI state machines must log transitions for debugging
- Never trust AI input from the network without validation
