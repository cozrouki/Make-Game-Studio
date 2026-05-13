---
name: design-system
description: "단일 게임 시스템의 GDD를 섹션별로 협업하여 작성한다. 의존성을 사전 조사하고 승인된 섹션을 즉시 파일에 기록하는 Incremental Section Writing 방식."
version: 1.0.0
tags: ["game-design", "GDD", "documentation", "design-system"]
argument-hint: "<시스템명> (예: combat-system, inventory, dialogue)"
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

# Design System — 시스템 GDD 작성

## 1. 인수 파싱 & 검증

시스템 이름 인수가 **필수**. 없으면 실패:
> "사용법: `/design-system <시스템명>` — 예: `/design-system combat-system`
> `/map-systems`를 먼저 실행해 시스템 인덱스를 생성하세요."

시스템명을 kebab-case로 정규화 (예: "전투 시스템" → `combat-system`).

---

## 2. 컨텍스트 수집 (Read Phase)

질문 전에 관련 문서를 모두 읽는다.

**필수 읽기**:
- `doc/{GameName}/game-concept.md` — 없으면 실패: `/brainstorm` 먼저 실행
- `doc/{GameName}/systems-index.md` — 없으면 실패: `/map-systems` 먼저 실행
- 시스템 인덱스에서 대상 시스템 확인. 없으면 경고 후 계속 여부 확인.

**의존성 읽기**:
- 시스템 인덱스에서 상류(upstream) 의존성 식별 → GDD가 있으면 읽기
- 하류(downstream) 의존성 식별 → GDD가 있으면 읽기
- 각 의존 GDD에서: 핵심 인터페이스, 수식, 엣지 케이스, 튜닝 값 추출

**선택적 읽기**:
- `doc/{GameName}/game-pillars.md` (있으면)
- `doc/{GameName}/{system-name}.md` (있으면 재개, 처음부터 재작성 금지)
- `Glob doc/{GameName}/*.md` — 주제 관련 GDD 탐색

---

## 3. 협업 설계 (섹션별 순차 작성)

각 섹션마다: **초안 → 검토 → 승인 → 즉시 파일 기록** 사이클을 반복.

### 파일 골격 먼저 생성
```
"이 구조로 doc/{GameName}/{system-name}.md를 생성해도 될까요?"
```
승인 시 모든 섹션 헤더가 있는 빈 파일 생성 후 섹션별로 채워나간다.

### 섹션 1: Overview
시스템이 무엇을 하는가? 한 문단 요약.
- 이 시스템의 목적은?
- 핵심 루프에서 어떤 역할인가?
- 기반이 되는 다른 시스템은?

### 섹션 2: Player Fantasy
플레이어가 이 시스템을 통해 어떤 감정을 느끼는가?
- 이 시스템을 사용할 때의 감정적 약속은?
- 어떤 MDA 미학을 지원하는가?
- 기둥과 어떻게 연결되는가?

### 섹션 3: Detailed Rules
모호함 없이 구현 가능한 수준의 규칙 명세.
- 스텝별 동작 흐름은?
- 플레이어가 내리는 결정은?
- 상태 전이 조건은?

### 섹션 4: Formulas
모든 수학은 명확한 변수와 함께 정의.
```
damage = base_damage * weapon_multiplier * crit_multiplier * (1 - resistance)
```
- 수식에 사용된 모든 변수 정의
- 예시 값으로 결과 검증
- 단위 명시 (HP, %, 초)

### 섹션 5: Edge Cases
비정상적 상황 처리.
- 경계값에서 시스템이 어떻게 동작하는가?
- 두 시스템이 충돌하면?
- 플레이어가 의도하지 않은 방식으로 사용하면?

### 섹션 6: Dependencies
이 시스템이 필요로 하는 것과 제공하는 것.
- 입력: 어떤 시스템/데이터에 의존하는가?
- 출력: 어떤 시스템이 이 시스템의 결과를 소비하는가?
- 인터페이스: 데이터 계약 (타입, 이벤트명)

### 섹션 7: Tuning Knobs
게임플레이 없이 조정할 수 있는 값들.
| 변수 | 기본값 | 범위 | 설명 |
|------|--------|------|------|

### 섹션 8: Acceptance Criteria
이 GDD가 올바르게 구현되었음을 증명하는 테스트 조건.
- [ ] 조건 1
- [ ] 조건 2

---

## 4. 완료 후

- `production/session-state/active.md` STATUS 블록 업데이트
- **다음 단계 안내**:
  - `/design-review doc/{GameName}/{system-name}.md` — 완성도 검토
  - `/balance-check {system-name}` — 밸런스 분석
  - 구현 시작 시 `@state-machine-architect`, `@ability-skill-system` 등 관련 스킬 참조

## TDD Contract

GDD 자체는 문서이므로 Unit Test 대상 아님.
수용 기준(Acceptance Criteria)이 구현 테스트의 계약서 역할을 한다.

## Related Skills
- `@brainstorm` — 컨셉 먼저 생성
- `@map-systems` — 시스템 목록 및 우선순위
- `@design-review` — 작성된 GDD 검토
- `@balance-check` — 수식 밸런스 검증
