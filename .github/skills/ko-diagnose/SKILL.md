---
name: ko-diagnose
description: "어려운 버그 · 성능 회귀 진단 — 재현 루프 → 최소화 → 가설 → 계측 → 수정 + 회귀 테스트 → 정리"
---
<!-- 생성물: scripts/gen-rule-mirrors.py — 직접 편집 금지 · 정본: .agent/workflows/ko-diagnose.md -->

# /ko-diagnose

어려운 버그 · 성능 회귀 진단 — 재현 루프 → 최소화 → 가설 → 계측 → 수정 + 회귀 테스트 → 정리

**정본 절차: `.agent/workflows/ko-diagnose.md` — 이 파일을 먼저 읽고 그 절차를 그대로 따른다.**
절차가 `.claude/skills/<이름>/SKILL.md` 를 가리키면 그 파일도 읽고 따른다 (이 도구에서 슬래시로 호출할 수 없는 스킬).
페르소나 · 표준은 `AGENTS.md` 를 따른다.

인수: 사용자가 요청과 함께 준 값.
