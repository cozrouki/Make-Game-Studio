---
name: ko-design-graph
description: 기획 문서 프런트매터 · 관계 그래프 검사 (한국어) — design/ 문서에 표준 프런트매터(id · 상태 · 추상 단계 L0~L4 · 관계)를 붙이고, 순환 · 충돌 결정 동시 승인 · 깨진 관계 · 추상 역행 · 고아 · 오래된 문서를 찾고, 문서 하나를 바꿀 때의 영향 범위 표와 관계도를 만든다
argument-hint: "[adopt [경로 ...] | check | impact <id|경로> | map]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-design-graph — 기획 문서 그래프

`/consistency-check` 는 문서들 사이의 **값**이 서로 다른지, `/map-systems` 는 처음 시스템을 나눌 때의 **의존 관계**를 본다. 이 스킬은 기획 문서 전체를 **계속 검사 가능한 그래프**로 만든다: 문서마다 짧은 프런트매터를 붙이면 도구가 관계를 모아 구조 문제를 찾는다. 사람은 관계를 한쪽 문서에만 적고, 반대 방향(누가 이 문서에 기대나)은 도구가 계산한다.

> 방법 참고: 이민수, 『게임 기획 실무에서 바로 쓰는 AI·클로드 코드 활용법』 2부(정보 구조) · 3부 3장(관계 지도) · 18부 4장(문서 영향 검색) · 부록 D(명명 · 프런트매터). 원문은 옮기지 않고 이 템플릿 구조로 다시 썼다. 원문: `/ext gdpractice 2부` (선택 설치 · 비상업 라이선스).

도구: `python .agent/tools/design/design_graph.py` · 표준: `.agent/tools/design/standard.json` (필드 · 허용 값 · 기준 숫자 — 프로젝트가 고쳐 쓴다, 코드는 고치지 않는다).

## 프런트매터 표준

```yaml
---
id: SYS-combat            # 안정 id — 파일 이름이 바뀌어도 그대로. <대문자 접두>-<이름>
title: 전투 시스템
type: gdd                 # pillar · gdd · rule · decision · spec · voice · lore · level · pattern · schema · report · meeting
abstraction: L1           # L0 비전 · 필러 / L1 시스템 · 세계 골격 / L2 콘텐츠 · 흐름 / L3 데이터 · 수식 / L4 빌드 · QA
status: draft             # draft · review · approved · archived
owner: 기획
updated: 2026-10-30
relations:                # 한쪽에만 적는다
  requires: [SYS-input]   # 이것 없이는 성립 안 함
  affects: [SYS-economy]  # 이게 바뀌면 대상도 다시 본다
  derives_from: [PIL-core]
  conflicts_with: []      # 함께 승인될 수 없음
  supersedes: []          # 대체 (대상은 archived)
  part_of: []
---
```

- `abstraction` 은 `/map-systems` 의 Layer(Foundation · Core · Feature · Presentation — 시스템 의존 층)와 **다른 축**이다: 얼마나 추상적인가 / 얼마나 자주 바뀌나. 위(L0)일수록 짧게 쓰고 드물게 바꾼다.
- **위 문서가 아래 문서에 기대지 않는다** (DG011): 필러(L0)가 수식 문서(L3)를 `requires` 하면 수식이 바뀔 때마다 필러가 흔들린다. 참조는 아래 → 위로.
- GDD 의 `## Dependencies` 절은 그대로 쓴다 — `.claude/rules/design-docs.md` 의 "양방향 언급" 규칙은 유지되고, DG015 가 그것을 검사한다.
- 프런트매터가 없는 문서는 그래프 밖이다 (검사 안 함 — 보고에 이름이 남는다). 한 번에 다 붙이지 않아도 된다.

## adopt [경로 ...] — 프런트매터 붙이기

1. 대상 문서(인수 없으면 `design/` 중 프런트매터 없는 것 — `check` 의 '검사 안 함' 목록)를 읽는다.
2. 문서마다 초안을 만든다: id(접두 규칙 — 필러 `PIL-` · 시스템 `SYS-` · 콘텐츠 `CNT-` · 데이터 `DAT-` · 레벨 `LVL-` · 서사 `NAR-` 등, 프로젝트가 정한 게 있으면 그것), type, abstraction, status(GDD 상태 블록에서), owner, updated(파일 마지막 커밋 날짜), relations(GDD `## Dependencies` 절 · 본문에 나온 다른 시스템).
3. 초안을 표로 보여 주고 **승인받은 문서만** 맨 위에 붙인다. 본문은 고치지 않는다.
4. `check` 로 확인한다.

## check

`python .agent/tools/design/design_graph.py check` (기계 판독: `--json`). 결과를 세 묶음으로 보여 준다.

| 묶음 | 규칙 | 해야 할 일 |
|---|---|---|
| 막는 것 (error) | DG001 파싱 · DG002 필수 · DG003 값 · DG004 id 중복 · DG006 깨진 관계 · DG008 순환 · DG009 충돌 결정 동시 승인 · DG102/105 결정 카드 | 승인 · 게이트 전에 고친다 |
| 볼 것 (warn) | DG005 id 형식 · DG007 archived 를 가리킴 · DG010 · DG011 추상 역행 · DG015 GDD 한쪽 언급 · DG101 · DG103 · DG106 템플릿 안내문 남음 | 의도면 이유를 문서에 남긴다 |
| 참고 (info) | DG012 고아(폐기 후보) · DG013 허브 과부하 · DG014 오래 갱신 안 됨 · DG104 사후 확인 시기 | 정리 후보 목록으로 |

판정: error 0 이면 **PASS**, error 가 있으면 **FAIL**, 프런트매터 있는 문서가 0 이면 **NOT ASSESSED** ("그래프 검사 안 함 — adopt 먼저"). "검사 안 함" 줄(프런트매터 없는 문서)은 판정과 함께 반드시 보여 준다 — 조용히 빠진 문서가 통과로 읽히지 않게.

고아 · 오래된 문서는 지우지 않는다. 사용자에게 폐기(status `archived`) 여부를 묻는다. 분기마다 일부가 정리되는 게 건강한 상태다 — 폐기가 한 건도 없으면 정리가 안 돌고 있다는 신호다.

## impact <id | 경로> — 영향 범위

`python .agent/tools/design/design_graph.py impact SYS-economy` — 네 갈래로 찾는다:
1. 이 문서에 관계를 건 문서 (requires · derives_from · part_of → **직접**)
2. 이 문서의 `affects` 대상 (**직접**) · 직접 대상에 다시 기대는 문서 (**간접**, 2단계)
3. 본문에서 id · 제목을 언급한 문서 — 프런트매터 없는 문서 · `docs/architecture/` ADR 포함 (**약**)
4. 데이터 파일(`design/data` · `assets/data`)에서 id 언급 (**약**)

누락보다 과잉을 택한다. 표를 보여 주고 사용자가 "약" 줄을 걸러 낸다. 우선순위 · 작업 지시는 하지 않는다 — 그건 결정 카드(`/ko-design-decision`)의 영향 절에서 사람이 정한다.

## map — 관계도

`python .agent/tools/design/design_graph.py map --out design/graph.md` — Mermaid 관계도(추상 단계별 색). GitHub · VS Code 에서 바로 렌더링된다. 생성물이라 손으로 고치지 않는다. 문서가 많이 바뀐 뒤나 게이트 전에 다시 만든다.

## 스튜디오 모드

`design/` 은 planning 영역이다. 도구 실행은 누구나 할 수 있지만 프런트매터를 붙이고 고치는 것은 planning 이 한다. 게이트(`/gate-check`) 전에 `check` 결과를 근거로 첨부하면 디렉터가 구조 문제를 한 번에 본다.

## 관련

- 결정 카드: `/ko-design-decision` (impact 결과를 영향 절에 쓴다)
- 값 충돌: `/consistency-check` · 전체 GDD 검토: `/review-all-gdds`
- 시스템 분해: `/map-systems`
