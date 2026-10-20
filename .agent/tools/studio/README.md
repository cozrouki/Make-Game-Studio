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

## 단계 게이트

| 게이트 | 요청자 | 산출물 (요청 시 존재 검사) | 승인되면 열리는 일 |
|---|---|---|---|
| **G1 컨셉** | planning | `design/gdd/game-concept.md`, `game-pillars.md` | 시스템 분해 · 아트 바이블 · 기술 셋업 |
| **G2 아트 디렉션** | planning | `art-bible.md`, `_style-tokens.json`, 스타일 프로브 `production/artgen/ASSET-000/review.md` | 에셋 양산 (art) |
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
| art | `design/assets/requests`, `production/artgen`, `Assets/*/Art/**`, `Assets/ArtGen` |
| dev | `Assets/**` (Art 제외), `Packages`, `ProjectSettings`, `production/qa`, `tests`, `production/epics` (스토리 상태 갱신만) |
| 공유 | `production/studio` (티켓 · 게이트), `doc/work_log.md` (최상단에 한 줄 추가만) |

다른 역할의 영역을 고쳐야 하면 **그 역할에 티켓을 보낸다.** 정의 정본은 `studio.config.json` 이다.

## 커밋 (게이트 통과 · 티켓 완료 시 각자)

```bash
python .agent/tools/studio/studio.py commit art -m "[studio:art] T-0012 전투 VFX 4종 승격" [--dry-run]
```
- 자기 쓰기 영역과 공유 영역의 변경만 파일을 명시해 커밋한다. 다른 세션이 스테이징한 파일은 섞이지 않는다.
- 다른 세션이 git 을 쓰고 있어 `index.lock` 이 잡혀 있으면 자동으로 재시도한다.
- `Assets/` 파일에 `.meta` 가 없으면 경고한다. 아트는 dev 가 Unity 임포트를 확인한 뒤(다음 커밋 때) `.meta` 와 함께 커밋한다.
- **푸시는 디렉터가 직접 한다.**

## CLI 요약

```bash
S="python .agent/tools/studio/studio.py"
$S join <role> <session>         $S roster
$S new --from R --to R --type T --title "…" [--body-file f] [--priority P0|P1|P2] [--gate G2] [--depends T-1,T-2] [--refs a,b]
$S inbox <role> [--all]          $S show T-0001
$S update T-0001 --by R [--status S] [--to R] [--note "…"]
$S gate list | request G1 --by planning | approve G1 --by director --note "…" | reject … | add M1 --name … --artifacts … --unlocks …
$S status                        $S pause --reason "…" | resume
$S commit <role> -m "…" [--dry-run]
```
모든 명령은 `--json` 을 지원한다. `new` 와 `update` 의 JSON 출력에는 알림을 보낼 세션 이름(`notifySession`)이 들어 있다.

## 운영 규칙 (모든 세션 공통)

1. **티켓 없는 메시지 금지.** SendMessage 는 티켓이 생기거나, 재배정되거나, 완료되거나, 게이트가 바뀔 때만 보낸다. 수신 확인이나 인사는 보내지 않는다 (핑퐁 방지).
2. 메시지 첫 줄 형식: `[studio] T-0012 asset-request planning→art: 전투 VFX 4종`. 둘째 줄: `처리: python .agent/tools/studio/studio.py show T-0012`
3. `[studio]` 메시지를 받은 세션은 진행 중인 작업을 마친 뒤 받은 티켓 처리 절차(`/studio-join` 의 업무 루프)로 들어간다.
4. **정지(`PAUSED`) 중에는 새 티켓에 착수하지 않는다.** 진행 중인 티켓만 안전한 지점까지 마무리하고 멈춘다.
5. **권한 경계:** 내 세션에서 거부되었거나 막힐 작업을 다른 세션에 대신 시키지 않는다. 그런 일은 디렉터 티켓으로 올린다.
6. 같은 티켓에서 2회 연속 실패하면 `blocked` 로 바꾸고 원인을 note 에 적는다. 같은 일을 계속 재시도하지 않는다.
7. 비밀값(API 키)을 티켓 · 메시지 · 로그에 쓰지 않는다.

## 한계

- 세션 간 알림은 **같은 PC 의 Claude Code 세션**끼리만 간다. 받는 세션이 꺼져 있으면 티켓은 파일에 남고, 다음 `/studio-join` 때 처리된다.
- 알림이 유실돼도 상태는 유실되지 않는다. 장시간 무인 운영이라면 각 세션에서 `/loop 30m /studio-join <역할>` 처럼 받은 티켓을 주기적으로 확인하게 할 수 있다.
- Unity 에디터 · MCP 는 하나뿐이므로 dev 세션이 병목이 될 수 있다. 아트 승격 후 임포트 확인은 dev 가 몰아서 처리한다.
