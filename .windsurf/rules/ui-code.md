---
trigger: glob
globs: src/ui/**
description: UI Code Rules
---
<!-- 생성물: scripts/gen-rule-mirrors.py — 직접 편집 금지 · 정본: .claude/rules/ui-code.md -->

# UI Code Rules

- UI must NEVER own or directly modify game state — display only, use commands/events to request changes
- All UI text must go through the localization system — no hardcoded user-facing strings
- Support both keyboard/mouse AND gamepad input for all interactive elements
- All animations must be skippable and respect user motion/accessibility preferences
- UI sounds trigger through the audio event system, not directly
- UI must never block the game thread
- Scalable text and colorblind modes are mandatory, not optional
- Test all screens at minimum and maximum supported resolutions
