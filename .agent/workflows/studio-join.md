---
description: 스튜디오 모드 참여 (IDE 에이전트용 — Antigravity · Windsurf · Cursor IDE 등) — 역할 등록 + 파일 감시 업무 루프
---

# /studio-join — IDE 에이전트로 스튜디오에 참여

> 헤드리스 CLI 가 없는 IDE 에이전트용이다. 헤드리스 CLI 가 있는 도구(Codex · Gemini · Cursor CLI · Copilot · OpenCode)는 터미널에서 `python .agent/tools/studio/studio.py dispatch <역할> --agent <도구>` 를 쓰는 편이 안정적이다.
> 인수: `<planning | art | dev>`

`S` = `python .agent/tools/studio/studio.py --json`

1. **등록** — `S join <역할> <IDE이름>-<역할> --kind manual --agent <IDE이름>`. 같은 역할에 다른 세션이 이미 등록되어 있으면 사용자에게 교체 여부를 묻는다.
2. **읽기** — `.agent/tools/studio/prompts/agent-loop.md` (업무 루프 정본), `.agent/tools/studio/README.md`, 역할 헌장.
3. **업무 루프** — `agent-loop.md` §1 을 ROLE=<역할> 로 수행한다. IDE 에서는 사용자가 곁에 있을 수 있으므로, 권한 밖의 질문은 티켓으로 올리기 전에 사용자에게 먼저 물어봐도 된다.
4. **대기** — 처리할 티켓이 없으면 터미널에서 `python .agent/tools/studio/studio.py watch <역할>` 을 실행해 둔다. 이 명령이 끝나면(티켓 · 게이트 · 정지 해제 감지) 3번으로 돌아간다. 사용자가 멈추라고 하면 멈춘다.
