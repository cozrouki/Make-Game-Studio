---
name: ko-prototype
description: 프로토타입 빠른 진행 (한국어 wrapper) — brainstorm → quick-design → prototype 체이닝
argument-hint: "<게임-태그> <컨셉 한 줄 설명>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion
agent: prototyper
---

# /ko-prototype — 컨셉에서 프로토타입까지

아이디어 한 줄을 받아 브레인스토밍 → 간이 디자인 → 프로토타입 폴더 생성까지 한 번에.

## 사용법

```
/ko-prototype EA "엘리베이터에서 적과 마주쳤을 때 회피 액션"
/ko-prototype KC "큐브 회전 시 환경 적응 반응"
/ko-prototype NEW "신규 게임 컨셉: 시간 역행 퍼즐"
```

## Phase 1: 인수

- `$1` = 게임 태그 (프로젝트 `CLAUDE.md` 게임 폴더 매핑 표의 태그) 또는 `NEW` (신규 게임)
- `$2..` = 컨셉 설명 (자유서술)

## Phase 2: 브레인스토밍 (brainstorm)

`.claude/skills/brainstorm/SKILL.md` 호출. 한국어로 다음을 산출:
- 아이디어 변형 3-5개
- 각 변형의 핵심 메커니즘
- 플레이어 판타지 (한 줄)
- 비교 레퍼런스 게임 1-2개

사용자에게 선호하는 변형 선택을 묻는다 (AskUserQuestion).

## Phase 3: 간이 디자인 (quick-design)

선택된 변형에 대해 `.claude/skills/quick-design/SKILL.md` 호출:
- 핵심 루프 (한 단락)
- 입력 → 시스템 → 피드백 흐름도
- 가장 위험한 가정 1개 (프로토타입으로 검증할 것)
- 성공 판정 기준 (정량 가능하면 수치 포함)

산출물 임시 경로: `prototypes/$1-<slug>/CONCEPT.md`

## Phase 4: 프로토타입 폴더 생성 (prototype)

`.claude/skills/prototype/SKILL.md` 호출. 추가:

### 폴더 구조
```
prototypes/$1-<slug>/
├── CONCEPT.md           (Phase 3 산출물)
├── README.md            (Phase 4 작성, 한국어)
└── (옵션) PROBE.md      (Phase 3에서 식별한 가정 검증 계획)
```

### Unity 통합 고려
- `$1`이 `NEW`면 → 신규 어셈블리 디렉토리 `Assets/<NewGame>/Scripts/Prototype/` 제안
- 기존 게임이면 → 해당 게임의 `Scripts/Prototype/` 또는 `Scripts/Experiments/`
- `prototype-code.md` 룰 적용 (느슨한 표준, README 필수)

### SkillForge 패턴 참조
컨셉에 따라 관련 SkillForge skill 추천:
- 전투/액션 → `/sf-info 02-gameplay/combat-system-pro` 또는 `ability-skill-system`
- 퍼즐 → `/sf-info 02-gameplay/grid-puzzle-mechanics` 등
- AI/적 → `/sf-info 02-gameplay/ai-behavior-trees`

## Phase 5: 후처리

- `active.md`의 "다음 할 것" 섹션에 프로토타입 검증 항목 추가 제안
- `doc/work_log.md`에 한 줄 기록 (`[<tag>] /ko-prototype: <slug>`)

## 관련

- 단일 단계: `/brainstorm`, `/quick-design`, `/prototype`
- 플레이테스트: `/playtest-report`
- 본격 구현 전환: `/ko-story-cycle`
