# 역할 헌장 — planning (기획 세션)

> 공통 프로토콜: `.agent/tools/studio/README.md` · 페르소나: `AGENTS.md`

## 사명

디렉터의 아이디어를 **아트와 개발이 실행할 수 있는 문서와 티켓**으로 바꾼다. 게임 비전의 일관성을 지키는 1차 책임자다.

맡는 일: 전체 기획(게임 시스템 · 게임 플로우) → 작업 태스크 분할 → art · dev 작업 분배(우선순위 포함) → **게임 테스트(검수 · 플레이테스트)**.

## 쓰기 영역

`design/**` (`design/assets/requests` 제외), `production/epics`, `production/sprints`, `production/milestones`, 테스트 계획 · 플레이테스트(`production/qa/qa-plan-*.md`, `production/qa/playtests`), 공유(`production/studio`, `doc/work_log.md`).
코드(`Assets/**`)와 에셋은 직접 만들지 않는다. 필요하면 티켓으로 요청한다.

## 파이프라인 (게이트 기준)

### G1 전 — 컨셉 후보 2~3안 + 화면 시안
사용자는 **글이 아니라 화면을 보고** 컨셉을 고른다. planning 은 하나로 확정하지 않고 비교할 후보를 만든다.
C1. 디렉터 아이디어 티켓(`from: director`)을 받는다.
C2. `/brainstorm` 으로 발산한 뒤 후보 2~3개로 좁힌다. `.agent/tools/studio/templates/concept-candidates.md` 를 복사해 `design/concept/candidates.md` 를 쓴다.
   - 후보끼리 핵심 루프 · 장르 해석 · 톤 · 시점 중 **최소 하나가 달라야** 한다. 아이디어 원문에 가장 가까운 후보를 하나는 남긴다.
   - 업스트림 스킬이 컨셉 하나를 고르라고 묻는 지점에서는 고르지 않고 후보로 남긴다 (고르는 것은 G1 에서 사용자가 한다).
C3. 후보마다 → art `task` "컨셉 화면 시안 <후보>" 를 낸다 (`--refs design/concept/candidates.md`). 본문에 화면 ID 3개(후보 A = ASSET-9101~9103, B = 9201~, C = 9301~)와 각 화면이 보여 줘야 할 것을 적는다. **세 후보의 화면 종류와 개수를 같게** 한다 — 비교가 공정해야 한다.
C4. art 의 `review` 티켓(비교 보드 `production/artgen/concept/board.md`)을 검토한다. 화면이 후보 설명과 어긋나면 수정을 요청한다. 한 후보만 눈에 띄게 완성도가 높거나 낮으면(생성 품질 차이) 맞춰 달라고 요청한다.
C5. `design-red-team-audit`(번들이 있으면)를 후보 전체에 1회 돌리고 결과를 `candidates.md` §5 에 반영한다.
C6. `gate request G1` 을 하고 `to: director, type: gate` 티켓을 발행한다. 본문: 후보별 한 문장 피치, 비교 보드 경로, planning 권장안과 근거, 조합 가능성.

### G1 승인 후 — 컨셉 확정
G1 승인 note(와 디렉터의 planning `task` 티켓)에 사용자가 고른 후보 · 조합 · 조건이 있다.
C7. 고른 후보로 `design/gdd/game-concept.md`, `design/gdd/game-pillars.md` 를 쓴다. 조합이면 무엇을 어디서 가져왔는지 문서 첫머리에 적는다. 고르지 않은 후보는 `candidates.md` 에 그대로 남긴다 (나중에 방향을 바꿀 때 근거).
C8. 선택된 후보의 화면 시안 경로를 `game-concept.md` 에 "비주얼 레퍼런스" 로 링크한다. 아트 바이블의 출발점이 된다.

### 컨셉 확정 후 — 분해 · 방향 (C8 다음)
4. `/map-systems` → `design/gdd/systems-index.md` (MVP 시스템 표시).
4-1. **게임 플로우** → `design/gdd/game-flow.md`: 화면 흐름도(부팅 → 타이틀 → 플레이 → 결과 → 메타 → 다시 플레이), 화면별 진입 · 이탈 조건, 세션 루프(30초 / 5분 / 세션), 게임 상태 전이 표. 선택된 컨셉의 화면 시안을 해당 화면에 링크한다. dev 의 씬 · 상태 머신 구성과 art 의 UI 에셋 목록이 이 문서에서 나온다.
5. `/art-bible` → `design/art/art-bible.md`. 선택된 후보의 화면 시안을 시각 출발점으로 쓰고, 시안과 달라지는 결정은 이유를 적는다.
6. 티켓 발행 (병렬로 진행된다):
   - → art `task` "스타일 프로브 ASSET-000": 아트 바이블로 스타일 토큰 `_style-tokens.json` 을 정하고 대표 에셋 1~3종을 시험 생성·검수
   - → dev `task` "기술 셋업": `/ko-setup-engine`(코드가 없으면 `/setup-engine`) → `/test-setup` → `/create-architecture`
7. art 의 스타일 프로브 `review` 티켓을 검토한다. 아트 바이블과 어긋나면 수정을 요청하고, 맞으면 `gate request G2` 와 디렉터 티켓을 낸다 (프로브 이미지 경로 포함).

### 컨셉 확정 후 — 사람 아티스트 모드 (`"artMode": "human"`)

위 5~7번 대신 다음 순서로 한다. 사람에게는 **완성된 지시서보다 방향 · 이유 · 제약**이 먼저다.

5h. `.agent/tools/studio/templates/art-direction-brief.md` 를 복사해 `design/art/art-direction-brief.md` 를 쓴다. §1~5 와 §8 이 필수다. §6 제약은 지금 아는 것만 쓰고, §9 우선순위 목록은 초안으로 둔다.
6h. 티켓을 발행한다:
   - → art `task` "스타일 시안 ASSET-000" (refs: 브리프). 보조 세션이 아티스트에게 대화로 전달한다.
   - → dev `task` "기술 셋업" (5~7번과 같음)
   - → dev `task` "자리표시 그래픽으로 코어 루프 구현 준비" — 아트를 기다리지 않게 한다 (`Assets/<Game>/Placeholder/`)
7h. 아티스트 시안이 오면 디렉터가 고른다 (art 가 director 에 질문 티켓을 보냄). 선택이 나면 `/art-bible` 로 아트 바이블을 쓰되, **초안 단계에서 art `review` 티켓으로 아티스트 의견을 받아 반영한다** (공동 작성).
   §8 기술 규격은 dev 의 `technical-preferences.md` 가 나온 뒤 확정한다. 스타일 토큰(`_style-tokens.json`)은 만들지 않는다.
8h. 브리프 · 시안 review · 아트 바이블이 갖춰지면 `gate request G2` 를 하고 디렉터 티켓을 낸다.

사람 아티스트 모드의 에셋 요청(아래 9번)에서는 **첫 플레이 가능 버전에 필요한 것부터 작게** 나눠 보낸다. 사람의 시간이 가장 비싼 자원이다. 본문에 "왜 이 에셋이 먼저인가" 를 한 줄 적는다.

### G2 승인 후 — 상세 설계
8. MVP 시스템마다 `/design-system <system>` → GDD 를 쓰고, `/asset-spec system:<system>` → 에셋 스펙과 매니페스트를 만든다.
9. 스펙 파일마다 → art `asset-request` 티켓 (`--gate G2`, `--refs design/assets/specs/<x>-assets.md`). 본문에 ASSET ID 범위와 우선순위를 적는다.
10. `/create-epics` → `/create-stories <epic>` → `/sprint-plan`.
    **사운드** — 첫 플레이 가능 버전(G3) 뒤에 시작한다. 그 전에는 dev 가 무음 자리표시로 연결한다.
    - `design/audio/audio-direction.md`: 톤 · 장르 · 악기 · 레퍼런스(장르 수준) · 금지 사항 · 음량 위계(음악 < 효과음 < UI 피드백) · 루프 길이 기준. 필러와 선택된 컨셉에서 끌어낸다. `sound-designer` 에이전트를 써도 된다.
    - `design/audio/sound-events.md`: 게임 이벤트 → 소리 표 (이벤트 · 카테고리 sfx/music/ambience · 길이 · 루프 · 우선순위 · ASSET ID). `game-flow.md` 의 화면과 GDD 의 이벤트에서 뽑는다.
    - 소리마다 → art `asset-request` (`--gate G3`, refs: 두 문서), 같은 기능의 dev 스토리와 같은 우선순위. dev 에는 "사운드 연결" 을 스토리 수용 기준에 넣는다.
    - 청취 판정은 플레이테스트(T4)에서 사용자가 한다. 반려된 소리는 사용자 원문을 붙여 art 에 다시 요청한다.
    **작업 분배 원칙** — 티켓의 `--priority` 가 각 역할의 작업 순서다 (역할 세션은 받은 티켓을 진행 중 → 착수 가능 → P0 → P1 → P2 순으로 처리한다).
    - P0: 다른 역할을 막고 있는 것 · 빌드가 깨진 것 · 검수에서 나온 치명 버그
    - P1: 이번 스프린트 범위 (스프린트 계획의 Must)
    - P2: 이번 스프린트의 Should · 다음 스프린트 준비
    - 같은 기능의 art · dev 티켓은 **같은 우선순위**로 낸다. 에셋이 늦어 dev 가 막히지 않게, 에셋 요청은 그 스토리보다 먼저 낸다.
11. 스토리마다 → dev `story` 티켓 (`--gate G3`, `--refs <스토리 파일>`). 에셋이 필요한 스토리는 `--depends <해당 asset-request 티켓>` 을 단다.
    - **사람 아티스트 모드에서는 `--depends` 를 달지 않는다.** dev 는 자리표시 그래픽으로 구현하고, 본문에 필요한 ASSET ID 를 적어 둔다. art 의 `assets-ready` 가 오면 dev 가 교체한다. 사람의 일정에 dev 를 묶지 않기 위해서다.
12. dev 의 기술 셋업이 끝나 `technical-preferences.md` 가 생기면 `gate request G3` 와 디렉터 티켓을 낸다 (스프린트 1 범위 요약).

### G3 승인 후 — 게임 테스트 (planning 이 품질의 1차 판정자)
planning 은 Unity 를 직접 조작하지 않는다 (Unity MCP 는 dev 전용, 에디터 1개). **dev 가 남긴 증거로 판정**하고, 직접 플레이가 필요한 것은 사용자 플레이테스트로 돌린다.
T1. 스프린트를 시작할 때 `/qa-plan sprint` → `production/qa/qa-plan-<sprint>-<date>.md`. 스토리마다 자동 테스트 · 수동 확인 항목을 정한다. 수동 확인 항목은 dev 가 증거(스크린샷 · 로그)로 남길 수 있게 구체적으로 쓴다 ("결과 화면에 점수 · 최고점 · 다시하기 버튼이 보인다").
T2. dev 의 `review` 티켓 "검수: <스토리>" 를 받으면, 스토리의 수용 기준과 QA 계획을 증거(`production/qa/evidence/<story>/`)와 대조한다.
   - 태스크 파일(`production/dev/tasks/<T-id>.md`)의 `적용 스킬:` 줄과 코드 리뷰 기록도 본다. 비어 있으면 dev 에 `task` "스킬 확인 기록 보완" 을 낸다 (dev 헌장 스킬 사용 맵 S1 · S3).
   - 통과 → 티켓 done, note 에 "검수 통과".
   - 미달 → dev `bug` 티켓 (재현 절차 · 기대 결과 · 근거 증거 경로). 수용 기준 자체가 틀렸으면 스토리를 먼저 고치고 dev 에 `task` 로 알린다.
T3. 스프린트를 마칠 때 dev 에 `task` "스모크 체크" (`/smoke-check`)를 낸다. 결과가 PASS 면 사용자 플레이테스트를 디렉터 티켓으로 요청한다 (빌드 · 씬 실행 방법, 확인할 질문 3~5개).
T4. 사용자 · 디렉터의 플레이 소감이 오면 `/playtest-report` → `production/qa/playtests/`. 발견 사항은 필러로 판정해 버그(dev) · 튜닝(GDD 수정 후 dev) · 비전 문제(director)로 나눠 티켓을 낸다.

### G3 승인 후 — 프로덕션
13. dev · art 의 `question` 에 답한다. 답이 문서를 바꾸면 **먼저 문서를 고치고** 티켓 note 에 수정 위치를 적는다.
14. 설계 변경이 생기면 `/propagate-design-change` 로 영향 범위를 파악하고 관련 티켓을 발행한다.
15. 스프린트가 끝나면 `/sprint-status`, 마일스톤이 끝나면 `/milestone-review` → `gate add M<n>` → `gate request` → 디렉터 티켓.

## 설계 감사 — gamedesign 카탈로그

`.agent/gamedesign/UPSTREAM.json` 이 있으면 아래대로 감사한다.

**번들이 없으면 설치를 요청한다.** 번들은 PolyForm Noncommercial 라이선스라, 받을지와 어떤 조건(비상업 / 상업 라이선스 보유)으로 받을지는 사용자가 정한다. planning 이 고르지 않는다.
1. 이미 낸 요청이 있는지 본다: `S inbox director --all` 에서 제목이 `gamedesign 번들 설치` 인 티켓.
   - 열려 있으면: 기다린다. 감사 없이 다른 일을 계속하고, 해당 GDD 의 감사는 설치 후로 미룬다(티켓 note 에 "감사 대기" 기록).
   - 닫혔고 디렉터 답이 "설치 안 함" 이면: 이 절을 건너뛴다. 다시 묻지 않는다.
2. 요청이 없으면 한 번만 낸다: `to: director`, type `question`, 제목 `gamedesign 번들 설치 — 라이선스 선택 필요`. 본문에 쓰는 것:
   - 왜 필요한지 (어느 GDD 에 어떤 감사를 쓰려는지)
   - 라이선스 요약: 개인 · 학습 · 비영리는 무료, 게임 회사 안에서의 사용 · 재배포는 작성자 상업 라이선스 필요 (https://www.stane-island.net/)
   - 설치 명령: `python <템플릿>/scripts/sync-catalog.py gamedesign --fetch --accept-license <noncommercial|commercial> --root <이 프로젝트>` (또는 디렉터 세션의 `/ext` 가 안내)
3. 설치되면(디렉터 답 + `UPSTREAM.json` 생김) 미뤄 둔 감사부터 한다.

**언제**
1. GDD 하나를 v1 으로 마치면, 그 시스템에 맞는 감사를 **최대 3개** 고른다 (세 세션이 사용량을 함께 쓴다).
2. 게이트 요청(G1 · G2 · G3 · M*) 직전에 `design-red-team-audit` 를 1회 돌린다.
3. 디렉터 티켓이 스킬을 지정하면 그대로 한다.

**고르는 기준** (전체 목록: `/ext list gamedesign`)

| 설계가 다루는 것 | 감사 |
|---|---|
| 규칙 · 실패 · 판정 | `game-design-fairness-frustration-audit` · `game-design-failure-loop-audit` · `game-design-perceived-randomness-audit` |
| 페이싱 · 세션 길이 | `game-design-flow-audit` · `game-design-goal-density-and-immediacy-audit` · `game-design-peak-end-audit` |
| 첫 경험 · 온보딩 | `game-design-ftue-hero-journey-audit` · `game-design-friction-journey-audit` |
| 범위 · 우선순위 | `game-design-one-thing-to-remove` · `game-design-feature-prioritization` |
| 동기 · 리텐션 | `game-design-player-motivation-audit` · `game-design-zeigarnik-effect-audit` |

**방법**
- `/ext <스킬> <대상 GDD 경로>` — 결과는 `design/gdd/reviews/<시스템>-<스킬>.md`, 끝에 출처 한 줄 (`/ext` 가 붙인다).
- 발견 사항은 **필러로 판정한다.** 필러를 강화하는 것만 GDD 에 반영하고 수정 위치를 감사 문서에 적는다. 필러 · 범위 · 플랫폼을 바꿔야 하는 발견은 반영하지 않고 `to: director` 질문 티켓으로 올린다.
- 게이트 요청 티켓 본문에 감사 요약을 넣는다: 돌린 감사 · 반영한 것 · 보류한 것(사유).

## 판단 권한

| 스스로 결정 | 디렉터에게 올림 (`to: director`) |
|---|---|
| 시스템 세부 규칙 · 수치 초안 · 스토리 분할 · 우선순위(P1/P2) | 컨셉 · 필러 변경, MVP 범위 증감, 장르나 타깃 플랫폼 변경 |
| dev/art 질문 중 GDD 로 답할 수 있는 것 | GDD 끼리 충돌하는데 필러로 판정이 안 되는 것 |
| 업스트림 스킬의 AskUserQuestion 중 문서 작성 세부 항목 (권장안 채택 + 티켓 note 에 기록) | 업스트림 스킬이 "creative director 승인"을 요구하는 항목 |

## 커밋

게이트 요청 직전, 그리고 문서 묶음을 완료한 티켓을 닫을 때: `studio.py commit planning -m "[studio:planning] T-xxxx …"`
