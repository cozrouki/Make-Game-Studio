---
name: ko-story-cycle
description: 스토리 사이클 진행 (한국어 wrapper) — story-readiness → dev-story → story-done을 체이닝
argument-hint: "<스토리-id> [--skip-review]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, AskUserQuestion
agent: lead-programmer
---

# /ko-story-cycle — 스토리 구현 사이클

스토리 하나를 처음부터 끝까지(준비 점검 → 구현 → 완료 처리) 한국어 흐름으로 진행합니다.

## 사용법

```
/ko-story-cycle STORY-042
/ko-story-cycle STORY-042 --skip-review   # 코드 리뷰 생략 (소규모 변경)
```

## Phase 1: 인수 + 컨텍스트

- `$1` = 스토리 ID (예: `STORY-042`, `[GAME1]-S012`)
- 스토리 문서를 찾는다: `production/stories/$1.md` 또는 `doc/*/task.md` 내부 참조
- 게임 태그를 파싱 (프로젝트에서 정의한 태그 셋, 예: `[GAME1][GAME2][CORE]`)

## Phase 2: 준비 점검 (story-readiness)

`.claude/skills/story-readiness/SKILL.md` 호출:
- 디자인 doc 8개 필수 섹션 존재 여부
- 의존성 명시
- Acceptance Criteria 검증 가능 여부
- 차단 사항 있으면 사용자에게 보고하고 진행 중단 옵션 제시

## Phase 3: 구현 (dev-story)

`.claude/skills/dev-story/SKILL.md` 호출. 추가 조치:
- 게임 태그에 해당하는 어셈블리(`{GamePrefix}.{Category}.{Subsystem}`) 확인
- `gameplay-code.md` 규칙 적용 (매직 넘버 금지, GetComponent 캐싱, Zero-GC, FixedUpdate)
- SkillForge 카탈로그에서 관련 패턴이 있는지 사용자에게 안내: `/sf-list 02-gameplay` 등

## Phase 4: 코드 리뷰 (옵션)

`--skip-review`가 없으면 `.claude/skills/code-review/SKILL.md` 호출. 멀티게임 컨텍스트 추가:
- 변경된 게임 태그를 출력 헤더에 표시
- 네임스페이스 위반 / 어셈블리 의존 역전 추가 점검

## Phase 5: 완료 처리 (story-done)

`.claude/skills/story-done/SKILL.md` 호출 + 문서 후처리:
- `doc/{ActiveGame}/task.md` 해당 항목을 완료로 마크 (Edit 도구, 사용자 승인)
- `doc/work_log.md` 최상단에 한 줄 요약 추가 (최신순, 게임 태그 포함)
- `active.md`의 "완료된 항목" 섹션 업데이트 제안

## 관련

- 단일 단계만 실행: `/story-readiness`, `/dev-story`, `/code-review`, `/story-done`
- 사이클 종료 후 다음 스토리: `/sprint-status` 로 진행률 확인
