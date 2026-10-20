---
name: studio-status
description: 스튜디오 모드 디렉터 콘솔 — 현황판, 게이트 승인/반려, 판단 요청 답변, 전체 정지/재개 (어느 세션에서든)
argument-hint: "[approve <G#> [메모] | reject <G#> <사유> | answer <T-####> <답변> | pause [사유] | resume | show <T-####>]"
user-invocable: true
allowed-tools: Read, Glob, Bash, ListAgents, SendMessage, AskUserQuestion
---

# /studio-status — 디렉터 콘솔

**사용자(디렉터)가 직접 입력할 때만** 승인·반려·답변·정지 권한으로 동작한다. 세션이 자기 판단으로 이 스킬을 실행해 승인하는 일은 금지다.

`S` = `python .agent/tools/studio/studio.py --json`

## 인수 없음 — 현황판

1. `S status` 를 실행하고, `ListAgents` 로 로스터 세션이 살아 있는지 대조한다.
2. 다음 순서로 보여 준다:
   - ⏸ 정지 상태 (있으면)
   - **게이트 표**: 게이트 · 상태 · 열리는 일. `requested` 상태 게이트는 산출물 경로를 함께 보여 준다 (`S gate list`).
   - **역할 표**: 진행 · 착수 가능 · 대기 · 차단 · 세션 (살아 있음 ✅ / 꺼짐 ⚠)
   - **디렉터 판단 대기**: 티켓마다 `S show` 로 본문 요약 2~3줄
   - **정체 티켓** (staleHours 이상 갱신 없음)
3. 다음 행동을 제안한다. 요청된 게이트가 있으면 승인 전에 확인할 산출물 경로를 함께 보여 준다.

## approve / reject <G#>

1. `S gate list` 로 게이트가 `requested` 상태인지 확인한다. 산출물 파일 목록을 보여 준다.
2. 디렉터가 인수에 메모를 이미 주었으면 그대로 진행한다. 주지 않았으면 `AskUserQuestion` 으로 한 번 확인한다: `[A] 승인` / `[B] 반려` / `[C] 산출물 먼저 보기`.
3. `S gate approve|reject <G#> --by director --note "<메모>"`.
4. 결과의 `roster` 에 있는 모든 세션에 알린다 (이 세션 제외):
   - 승인: `[studio] 게이트 <G#> 승인 — 착수 가능 티켓 확인` + 메모
   - 반려: `[studio] 게이트 <G#> 반려 — <사유>` (요청자 역할은 사유를 반영해 다시 요청한다)
5. 이 세션도 역할이 있으면(로스터에 이 세션 이름이 있으면) 업무 루프를 다시 시작한다.

## answer <T-####> <답변>

1. `S show <id>` 로 디렉터 대상 티켓인지 확인한다.
2. 답변을 원문 그대로 기록한다. `S update <id> --by director --status done --note "<답변>"`
3. 결과의 `notifySession`(질문한 세션)에 알린다: `[studio] <id> 디렉터 답변 — <답변 첫 줄>`
   - 질문자가 그 답을 근거로 이어서 일하도록 한다. 질문자의 원래 작업 티켓이 blocked 면 질문자가 스스로 재개한다.

## pause [사유] / resume

1. `S pause --reason "<사유>"` 또는 `S resume`.
2. 로스터의 모든 세션에 알린다. 정지: `[studio] ⏸ 디렉터 정지 — <사유>`. 재개: `[studio] ▶ 재개 — 받은 티켓 확인`.

## show <T-####>

`S show <id>` 의 결과를 읽기 쉽게 보여 준다 (메타 · 본문 · 스레드).
