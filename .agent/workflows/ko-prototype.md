---
description: 컨셉 → 프로토타입 (한국어) — brainstorm → quick-design → prototype 체이닝
---

# /ko-prototype — 컨셉에서 프로토타입까지

> Antigravity 워크플로. 아이디어 한 줄을 브레인스토밍 → 간이 디자인 → 프로토타입 폴더까지.
> 인수: `<게임-태그 | NEW> <컨셉 한 줄>`  예) `/ko-prototype NEW "시간 역행 퍼즐"`

## 절차

**1. 인수** — `$1`=게임 태그(`AGENTS.md` §6 매핑) 또는 `NEW`(신규), `$2..`=컨셉 설명.

**2. 브레인스토밍** — `.claude/skills/brainstorm/SKILL.md` 절차로 한국어 산출: 아이디어 변형 3~5개·각 핵심 메커니즘·플레이어 판타지(한 줄)·레퍼런스 게임 1~2개. 사용자에게 선호 변형을 질문.

**3. 간이 디자인** — 선택 변형에 `.claude/skills/quick-design/SKILL.md` 절차: 핵심 루프·입력→시스템→피드백 흐름·가장 위험한 가정 1개·성공 판정 기준. 임시 경로 `prototypes/$1-<slug>/CONCEPT.md`.

**4. 프로토타입 폴더 생성** — `.claude/skills/prototype/SKILL.md` 절차. 구조:
```
prototypes/$1-<slug>/
├── CONCEPT.md      (3단계 산출물)
├── README.md       (한국어)
└── PROBE.md        (옵션 — 가정 검증 계획)
```
Unity 통합: `NEW`면 `Assets/<NewGame>/Scripts/Prototype/` 제안, 기존 게임이면 해당 게임 `Scripts/Prototype/`. `.agent/rules/prototype-code.md` 적용(느슨한 표준, README 필수). 컨셉별 관련 패턴은 `.agent/skills/02-gameplay/` 카탈로그 SKILL.md 참조(전투 `combat-system-pro`/`ability-skill-system`, 퍼즐 `grid-puzzle-mechanics`, AI `ai-behavior-trees`).

**5. 후처리** — `active.md` "다음 할 것"에 검증 항목 추가 제안, `doc/work_log.md`에 `[<tag>] /ko-prototype: <slug>` 한 줄 기록.
