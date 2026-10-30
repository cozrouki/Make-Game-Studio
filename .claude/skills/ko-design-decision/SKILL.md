---
name: ko-design-decision
description: 기획 결정 카드 · 변경 관리 (한국어) — 기획 결정을 design/decisions/ 카드로 남기고(이유 · 대안 · 영향 등급 T0~T4 · 영향 표), 회의록에서 결정을 뽑고, 반영 뒤 실측으로 사후 확인. "왜 이 값인가" 를 기록하거나, 회의 결정을 정리하거나, 결정의 영향 · 후속 확인이 필요할 때
argument-hint: "[new <결정 요약> | from-meeting <회의록 경로> | review | close <D2026-001>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-design-decision — 기획 결정 카드

ADR(`/architecture-decision`)은 기술 결정을, GDD 는 현재 설계를 담는다. 이 스킬은 그 사이 — **기획 결정 하나가 왜 그렇게 됐는지와 그 뒤 어떻게 됐는지** — 를 카드 한 장으로 남긴다. 값이 바뀐 이유가 GDD 에서 사라지는 것을 막는다.

> 방법 참고: 이민수, 『게임 기획 실무에서 바로 쓰는 AI·클로드 코드 활용법』 17부(회의록) · 18부(의사결정 · 임팩트) · 10부 2장(결정 검증). 원문은 옮기지 않고 이 템플릿 구조로 다시 썼다. 원문을 보려면 `/ext gdpractice 18부` (선택 설치 · 비상업 라이선스).

도구: `python .agent/tools/design/design_graph.py` (카드 검사 · 영향 범위 · 다음 번호). 표준: `.agent/tools/design/standard.json` 의 `decision`. 템플릿: `.claude/skills/ko-design-decision/templates/decision-card.md`.

## 원칙

- **결정은 사람이 한다.** AI 는 사람이 말한 결정의 빈칸(근거 문장 · 영향 표 · 등급 초안)만 채운다. 회의록이나 대화에서 결정을 지어내지 않는다.
- **담당이 비면 승인하지 않는다.** owner · decided_by 를 모르면 `"[MISSING]"` 으로 적는다 — 검사(DG105)가 승인 전에 잡는다.
- **기각한 대안도 남긴다.** 다음 사람이 같은 실험을 반복하지 않게.
- **근거 없는 수치를 쓰지 않는다.** 영향 크기를 모르면 "영향 있음(크기 미측정)" 이라고 쓴다.
- 카드는 지우지 않는다. 뒤집힌 결정은 새 카드가 `supersedes` 하고 옛 카드는 `archived` 로 둔다.

## 영향 등급 (standard.json `decision.impact` — 프로젝트가 고쳐 쓴다)

| 등급 | 무엇 | 결정자 (기본값) |
|---|---|---|
| T0 | 비전 · 필러를 바꾼다 | 사용자(디렉터) |
| T1 | 여러 시스템 구조를 바꾼다 | 디렉터 승인 |
| T2 | 한 시스템의 규칙 · 흐름을 바꾼다 | 기획 리드 |
| T3 | 수치 · 콘텐츠 조정 | 담당 기획 |
| T4 | 오류 수정 · 표기 | 담당자 즉시 |

등급은 세 질문 중 **가장 높게 나온 것**으로 정한다: ① 영향받는 문서 · 시스템 수(`impact` 결과의 직접 줄) ② 되돌리는 비용(빌드 반영 · 녹음 · 출시 후면 높다) ③ 플레이어가 느끼는 범위. ①은 도구 결과로, ②③은 초안을 제시하고 사람이 확정한다. 1인 개발이면 결정자 칸은 모두 본인이어도 되지만 **등급은 그대로 매긴다** — T0~T1 은 하루 묵혀 다시 본다.

## new <결정 요약>

1. 번호: `python .agent/tools/design/design_graph.py next-id` (기존 최대 + 1 — 지운 번호도 재사용하지 않는다).
2. 템플릿을 `design/decisions/<id>.md` 로 복사해 채운다. 사용자에게 모르는 칸(이유 · 결정자 · 대안)을 묻는다 — 추측으로 채우지 않는다.
3. 관계: 이 결정이 바꾸는 문서를 `relations.affects` 에, 근거 문서(필러 · GDD)를 `derives_from` 에 id 로 적는다. 대상 문서에 프런트매터가 없으면 `/ko-design-graph adopt` 를 먼저 권한다 (그 전까지 영향 표는 '약' 줄만 나온다).
4. 영향 표: `python .agent/tools/design/design_graph.py impact <이 카드 id 또는 affects 대상 id>` 결과를 보여 주고, 사용자가 확인한 줄만 `## 영향` 에 옮긴다. 각 줄 분류: 확정 · 영향 있음(크기 미측정) · 근거 없음.
5. 수치 결정이고 `/ko-balance-sim` 의 "시뮬 의무" 에 해당하면 시뮬 결과 파일을 `## 검토한 대안` 에 링크한다. 없으면 status 를 `review` 에 두고 시뮬을 먼저 권한다.
6. `review_after` = 오늘 + `reviewAfterDays`(기본 30일) — 빌드 반영 후 실측할 날.
7. 검사: `python .agent/tools/design/design_graph.py check` — 이 카드에 error 가 없고 DG106(템플릿 안내문 `<…>` 남음)도 없을 때만 `approved` 로 바꾼다. 승인 후 GDD 의 해당 값 옆에 `(D2026-001)` 처럼 카드 id 를 남긴다.
8. GDD 가 바뀌었으면 `/propagate-design-change` 로 ADR 영향을 확인하라고 안내한다.

## from-meeting <회의록 경로>

1. 회의록을 읽고 **사람이 결정했다고 말한 것**만 뽑는다 (제안 · 의견 · 질문은 결정이 아니다 — 따로 "미결 질문" 으로 모은다).
2. 결정마다 네 칸: 결정 · 담당 · 이유 · 후속 할 일. 회의록에 없는 칸은 `"[MISSING]"`.
3. 목록을 표로 보여 주고 사용자가 고른 것만 `new` 절차로 카드를 만든다 (status `draft`). 1주 안에 확정되지 않은 draft 는 `review` 에서 다시 묻는다.
4. 회의록 자체는 고치지 않는다. 카드의 `relations.derives_from` 에 회의록 id(있으면) 또는 본문에 회의록 경로를 남긴다.

## review

`design_graph.py check` 를 돌려 결정 카드 관련 줄만 모아 보여 준다:
- DG105 `[MISSING]` 이 남은 카드 · DG102 필수 칸 누락 → 승인 전 처리
- DG104 사후 확인 시기가 지난 승인 카드 → `close` 대상
- 1주 넘은 draft → 확정 · 폐기를 묻는다
- DG009 충돌 결정이 둘 다 승인 → 사용자에게 어느 쪽을 `supersedes` 할지 묻는다
검사가 돌지 않았으면(문서 없음 · 파싱 실패) 그 사실을 첫 줄에 쓴다 — "확인할 카드 없음" 과 "확인하지 못함" 을 섞지 않는다.

## close <id> — 사후 확인

1. 카드의 의도(목표 값 · 기대 효과)와 실측(플레이테스트 · 지표 · 시뮬 재실행)을 나란히 적는다. 실측이 없으면 "실측 없음 — 확인 못 함" 으로 두고 닫지 않는다.
2. 차이 판단 (standard.json `measureTolerance`, 기본값): 의도 대비 **±10% 이내 통과 · ±10~25% 해석 필요 · ±25% 초과 재검토**. 해석 · 재검토면 후속 결정 카드 후보로 `new` 를 제안한다.
3. `## 사후 확인` 을 채우고 `updated` 를 갱신한다. status 는 approved 그대로 둔다 (뒤집으면 새 카드가 supersedes).

## 스튜디오 모드

결정 카드는 기획 영역(`design/`)이다 — planning 역할이 쓴다. T0 · T1 은 `to: director` 질문 티켓으로 올리고 디렉터 승인 후 approved 로 바꾼다 (`roles/director.md` 결정 권한표).

## 관련

- 문서 프런트매터 · 그래프: `/ko-design-graph`
- 수치 후보 비교: `/ko-balance-sim`
- 기술 결정: `/architecture-decision` · GDD 변경의 ADR 영향: `/propagate-design-change`
