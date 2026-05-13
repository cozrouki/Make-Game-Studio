---
name: scope-check
description: "피처 또는 스프린트의 범위 팽창(scope creep)을 원래 계획과 비교해 감지한다. 추가된 항목을 정량화하고 컷/연기/유지를 권장한다."
version: 1.0.0
tags: ["game-design", "production", "scope", "planning", "project-management"]
argument-hint: "[피처명 또는 sprint-N] (예: combat-system, sprint-3)"
user-invocable: true
tdd_first: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# Scope Check — 범위 팽창 분석

## 호출 시 동작

### 1. 원래 계획 읽기
인수로 탐색:
- 피처명 → `doc/{GameName}/{feature}.md` GDD
- 스프린트 번호 → `production/sprints/sprint-{N}.md`
- 마일스톤 → `production/milestones/*.md`

### 2. 현재 상태 파악
- 피처/스프린트와 관련된 파일 스캔 (Glob `Assets/**/*.cs`, `doc/**/*.md`)
- 최근 git 커밋 조회 (관련 커밋 필터링)
- TODO 주석 확인 (미완료 범위 추가 감지)

### 3. 비교 분석

**원래 범위 vs 현재 범위**:

```markdown
## Scope Check: [피처/스프린트명]
생성: [날짜]

### 원래 범위
[원래 계획의 항목 목록]

### 현재 범위
[실제 구현 중이거나 완료된 항목]

### 범위 추가 (원래 계획 외)
| 추가 항목 | 추가 경위 | 시기 | 정당성 | 공수 |
|----------|-----------|------|--------|------|
| [항목] | [커밋/사람] | [날짜] | 있음/없음/불명 | S/M/L |

### 범위 제거 (계획에 있었으나 빠진 것)
| 제거 항목 | 이유 | 영향 |
|----------|------|------|

### Bloat Score
- 원래 항목: [N]개
- 현재 항목: [N]개
- 추가된 항목: [N]개 (+[X]%)
- 제거된 항목: [N]개
- 순 범위 변화: [+/-N]개 ([X]%)

### 리스크 평가
- **일정 리스크**: [낮음/중간/높음] — [설명]
- **품질 리스크**: [낮음/중간/높음] — [설명]
- **통합 리스크**: [낮음/중간/높음] — [설명]

### 권장 사항
1. **컷**: [일정 유지를 위해 제거할 항목]
2. **연기**: [다음 스프린트/버전으로 이동 가능한 항목]
3. **유지**: [진짜로 필요한 추가 항목]
4. **결정 필요**: [Architect/Producer 결정이 필요한 항목]
```

### 4. 위기 판단 기준

| Bloat | 상태 | 액션 |
|-------|------|------|
| 0~15% | 🟢 정상 | 계속 진행 |
| 15~30% | 🟡 주의 | 낮은 가치 항목 컷 검토 |
| 30~50% | 🟠 경고 | 즉시 컷/연기 결정 필요 |
| 50%+ | 🔴 위기 | Architect 에스컬레이션 |

## TDD Contract

Scope Check는 분석 보고서를 산출한다.
보고서의 권장 사항을 실행한 후 `/sprint-plan` 또는 `doc/{GameName}/task.md` 업데이트로 검증.

## Related Skills
- `@design-review` — 범위 추가가 GDD와 일치하는지 검토
- `@balance-check` — 추가된 범위의 밸런스 영향
- `@map-systems` — 시스템 간 의존성 변화 재매핑
