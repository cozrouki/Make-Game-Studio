---
description: 그래픽 생성 파이프라인 (한국어) — 에셋 스펙 → 생성 요청 → 이미지 생성 → 아트 바이블 검수 → 엔진 승격
---

# /ko-art-gen — 기획 의도대로 그래픽 만들기

> Antigravity 워크플로. 정본 절차는 `.claude/skills/ko-art-gen/SKILL.md`, 도구 문서는 `.agent/tools/artgen/README.md`.
> 인수: `<ASSET-NNN | spec:<target> | next> [--provider <이름>] [--variants N] [--rounds N] [--auto]`

CLI: `python .agent/tools/artgen/artgen.py --json <명령>` (게임 프로젝트 루트에서 실행 — Unity · Godot · Unreal)

## 절차

**0. 사전 점검** — `design/art/art-bible.md`, `design/assets/asset-manifest.md`, 스펙 파일 중 하나라도 없으면 중단하고 `/art-bible`·`/asset-spec` 을 안내한다. `artgen providers` 결과를 보여 준다. 활성 provider 가 `mock` 이면 "백엔드 미정 — 자리표시 이미지로 흐름만 검증" 이라고 알린다.

**1. 대상 · 컨텍스트** — 인수로 에셋을 정한다 (3D 는 범위 밖. Audio 는 category sfx · music · ambience 로 만들고 기준 문서는 `design/audio/audio-direction.md` — README §오디오). 아트 바이블(Visual Identity·Shape Language·Color System·금지 사항·§8), `technical-preferences.md`(네이밍·예산), `AGENTS.md` §6(게임 폴더)을 읽는다.

**2. 생성 요청** — `design/assets/requests/ASSET-NNN.json` 을 `artgen-request/1` 형식으로 작성한다 (예시 `.agent/tools/artgen/schema/example-request.json`). 스타일 토큰은 `design/assets/requests/_style-tokens.json` 에 한 번 정하고 모든 에셋이 공유한다. `artgen validate` → `artgen prompt` 로 미리 보고 사용자 확인을 받는다.

**3. 생성** — `artgen generate <요청>`. 오류는 원문 그대로 보고하고 해당 에셋을 중단한다. 매니페스트 상태를 `In Progress` 로 바꾼다.

**4. 검수** — 각 PNG 를 직접 보고 README §검수 루브릭 5축(스타일·형태·색·판독성·기술)으로 1~5점을 매긴다. 점수마다 아트 바이블 근거를 붙이고 `production/artgen/ASSET-NNN/review.md` 에 기록한다. 미달이면 subject·composition·negative 만 고친다 (style 토큰은 고정). 수정 내역을 요청 `history` 에 남기고 3으로 돌아간다 (최대 maxRounds). mock 결과는 기술 항목만 본다. 오디오는 들을 수 없으므로 `run.json` 의 기술 지표 · 경고로만 채점하고 청취 판정은 사람에게 넘긴다 (review.md 에 "청취 대기").

**5. 선택** — 추천 변형과 점수를 보여 주고 사용자에게 고르게 한다 (승격 / 다른 변형 / 재생성 / 반려). 결과에 따라 `artgen select` 또는 `artgen reject --reason` 을 실행한다.

**6. 엔진 승격** — (Unity) `Assets/ArtGen/Editor/` 에 임포터가 없으면 확인받은 뒤 `.agent/tools/artgen/unity/` 의 `.cs` 와 `.asmdef` 를 복사한다. 이어서 `artgen promote <요청>` 을 실행한다 (기존 파일이 있으면 확인받고 `--force`). 매니페스트를 `Done` 으로 바꾼다. mock 결과면 `In Progress (placeholder)` 로 둔다.

**7. 마무리** — 요약 표를 보여 주고 `doc/work_log.md` 에 `[<tag>] /ko-art-gen: ASSET-… 승격 (provider=…)` 를 기록한다. 다음 단계로 `/ko-art-gen next` 또는 `/asset-audit` 을 제안한다.

## 원칙

기획 문서가 정본이다. 스펙에 없는 요소는 넣지 않는다. 생성 결과는 버전으로 쌓이며 덮어쓰지 않는다. 비밀값은 파일에 쓰지 않는다. 사용자 승인 없이 `Assets/` 에 쓰지 않는다.
