---
name: ko-sprint-plan
description: 스프린트 계획 수립 (한국어 wrapper) — Game-Studios의 sprint-plan을 호출
argument-hint: "<스프린트-번호> [기간일수=14]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion
agent: producer
---

# /ko-sprint-plan — 스프린트 계획 수립

Game-Studios의 `sprint-plan` skill을 한국어 인터페이스로 래핑합니다. 산출물은 `production/sprints/sprint-<번호>.md`에 저장됩니다.

## 사용법

```
/ko-sprint-plan 7
/ko-sprint-plan 7 10        # 10일짜리 스프린트
/ko-sprint-plan 7 14 --solo  # 1인 모드
```

## Phase 1: 인수 파싱

- `$1` = 스프린트 번호 (필수)
- `$2` = 기간 일수 (기본값 14)
- `--solo` 플래그 = 솔로 개발자 모드 (간소화된 리뷰)

## Phase 2: 컨텍스트 수집

다음을 읽고 컨텍스트를 만든다:
- `doc/work_log.md` 최근 50줄 — 직전 작업 흐름
- `doc/{ActiveGame}/task.md` — 현재 게임의 태스크 상태
- `production/session-state/active.md` — 활성 게임/Epic/Feature
- 이전 스프린트가 있다면 `production/sprints/sprint-<N-1>.md` 회고 섹션

## Phase 3: 본 skill 위임

`.claude/skills/sprint-plan/SKILL.md`의 절차에 따라 진행하되, 다음을 한국어로 출력:
- 스프린트 목표 (한 줄)
- 게임 태그별 작업 (`[NZS][EA][MMC][NJM][KC][CORE]`)
- 인수받은 기간에 맞춘 스프린트 capacity 추정
- 리스크 / 의존성

## Phase 4: 저장 및 확인

- 산출물 경로: `production/sprints/sprint-$1.md`
- Write 도구로 저장 전 사용자 승인 요청 (한국어)
- 저장 후 `active.md`의 "다음 할 것" 섹션에 스프린트 ID 링크 추가 제안

## 관련

- 본 skill: `/sprint-plan` (Game-Studios)
- 상태 확인: `/sprint-status`
- 사이클 진행: `/ko-story-cycle`
