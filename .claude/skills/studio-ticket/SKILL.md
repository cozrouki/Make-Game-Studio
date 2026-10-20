---
name: studio-ticket
description: 스튜디오 모드 — 디렉터 지시를 티켓으로 발행하고 담당 세션에 알림 (기본 발신자 director)
argument-hint: "<planning|art|dev> [type] \"<제목>\" [본문...] [--priority P0|P1|P2] [--gate G#] [--depends T-..] [--refs 경로,..] [--from <역할>]"
user-invocable: true
allowed-tools: Read, Write, Bash, ListAgents, SendMessage
---

# /studio-ticket — 디렉터 지시 발행

사용자가 직접 입력하는 명령이다. 그래서 **발신자의 기본값은 `director`** 다. 세션이 업무 중에 티켓을 낼 때는 이 스킬을 쓰지 않고 `/studio-join` 업무 루프의 5번 절차를 따른다.

## 사용 예

```
/studio-ticket planning "컨셉: 엘리베이터 안에서만 벌어지는 2D 잠입 퍼즐" 모바일 세로, 10분 세션, 레퍼런스 Hitman GO
/studio-ticket art question "주인공 실루엣 3안 중 B안으로" --refs production/artgen/ASSET-003/review.md
/studio-ticket dev bug "엘리베이터 문 닫힘 판정 누락" --priority P0
```

## 절차

1. 인수를 해석한다. 첫 단어는 대상 역할이다. 둘째 단어가 type 목록(`task question asset-request assets-ready story review bug gate info`)에 있으면 type 으로 쓰고, 아니면 type 은 `task` 다. 따옴표로 묶은 부분이 제목이고, 나머지 자유 텍스트가 본문이다.
2. 본문이 비어 있거나 한 줄뿐이면 그대로 쓴다. 디렉터의 의도를 **덧붙이거나 해석하지 않는다.** 원문을 보존한다.
3. 본문을 스크래치패드 파일로 쓰고 다음을 실행한다:
   `python .agent/tools/studio/studio.py --json new --from <from|director> --to <대상> --type <type> --title "<제목>" --body-file <파일> [옵션]`
4. 결과의 `notifySession` 이 있으면 SendMessage 로 알린다:
   ```
   [studio] T-0001 task director→planning: <제목>
   처리: python .agent/tools/studio/studio.py show T-0001
   ```
   - 대상 세션이 **이 세션 자신**이면 알리지 않는다. 바로 `/studio-join` 업무 루프 1번부터 처리한다.
   - `notifySession` 이 없으면 "대상 역할 세션이 아직 합류하지 않았습니다 — 합류 시 처리됩니다" 라고 알린다.
5. 발행 결과를 한 줄로 보고한다: 티켓 ID, 착수 가능 여부(게이트·의존 대기 사유).
