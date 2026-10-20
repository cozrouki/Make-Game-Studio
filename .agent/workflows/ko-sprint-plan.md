---
description: 스프린트 계획 수립 (한국어) — production/sprints/sprint-<번호>.md 산출
---

# /ko-sprint-plan — 스프린트 계획 수립

> Antigravity 워크플로. Claude Code의 `.claude/skills/ko-sprint-plan` 과 동일한 절차의 Antigravity 네이티브 진입점.
> 인수: `<스프린트-번호> [기간일수=14] [--solo]`  예) `/ko-sprint-plan 7 10`

## 절차

**1. 인수 파싱** — `$1`=스프린트 번호(필수), `$2`=기간 일수(기본 14), `--solo`=1인 모드(리뷰 간소화).

**2. 컨텍스트 수집** — 다음을 읽어 컨텍스트를 만든다:
- `doc/work_log.md` 상단 50줄 (최신순) — 직전 작업 흐름
- `doc/{ActiveGame}/task.md` — 현재 게임 태스크 상태
- `production/session-state/active.md` — 활성 게임/Epic/Feature
- 이전 스프린트가 있으면 `production/sprints/sprint-<N-1>.md` 회고 섹션

**3. 본 절차 위임** — `.claude/skills/sprint-plan/SKILL.md` 를 읽어 그 절차를 따르되, 다음을 **한국어**로 출력:
- 스프린트 목표 (한 줄)
- 게임 태그별 작업 (프로젝트에서 정의한 태그 셋 — `AGENTS.md` §6 게임 폴더 매핑 참조)
- 인수 기간에 맞춘 capacity 추정
- 리스크 / 의존성

**4. 저장 및 확인** — `production/sprints/sprint-$1.md` 로 저장(사용자 승인 후). 저장 뒤 `active.md` "다음 할 것"에 스프린트 ID 링크 추가 제안.

## 관련
- 상태 확인 → `/sprint-status` (또는 Antigravity에서 해당 워크플로)
- 사이클 진행 → `/ko-story-cycle`
