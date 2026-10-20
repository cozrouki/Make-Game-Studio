# studio — 기획 · 아트 · 개발 3세션 자동 개발 프로토콜

> 디렉터(사용자) 1명 + Claude Code 세션 3개(기획 · 그래픽 아트 · Unity 개발)가 같은 Unity 프로젝트 폴더에서 서로 일을 주고받으며 게임을 만든다.
> 디렉터는 **단계 게이트**에서만 승인하고, 그 사이에는 세션끼리 자율로 진행한다.

## 구성

```
                ┌──────────── 디렉터 (사용자) ────────────┐
                │  게이트 승인 · 판단 요청 응답 · 정지/재개 │
                │  /studio-status  (어느 세션에서든)        │
                └───────────────▲──────────────────────────┘
                                │ to: director 티켓
   ┌──────────────┐  티켓+알림  ┌──────────────┐  티켓+알림  ┌──────────────┐
   │  planning    │ ──────────▶ │     art      │ ──────────▶ │     dev      │
   │  기획 세션    │ ◀────────── │  아트 세션    │ ◀────────── │  개발 세션    │
   └──────────────┘   질문/리뷰  └──────────────┘  에셋 요청   └──────────────┘
          │                            │                            │
          └────────── production/studio/ (티켓 · 게이트 · 로스터) ───┘
```

| 계층 | 수단 | 역할 |
|---|---|---|
| **상태** (정본) | `production/studio/` 파일 | 티켓 · 게이트 · 로스터. 세션이 재시작되거나 대화가 요약돼도 남고, 디렉터가 그대로 읽을 수 있다 |
| **알림** (초인종) | Claude Code `SendMessage` (같은 PC 세션 간) | "T-0012 가 배정됨" 한 줄. **내용은 보내지 않는다.** 받는 세션이 티켓 파일을 읽는다 |
| **결정적 조작** | `python .agent/tools/studio/studio.py` | 번호 발급(동시 발행에도 충돌 없음) · 착수 조건 검사 · 게이트 · 역할별 커밋 |
| **행동 규범** | `roles/<역할>.md` + `/studio-join` | 역할마다 무엇을 하고, 무엇을 하지 않는지 |

## 시작하기

1. **같은 Unity 프로젝트 폴더**에서 터미널 3개를 열고 각각 `claude` 를 실행한다. **세 세션의 권한 모드를 같게 둔다.** 모드가 다르면 세션 간 메시지가 받는 쪽 사용자 승인 대기로 묶인다.
2. 각 세션에서 역할을 등록한다.
   ```
   /studio-join planning      (1번 터미널)
   /studio-join art           (2번 터미널)
   /studio-join dev           (3번 터미널)
   ```
   세션은 자기 이름을 `ListAgents` 로 확인해 `roster.json` 에 등록한다. 그다음 받은 티켓을 처리하기 시작한다.
3. 디렉터가 기획 세션에 아이디어를 준다.
   ```
   /studio-ticket planning "컨셉: 엘리베이터 안에서만 벌어지는 2D 잠입 퍼즐" 모바일 세로, 10분 세션
   ```
   `/studio-ticket` 은 어느 세션에서 입력해도 되고, 발신자는 `director` 로 기록된다.
4. 이후 디렉터는 `/studio-status` 로 현황을 보다가 게이트 요청이 오면 승인하거나 반려한다.

Unity 에디터는 1개만 띄운다. **Unity MCP 는 dev 세션만 사용한다.**

## 아트 모드 — AI 생성 / 사람 아티스트

`studio.config.json` 의 `"artMode"` 로 art 역할의 운영 방식을 고른다.

| | `"ai"` (기본) | `"human"` |
|---|---|---|
| 그림을 만드는 쪽 | art 세션 (artgen 백엔드) | **사람 아티스트** |
| art 세션의 역할 | 자율 생성 · 검수 · 승격 | 아티스트의 **보조 · 연락 창구**: 티켓을 대화 브리프로 전달하고, 질문 · 결정을 티켓으로 옮기고, 납품물을 규격 검사 · 승격한다 |
| 헌장 | `roles/art.md` | `roles/art-human.md` |
| 기획의 첫 산출물 (G1 후) | 아트 바이블 + 스타일 토큰 | **아트 디렉션 브리프** (`templates/art-direction-brief.md`) → 아티스트 시안 → 디렉터 선택 → 아트 바이블 공동 작성 |
| G2 산출물 | `art-bible.md`, `_style-tokens.json`, ASSET-000 review | `art-direction-brief.md`, ASSET-000(시안) review, `art-bible.md` |
| 납품 수령 | `artgen generate` (활성 백엔드) | `artgen generate --provider manual` — `production/artgen/_inbox/<ASSET-ID>/` 의 PNG 를 새 버전으로 이동 |
| 시각 루브릭 | 통과 기준 (자동 재생성) | 아티스트에게 주는 **의견** (최종 판단은 아티스트) |

human 모드에서 아티스트는 art 세션의 터미널 앞에 앉아 대화만 하면 된다. 티켓 파일 · git · CLI 를 몰라도 된다.
아트를 기다리는 동안 dev 는 자리표시 그래픽(`Assets/<Game>/Placeholder/`)으로 진행한다.

## 여러 AI 도구 혼합

역할마다 다른 AI 도구를 쓸 수 있다. 예: 기획 = Claude Code, 개발 = Codex CLI, 아트 = 사람 아티스트 + Claude 보조.
상태가 파일(티켓 · 게이트)에 있으므로 **`studio.py` 를 실행할 수 있는 도구면 누구나 참여**한다. 깨우는 방식만 도구에 따라 다르다.

| 참여 방식 | 대상 | 깨어나는 방법 | 시작 |
|---|---|---|---|
| **claude** (대화형) | Claude Code 터미널 세션 | 백그라운드 `studio.py watch` 종료 + (Claude 끼리) SendMessage | `/studio-join <역할>` |
| **dispatch** (헤드리스) | Codex CLI · Gemini CLI · Cursor CLI · Copilot CLI · OpenCode · 헤드리스 Claude | 감독 루프가 티켓을 감지하면 도구를 실행 | `python .agent/tools/studio/studio.py dispatch <역할> --agent <도구>` |
| **manual** (IDE) | Antigravity · Windsurf · Cursor IDE 등 헤드리스가 없는 에이전트 | 에이전트 터미널의 `studio.py watch` 종료 | Antigravity: `/studio-join` 워크플로 · 그 외: `prompts/agent-loop.md` 를 읽게 함 |

**파일 감시 (`watch`)** — 역할에 처리할 티켓(진행 중, 또는 착수 가능한 open)이 생길 때까지 파일만 보며 기다린다. 이미 있으면 바로 끝난다(종료 코드 0, 시간 초과는 3). 정지 중에는 끝나지 않는다. 티켓을 누가 만들었든(Claude · 다른 도구 · 사람 · 디렉터) 같은 방식으로 깨어나고, 대기 중에는 AI 토큰을 쓰지 않는다.

**감독 루프 (`dispatch`)**
```bash
python .agent/tools/studio/studio.py agents                          # 프리셋 · 설치 여부
python .agent/tools/studio/studio.py dispatch dev --agent codex --dry-run   # 실행될 명령 확인
python .agent/tools/studio/studio.py dispatch dev --agent codex      # 실행 (Ctrl+C 로 종료)
```
- 처리할 티켓이 생기면 도구를 헤드리스로 실행한다. 프롬프트는 "`prompts/agent-loop.md` 를 읽고 ROLE=<역할> 로 따르라" 는 한 줄이다 (도구 공통 업무 루프).
- 실행 로그: `production/studio/logs/<역할>-<시각>-<도구>.log` (git 무시).
- **진전 감지:** 실행 전후의 티켓 · 게이트 · HEAD 를 비교한다. 진전이 없으면 `backoffSec`(60 → 300 → 900초)만큼 기다리되, 그 사이 상태가 바뀌면 바로 재개한다. `maxNoProgress`(3)회 연속이면 디렉터에게 P0 `bug` 티켓을 1회 낸다 (사용량 한도 · 인증 만료 · CLI 옵션 변경 의심).
- **역할당 1개:** `production/studio/locks/<역할>.json` 잠금. 하트비트가 끊긴 잠금(죽은 프로세스)은 자동으로 가져가고, 그 외에는 `--force-lock`.
- 실행 시간 제한 `runTimeoutSec`(3600초)를 넘으면 종료한다. 끊긴 티켓은 다음 실행에서 재개 절차로 이어진다.
- 로스터에 `kind: dispatch` 로 등록된다. 다른 세션은 이 역할에 SendMessage 를 보내지 않는다.

**에이전트 프리셋** — `studio.config.json` 의 `agents`. CLI 옵션은 버전마다 바뀌므로 **설치한 버전의 `--help` 로 확인**하고, 다르면 `studio.config.local.json` 에서 덮어쓴다 (깊은 병합).

| 프리셋 | 명령 | 근거 |
|---|---|---|
| `claude` | `claude -p … --dangerously-skip-permissions` | 공식 |
| `codex` | `codex exec --sandbox workspace-write …` | 공식 (`--full-auto` 는 폐기 예정) |
| `gemini` | `gemini -p … --yolo` (+ `GEMINI_CLI_TRUST_WORKSPACE`) | 커뮤니티 자료 |
| `cursor` | `cursor-agent -p … --force --output-format text` | 공식 (실행 파일명이 `agent` 인 설치도 있음) |
| `copilot` | `copilot -p … --allow-all-tools --no-ask-user -s` | 공식 + 커뮤니티. 공식 권장은 `--allow-tool` 로 최소 권한 |
| `opencode` | `opencode run …` | 미확인 (권한 설정은 opencode 쪽 설정) |
| `antigravity` · `windsurf` | (헤드리스 없음) | manual 참여 |

**주의**
- 헤드리스 실행은 **사람의 승인 없이 파일을 고치고 명령을 실행한다.** 신뢰할 수 있는 프로젝트에서만 쓰고, 쓰기 영역과 역할별 커밋으로 범위를 제한한다.
- Windows 에서 npm 으로 설치한 CLI(`.cmd`)는 cmd.exe 를 거친다. 그래서 인자에 `& | < > ^ % " !` 가 있으면 실행을 거부한다. 기본 프롬프트에는 이 문자가 없다.
- 사람 아티스트 모드(`artMode: human`)의 art 는 헤드리스로 돌리지 않는다. 대화형 세션이 맡는다.

## 단계 게이트

| 게이트 | 요청자 | 산출물 (요청 시 존재 검사) | 승인되면 열리는 일 |
|---|---|---|---|
| **G1 컨셉** | planning | `design/gdd/game-concept.md`, `game-pillars.md` | 시스템 분해 · 아트 바이블 · 기술 셋업 |
| **G2 아트 디렉션** | planning | ai: `art-bible.md`, `_style-tokens.json`, 스타일 프로브 `ASSET-000/review.md` · human: `art-direction-brief.md`, 시안 `ASSET-000/review.md`, `art-bible.md` | 에셋 양산 (art) |
| **G3 프리프로덕션** | planning | `systems-index.md`, `asset-manifest.md`, `production/epics/index.md`, `production/sprints/`, `technical-preferences.md` | 기능 스토리 구현 (dev) |
| **M1, M2 …** | planning (`gate add`) | 마일스톤 리뷰 문서 | 다음 마일스톤 |

- 티켓에 `gate` 를 지정하면 그 게이트가 승인되기 전에는 **착수할 수 없다** (`update --status in-progress` 거부).
- 승인과 반려는 `--by director` 로만 할 수 있다. 세션이 스스로 승인하지 않는다.
- 게이트 사이에서 역할 권한을 넘는 결정(비전·범위·일정·외부 비용)은 `to: director` 티켓으로 올린다.

## 티켓

`production/studio/tickets/T-0001.md` — 프론트매터 + 요청 본문 + 스레드(추가만 함).

| type | 쓰임 | 예 |
|---|---|---|
| `task` | 일반 작업 | dev: "엔진 셋업 /ko-setup-engine" |
| `story` | 구현 스토리 (`refs` 에 스토리 파일) | planning → dev |
| `asset-request` | 에셋 생성 (`refs` 에 스펙 · ASSET ID) | planning/dev → art |
| `assets-ready` | 에셋 승격 완료 알림 | art → dev |
| `question` | 결정 · 해석 요청 | dev → planning, 누구든 → director |
| `review` | 산출물 검토 요청 | art → planning (스타일 프로브) |
| `bug` | 결함 | 누구든 → 담당 |
| `gate` | 게이트 요청 알림 | planning → director |
| `info` | 공지 (처리 후 바로 done) | |

상태 흐름: `open → in-progress → done`. 막히면 `blocked`(사유를 note 에), 필요 없어지면 `cancelled`.
`depends` 에 적은 티켓이 모두 done 이어야 착수할 수 있다. 결과를 넘길 때는 **완료한 티켓에 note 로 산출물 경로를 남긴다.**

## 쓰기 영역 (같은 폴더 공유의 안전장치)

| 역할 | 쓸 수 있는 곳 |
|---|---|
| planning | `design/**` (`design/assets/requests` 제외), `production/epics`, `production/sprints`, `production/milestones` |
| art | `design/assets/requests`, `production/artgen`, `Assets/*/Art/**`, `Assets/ArtGen`, `art-source` (아티스트 원본, human 모드) |
| dev | `Assets/**` (Art 제외), `Packages`, `ProjectSettings`, `production/qa`, `tests`, `production/epics` (스토리 상태 갱신만), 기술 셋업 산출물(`.claude/docs/technical-preferences.md` · `docs/architecture` · `docs/engine-reference` · `.github/workflows`) |
| **director** (사람) | 프로토콜 · 지침 · 도구: `CLAUDE.md` · `AGENTS.md` · `.claude/**` · `.agent/tools` · `.agent/rules` · `.agent/workflows` · 도구별 미러(`.cursor` · `.github/instructions` 등). dev 가 `/setup-engine` 으로 `CLAUDE.md` Technology Stack 을 고치면 **디렉터가 확인 후 커밋**한다 |
| 공유 | `production/studio` (티켓 · 게이트), `doc/work_log.md` (최상단에 한 줄 추가만) |

다른 역할의 영역을 고쳐야 하면 **그 역할에 티켓을 보낸다.** 정의 정본은 `studio.config.json` 이다 (`roles.*.owns` · `directorOwns` · `shared` · `allowedOverlaps`).

## 유지보수 — 감사 · 프로토콜 변경 · 업그레이드

리허설에서 쓰기 영역 문제가 반복된 원인은 세 가지였다: 주인 없는 프로토콜 파일, 커밋 시점에야 드러나는 영역 밖 쓰기, 기록 없는 템플릿 덮어쓰기. 그래서 다음을 둔다.

| 기능 | 명령 | 하는 일 |
|---|---|---|
| **감사** | `studio.py audit` | 미커밋 변경 중 **어느 영역에도 없는 파일**(주인 없음)과 **여러 역할에 겹치는 파일**을 보여 준다. 의도된 겹침(`allowedOverlaps`, 기본 `production/epics`)은 제외. 현황판에 건수가 뜬다 |
| **프로토콜 변경 기록** | `studio.py protocol` · `protocol ack --by director --note "…"` | 설정 · 도구 · 헌장 · 프롬프트 · `CLAUDE.md` · `AGENTS.md` 의 지문을 `production/studio/protocol.json` 에 기록한다. 바뀌면 inbox · 현황판에 "미승인 변경" 이 표시되고, 디렉터가 확인(ack)하면 누가 · 언제 · 왜가 남는다 |
| **템플릿 업그레이드** | `studio.py upgrade --from <템플릿 저장소> [--dry-run]` | 스튜디오 · artgen 도구와 스튜디오 스킬을 갱신한다. 설정 파일은 **깊은 병합**(템플릿 기반 + 프로젝트 값 우선) — 디렉터 결정은 보존되고 새 키만 추가된다. `*.local.json` 은 건드리지 않는다. 끝나면 지문을 승인하고 역할마다 `info` 공지 티켓을 낸다 |

**세션의 반응 규칙**
- inbox 에 "프로토콜 미승인 변경" 이 보이면 **헌장 · README · 업무 루프를 다시 읽고 그대로 진행**한다. 수상한 변경으로 반복 보고하지 않는다 (디렉터가 현황판에서 확인한다).
- 실행 중인 프로젝트의 도구 파일을 손으로 덮어쓰지 않는다. 갱신은 `upgrade` 로만 한다.
- 티켓을 완료하기 전에 `studio.py audit` 을 보고, 자기가 만든 주인 없는 파일이 있으면 완료 note 에 경로와 함께 적는다 (디렉터가 영역을 정하거나 직접 커밋).

## 커밋 (게이트 통과 · 티켓 완료 시 각자)

```bash
python .agent/tools/studio/studio.py commit art -m "[studio:art] T-0012 전투 VFX 4종 승격" [--dry-run]
```
- 자기 쓰기 영역과 공유 영역의 변경만 파일을 명시해 커밋한다. 다른 세션이 스테이징한 파일은 섞이지 않는다.
- 다른 세션이 git 을 쓰고 있어 `index.lock` 이 잡혀 있으면 자동으로 재시도한다.
- `Assets/` 파일에 `.meta` 가 없으면 경고한다. 아트는 dev 가 Unity 임포트를 확인한 뒤(다음 커밋 때) `.meta` 와 함께 커밋한다.
- 디렉터 영역(프로토콜 · 지침 · `CLAUDE.md`)은 `studio.py commit director -m "…"` 로 디렉터가 커밋한다 (`/studio-status commit`).
- **푸시는 디렉터가 직접 한다.**

## CLI 요약

```bash
S="python .agent/tools/studio/studio.py"
$S join <role> <session> [--kind claude|dispatch|manual] [--agent <도구>]      $S roster
$S watch <role> [--timeout 초]    # 처리할 티켓이 생길 때까지 대기 (0 = 생김, 3 = 시간 초과)
$S dispatch <role> --agent <프리셋> [--once] [--max-runs N] [--dry-run] [--force-lock]
$S agents                        # 에이전트 프리셋 · 설치 여부
$S new --from R --to R --type T --title "…" [--body-file f] [--priority P0|P1|P2] [--gate G2] [--depends T-1,T-2] [--refs a,b]
$S inbox <role> [--all]          $S show T-0001
$S update T-0001 --by R [--status S] [--to R] [--note "…"]
$S gate list | request G1 --by planning | approve G1 --by director --note "…" | reject … | add M1 --name … --artifacts … --unlocks …
$S status                        $S pause --reason "…" | resume
$S changes <role>                # 내 영역 미커밋 변경 + 진행 중 티켓 (중단 후 재개 점검)
$S audit                         # 주인 없는 변경 · 역할 겹침
$S protocol [ack --by director --note "…"]   # 프로토콜 변경 확인 · 승인
$S upgrade --from <템플릿> [--dry-run]         # 도구 갱신 (설정 보존 · 공지 티켓)
$S commit <role|director> -m "…" [--dry-run]
```
모든 명령은 `--json` 을 지원한다. `new` 와 `update` 의 JSON 출력에는 알림을 보낼 세션 이름(`notifySession`)이 들어 있다.

## 운영 규칙 (모든 세션 공통)

1. **티켓 없는 메시지 금지.** SendMessage 는 티켓이 생기거나, 재배정되거나, 완료되거나, 게이트가 바뀔 때만, 로스터의 `kind: claude` 세션에만 보낸다. 수신 확인이나 인사는 보내지 않는다 (핑퐁 방지).
2. 메시지 첫 줄 형식: `[studio] T-0012 asset-request planning→art: 전투 VFX 4종`. 둘째 줄: `처리: python .agent/tools/studio/studio.py show T-0012`
3. `[studio]` 메시지를 받은 세션은 진행 중인 작업을 마친 뒤 받은 티켓 처리 절차(`/studio-join` 의 업무 루프)로 들어간다.
4. **정지(`PAUSED`) 중에는 새 티켓에 착수하지 않는다.** 진행 중인 티켓만 안전한 지점까지 마무리하고 멈춘다.
5. **권한 경계:** 내 세션에서 거부되었거나 막힐 작업을 다른 세션에 대신 시키지 않는다. 그런 일은 디렉터 티켓으로 올린다.
6. 같은 티켓에서 2회 연속 실패하면 `blocked` 로 바꾸고 원인을 note 에 적는다. 같은 일을 계속 재시도하지 않는다.
7. 비밀값(API 키)을 티켓 · 메시지 · 로그에 쓰지 않는다.

## 사용량 한도

세 세션은 **같은 계정의 사용량 한도를 함께 쓴다.** 그래서 단일 세션보다 약 3배 빨리 한도에 닿고, 닿으면 보통 세 세션이 함께 멈춘다.

| 대상 | 한도 도달 시 |
|---|---|
| 세션 | 응답이 중단되고, 초기화 후에도 **스스로 재시작하지 않는다** |
| 티켓 · 게이트 · 로스터 | 파일에 그대로 남는다. 처리 중이던 티켓은 `in-progress` 로 남는다 |
| 작업 중 파일 | 반쯤 된 상태로 작업 트리에 남는다. 커밋은 티켓 완료 시점에만 하므로 미완성 작업은 커밋되지 않는다 |
| 세션 간 알림 | 받는 세션의 대기열에 남았다가 다시 움직일 때 전달된다. 놓쳐도 일감은 티켓 파일에 있다 |

**예방**
- 한도가 가까우면 `/studio-status pause` 로 먼저 정지한다. 진행 중 티켓만 마무리하고 멈추므로 깔끔하게 선다. 사용량은 `/usage` 로 확인한다.
- 역할별로 모델을 나눈다. 판단이 많은 planning 은 상위 모델, 정해진 절차를 반복하는 art · dev 는 `/model` 로 가벼운 모델.
- 작업량을 줄인다. `/asset-spec` · 리뷰 스킬은 `--review lean`, `/ko-art-gen` 은 `--variants` 를 작게.

**복구 (한도 초기화 후)**
1. 각 세션에 `/studio-join <역할>` 을 다시 입력한다. 업무 루프가 `in-progress` 티켓부터 처리한다. 재개 시에는 `studio.py changes <역할>` 로 반쯤 된 변경을 확인하고, 이어서 할지 되돌리고 다시 할지 정해 스레드에 기록한다.
2. `/studio-status` 로 정체 티켓이 없는지 확인한다. 정지했던 경우에는 `/studio-status resume` 도 한다.

## 한계

- **같은 작업 폴더를 전제로 한다.** 상태 파일 · 역할별 커밋이 한 작업 트리에 있어야 한다. 다른 PC 의 Claude Code 세션도 Remote Control(같은 계정)로 메시지는 받을 수 있지만, 티켓 파일이 공유되지 않으므로 지금 구조로는 다른 PC 에 역할을 둘 수 없다.
- 깨우기는 파일 감시가 기본이고, SendMessage 는 Claude 세션끼리의 보조 경로다. 알림이 유실돼도 상태는 유실되지 않는다. 꺼져 있던 세션은 다음 `/studio-join` 또는 `dispatch` 시작 때 밀린 티켓을 처리한다.
- Unity 에디터 · MCP 는 하나뿐이므로 dev 세션이 병목이 될 수 있다. 아트 승격 후 임포트 확인은 dev 가 몰아서 처리한다.
