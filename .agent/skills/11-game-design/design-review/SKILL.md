---
name: design-review
description: "GDD(게임 디자인 문서)의 완성도·일관성·구현 가능성·프로젝트 표준 준수 여부를 검토한다. 프로그래머에게 넘기기 전 필수 실행."
version: 1.0.0
tags: ["game-design", "GDD", "review", "quality", "documentation"]
argument-hint: "[GDD 파일 경로] (예: doc/KickleCubicle/combat-system.md)"
user-invocable: true
tdd_first: false
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Design Review — GDD 품질 검토

## 호출 시 동작

### 1. 대상 문서 읽기
인수로 지정된 GDD를 전체 읽기.
인수 없으면: `doc/{GameName}/` 안의 최근 수정된 GDD를 찾아 검토 대상으로 제안.

### 2. 컨텍스트 읽기
- `AGENT.md` / `CLAUDE.md` — 프로젝트 표준 파악
- `doc/{GameName}/game-concept.md` — 컨셉 문서 (있으면)
- `doc/{GameName}/game-pillars.md` — 기둥 문서 (있으면)
- `doc/{GameName}/` 안의 관련 시스템 GDD들

### 3. 표준 체크리스트 평가 (8개 섹션)

| # | 섹션 | 있음 | 품질 |
|---|------|------|------|
| 1 | Overview (한 문단 요약) | [ ] | |
| 2 | Player Fantasy (의도된 감정) | [ ] | |
| 3 | Detailed Rules (모호함 없는 규칙) | [ ] | |
| 4 | Formulas (모든 수식 변수 정의) | [ ] | |
| 5 | Edge Cases (예외 상황 처리) | [ ] | |
| 6 | Dependencies (입출력 시스템 목록) | [ ] | |
| 7 | Tuning Knobs (조정 가능한 값) | [ ] | |
| 8 | Acceptance Criteria (테스트 조건) | [ ] | |

### 4. 내부 일관성 검사
- 수식의 결과값이 서술된 동작과 일치하는가?
- 엣지 케이스가 메인 규칙과 모순되지 않는가?
- 의존성이 양방향으로 선언되었는가?

### 5. 구현 가능성 검사
- 프로그래머가 추측 없이 구현할 수 있을 만큼 규칙이 명확한가?
- "손으로 넘기는" 섹션 (세부 사항 미정)이 있는가?
- 성능 영향이 고려되었는가?

### 6. 크로스-시스템 일관성 검사
- 기존 메카닉과 충돌하는가?
- 의도하지 않은 시스템 간 상호작용을 만드는가?
- 게임의 기둥(Pillars) 및 톤과 일치하는가?
- AGENT.md §2~3 아키텍처 원칙과 충돌하는가?

### 7. 밸런스 초기 경고
- 명백한 지배 전략(항상 우월한 선택)이 보이는가?
- 수식이 극단값에서 비이상적인 결과를 내는가?
- 경제 루프가 무한 자원 획득을 허용하는가?

---

## 출력 형식

```markdown
## Design Review: [문서 제목]

### 완성도: [X/8 섹션 존재]
누락된 섹션: [목록]

### 일관성 이슈
[내부 또는 크로스-시스템 모순 목록]

### 구현 가능성 우려
[모호하거나 구현 불가능한 섹션]

### 밸런스 초기 경고
[명백한 밸런스 리스크]

### 권장 사항
**반드시 수정** (구현 전):
- [항목]

**수정 권장** (구현 중 가능):
- [항목]

**선택적 개선** (폴리시 단계):
- [항목]

### 최종 판정: [PASS / PASS WITH NOTES / NEEDS REVISION]
```

## TDD Contract

검토 결과 문서 자체가 산출물. PASS 판정 = 구현 진행 가능.

## Related Skills
- `@design-system` — GDD 작성
- `@balance-check` — 수식·밸런스 심층 분석
- `@map-systems` — 시스템 의존성 검토
