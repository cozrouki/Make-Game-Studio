---
description: 한국어 코드 리뷰 — 게임 태그 분류 + Unity 코딩 규칙 점검
---

# /ko-code-review — 한국어 코드 리뷰

> Antigravity 워크플로. 변경분을 한국어로 리뷰하고 Unity/멀티게임 컨텍스트를 더한다.
> 인수: `<PR번호 | 브랜치 | HEAD> [--lean] [--solo]`  예) `/ko-code-review feature/my-feature`

## 절차

**1. 변경 사항 파악**
- `$1`이 PR 번호(`PR-N`/`#N`)면 → `gh pr diff $1`
- 브랜치명이면 → `git diff main...$1`
- `HEAD` 면 → `git diff HEAD~5 HEAD`

**2. 게임 태그 분류** (멀티 게임 프로젝트) — 변경 파일 경로에서 태그 추출:
- `Assets/{GameName}/...` → 해당 게임 태그, `Assets/SharedCore/...` → `[CORE]`
- 매핑은 `AGENTS.md` §6 "게임 폴더 매핑" 표를 따른다. 단일 게임이면 생략.

**3. 본 절차 위임** — `.claude/skills/code-review/SKILL.md` 절차 적용. Unity 추가 점검(`.agent/rules/gameplay-code.md` 준수):
- [ ] 매직 넘버 → `[SerializeField] private` 또는 ScriptableObject 외부화
- [ ] `Time.deltaTime` / `Time.fixedDeltaTime` 누락 없음
- [ ] Hot Path(`Update`/`FixedUpdate`)에 LINQ/string/new 없음
- [ ] `GetComponent` `Awake()` 캐싱, `Animator.StringToHash` 캐싱
- [ ] 네임스페이스 `{GamePrefix}.{Category}.{Subsystem}` 준수, **Game→SharedCore 단방향** 의존

**4. 결과 출력** (한국어)
```
🔴 CRITICAL N / 🟡 WARNING N / 🔵 INFO N
[GAME1]
  - <file:line> — <문제> — <제안>
```
`--lean`=CRITICAL만, `--solo`=제안만·승인 절차 생략.
