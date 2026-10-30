---
name: ko-data-schema
description: 게임 데이터 스키마 우선 설계 · 검사 (한국어) — GDD 튜닝 값을 데이터 테이블로 옮길 때 스키마 → enum → 데이터 행 순서로 만들고, 타입 · 범위 · enum · 깨진 참조 · 키 중복 · 필수 값을 검사하고, 스키마 설명 문서를 자동 생성한다. 엔진 데이터 자산(ScriptableObject · Resource · DataTable)으로 넘기기 전
argument-hint: "[design <시스템 GDD> | check <schema.json> | doc <schema.json>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-data-schema — 스키마 우선 데이터 설계

GDD 의 `## Tuning Knobs` 는 값과 안전 범위를 말하지만, 그 값이 실제로 들어갈 **데이터 테이블**의 모양은 정하지 않는다. 이 스킬은 그 다리다. 순서를 강제한다: **스키마를 먼저 정하고, enum 을 고정하고, 그다음에 데이터 행을 넣는다.** 행부터 넣으면 나중에 열 의미가 바뀌어 참조가 조용히 깨진다.

> 방법 참고: 이민수, 『게임 기획 실무에서 바로 쓰는 AI·클로드 코드 활용법』 3부(시스템 기획 — 스키마 우선 · 관계 지도) · 10부 1장(정합성 검사). 원문은 옮기지 않고 이 템플릿 구조로 다시 썼다. 원문: `/ext gdpractice 3부` (선택 설치 · 비상업 라이선스).

도구: `python .agent/tools/design/data_schema.py` (표준 라이브러리만). 종료 코드 0 = error 없음 · 1 = error 있음 · 2 = 스키마 파일 없음 · JSON 오류.

## design <시스템 GDD> — 스키마 만들기

1. GDD 의 `## Tuning Knobs` · `## Formulas` · `design/registry/entities.yaml` 을 읽어 테이블 후보(무엇이 행인가 — 몬스터 · 아이템 · 스킬 …)와 필드를 뽑는다.
2. `design/data/schema.json` 초안:
   ```json
   {"owner": "기획",
    "enums": {"Element": ["NONE", "FIRE", "ICE"]},
    "tables": {
      "Monster": {"source": "design/data/monster.csv", "key": "id", "desc": "몬스터 기본 능력치",
        "fields": {"id": {"type": "string", "pattern": "^MON_[0-9]{3}$"},
                   "hp": {"type": "int", "min": 1, "max": 99999, "desc": "GDD SYS-combat Tuning Knobs"},
                   "element": {"type": "enum", "enum": "Element"},
                   "drop": {"type": "ref", "table": "Item", "optional": true},
                   "tags": {"type": "list", "item": "string", "optional": true}}},
      "Item": {"source": "design/data/item.json", "key": "id", "fields": {"id": {"type": "string"}}}}}
   ```
   - 타입: string · int · float · bool · enum · ref(다른 테이블 키) · list(`item` 타입, CSV 는 `a;b;c`).
   - **enum 0번은 '미지정' 자리**(NONE · UNSPECIFIED 등)로 비워 두고 의미 값은 1번부터 — 초기화되지 않은 값이 의미 있는 값(FIRE)으로 읽히는 사고를 막는다.
   - min · max 는 GDD 의 안전 범위에서 가져온다. 범위가 GDD 에 없으면 사용자에게 묻는다.
3. 사용자 승인 후 스키마를 쓴다. 스키마는 기획 결정이다 — 열 의미를 바꾸면 `/ko-design-decision` 카드를 남긴다.
4. 그다음에 데이터 행(CSV · JSON)을 채운다. AI 가 행을 대량 생성해도 되지만 반드시 `check` 를 통과해야 넘긴다.

## check <schema.json>

```
python .agent/tools/design/data_schema.py check design/data/schema.json [--json]
```

| 묶음 | 규칙 |
|---|---|
| error | DS001 스키마 오류 · DS003 데이터 파일 읽기 실패 · DS005 타입 위반 · DS007 깨진 참조 · DS008 키 중복 · 빈 키 · DS009 필수 값 비어 있음 |
| warn | DS002 enum 0번이 미지정 이름 아님 · DS003 데이터 파일 없음 · DS004 열 불일치 · DS005 범위 · pattern 위반 · DS006 enum 밖 값 · 필수 필드에 0번 값 · DS010 이유 없는 `_ignore` |

판정: error 0 → PASS · error → FAIL · 종료 코드 2 → NOT ASSESSED. **"검사 안 함"** 줄(데이터 파일이 없는 테이블 · 데이터 없는 테이블을 가리키는 참조 · 깨진 스키마)은 판정과 함께 반드시 보여 준다.

의도된 예외(아직 없는 아이템을 다음 패치에서 넣는 등)는 그 행에 `_ignore` 를 단다 — CSV `_ignore` 열 `"DS007: 다음 패치에서 추가"`, JSON `"_ignore": "DS007: 이유"`. 이유 없는 예외는 DS010 으로 드러난다. 오탐이라고 판단한 것도 이렇게 **이유를 남겨서** 건너뛴다.

## doc <schema.json>

```
python .agent/tools/design/data_schema.py doc design/data/schema.json --out design/data/schema.md
```
enum 표 · 테이블별 필드표 · 참조 관계(Mermaid)를 만든다. 생성물이라 손으로 고치지 않는다 — 스키마를 고치고 다시 만든다. 프런트매터(`type: schema` · `abstraction: L3`)가 붙어 `/ko-design-graph` 그래프에 들어간다.

## 엔진 데이터로 넘기기

스키마 · CSV 는 엔진 중립 기획 정본이다. 엔진 쪽 반영은 dev 가 하고(`.claude/docs/engine-layers.md`), 방법은 엔진 전문가 에이전트와 정한다:
- Unity: CSV → ScriptableObject 임포터(에디터 스크립트) · enum 은 C# enum 으로 생성 (0번 = None)
- Godot: CSV → `Resource`(`.tres`) 생성 스크립트 또는 런타임 로더
- Unreal: CSV → DataTable (`USTRUCT` 행 구조 — 열 이름을 스키마와 맞춘다)
엔진 쪽에서 열을 바꾸고 싶으면 스키마를 먼저 고친다 (스키마가 정본).

## 관련

- 값 충돌 · 엔티티 레지스트리: `/consistency-check` · 밸런스 이상치: `/balance-check` · 시뮬레이션: `/ko-balance-sim`
- 결정 기록: `/ko-design-decision` · 문서 그래프: `/ko-design-graph`
