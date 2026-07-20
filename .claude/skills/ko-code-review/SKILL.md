---
name: ko-code-review
description: 코드 리뷰 (한국어 wrapper) — Tiki 게임 태그·어셈블리 컨텍스트 추가
argument-hint: "<PR-번호 또는 브랜치명> [--lean | --solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash
agent: lead-programmer
---

# /ko-code-review — 한국어 코드 리뷰

Game-Studios의 `code-review` skill에 멀티 게임 컨텍스트를 더한 한국어 리뷰.

## 사용법

```
/ko-code-review PR-42
/ko-code-review feature/my-feature-v2
/ko-code-review HEAD --solo   # 1인 개발 약식 리뷰
```

## Phase 1: 변경 사항 파악

- `$1`이 PR 번호면 (`PR-N` 또는 `#N`) → `gh pr diff $1` 또는 안내
- 브랜치 명이면 → `git diff main...$1`
- `HEAD` 면 → `git diff HEAD~5 HEAD`

## Phase 2: 게임 태그 분류

변경된 파일 경로에서 게임 태그를 추출 (멀티 게임 프로젝트):
- `Assets/{GameName}/...` → 해당 게임 태그 (예: `[GAME1]`, `[GAME2]`)
- `Assets/<SharedModule>/...` → `[CORE]`
- 태그 매핑은 프로젝트 `CLAUDE.md`의 "게임 폴더 매핑" 표를 따른다.
- 단일 게임 프로젝트면 이 단계를 생략한다.

게임별로 그룹화해서 출력 헤더에 표시.

## Phase 3: 본 skill 위임

`.claude/skills/code-review/SKILL.md` 절차에 따라 진행. 추가 점검 항목 (한국어로 보고):

### Unity-specific (gameplay-code.md 준수)
- [ ] 매직 넘버 — `[SerializeField] private` 또는 데이터 ScriptableObject로 외부화 되어 있나?
- [ ] `Time.deltaTime` / `Time.fixedDeltaTime` 누락 없는지
- [ ] Hot Path (`Update`/`FixedUpdate`)에서 LINQ/string 연산/new 호출 없는지
- [ ] `GetComponent` 가 `Awake()` 캐싱 되어 있는지
- [ ] `Animator.StringToHash` 캐싱

### 멀티게임 어셈블리 (멀티 게임 프로젝트)
- [ ] 네임스페이스 `{GamePrefix}.{Category}.{Subsystem}` 준수
- [ ] **Game → <SharedModule> 단방향** 의존만 — 역방향 / 게임 간 직접 참조 금지
- [ ] Editor 코드는 `Scripts/Editor/` + Editor asmdef 내부

### 일반 (engine-agnostic)
- 본 `code-review` skill의 ADR 컴플라이언스 체크 적용

## Phase 4: 결과 출력

```
🔴 CRITICAL N건 / 🟡 WARNING N건 / 🔵 INFO N건

[GAME1]
  - <file:line> — <문제> — <제안>
[GAME2]
  - ...
```

`--lean` 모드: WARNING/INFO 생략, CRITICAL만.
`--solo` 모드: 제안만 출력, 승인 절차 생략.

## 관련

- 본 skill: `/code-review`
- 디자인 리뷰: `/design-review`
- 성능 리뷰: `/ko-perf-profile`
