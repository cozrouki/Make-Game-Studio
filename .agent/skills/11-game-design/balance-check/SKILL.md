---
name: balance-check
description: "게임 밸런스 데이터·수식·설정값을 분석하여 이상값·퇴화 전략·경제 불균형을 감지한다. 밸런스 관련 데이터나 디자인 변경 후 실행."
version: 1.0.0
tags: ["game-design", "balance", "economy", "combat", "progression", "analysis"]
argument-hint: "[시스템명 또는 데이터 파일 경로] (예: combat, economy, Assets/Data/weapons.json)"
user-invocable: true
tdd_first: false
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Balance Check — 게임 밸런스 분석

## 호출 시 동작

### 1. 밸런스 도메인 식별
인수에서 분석 대상을 파악:
- 시스템명 (combat, economy, progression, loot)
- 데이터 파일 경로 (Assets/Data/*.json, doc/{GameName}/balance/*.md)
- 인수 없으면 `doc/{GameName}/` 아래 balance 관련 문서 전체 스캔

### 2. 관련 파일 읽기
- `Assets/*/Data/` 또는 `Assets/*/Resources/` 아래 관련 ScriptableObject 데이터
- `doc/{GameName}/{system}.md` GDD
- `doc/{GameName}/game-concept.md` (밸런스 의도 파악)

---

## 분석 영역별 체크리스트

### 전투 밸런스 (Combat)
- 각 무기/스킬의 DPS를 파워 티어별로 계산
- 티어별 time-to-kill(TTK) 확인
- 모든 상황에서 지배적인 선택지(strictly dominant) 존재 여부
- 방어 옵션으로 무적 상태 생성 가능 여부
- 데미지 타입 / 저항 상호작용 균형

### 경제 밸런스 (Economy)
- 모든 자원 공급원(faucet)과 소비처(sink) 및 유량 매핑
- 시간에 따른 자원 누적 추이 예측
- 무한 자원 루프 여부
- 골드 싱크가 골드 생성량에 비례하는가
- 절대 구매할 이유 없는 아이템 존재 여부

### 진행 밸런스 (Progression)
- XP 곡선과 파워 곡선 플롯
- 진행이 정체되는 Dead Zone 존재 여부
- 갑작스러운 파워 스파이크 여부
- 콘텐츠 게이트가 예상 플레이어 파워와 정렬되는가
- 스킵/그라인드 전략으로 의도된 페이싱 파괴 가능 여부

### 전리품 밸런스 (Loot)
- 각 희귀도 티어 획득까지 예상 시간 계산
- 천장(pity timer) 수식 검증
- 어떤 단계에서도 완전히 쓸모없는 아이템 없는지 확인
- 인벤토리 압박 vs 획득 속도 균형

---

## 출력 형식

```markdown
## Balance Check: [시스템명]
생성: [날짜]

### 분석된 데이터 소스
- [파일 목록]

### 종합 상태: [HEALTHY / CONCERNS / CRITICAL ISSUES]

### 감지된 이상값
| 항목/값 | 예상 범위 | 실제값 | 문제 |
|---------|-----------|--------|------|

### 발견된 퇴화 전략
[항상 최선인 선택지, 무한 루프 등]

### 경제 흐름 분석
[자원 공급/소비 요약, 장기 누적 예측]

### 권장 조정
| 변수 | 현재 | 제안 | 이유 |
|------|------|------|------|

### 우선순위
1. **즉시 수정**: [출시 전 반드시]
2. **수정 권장**: [다음 이터레이션]
3. **모니터링**: [출시 후 데이터 수집]
```

## TDD Contract

```csharp
// Balance Check는 분석 보고서를 산출한다.
// 수식 기반 수치 검증은 별도 Unit Test로 작성할 것:

[Test]
public void DamageFormula_ShouldNotExceedMaxDamage_AtMaxStats()
{
    // Arrange
    float baseDmg = 100f; float weaponMult = 2f;
    float critMult = 2f; float resistance = 0f;

    // Act
    float result = baseDmg * weaponMult * critMult * (1 - resistance);

    // Assert
    Assert.LessOrEqual(result, 1000f); // 최대 데미지 캡
}
```

## Related Skills
- `@design-review` — GDD 품질 검토
- `@design-system` — 밸런스 수식 설계
- `@scope-check` — 밸런스 작업 범위 관리
