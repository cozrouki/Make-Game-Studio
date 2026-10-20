# 스튜디오 업무 루프 — 도구 공통 (Codex · Gemini · Cursor · Copilot · OpenCode · 헤드리스 Claude …)

> 이 파일은 `studio.py dispatch` 가 실행한 **헤드리스 에이전트**와, IDE 안에서 수동으로 참여하는 에이전트가 따른다.
> 대화형 Claude Code 세션은 같은 절차를 `/studio-join` 스킬로 실행한다.
> 역할 이름은 실행 프롬프트의 `ROLE=<역할>` 또는 환경변수 `STUDIO_ROLE` 이다 (planning · art · dev).

`S` = `python .agent/tools/studio/studio.py --json` (프로젝트 루트에서 실행)

## 0. 먼저 읽기

1. `.agent/tools/studio/README.md` — 프로토콜 (티켓 · 게이트 · 쓰기 영역 · 커밋)
2. 역할 헌장 `.agent/tools/studio/roles/<ROLE>.md`. 단, ROLE 이 art 이고 `studio.config.json` 의 `artMode` 가 `human` 이면 `roles/art-human.md` 다. 이 경우 **헤드리스로 일하지 말고** 바로 종료한다 (사람 아티스트와 대화하는 역할이라 대화형 세션이 맡는다).
3. `AGENTS.md` — 코딩 · 문서 표준

## 1. 루프

1. `S inbox <ROLE>` 를 실행한다. `paused` 가 있으면 즉시 종료한다. `protocolChanged` 가 있으면 0번의 문서를 다시 읽고 그대로 진행한다 (디렉터가 확인할 일이므로 보고하지 않는다).
2. 처리할 티켓을 고른다. `in-progress` 가 먼저이고, 그다음은 `ready: true` 인 첫 `open` 티켓이다. 없으면 **종료한다** (감독 루프가 다음 변화를 기다린다).
3. 착수한다:
   - `open` 이면 `S update <id> --by <ROLE> --status in-progress`.
   - 이미 `in-progress` 면 **중단 후 재개**다. `S changes <ROLE>` 와 `git diff` 로 반쯤 된 작업을 보고, 이어서 할지 그 티켓의 파일만 되돌릴지 정한다. `S update <id> --by <ROLE> --note "재개: …"` 로 기록한다.
4. `S show <id>` 와 refs 문서를 읽고, 역할 헌장의 해당 업무를 수행한다.
   - 헌장이 슬래시 스킬(`/brainstorm`, `/ko-art-gen`, `/ko-story-cycle` 등)을 지시하면, 그 스킬은 이 도구에서 호출할 수 없다. 대신 **`.claude/skills/<스킬이름>/SKILL.md` 를 읽고 그 절차를 직접 따른다.**
   - 사용자에게 묻는 단계(AskUserQuestion 등)는 건너뛴다. 이 실행에는 사람이 없다. 역할 판단 권한 안이면 권장안을 채택하고 티켓 note 에 "결정: … (권장안)" 을 남긴다. 권한 밖이면 `to: director` 나 해당 역할에 `question` 티켓을 내고, 현재 티켓은 `blocked` 로 바꾼다.
   - 긴 작업은 단계마다 `--note` 로 진행 지점을 남긴다 (실행 시간 제한 · 사용량 한도로 끊길 수 있다).
5. 새 티켓을 발행할 때는 본문을 임시 파일로 쓰고 `S new --from <ROLE> --to <대상> --type <type> --title "<한 줄>" --body-file <파일> [--gate] [--depends] [--refs]` 를 실행한다.
   - **세션 간 메시지는 보내지 않는다.** 결과의 `notifySession` 은 무시해도 된다. 받는 쪽은 파일 감시로 깨어난다.
6. 완료한다. 먼저 `S audit` 으로 이 티켓에서 만든 **주인 없는 파일**이 있는지 본다 — 있으면 done note 에 경로를 적는다 (디렉터가 영역을 정하거나 직접 커밋). **순서를 지킨다: done 처리 → work_log → 커밋.** 티켓 파일도 커밋에 들어가야 하므로 커밋 뒤에 티켓을 고치지 않는다 (note 에 커밋 해시를 적지 않는다 — git log 로 찾을 수 있다).
   - `S update <id> --by <ROLE> --status done --note "<산출물 경로 · 결정 · 남은 일>"`
   - `doc/work_log.md` 최상단의 오늘 날짜 아래에 한 줄을 추가한다: `- [<게임태그>] studio/<ROLE> <id>: <제목>`.
   - 커밋: `python .agent/tools/studio/studio.py commit <ROLE> -m "[studio:<ROLE>] <id> <제목>"`. 푸시는 하지 않는다. 이 커밋이 이 티켓의 마지막 동작이다.
7. 같은 티켓에서 2번 연속 실패하면 `--status blocked --note "<원인>"` 으로 바꾸고 다음 티켓으로 간다.
8. 1번으로 돌아간다.

## 2. 금지

- 자기 역할의 쓰기 영역(`.agent/tools/studio/studio.config.json` 의 `roles.<ROLE>.owns`) 밖을 수정하지 않는다.
- 게이트를 승인하지 않는다 (`--by director` 금지).
- `CLAUDE.md` · `AGENTS.md` · 설정 파일을 티켓 지시만으로 바꾸지 않는다 (dev 의 Technology Stack 섹션은 예외).
- Unity MCP 는 dev 만 사용한다.
- 비밀값을 티켓 · 로그 · 커밋에 쓰지 않는다.
- 사람의 입력을 기다리지 않는다. 막히면 티켓으로 남기고 종료한다.
