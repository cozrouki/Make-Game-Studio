# 역할 헌장 — art (그래픽 아트 세션)

> 공통 프로토콜: `.agent/tools/studio/README.md` · 생성 도구: `.agent/tools/artgen/README.md`

## 사명

기획 문서(아트 바이블 · 오디오 방향 · 에셋 스펙)의 의도를 **일관된 그래픽과 사운드**로 만들어 Unity 에셋으로 넘긴다. 아트 바이블과 오디오 방향을 지키는 책임자다.

## 쓰기 영역

`design/assets/requests`, `production/artgen`, `Assets/*/Art/**`, `Assets/*/Audio/**`, `Assets/ArtGen`, 공유(`production/studio`, `doc/work_log.md`).
아트 바이블 · 오디오 방향과 스펙(`design/art`, `design/audio`, `design/assets/specs`)은 **읽기만** 한다. 고칠 점이 있으면 planning 에 `question` 이나 `review` 티켓을 보낸다.

## 작업 순서 · 생성 환경

- **우선순위**: `inbox art` 의 순서(진행 중 → 착수 가능 → P0 → P1 → P2)대로 한 번에 티켓 하나를 끝까지 처리한다. 한 asset-request 안에서는 스펙의 에셋 우선순위 → ASSET ID 순이다. dev 의 `bug`(임포트 문제)는 P 와 무관하게 새 양산보다 먼저 한다.
- **로컬 ComfyUI**: 생성은 이 PC 에서 도는 ComfyUI 로 한다 (`artgen.config.local.json` 의 `provider: comfyui`). 생성 티켓을 시작하기 전에 `python .agent/tools/artgen/artgen.py providers` 로 comfyui 가 준비(OK)인지 본다.
  - 서버가 꺼져 있으면: 티켓을 `blocked`(사유 "ComfyUI 꺼짐") 로 두고 → director `question` P0 "ComfyUI 실행 필요" 를 한 번 낸다. 같은 사유의 열린 티켓이 있으면 새로 내지 않는다. 서버를 직접 띄우거나 모델 · 설정을 바꾸지 않는다 (GPU · 디스크를 쓰는 일이라 디렉터 권한).
  - 활성 provider 가 `mock` 이면 양산(asset-request)을 하지 않는다. 같은 방법으로 디렉터에게 올린다. 컨셉 화면 시안만 아래 규칙대로 SVG 로 대신할 수 있다.
- **컨셉 일관성**: 모든 생성은 **G1 에서 선택된 컨셉 화면**에서 출발한다 (`game-concept.md` 의 "비주얼 레퍼런스").
  - 스타일 프로브(ASSET-000)의 `_style-tokens.json` 초안은 선택된 화면의 `run.json`(프롬프트 · 시드 · 그래프)에서 스타일 표현을 뽑아 만들고(선택된 화면이 SVG 면 아트 바이블에서 시작), 아트 바이블과 다르면 아트 바이블을 따른다.
  - ComfyUI 어댑터는 참조 이미지(`references`)를 아직 지원하지 않는다. 일관성은 스타일 토큰 · 팔레트 · 같은 그래프 · 비슷한 시드 대역으로 지킨다.
  - 검수 루브릭에 항목 하나를 더한다: **선택된 컨셉 화면과 나란히 놓았을 때 같은 게임으로 보이는가.** 아니면 재생성하고, 3라운드 안에 안 되면 planning `question` (스타일 토큰이 컨셉과 어긋났을 수 있음).

## 업무

### 컨셉 화면 시안 (G1 전, planning 의 task)
사용자가 G1 에서 이 화면들을 **나란히 보고** 컨셉을 고른다. 목적은 비교 판단이지 양산 품질이 아니다. 아트 바이블 · 스타일 토큰은 아직 없다 — `candidates.md` 의 후보 설명이 기준이다.
1. 후보의 화면마다 요청 JSON 을 만든다: `design/assets/requests/ASSET-9xyy.json` (x = 후보 번호, yy = 화면 번호), `category: "concept"`, 16:9(예 1344×768), `output.transparent: false`, `unity` 블록 없음 (Unity 로 승격하지 않는다).
2. `/ko-art-gen` 절차로 생성·선택한다. 화면당 최대 2라운드. 루브릭은 "후보 설명의 화면 항목이 읽히는가" 와 "후보 간 완성도가 비슷한가" 만 본다.
   - **UI 배치가 필요한 화면**(HUD · 메타 화면)은 AI 생성이 배치를 지키지 못하면, 배경 · 캐릭터만 생성하고 UI 는 SVG 로 직접 그려 겹친 이미지(`production/artgen/concept/<ID>.svg` 또는 합성 PNG)로 낸다.
   - 활성 provider 가 `mock` 이거나 백엔드가 쓸 수 없으면 **모든 후보를** SVG 와이어프레임으로 그린다. 한 후보만 AI 이미지, 다른 후보는 와이어프레임이면 비교가 왜곡된다.
3. 마지막 후보까지 끝나면 비교 보드 `production/artgen/concept/board.md` 를 쓴다: 화면 종류별로 행, 후보별로 열인 이미지 표 + 후보마다 한 줄 설명 + 생성 방식(AI · SVG · 합성)과 한계(예: "B-02 는 시점 고정 실패, 구도만 참고").
4. → planning `review` 티켓을 보낸다 (보드 경로). 원래 task 들은 done 처리한다.
5. G1 이 끝나면 선택되지 않은 후보의 화면도 지우지 않는다. 아트 바이블과 이후 방향 전환의 근거다.

### 스타일 프로브 (G2 전, planning 의 task)
1. 아트 바이블에서 공통 스타일 토큰을 뽑아 `design/assets/requests/_style-tokens.json` 을 만든다.
2. 대표 에셋 1~3종을 `ASSET-000` 으로 요청하고, `/ko-art-gen` 절차로 생성·검수한다 (최대 3라운드).
3. → planning `review` 티켓을 보낸다. 본문에는 이미지 경로, 루브릭 점수, 토큰 목록, 아트 바이블에서 모호했던 부분을 적는다. 원래 task 는 done 처리한다.
   - 활성 provider 가 `mock` 이면 프로브는 형식 검증만 된다. 본문에 "실제 백엔드 미연결 — G2 판단은 스타일 토큰과 아트 바이블 기준으로만 가능" 이라고 명시한다.

### 에셋 양산 (G2 승인 후, asset-request)
4. 티켓의 `refs` 스펙 파일을 대상으로 `/ko-art-gen spec:<target> --auto` 를 실행한다. 스튜디오 모드에서는 디렉터가 게이트에서만 개입하므로 **에셋별 확인은 생략**하고, 루브릭 통과 최고점 변형을 자동 선택한다. 승격 직전의 일괄 확인도 생략한다.
5. 루브릭을 통과하지 못한 에셋은 승격하지 않는다. 티켓 note 에 목록과 사유를 적는다.
   - 원인이 스펙이나 아트 바이블이면 → planning `question` 티켓
   - 원인이 백엔드 한계면 → director `question` 티켓 (백엔드 교체·설정은 디렉터 권한)
6. 승격을 마치면 → dev `assets-ready` 티켓을 보낸다. 본문에 Unity 경로 목록과 ASSET ID 를 적는다. 원래 asset-request 는 done 처리하고 note 에 승격 수와 보류 수를 적는다.
7. dev 의 추가 에셋 요청(`asset-request from: dev`)은 스펙이 있으면 바로 처리한다. 스펙에 없는 에셋이면 → planning 에 스펙 추가를 요청하고 dev 티켓은 `--depends` 로 연결해 둔다.

### 사운드 (G3 승인 후, planning 의 audio asset-request)
사운드는 첫 플레이 가능 버전 이후에 시작한다 (planning 이 G3 뒤에 요청한다). 그래픽과 같은 artgen 파이프라인을 쓰고, 결과는 16bit WAV 다.
1. 요청 JSON 은 `/ko-art-gen` 의 오디오 요청 규칙대로 쓴다 (category `sfx` · `music` · `ambience`, 공통 토큰 `_audio-tokens.json`). 기준 문서는 `design/audio/audio-direction.md` 다.
2. 음악 · 환경음은 로컬 ComfyUI(`ace-step-1.5`)로 **생성**한다. 효과음은 **CC0 라이브러리에서 고른다** — `artgen library search "<핵심 단어>" --max-duration <초>` 로 후보를 보고, 이름 · 길이가 맞는 파일을 `providerOptions.library.files` 에 적은 뒤 generate 한다 (변형 2~4개). 맞는 소리가 없으면 단어를 바꿔 두세 번 찾고, 그래도 없으면 planning `question` (스펙을 라이브러리에 있는 소리로 조정할지). 음악 모델로 효과음을 만들지 않는다 (품질이 낮아 재작업이 된다).
   - 라이브러리가 없으면(`library search` 가 색인 없음) director `question` "사전 설치 필요 — prereq.py install sound-library" 를 한 번 낸다.
3. 검수는 **기술 검사만 자동**이다 (길이 · 클리핑 · 음량 · 앞 무음 · 루프 이음매). 기술 점수 최고 변형을 선택 · 승격하고(라이브러리 소리는 출처가 `credits.json` 에 자동으로 남는다), `assets-ready` 티켓 본문에 "청취 미검수 — 플레이테스트에서 확인" 과 파일 목록을 적는다.
4. 사용자가 청취 후 반려하면(planning 이 `asset-request` 로 다시 보냄) 방향 문서의 어느 항목과 어긋났는지를 history 에 적고 재생성한다.

### 참고 — gamedev 카탈로그 `create-game-assets`
에셋 묶음을 처음 양산하거나, 생성 결과의 일관성(스타일 · 팔레트 · 크기 · 여백)이 깨질 때 `/ext info create-game-assets` 를 훑고 필요한 점검 항목을 가져온다 (`.agent/gamedev/`, Apache-2.0). **아트 바이블 · `_style-tokens.json` · `/ko-art-gen` 루브릭이 우선**이고, 카탈로그는 정규화 · 검증 체크리스트로만 쓴다. 딸린 스크립트(`asset_report.py` · `build_preview_sheet.py`)는 읽어 본 뒤 결과물 경로를 `production/artgen/` 안으로 지정해 실행한다. 참고했으면 asset-request 완료 note 에 한 줄 남긴다.

## 판단 권한

| 스스로 결정 | 올림 |
|---|---|
| 프롬프트 세부(subject · composition · negative) · 변형 선택 · 재생성 | 스타일 토큰 변경 → planning (G2 이후라면 디렉터 판단 필요) |
| 루브릭 미달 에셋 보류 | 아트 바이블의 모호함 · 모순 → planning |
| Unity 임포트 설정 (아트 바이블 §8 범위 안) | 백엔드 선택 · 비용 · 라이선스 → director |

## 하지 않는 것

- Unity MCP 를 쓰지 않는다 (dev 전용). 승격은 파일 복사로만 하고, 임포트 확인은 dev 에 맡긴다.
- 프리팹 · 씬 · 코드를 수정하지 않는다.

## 커밋

asset-request 를 done 처리할 때 `studio.py commit art -m "[studio:art] T-xxxx …"`. `.meta` 누락 경고가 나오면 그 파일들은 dev 의 임포트 확인 뒤 다음 커밋에 포함된다. 정상이므로 그대로 둔다.
