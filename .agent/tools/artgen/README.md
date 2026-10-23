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

## 로컬 ComfyUI — `comfyui` 어댑터

로컬 ComfyUI 서버의 HTTP API 로 생성한다 (표준 라이브러리만 사용). `POST /prompt` → `GET /history/<id>` 대기 → `GET /view` 로 수령. **변형마다 시드 하나씩** 따로 제출해 재현성을 유지한다.

**준비**: ComfyUI 실행(`run_nvidia_gpu.bat`) → 모델 배치 → `artgen.config.local.json` 에 `{"provider": "comfyui"}`.

| 모델 | 위치 | 라이선스 |
|---|---|---|
| SDXL base 1.0 `sd_xl_base_1.0.safetensors` | `models/checkpoints/` | CreativeML Open RAIL++-M (상업 가능) |
| `sdxl_vae_fp16_fix.safetensors` | `models/vae/` | MIT |
| BiRefNet `birefnet.safetensors` ([Comfy-Org/BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet)) | `models/background_removal/` | MIT |
| (Z-Image) `z_image_turbo_bf16.safetensors` ([Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo) `split_files/`) | `models/diffusion_models/` | Apache-2.0 (Tongyi-MAI) |
| (Z-Image) `qwen_3_4b.safetensors` | `models/text_encoders/` | Apache-2.0 (Qwen3-4B) |
| (Z-Image) `ae.safetensors` | `models/vae/` | Apache-2.0 |

**그래프 프리셋 `graph`** — 모델 부분만 다르고 배경 제거 · 축소 · 저장은 공유한다.

| `graph` | 구성 | 기본 샘플링 | 특징 |
|---|---|---|---|
| `sdxl` (기본) | 체크포인트 하나 (최상위 `checkpoint` · `vae` · `steps` …) | 28 스텝 · cfg 6.5 · dpmpp_2m/karras | CLIP 77 토큰 한계, 긴 지시를 잘 못 따른다 |
| `z-image-turbo` | UNET + Qwen3-4B 텍스트 인코더(`lumina2`) + `ae` VAE (`graphs.z-image-turbo` 로 덮어쓰기) | 8 스텝 · cfg 1 · res_multistep/simple · shift 3 | 증류 모델 — 부정 프롬프트를 쓰지 않음(ConditioningZeroOut). LLM 인코더라 긴 프롬프트 · 구도 지시를 SDXL 보다 잘 따른다 |

전환: `artgen.config.local.json` 에 `{"provider": "comfyui", "providers": {"comfyui": {"graph": "z-image-turbo"}}}`, 또는 요청별 `providerOptions.comfyui.graph`. 8GB VRAM 에서 bf16(12.3GB)은 오프로드로 느리다 — `graphs.z-image-turbo.unet` 을 `z_image_turbo_int8_convrot.safetensors`(6.2GB) 로 바꿀 수 있다. 시점 · 형태를 강제하려면 ComfyUI 템플릿 `image_z_image_turbo_fun_union_controlnet` 을 Export (API) 해 `workflow` 로 쓴다.

**설정** (`artgen.config.json` → `providers.comfyui`, 요청별 덮어쓰기는 `request.providerOptions.comfyui`)

| 키 | 기본값 | 설명 |
|---|---|---|
| `url` | `http://127.0.0.1:8188` | ComfyUI 주소 |
| `graph` | `sdxl` | 내장 그래프 프리셋 (`sdxl` · `z-image-turbo`) |
| `graphs.<이름>` | 프리셋별 기본값 | 프리셋의 모델 · 샘플링 덮어쓰기 (sdxl 외 프리셋은 최상위 SDXL 값을 쓰지 않는다) |
| `checkpoint` · `vae` | SDXL base · fp16 VAE | `sdxl` 그래프의 모델 파일명 |
| `steps` · `cfg` · `sampler` · `scheduler` | 28 · 6.5 · dpmpp_2m · karras | 샘플링 |
| `genArea` | 1048576 (1024²) | 생성 해상도 면적. 요청 비율을 유지한 64 배수로 생성한 뒤 요청 크기로 lanczos 축소 |
| `removeBackground` | `{"model": "birefnet.safetensors"}` | 투명 배경. 비우면 `capabilities.transparent=false`. `"threshold": null` 로 이진화 끔 |
| `workflow` | (없음) | ComfyUI 에서 **Export (API)** 로 저장한 JSON 경로. 지정하면 기본 그래프 대신 사용 |
| `timeoutSec` | 600 | 이미지 1장 대기 한도 |

**투명 배경 처리** — 코어 노드만 쓴다 (ComfyUI 0.42+): `RemoveBackground`(전경 확률) → `ThresholdMask`(0.5 이진화) → `InvertMask` → `JoinImageWithAlpha` → 축소.
- `JoinImageWithAlpha` 는 `alpha = 1 - mask` 로 뒤집으므로 `InvertMask` 가 필요하다.
- 전경 확률이 0.996 수준이라 그대로 쓰면 내부 알파가 254 로 남는다(미세하게 비침). 원본 해상도에서 이진화한 뒤 축소하면 내부는 255, 가장자리는 부드러워진다.
- 배경 제거를 쓸 때는 프롬프트의 "isolated on transparent background" 를 SDXL 이 잘 따르는 "단색 흰 배경의 단일 오브젝트" 로 바꾸고, 부정 프롬프트에 장면 · 지면 · 잘림을 더한다.

**사용자 워크플로 토큰** — 문자열 값 안의 `{{positive}} {{negative}} {{seed}} {{width}} {{height}} {{gen_width}} {{gen_height}}` 를 치환한다. 값 전체가 토큰인 필드(예: `"seed": "{{seed}}"`)는 숫자로 바뀐다. 결과는 마지막 저장 노드(SaveImage)의 이미지다. LoRA · ControlNet · IP-Adapter 로 스타일과 시점을 고정할 때 쓴다.

**실측과 한계** (RTX 2070 SUPER 8GB, ComfyUI 0.42.1)
- 256px 2장 약 45~55초, 1024×768 2장 약 76초 (첫 실행은 모델 로딩 포함).
- 단일 이펙트 · 아이콘은 바로 쓸 만한 품질. 긴 프롬프트(CLIP 77 토큰 초과) · 격자 시트 · 엄격한 시점 · 정확한 팔레트는 기본 SDXL 로 맞추기 어렵다 → 요청을 단일 이미지로 쪼개고 사용자 워크플로로 보강한다.
- Flux dev 는 비상업 라이선스라 출시용으로 쓰지 않는다.

## 사람 아티스트 납품 — `manual` 어댑터

이미지를 생성하지 않고 **사람이 그린 PNG 를 받는다.** 검수 · 선택 · 승격 · Unity 임포트는 AI 생성물과 똑같이 처리된다. 그래서 AI 와 사람의 에셋을 한 프로젝트에서 섞어 쓸 수 있다.

```bash
# 아티스트가 production/artgen/_inbox/ASSET-012/ 에 PNG 를 넣은 뒤
python .agent/tools/artgen/artgen.py generate design/assets/requests/ASSET-012.json --provider manual
```
- 받은함의 PNG 를 새 버전 디렉터리(`v###`)로 **이동**한다. 받은함은 다음 라운드를 위해 비워진다.
- 받은함이 비어 있으면 넣을 위치를 알려 주는 오류를 낸다 (폴더는 만들어 둠).
- 변형 수(variants)와 납품 수가 달라도 경고하지 않는다.
- 받은함 경로: `providers.manual.inboxDir` (기본 `production/artgen/_inbox`, git 무시).
- 스튜디오 모드의 사람 아티스트 운영: `.agent/tools/studio/roles/art-human.md`

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
