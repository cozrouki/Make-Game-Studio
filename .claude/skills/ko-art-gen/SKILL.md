---
name: ko-art-gen
description: 그래픽 생성 파이프라인 (한국어) — 에셋 스펙 → 생성 요청 → 이미지 생성 → 아트 바이블 검수·재생성 → Unity 승격·임포트 설정. 백엔드 중립(artgen 어댑터)
argument-hint: "<ASSET-NNN | spec:<target> | next> [--provider <이름>] [--variants N] [--rounds N] [--auto]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, AskUserQuestion
---

# /ko-art-gen — 기획 의도대로 그래픽 만들기

`/asset-spec` 이 만든 스펙을 실제 이미지로 만들고, 아트 바이블 기준으로 검수한 뒤 Unity 에셋으로 넣는다.
결정적 작업(생성·저장·승격)은 `.agent/tools/artgen/artgen.py` CLI 가, 판단(요청 작성·시각 검수·재생성 방향)은 이 스킬이 맡는다.
설계·스키마·백엔드 연결: `.agent/tools/artgen/README.md` — **처음 실행할 때는 반드시 읽는다.**

## 사용법

```
/ko-art-gen ASSET-012                 단일 에셋
/ko-art-gen spec:combat               design/assets/specs/combat-assets.md 의 Needed 에셋 전부
/ko-art-gen next                      매니페스트에서 Needed 인 첫 에셋
/ko-art-gen ASSET-012 --variants 6 --rounds 2
/ko-art-gen spec:combat --auto        에셋별 사용자 확인 생략 (최종 승격 목록만 확인)
```

CLI 호출은 줄여서 `artgen` 이라고 쓴다. 실제 명령은 `python .agent/tools/artgen/artgen.py --json <명령>` 이다 (`--json` 은 하위 명령 앞에 둔다).

---

## Phase 0: 사전 점검

1. **선행 산출물** — 하나라도 없으면 중단하고 안내한다.
   - `design/art/art-bible.md` 가 없으면 → "`/art-bible` 을 먼저 실행하세요. 검수 기준이 아트 바이블입니다."
   - `design/assets/asset-manifest.md` 와 해당 스펙 파일이 없으면 → "`/asset-spec system:<이름>` 을 먼저 실행하세요."
2. **백엔드 상태** — `artgen providers` 를 실행해 결과를 보여 준다.
   - 스튜디오 모드가 사람 아티스트 모드(`.agent/tools/studio/studio.config.json` 의 `"artMode": "human"`)이면 이 스킬의 자동 생성 루프를 쓰지 않는다. `roles/art-human.md` 절차(`--provider manual` 로 납품 수령)를 따른다.
   - 활성 provider 가 `mock` 이면 이렇게 알린다: "이미지 생성 백엔드가 아직 정해지지 않아 **자리표시 이미지(mock)** 로 진행합니다. 요청·승격·임포트 흐름은 실제와 같고, 시각 검수만 생략합니다. 백엔드 연결 방법은 `.agent/tools/artgen/README.md` §백엔드 연결을 보세요."
   - 활성 provider 가 `ready: false` 이면 메시지를 보여 주고 중단한다. 대안으로 `--provider mock` 을 제안한다.
3. **설정 값** — `.agent/tools/artgen/artgen.config.json`(+ `.local.json`)에서 `defaults.variants / maxRounds / passScore` 를 읽는다. 인수로 받은 `--variants`·`--rounds` 가 이 값보다 우선한다.

## Phase 1: 대상 결정 · 컨텍스트 로드

- `ASSET-NNN` → 매니페스트에서 행을 찾고, 그 행의 Spec File 에서 `## ASSET-NNN` 섹션을 읽는다.
- `spec:<target>` → `design/assets/specs/<target>-assets.md` 에서 Status 가 Needed 인 섹션을 모두 읽는다.
- `next` → 매니페스트에서 Status 가 Needed 인 첫 행.
- 카테고리가 Audio 또는 3D 인 에셋은 **범위 밖**으로 표시하고 건너뛴다 (artgen 은 2D PNG 만 다룸).

함께 읽을 것:
- 아트 바이블에서 Visual Identity Statement, Shape Language, Color System(의미 색 hex), 금지 사항, §8 Asset Standards 를 추출한다.
- `.claude/docs/technical-preferences.md` 에서 네이밍 규칙과 텍스처 예산을 추출한다. 없으면 아트 바이블 §8 만 쓰고 그 사실을 알린다.
- `AGENTS.md` §6 게임 폴더 매핑으로 `unity.dest` 의 게임 폴더를 정한다.
- 기존 요청 `design/assets/requests/ASSET-NNN.json` 이 있으면 재사용한다. 이 경우 Phase 2 를 건너뛰고 history 를 이어 간다.

## Phase 2: 생성 요청 작성 (기획 → 그래픽 계약)

에셋마다 `design/assets/requests/ASSET-NNN.json` 을 `artgen-request/1` 형식으로 작성한다 (`.agent/tools/artgen/schema/example-request.json` 참고).

| 필드 | 작성 규칙 |
|---|---|
| `prompt.subject` | 스펙의 Visual Description 을 **영어** 묘사로 옮긴다. 스펙의 Generation Prompt 가 있으면 출발점으로 쓰되, 스타일·팔레트 단어는 아래 필드로 분리한다 |
| `prompt.style` | 아트 바이블에서 뽑은 **프로젝트 공통 스타일 토큰**. 처음 정한 토큰 목록을 `design/assets/requests/_style-tokens.json` 에 저장하고 모든 요청이 그대로 재사용한다. 에셋마다 다르게 쓰지 않는다 (일관성의 핵심) |
| `prompt.palette` | 이 에셋의 의미 색만 넣는다 (2~5개, hex) |
| `prompt.negative` | 공통(text, watermark, signature, blurry, jpeg artifacts)에 아트 바이블 금지 사항을 더한다 |
| `output` | 스펙의 Dimensions. 스프라이트·아이콘·VFX·UI 는 `transparent: true` 가 기본, 환경·텍스처는 false |
| `unity.dest` | 스펙의 Naming 을 따르며 `Assets/<게임폴더>/Art/<Category>/...png` 형태 |
| `unity.import` | 카테고리 기본값(아래 표)에 아트 바이블 §8 · 성능 예산을 반영한다 |
| `source` | spec · artBible · gdd 경로 (추적성) |

카테고리별 `unity.import` 기본값 (아트 바이블과 충돌하면 **아트 바이블이 우선**한다):

| category | textureType | filterMode | mipmaps | wrapMode | compression |
|---|---|---|---|---|---|
| sprite · vfx · icon · ui | Sprite | Bilinear (픽셀아트면 Point) | false | Clamp | Normal (UI 는 HighQuality) |
| environment | Sprite 또는 Default | Bilinear | true | Clamp | Normal |
| texture | Default | Trilinear | true | Repeat | Normal |
| concept | Default | Bilinear | false | Clamp | None (참고용, 런타임 미사용 경로 권장) |

`maxSize` 는 출력 크기 이상인 가장 작은 2의 거듭제곱으로 한다 (예: 300px → 512).

작성 후 `artgen validate <요청들>` 을 실행하고, 실패한 요청은 고친 뒤 다시 검증한다.
그다음 `artgen prompt <요청>` 으로 컴파일된 프롬프트를 사용자에게 보여 준다. `--auto` 가 아니면 `AskUserQuestion` 으로 확인받는다:
- `[A] 생성 진행` / `[B] 프롬프트 수정` / `[C] 이 에셋 건너뛰기`

## Phase 3: 생성

`artgen generate <요청> [--provider ..] [--variants ..]` 를 실행한다.
- `error` 가 오면 원문을 그대로 보여 주고 이 에셋을 중단한다 (다른 에셋은 계속). 자동 재시도는 하지 않는다.
- `warnings` 는 Phase 4 의 기술 점수에 반영한다.
- 매니페스트에서 이 에셋의 Status 를 `In Progress` 로 바꾼다 (Progress Summary 개수도 같이 갱신).

## Phase 4: 검수 (기획 의도 대조)

`run.json` 의 `placeholder` 가 true(mock)이면 **기술 항목만** 채점하고 시각 항목은 "N/A (placeholder)" 로 적는다. 다음으로 넘어가되 재생성은 하지 않는다.

그 외에는 각 변형 PNG 를 **Read 로 직접 보고** `.agent/tools/artgen/README.md` §검수 루브릭 5축으로 1~5점을 매긴다.
- 판독성은 게임 내 표시 크기를 기준으로 판단한다. 스펙의 표시 크기를 떠올려 축소했을 때를 가정한다.
- 점수마다 **근거 한 줄과 아트 바이블 섹션 인용**을 붙인다. "좋아 보임" 같은 근거 없는 점수는 금지한다.
- 통과 조건: 평균 ≥ passScore, 그리고 기술 항목 1점 없음.

결과는 `production/artgen/ASSET-NNN/review.md` 에 추가한다 (최신이 위):

```markdown
## v002 — 2026-10-20 · provider=<이름> · 통과 2/4

| 변형 | 스타일 | 형태 | 색 | 판독성 | 기술 | 평균 | 판정 |
|---|---|---|---|---|---|---|---|
| variant_01 | 4 | 3 | 5 | 4 | 5 | 4.2 | 통과 |

- variant_01 형태 3: 실루엣 하단이 뭉개짐 — 아트 바이블 §3 "64px 에서 실루엣 판독" 미달
- 프롬프트 변경(다음 라운드): ...
```

**재생성 루프** — 통과 변형이 없고 라운드가 남았으면:
1. 실패 원인을 프롬프트 수정으로 바꾼다. subject·composition·negative 만 고치고 **style 토큰은 고치지 않는다**. 스타일 자체가 문제면 루프를 멈추고 사용자에게 아트 바이블 또는 공통 토큰 수정을 제안한다.
2. 요청 JSON 의 `history` 에 `{round, version, change, reason}` 을 추가한다.
3. Phase 3 으로 돌아간다. 라운드를 다 쓰면 루프를 멈추고 Phase 5 에서 사용자에게 판단을 넘긴다.

## Phase 5: 선택 (사용자 승인)

통과 변형(없으면 최고점 변형)의 경로와 점수표를 보여 준다. 사용자가 직접 볼 수 있도록 파일 경로를 절대경로로 제시한다. 그리고 `AskUserQuestion` 으로 묻는다:
- `[A] <추천 변형> 승격` / `[B] 다른 변형 선택` / `[C] 방향 바꿔 재생성` / `[D] 반려`

- A·B → `artgen select ASSET-NNN <version> <file>`
- C → 사용자 지시를 history 에 기록하고 Phase 3 으로 간다 (라운드 카운트 초기화)
- D → `artgen reject ASSET-NNN --reason "<사유>"`. 매니페스트 상태는 Needed 로 되돌리고 사유를 review.md 에 적는다

`--auto` 모드에서는 통과한 최고점 변형을 자동으로 select 한다. 통과 변형이 없는 에셋은 승격하지 않고 보고만 한다. **승격 직전에 전체 목록을 한 번 확인받는다.**
단, **스튜디오 모드**(이 세션이 `production/studio/roster.json` 의 art 역할로 등록됨)에서는 이 일괄 확인도 생략한다. 디렉터의 G2 게이트 승인이 양산 승인을 대신한다. 결과는 티켓 note 와 review.md 에 남긴다.

## Phase 6: Unity 승격

1. **임포터 설치 (최초 1회)** — `Assets/ArtGen/Editor/ArtGenImportPostprocessor.cs` 가 없으면, 사용자에게 확인받은 뒤 `.agent/tools/artgen/unity/` 의 `.cs` 와 `.asmdef` 를 그 위치로 복사한다. 임포터가 없으면 승격된 텍스처가 Unity 기본 설정으로 임포트된다고 알린다.
2. `artgen promote <요청>` 을 실행한다. "이미 존재" 오류가 나면 교체 여부를 묻고, 승인받으면 `--force` 로 다시 실행한다 (기존 파일은 자동 백업됨).
3. **Unity 갱신** — MCP for Unity 가 연결되어 있으면 에셋 데이터베이스를 refresh 한 뒤 임포트 결과(textureType·maxSize)를 확인한다. 연결되어 있지 않으면 "Unity 에디터로 돌아가면 자동 임포트됩니다" 라고 안내한다.
4. 매니페스트 Status 를 `Done` 으로 바꾼다. `Approved` 는 인게임에서 확인한 뒤 사용자가 결정한다. 스펙 파일의 해당 `**Status:**` 줄도 같이 갱신한다.
   - mock 결과를 승격했다면 Status 를 Done 으로 올리지 않고 `In Progress` 에 그대로 둔다. 매니페스트 행 끝에 `(placeholder)` 를 붙여 실제 백엔드로 다시 생성해야 함을 표시한다.

## Phase 7: 마무리

- 처리 요약을 표로 보여 준다: 에셋 · 라운드 · 최종 점수 · 결과(승격/반려/보류) · Unity 경로.
- `doc/work_log.md` 에 한 줄 기록: `[<게임태그>] /ko-art-gen: ASSET-012, ASSET-013 승격 (provider=<이름>)`.
- 다음 단계 제안:
  - 남은 Needed 에셋 → `/ko-art-gen next`
  - 납품물 대조 → `/asset-audit`
  - 인게임 배치·확인 → `/ko-story-cycle` 또는 MCP 씬 작업

## 원칙

- **기획 문서가 정본이다.** 스펙에 없는 요소를 프롬프트에 임의로 넣지 않는다. 필요하면 `/asset-spec` 에서 스펙을 먼저 고치도록 제안한다.
- 모든 생성은 새 버전으로 남는다. 덮어쓰기·삭제는 하지 않는다 (`promote --force` 는 백업 후 교체).
- 비밀값(API 키)을 요청·설정 파일·로그에 쓰지 않는다.
- 사용자 승인 없이 `Assets/` 에 쓰지 않는다 (`--auto` 도 승격 직전 일괄 확인 — 스튜디오 모드에서는 G2 승인이 이를 대신함).

## 관련

- 선행: `/art-bible` → `/asset-spec`
- 검증: `/asset-audit`
- 엔진 설정: `/ko-setup-engine` (technical-preferences.md — 네이밍·텍스처 예산)
- 도구 문서: `.agent/tools/artgen/README.md`
