---
name: map-systems
description: "게임 컨셉을 개별 시스템으로 분해하고, 의존성을 매핑하며, 설계 순서를 우선순위화하여 시스템 인덱스를 생성한다."
version: 1.0.0
tags: ["game-design", "systems", "architecture", "dependencies", "planning"]
argument-hint: "[없음: 전체 분해 실행 | 'next': 다음 미설계 시스템 선택]"
user-invocable: true
tdd_first: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - TodoWrite
---

# Map Systems — 시스템 의존성 분해 & 인덱스

## 1. 인수 파싱

두 가지 모드:
- **인수 없음** (`/map-systems`): 전체 분해 워크플로우 실행 (Phase 1~5)
- **`next`** (`/map-systems next`): 인덱스에서 우선순위 최고의 미설계 시스템 선택 → `/design-system`으로 핸드오프

---

## 2. Phase 1: 컨텍스트 읽기

**필수**:
- `doc/{GameName}/game-concept.md` — 없으면 실패: `/brainstorm` 먼저

**선택 (있으면 읽기)**:
- `doc/{GameName}/game-pillars.md`
- `doc/{GameName}/systems-index.md` — 있으면 현황 표시 후 계속 여부 확인
- `Glob doc/{GameName}/*.md` — 기존 설계된 시스템 확인

---

## 3. Phase 2: 시스템 열거 (협업)

컨셉 문서에서 시스템을 추출하고 유저와 함께 보완.

**명시적 시스템 추출**:
- Core Mechanics 섹션 → 직접 언급된 시스템
- Core Loop 섹션 → 각 루프를 구동하는 시스템
- MVP 정의 섹션 → 필수 기능 = 필수 시스템

**암시적 시스템 도출** (컨셉에 없지만 반드시 필요):
- 저장/불러오기, 입력 처리, 오디오 관리, UI/HUD
- 씬 전환, 오브젝트 풀링
- 컨셉에서 암시하는 인프라 시스템

모든 시스템 후보를 제시하고 AskUserQuestion으로 추가/제거 요청.

---

## 4. Phase 3: 분류 (Classification)

각 시스템을 다음 4가지로 분류:

| 계층 | 설명 | 예시 |
|------|------|------|
| **Foundation** | 다른 모든 것이 의존하는 핵심 인프라 | Input, Save/Load, AudioManager |
| **Core Gameplay** | 게임을 게임으로 만드는 핵심 루프 | Combat, Movement, Inventory |
| **Content** | Core Gameplay 위에 쌓이는 콘텐츠 | Quest, Dialogue, Level Progression |
| **Polish** | 느낌과 경험 향상 | VFX, Cinemachine, Juice |

---

## 5. Phase 4: 의존성 매핑 (Dependency Map)

각 시스템의 의존성을 명시:

```
CombatSystem
  → depends on: InputSystem, HealthSystem, AudioManager
  → depended on by: QuestSystem, ProgressionSystem

InventorySystem
  → depends on: SaveSystem, UISystem
  → depended on by: CraftingSystem, ShopSystem
```

순환 의존성을 발견하면 즉시 경고하고 인터페이스 추상화 제안.

---

## 6. Phase 5: 우선순위화 & 인덱스 생성

**우선순위 기준**:
1. 다른 시스템의 의존 수 (많을수록 먼저)
2. 핵심 루프에 얼마나 중요한가
3. 기둥과의 연관성
4. 구현 난이도 (의존성 적은 것부터)

**시스템 인덱스 형식**:

```markdown
# Systems Index: {GameName}
업데이트: {날짜}

## Foundation (먼저 설계)
| 시스템 | 우선순위 | 의존처 | GDD 상태 |
|--------|----------|--------|----------|
| InputSystem | P0 | 없음 | ✅ 완료 |

## Core Gameplay
| 시스템 | 우선순위 | 의존처 | GDD 상태 |
|--------|----------|--------|----------|
| CombatSystem | P1 | InputSystem, HealthSystem | 🔲 미작성 |

## Content
...

## Polish
...
```

저장 경로: `doc/{GameName}/systems-index.md`

---

## 7. `next` 모드

`/map-systems next` 호출 시:
1. 인덱스를 읽어 GDD 미작성 시스템 중 최고 우선순위 선택
2. "다음 설계할 시스템: [시스템명]. `/design-system [시스템명]`을 실행할까요?" 확인
3. 확인 시 해당 스킬로 핸드오프

## TDD Contract

시스템 인덱스는 문서 산출물. 검증은 의존성 그래프의 순환 없음으로 측정.

## Related Skills
- `@brainstorm` — 컨셉 문서 생성
- `@design-system` — 개별 시스템 GDD 작성
- `@design-review` — 완성된 GDD 검토
