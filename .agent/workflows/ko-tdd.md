---
description: 테스트 주도 개발 — 합의한 접점(seam)에서 red → green 을 수직 조각 하나씩 반복
---

# /ko-tdd — 테스트 주도 개발

> 정본: `.claude/skills/ko-tdd/SKILL.md` (예시 · 대역 기준 `tests.md`) — 읽고 그대로 따른다. MCP for Unity 가 없는 도구는 `Unity -batchmode -runTests -testPlatform EditMode` 로 테스트를 돌린다.
> 인수: `<구현할 기능 또는 고칠 버그> [게임-태그]`

**1. 접점 합의** — 공개 인터페이스와 테스트할 접점을 제안하고(각각 잡는 것 · 놓치는 것 한 줄) 사용자 확인을 받는다. 로직은 MonoBehaviour 밖, EditMode 우선.

**2. 루프** — 접점 하나 → 실패하는 테스트 하나 → 기대한 이유로 red 확인 → 통과할 만큼만 구현 → green. 반복.

**3. 완료** — 합의한 접점이 모두 green 이고 대상 게임 전체 테스트도 green. 통과 수를 보고한다. 리팩터링은 `/ko-code-review` 에서.
