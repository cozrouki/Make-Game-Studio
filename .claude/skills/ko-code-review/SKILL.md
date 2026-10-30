---
name: ko-code-review
description: 코드 리뷰 (한국어 wrapper) — 멀티 게임 태그·어셈블리 컨텍스트 추가
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
- `<코드 루트>/{GameName}/...` → 해당 게임 태그 (예: `[GAME1]`, `[GAME2]`) — 코드 루트는 Unity `Assets/` · Godot `src/` · Unreal `Source/`
- `<코드 루트>/<SharedModule>/...` → `[CORE]`
- 태그 매핑은 프로젝트 `CLAUDE.md`의 "게임 폴더 매핑" 표를 따른다.
- 단일 게임 프로젝트면 이 단계를 생략한다.

게임별로 그룹화해서 출력 헤더에 표시.

## Phase 2-1: 결정적 검사 먼저

AI 리뷰 전에 기계 검사를 돌리고 결과를 리뷰 보고에 그대로 붙인다 (하네스: 결정적 센서 + AI 센서). 엔진별 검사기는 `.claude/docs/engine-layers.md` — Godot · Unreal 은 아직 검사기가 없으므로 보고 첫 줄에 "결정적 검사 없음 (<엔진>) — AI 리뷰만" 이라고 적는다.
- (Unity) `python .agent/tools/lint/unity_lint.py <바뀐 .cs>` — UL001~008. 오탐은 `// unity-lint: ignore ULxxx` 와 이유가 있는지 본다.
- (Unity) Unity 공식 분석기(`Assets/Analyzers/Microsoft.Unity.Analyzers.dll`)가 있으면 Unity 콘솔 · 컴파일 로그의 UNT 경고를 확인한다. 없으면 `prereq.py install unity-analyzers` 를 권한다.
- 같은 지적이 이 프로젝트에서 반복되면(스튜디오 모드) `studio.py lesson add <종류> --by <역할> --note "…"` 로 기록하라고 보고에 적는다.

## Phase 3: 본 skill 위임

`.claude/skills/code-review/SKILL.md` 절차에 따라 진행. 추가 점검 항목 (한국어로 보고):

### 엔진 규칙 (gameplay-code.md — 공통 절 + 프로젝트 엔진 절)
- [ ] 매직 넘버 — 에디터 노출 또는 데이터 자산(ScriptableObject · Resource · Data Asset)으로 외부화 되어 있나?
- [ ] 프레임 시간(`Time.deltaTime` · `delta` · `DeltaTime`) 누락 없는지
- [ ] 매 프레임 코드(`Update` · `_process` · `Tick`)에서 할당 · 문자열 연산 · 탐색 없는지
- [ ] 탐색 캐싱 (Unity `GetComponent` → `Awake` · Godot `@onready` · Unreal `BeginPlay`)
- [ ] Unity: `Animator.StringToHash` 캐싱 · Godot: 정적 타입 · signal 통신 · Unreal: UObject 포인터에 `UPROPERTY()` · 필요 없는 Tick 꺼짐

### 변경 범위 · 단순성 (AGENTS.md §3-1)
- [ ] 모든 변경 줄이 요청 · 스토리로 거슬러 올라가나? (관련 없는 리팩터링 · 포맷 정리 · 주석 수정이 섞이지 않았나)
- [ ] 요청 · GDD 에 없는 기능 · 설정 옵션 · 확장 지점이 들어가지 않았나?
- [ ] 시스템 경계가 아닌 곳에 구현 하나짜리 인터페이스 · 팩토리 · 매니저를 만들지 않았나?
- [ ] 같은 일을 하는 더 짧은 코드가 있나? (있으면 "과잉" 으로 지적)
- [ ] 내 변경 때문에 안 쓰이게 된 코드만 지웠나? (원래 있던 죽은 코드는 지우지 않고 보고)

### 멀티게임 어셈블리 (멀티 게임 프로젝트)
- [ ] 네임스페이스 `{GamePrefix}.{Category}.{Subsystem}` 준수
- [ ] **Game → <SharedModule> 단방향** 의존만 — 역방향 / 게임 간 직접 참조 금지 (Unity asmdef · Unreal `*.Build.cs` · Godot 은 폴더 규칙)
- [ ] Editor 코드 격리 (Unity `Scripts/Editor/` + Editor asmdef · Godot `@tool` 스크립트는 `editor/` · Unreal Editor 모듈)

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
