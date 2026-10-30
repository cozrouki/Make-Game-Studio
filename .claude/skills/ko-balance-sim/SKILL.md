---
name: ko-balance-sim
description: 결정론 밸런스 시뮬레이션 (한국어) — 공식 · 수치를 바꾸기 전에 후보 여러 개를 고정 시드로 반복 실행해 비교하고, 명세값과의 차이를 구조적 차이 · 통계적 분산으로 나누고, 경제 source/sink 흐름을 플레이어층별로 시뮬레이션해 게이트를 낸다. 정적 분석은 /balance-check
argument-hint: "[run <spec.json> | economy <spec.json> | new <combat|economy> <이름>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-balance-sim — 결정론 밸런스 시뮬레이션

`/balance-check` 는 데이터 · 공식을 **읽어서** 이상치를 찾는다. 이 스킬은 **돌려서** 비교한다. 같은 시드면 같은 결과가 나오므로, 후보 A 와 B 의 차이가 값 때문인지 운 때문인지 가를 수 있다.

> 방법 참고: 이민수, 『게임 기획 실무에서 바로 쓰는 AI·클로드 코드 활용법』 8부(밸런스 — 전투 공식 · 경제 흐름 · 시뮬레이션 · PvP). 원문은 옮기지 않고 이 템플릿 구조로 다시 썼다. 원문: `/ext gdpractice 8부` (선택 설치 · 비상업 라이선스).

도구: `python .agent/tools/design/balance_sim.py` (표준 라이브러리만). 결과 파일: `design/balance/reports/` (결정 카드에 링크).

## 역할 나눔

- **계산은 코드가 한다.** 공식 계산 · 보상 곡선 · 누적량을 AI 가 머리로 추정하지 않는다.
- **AI 는 해석한다.** 결과 표 설명, 이상치(BS005) 원인 가설, 다음 후보 제안, 결정 카드 초안.
- **결정은 사람이 한다.** 어떤 후보를 쓸지는 사용자가 고르고 `/ko-design-decision` 에 남긴다.

## 시뮬레이션이 필요한 변경 (기본값 — 프로젝트가 고쳐 쓴다)

| 변경 | 시뮬 |
|---|---|
| 경제에 source · sink 추가 / 제거 | 필수 (`economy`) |
| 재화 교환 비율 · 가격 ±10% 이상 | 필수 (`economy`) |
| 보상 테이블 · 드롭률 설계 | 필수 |
| 전투 공식 구조 변경 (항 추가 · 곱셈 ↔ 덧셈) | 필수 (`run`) |
| 수치 하나 ±10% 미만 조정 | 권장 |
| 표기 · 오류 수정 | 불필요 |

1인 · 프로토타입 단계면 "필수" 를 "권장" 으로 내려도 된다 — 단 내린 사실을 결정 카드에 적는다.

## new combat <이름> — 전투 · 수치 모델 만들기

1. GDD 의 `## Formulas` 절과 `## Tuning Knobs` 를 읽는다 (없으면 `/design-system` 으로 먼저 쓴다).
2. `design/balance/<이름>_model.py` 를 만든다 — 함수 하나:
   ```python
   def simulate(params, rng):
       """한 번의 전투 · 세션 · 보상 굴림. params = 튜닝 값, rng = random.Random — 이것만 쓴다."""
       ...
       return {"ttk_sec": t, "win_rate": w}      # 지표 이름 → 숫자
   ```
   **전역 `random` · `time` · 집합 순회 순서를 쓰지 않는다** — 재현성 검사(BS002)가 잡는다. 공식은 GDD 에 적힌 대로 옮기고, GDD 에 없는 가정을 넣으면 코드 주석과 사용자 보고에 밝힌다.
3. `design/balance/<이름>.json`:
   ```json
   {"model": "design/balance/<이름>_model.py", "runs": 1000, "seed": 20261030,
    "baseline": {"atk": 50, "crit": 0.1},
    "candidates": {"A": {"atk": 55}, "B": {"crit": 0.15}},
    "targets": {"ttk_sec": {"min": 8, "max": 12}},
    "expected": {"ttk_sec": 10}}
   ```
   targets 는 GDD 의 목표 범위, expected 는 GDD 공식으로 손계산한 명세값이다. 둘 다 없으면 사용자에게 묻는다 — 지어내지 않는다.

## new economy <이름> — 경제 흐름 모델 만들기

코드 없이 JSON 으로 쓴다 (`balance_sim.py` docstring 의 economy 형식). 플레이어층(`segments` — 비중 · 하루 플레이 시간), 자원별 source · sink(시간당 양 · 흔들림 `jitter`), 하루 순증가 목표 `netPerDay`, 계획 대비 허용 오차 `tolerance`(기본 0.10). 처음엔 **자원 하나**로 시작해 맞으면 넓힌다. AI 가 초안을 쓰면 넣은 가정(시간당 양의 출처)을 표로 보여 주고 사용자가 고치거나 거부한다.

## run <spec> · economy <spec>

```
python .agent/tools/design/balance_sim.py run design/balance/<이름>.json --out design/balance/reports
python .agent/tools/design/balance_sim.py economy design/balance/<이름>.json --out design/balance/reports
```

보고는 이 순서로 한다.
1. **판정**: error 0 이면 PASS · error 있으면 FAIL · spec · 모델 오류로 못 돌렸으면(종료 코드 2) **NOT ASSESSED** 와 이유. BS006(목표 없는 지표)은 "판정 안 한 지표" 로 따로 적는다 — 통과가 아니다.
2. 후보별 표(평균 · 표준편차 · p5 · p50 · p95)와 목표 범위 안 / 밖.
3. 명세 대비 차이(BS004): **구조적 차이**(95% 구간 밖 — 공식 · 명세 · 모델 중 하나가 다르다 → GDD 를 고칠지 모델을 고칠지 묻는다) / **통계적 분산**(구간 안 — 정상).
4. 이상치(BS005) — 원인 가설을 붙이되 확인된 사실처럼 쓰지 않는다.
5. 경제: 층별 하루 순증가 · 누적 vs 계획, 격차(EC004), sink 없는 자원(EC005).
6. 다음 단계 제안: 후보 채택이면 `/ko-design-decision new` (결과 파일을 `## 검토한 대안` 에 링크), 목표 밖이면 보정 후보를 제안해 다시 돌린다.

## PvP · 상성

모든 조합이 50% 가 목표가 아니다. 승률 매트릭스를 지표로 내게 모델을 짜고(예: `"A_vs_B": 0.58`), 목표는 **순환하는 상성**(A>B>C>A)과 어떤 하나가 모두를 이기지 않는 것으로 잡는다. 지배 전략 의심은 `/balance-check` 결과와 함께 본다.

## 관련

- 정적 이상치: `/balance-check` · 경제 설계: `economy-designer` 에이전트 · 결정 기록: `/ko-design-decision`
