---
description: 스토리 구현 사이클 (한국어) — 준비 점검 → 구현 → 리뷰 → 완료 처리
---

# /ko-story-cycle — 스토리 구현 사이클

> Antigravity 워크플로. 스토리 하나를 준비 점검부터 완료까지 한 흐름으로 진행.
> 인수: `<스토리-id> [--skip-review]`  예) `/ko-story-cycle STORY-042`

## 절차

**1. 인수 + 컨텍스트** — `$1`=스토리 ID(예 `STORY-042`, `[GAME1]-S012`). 스토리 문서를 `production/stories/$1.md` 또는 `doc/*/task.md` 내부 참조에서 찾는다. 게임 태그 파싱(`AGENTS.md` §6 매핑 참조).

**2. 준비 점검** — `.claude/skills/story-readiness/SKILL.md` 절차 적용: 디자인 doc 필수 섹션·의존성 명시·Acceptance Criteria 검증 가능 여부. 차단 사항 있으면 보고 후 진행 중단 옵션 제시.

**3. 구현** — `.claude/skills/dev-story/SKILL.md` 절차 적용. 추가:
- 게임 태그 어셈블리(`{GamePrefix}.{Category}.{Subsystem}`) 확인
- `.agent/rules/gameplay-code.md` 규칙 적용 (매직 넘버 금지·GetComponent 캐싱·Zero-GC·FixedUpdate)
- 관련 코드 패턴은 `.agent/skills/02-gameplay/` 등 카탈로그의 SKILL.md 를 참조하고, 필요하면 `templates/` 의 `.cs.txt` 를 복사·주입

**4. 코드 리뷰 (옵션)** — `--skip-review` 없으면 `.claude/skills/code-review/SKILL.md` 절차 적용 + 게임 태그 헤더 표시·네임스페이스/어셈블리 의존 역전 점검. (`/ko-code-review` 워크플로 재사용 가능)

**5. 완료 처리** — `.claude/skills/story-done/SKILL.md` 절차 + 후처리:
- `doc/{ActiveGame}/task.md` 항목 완료 마크(사용자 승인)
- `doc/work_log.md` 최상단에 한 줄 요약(최신순, 게임 태그 포함)
- `active.md` "완료된 항목" 업데이트 제안

## 관련
- 단일 단계 → `/ko-code-review` / 각 `.claude/skills/*` 절차
- 진행률 확인 → `/sprint-status`
