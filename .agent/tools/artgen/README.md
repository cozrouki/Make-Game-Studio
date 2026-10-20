# artgen — 기획 의도 → 게임 그래픽 → Unity 에셋 파이프라인

> 백엔드 중립 그래픽 생성 도구. 이미지 생성 백엔드(로컬 ComfyUI · 상용 API · 사내 서버 등)는 **어댑터로 나중에 연결**한다.
> 백엔드가 정해지기 전에도 `mock` 어댑터로 파이프라인 전체(요청 → 생성 → 검수 → 승격 → Unity 임포트)를 돌릴 수 있다.
> 오케스트레이션(아트 바이블 해석·시각 검수·재생성 판단)은 `/ko-art-gen` 스킬이 맡고, 이 CLI 는 결정적(deterministic) 작업만 한다.

## 전체 흐름

```
/brainstorm → /design-system (GDD) → /art-bible → /asset-spec
                                                       │  design/assets/specs/*.md (스펙 + 생성 프롬프트)
                                                       ▼
/ko-art-gen ─┬─ ① 요청 작성   design/assets/requests/ASSET-NNN.json   (스펙 → artgen-request/1)
             ├─ ② 생성        artgen.py generate  → production/artgen/ASSET-NNN/v###/
             ├─ ③ 검수        Claude 가 이미지를 보고 아트 바이블 루브릭으로 채점 → review.md
             │               미달 시 프롬프트 수정(history 기록) 후 ②로 — 최대 maxRounds
             ├─ ④ 선택        사용자 승인 → artgen.py select
             ├─ ⑤ 승격        artgen.py promote → Assets/... + import-map.json
             │               ArtGenImportPostprocessor 가 TextureImporter 설정 적용
             └─ ⑥ 기록        asset-manifest.md 상태 갱신 · work_log
```

## 디렉터리

| 경로 | 무엇 | git |
|---|---|---|
| `.agent/tools/artgen/` | 이 도구 (CLI · 어댑터 · Unity 임포터 템플릿 · 테스트) | 추적 |
| `.agent/tools/artgen/artgen.config.json` | 기본 설정 (provider=`mock`) | 추적 |
| `.agent/tools/artgen/artgen.config.local.json` | 로컬 설정 — 백엔드 선택·엔드포인트 | **무시** |
| `design/assets/requests/ASSET-NNN.json` | 생성 요청 (기획 → 그래픽의 계약) | 추적 |
| `production/artgen/ASSET-NNN/state.json` · `review.md` | 상태 · 검수 기록 | 추적 |
| `production/artgen/ASSET-NNN/v###/` · `replaced/` | 생성 원본 · 교체 백업 (용량 큼) | **무시** |
| `production/artgen/import-map.json` | Unity 임포트 설정 (팀원 재임포트에 필요) | 추적 |
| `Assets/ArtGen/Editor/` | 임포트 후처리기 (최초 승격 시 설치) | 추적 |

## CLI

Unity 프로젝트 루트에서 실행. 모든 명령에 `--json` (기계 판독), `--root <경로>` 사용 가능.

```bash
python .agent/tools/artgen/artgen.py providers                       # 어댑터 목록 · 준비 상태
python .agent/tools/artgen/artgen.py validate design/assets/requests/*.json
python .agent/tools/artgen/artgen.py prompt   design/assets/requests/ASSET-001.json   # 컴파일된 프롬프트 미리보기
python .agent/tools/artgen/artgen.py generate design/assets/requests/ASSET-001.json [--provider X] [--variants N] [--seed S] [--dry-run]
python .agent/tools/artgen/artgen.py select   ASSET-001 v002 variant_03.png
python .agent/tools/artgen/artgen.py reject   ASSET-001 --reason "실루엣이 아트 바이블 §3 과 불일치"
python .agent/tools/artgen/artgen.py promote  design/assets/requests/ASSET-001.json [--dest Assets/...] [--force]
python .agent/tools/artgen/artgen.py status   [ASSET-001]
```

- `generate` 는 매번 새 버전 디렉터리(`v001`, `v002` …)를 만든다. 이전 결과를 덮어쓰지 않는다.
- 시드를 지정하지 않으면 무작위 시드를 뽑아 `run.json` 에 기록한다 (재현 가능).
- 출력 검사(크기 불일치·투명 요청인데 알파 없음·변형 수 부족)는 **경고**로만 기록한다. 판단은 검수 단계에서 한다.
- `promote` 는 기존 파일이 있으면 거부한다. `--force` 면 기존 파일을 `replaced/` 에 백업한 뒤 교체한다.

## 요청 스키마 (artgen-request/1)

정본 검증: `artgen_lib/request.py` · 문서: `schema/request.schema.json` · 예시: `schema/example-request.json`

| 필드 | 출처 (기획 문서) |
|---|---|
| `assetId`, `name`, `category` | `asset-manifest.md`, 에셋 스펙 |
| `prompt.subject` | 에셋 스펙의 Visual Description |
| `prompt.style` | 아트 바이블 Visual Identity · Shape Language. **모든 에셋이 같은 토큰을 공유해야 일관성이 생긴다** |
| `prompt.palette` | 아트 바이블 Color System 의 의미 색 (#RRGGBB) |
| `prompt.negative` | 아트 바이블 금지 사항 + 공통 (text, watermark …) |
| `output.width/height/transparent` | 에셋 스펙 Dimensions · 아트 바이블 §8 Asset Standards |
| `unity.dest` | `technical-preferences.md` 네이밍 규칙 + 게임 폴더 (AGENTS.md §6) |
| `unity.import` | 아트 바이블 §8 + 성능 예산 (maxSize·압축·PPU·필터) |
| `providerOptions.<이름>` | 백엔드별 값 (워크플로 파일·모델·LoRA 등) — 백엔드 결정 후 |

## 백엔드 연결 (나중에)

백엔드가 정해지면 둘 중 하나를 고른다. **파이프라인의 다른 부분은 바뀌지 않는다.**

### 방법 A — `command` 어댑터 (코드 수정 없음)

이미 있는 스크립트나 CLI 를 그대로 연결한다. `artgen.config.local.json`:

```json
{
  "provider": "command",
  "providers": {
    "command": {
      "argv": ["python", "tools/comfy_run.py", "--job", "{job_file}", "--out", "{out_dir}"],
      "timeoutSec": 900,
      "env": { "COMFY_URL": "http://127.0.0.1:8188" },
      "capabilities": { "transparent": false, "references": true, "seed": true }
    }
  }
}
```

외부 프로그램의 계약은 다음과 같다.
- `{job_file}`(JSON)을 읽는다. 여기에 `positive`, `negative`, `width`, `height`, `transparent`, `variants`, `seeds[]`, `references[]`, `options`, 원본 `request` 가 들어 있다.
- `{out_dir}` 에 PNG 를 `variants` 개 쓴다. 파일명 정렬 순서가 변형 순서가 된다.
- 종료 코드 0 이면 성공이다. stdout/stderr 는 `command.log` 에 남는다.
- 셸을 거치지 않는다(`shell=False`). 치환 토큰: `{job_file} {out_dir} {prompt} {negative} {width} {height} {variants} {seed} {asset_id}`

### 방법 B — Python 어댑터

1. `artgen_lib/providers/_template.py` 를 `artgen_lib/providers/<이름>.py` 로 복사한다.
2. `name` · `capabilities` · `check()` · `generate()` 를 구현하고, 파일 끝에서 `PROVIDER_CLASS` 주석을 해제한다. 레지스트리가 자동으로 발견한다.
3. 비밀값은 환경변수로만 받는다. 설정 파일에는 변수 **이름**만 둔다 (`"apiKeyEnv": "MY_API_KEY"`).
4. `tests/test_artgen.py` 에 `check()` 테스트를 추가한다.
5. `artgen.config.local.json` 의 `"provider"` 를 바꾼다. 일회성 실행이면 `ARTGEN_PROVIDER` 환경변수나 `--provider` 옵션을 쓴다.

### 백엔드 선택 시 확인할 것

| 항목 | 왜 |
|---|---|
| 스타일 일관성 수단 (LoRA·스타일 참조·시드 고정) | 에셋 수십~수백 개가 한 게임처럼 보여야 함. 프롬프트만으로는 한계 |
| 투명 배경 (네이티브 또는 배경 제거 후처리) | 스프라이트·아이콘·VFX 대부분이 알파 필요 |
| 해상도 · 종횡비 제어 | 아트 바이블 §8 크기 규격 |
| 참조 이미지 (img2img · 컨트롤넷) | 컨셉 → 변형, 캐릭터 일관성 |
| 시드 재현성 | 같은 요청 = 같은 결과 → 버전 관리 · 회귀 비교 |
| 라이선스 · 상업적 이용 조건 | 출시 가능 여부 |
| 비용 · 속도 | 재생성 루프(maxRounds × variants) 예산 |

## 검수 루브릭

`/ko-art-gen` 이 생성 결과를 직접 보고 채점한다 (1~5). 평균이 `defaults.passScore`(기본 4.0) 이상이고 **기술 항목에 1점이 없어야** 통과한다.

| 축 | 기준 (아트 바이블 근거) |
|---|---|
| 스타일 일치 | Visual Identity Statement · 렌더링 스타일 토큰 준수 |
| 형태 언어 | §Shape Language — 실루엣 판독성, 의도된 형태 (예: 아군=둥근, 적=각진) |
| 색 체계 | 의미 색 팔레트 준수, 금지 색 없음 |
| 판독성 | **게임 내 실제 표시 크기**에서 식별 가능한가 (축소해서 볼 것) |
| 기술 | 크기 · 알파 · 잘림 · 아티팩트(손가락·글자·워터마크) · 타일링 이음새 |

`mock` 결과(`run.json` 의 `placeholder: true`)는 시각 항목을 건너뛰고 기술 항목만 본다.

## Unity 임포트

- `unity/ArtGenImportPostprocessor.cs` 와 `unity/ArtGen.Editor.asmdef` 를 `Assets/ArtGen/Editor/` 에 설치한다 (Editor 전용 어셈블리, 런타임 빌드에 포함되지 않음).
- `OnPreprocessTexture` 에서 `production/artgen/import-map.json` 의 경로가 일치하는 항목의 설정을 적용한다. 대상: textureType · spriteMode · PPU · filter · wrap · mipmaps · alphaIsTransparency · sRGB · maxSize · compression.
- `promote` 는 임포트 맵을 **먼저** 쓰고 그다음 파일을 복사한다. 그래서 첫 임포트부터 설정이 적용된다.
- 설정만 바꾸고 파일이 그대로면 Unity 가 다시 임포트하지 않는다. 이때는 `promote --force` 로 다시 승격하거나 에디터에서 Reimport 한다. MCP 를 쓸 수 있으면 `manage_asset` 으로 처리한다.
- 아직 범위 밖: 스프라이트 시트 자동 슬라이싱(`spriteMode: Multiple` 은 모드만 설정), 3D 메시·머티리얼, 오디오.

## 테스트

```bash
python -m pytest .agent/tools/artgen/tests -q
```

외부 의존성은 없다. 표준 라이브러리만 쓰고, 테스트에만 pytest 가 필요하다.
