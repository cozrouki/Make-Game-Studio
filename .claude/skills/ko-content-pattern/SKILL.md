---
name: ko-content-pattern
description: 콘텐츠 자동화 배치 · 레벨 메타데이터 · 패턴 라이브러리 (한국어) — 콘텐츠마다 수작업 · 룰북 · AI 중 어디까지 맡길지 다섯 질문으로 정하고, 레벨 룸 그래프(도달성 · 고립 · 막다른 길 · 양방향 · 태그 사전)를 검사하고, 재사용 패턴의 사용 현황 · 폐기 후보를 낸다
argument-hint: "[scale | tiers <tiers.json> | levels <level.json ...> | patterns <패턴 폴더> <레벨 폴더>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-content-pattern — 콘텐츠 배치 · 레벨 메타 · 패턴

`/team-level` · `level-designer` 에이전트는 **서술형** 레벨 문서를 만든다. 이 스킬은 그 옆에 **기계가 읽는 메타데이터**를 두고 구조를 검사한다. 양산 콘텐츠를 어디까지 자동화할지도 여기서 정한다.

> 방법 참고: 이민수, 『게임 기획 실무에서 바로 쓰는 AI·클로드 코드 활용법』 6부(콘텐츠 — 절차적 생성 · 제작 흐름) · 7부(레벨 — 메타데이터 · 패턴 라이브러리). 원문은 옮기지 않고 이 템플릿 구조로 다시 썼다. 원문: `/ext gdpractice 7부` (선택 설치 · 비상업 라이선스).

도구: `python .agent/tools/design/content_pattern.py` (표준 라이브러리만). 종료 코드 0 = error 없음 · 1 = error 있음 · 2 = 입력 오류.

## scale — 먼저 규모를 본다

패턴 라이브러리 · 레벨 메타데이터는 **양이 많을 때** 이득이다. 시작 전에 묻는다: 레벨(던전 · 맵) 수, 레벨 디자이너 수, 같은 구조를 반복하는가. 레벨 5개 미만이거나 디자이너 1명이면 **패턴 라이브러리는 만들지 않는다**고 권하고(도구도 CP204 info 로 알린다), `levels` 검사만 쓴다. 사용자가 그래도 원하면 진행한다.

## tiers <tiers.json> — 자동화 강도 배치

콘텐츠 종류마다 강도를 하나 고른다: `manual`(사람이 씀) · `rulebook`(규칙 · 표로 생성) · `rulebook+ai`(규칙 위에서 AI 가 변주) · `ai-first`(AI 초안, 사람이 검수).

`design/content/tiers.json`:
```json
{"items": [{"id": "CNT-npc-bark", "tier": "rulebook+ai", "volume": 200, "consistency": "mid",
            "nondeterminism_ok": true, "review_cost": "low", "incident_cost": "low", "reason": "잡담 대사 — 틀려도 사고 작음"}]}
```
다섯 질문: 양 · 일관성 요구 · 비결정성 허용 · 검수 비용 · 사고 비용. 도구가 권장 범위를 계산한다 — 사고 비용이 크거나(일관성 높음 + 비결정성 불가) 보수 쪽, 양이 많고(`--ai-volume`, 기본 100) 검수 싸고 비결정성 허용이면 AI 쪽. 실제 강도가 권장 밖이면 CP301 warn — 이유(reason)가 타당하면 그대로 둔다. 빈 이유는 CP302. 아트 에셋 생성 강도는 `/ko-art-gen` 이 따로 다룬다.

## levels <level.json ...> — 레벨 룸 그래프

`design/levels/<던전>.json`:
```json
{"id": "LVL-crypt", "start": "R01", "goal": "R09", "tags": "design/levels/tags.json",
 "rooms": [{"id": "R01", "type": "entrance", "size": "S", "tags": ["dark"], "connections": ["R02"], "eventSlots": 1,
            "patterns": ["PAT-ambush"]},
           {"id": "R02", "type": "combat", "size": "M", "tags": ["narrow"], "connections": ["R01", "R03"], "oneWay": ["R03"]}]}
```
태그 사전 `design/levels/tags.json`: `{"maxPerRoom": 5, "categories": {"분위기": ["dark"], "구조": ["narrow", "open"]}}` — 작게 유지한다. **사전에 없는 태그는 받지 않는다**(CP106) — 새 태그는 사전에 먼저 넣고(사용자 승인), AI 가 태그를 지어내지 못하게 한다.

| 묶음 | 규칙 |
|---|---|
| error | CP100 입력 구조(룸 id 중복 · start/goal 없음) · CP101 시작→목표 도달 불가 · CP102 고립 룸 · CP105 없는 룸 연결 · CP106 사전 밖 태그 |
| warn | CP104 양방향 불일치(출발 룸 `oneWay` 에 있으면 의도된 일방) · CP107 태그 수 초과 |
| info | CP103 막다른 길(보상방일 수 있음) · CP108 짧은 순환 · 분기 폭 분포 |

판정: error 0 → PASS, error → FAIL, 태그 사전이 없어 CP106 · CP107 을 못 돌렸으면 결과에 "태그 검사 안 함" 을 붙인다 (not_run). 도달 불가(CP101)는 빌드 전에 반드시 고친다.

엔진 쪽 반영: 이 JSON 은 기획 메타데이터다. 실제 레벨(Unity 씬 · Godot `.tscn` · Unreal `.umap`)과 맞추는 일은 dev 가 하고, 어긋나면 이 파일을 정본으로 본다 — 맞추는 방법은 `level-designer` · 엔진 전문가 에이전트와 정한다.

## patterns <패턴 폴더> <레벨 폴더>

패턴 파일 `design/patterns/<id>.json`: `{"id": "PAT-ambush", "status": "active", "kind": "space|npc|event", "created": "2026-01-10", "description": "..."}`. 레벨 룸의 `"patterns"` 에서 사용 수를 센다.

- CP201 없는 패턴 사용(error) · CP202 deprecated 패턴 사용(warn — 기존 사용은 보존이 원칙이라 새 사용인지 사람이 본다) · CP203 오래됐는데 안 쓰임 → deprecated 후보(info, `--stale-days` 기본 180) · CP204 레벨 5개 미만(info) · CP200 패턴 파일 구조.
- 권장 비율: 레벨 하나에 재사용 패턴이 대부분이고 고유 변주가 일부 — 변주 없이 패턴만 이어 붙이면 단조롭다. 비율은 사용 수 표로 사람이 본다.
- 패턴을 deprecated 로 바꿀 때 기존 레벨은 고치지 않는다.

## 관련

- 레벨 서술 문서 · 팀: `/team-level` · `level-designer` · 문서 그래프(`type: level` · `pattern`): `/ko-design-graph`
- 콘텐츠 수량 대조: `/content-audit` · 아트 생성 강도: `/ko-art-gen`
