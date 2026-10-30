# Make Game Studio — 게임 개발 풀스택 통합 스킬 패키지 (Unity · Godot · Unreal)

> **English:** [jump to the English summary](#make-game-studio--game-dev-claude-skills-unity--godot--unreal)

게임 개발용 Claude Code 통합 환경입니다. 목표는 **게임 아이디어를 기획으로 만들고, 기획 의도대로 그래픽을 만들고, 게임 엔진(Unity · Godot · Unreal)으로 개발하는 과정을 자동화**하는 것입니다.
외부 저장소를 흡수해 만든 **엔진 중립 4계층 스킬 셋** 위에, 자체 도구 두 가지(그래픽 생성 파이프라인 · 스튜디오 모드)를 얹었습니다. 마스터 진입점 `/unity-fullstack` 은 처음 Unity 전용으로 시작한 이름을 호환 때문에 그대로 둔 것이고, 지금은 세 엔진을 지원합니다 — 엔진별로 무엇이 되는지는 [엔진 지원](#엔진-지원).

```
아이디어 ─▶ 기획 ──────────────────▶ 그래픽 ─────────────────▶ 엔진 개발
          /brainstorm · /map-systems   /art-bible · /asset-spec      /ko-setup-engine
          /design-system (GDD)         /ko-art-gen (artgen)          /ko-story-cycle · /ko-tdd
          ─────────── 한 세션에서 순서대로, 또는 스튜디오 모드(3세션 + 디렉터)로 병렬 ───────────
```

원본 통합 시점: **2026-05-13** (Unity 멀티 게임 프로젝트에서 추출·일반화)

## 빠른 시작

설치 스크립트 한 번 + Claude Code에서 엔진 설정 한 번이면 끝납니다.

```powershell
# 1. 템플릿 받기
git clone https://github.com/cozrouki/Make-Game-Studio
cd Make-Game-Studio

# 2. 대상 게임 프로젝트에 설치 (엔진 자동 판정 · 복사 · 자리표시자 · 권한 · MCP(Unity) · .gitignore)
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"
```

3. (Unity 만) **Unity 에디터**에서 프로젝트를 열고 `Window > MCP for Unity`에서 브리지 연결을 확인합니다 (패키지는 2에서 manifest에 추가됨). Godot · Unreal 은 이 단계가 없습니다.
4. 프로젝트 루트에서 Claude Code를 실행합니다.
   ```powershell
   cd D:\Projects\MyGame
   claude
   ```
5. **`/ko-prereq`** — 최초 1회 (PC 마다). 자동화에 필요한 것(Git · Claude Code · uv · 엔진 에디터(Unity · Godot · Unreal 중 프로젝트 엔진) · MCP(Unity) · gdUnit4(Godot) · GPU · ComfyUI · 생성 모델 · 효과음 라이브러리 · 로컬 설정)을 점검하고, 자동으로 고칠 수 있는 것은 확인 후 설치합니다. Claude Code 밖에서는 `python .agent/tools/setup/prereq.py check` → `install`.
6. **`/ko-setup-engine`** — 최초 1회. 엔진(Unity · Godot · Unreal)·패키지·입력·명명 규칙을 실측하고 플랫폼·목표 fps 두 가지만 물은 뒤 `project.yaml`(정본) · `technical-preferences.md` · `CLAUDE.md` Technology Stack을 씁니다. 엔진·패키지를 업그레이드할 때마다 다시 실행합니다.
7. **`/unity-fullstack`** — 이후 작업 메뉴 (스프린트·스토리·리뷰·코드 패턴·에디터 자동화·그래픽 생성).
8. 진행 방식을 고릅니다.
   - **한 세션**: 위 흐름의 스킬을 순서대로 직접 호출합니다.
   - **스튜디오 모드**: 기획·아트·개발 세션을 명령 하나(`/studio-status launch`)로 띄우고, 디렉터로서 게이트에서만 승인합니다 → [스튜디오 모드](#스튜디오-모드--3세션-자동-개발)

- 옵션(멀티 게임, Cursor 병행, 미리보기, 덮어쓰기): [자동 설치](#자동-설치-권장--scriptsinstallps1)
- 엔진 설정 상세: [6단계](#6단계-엔진-설정-자동수동-설치-공통--technology-stack--technical-preferencesmd)
- 스크립트를 쓸 수 없으면: [수동 1~5단계](#1단계-자산-복사-수동)

## Windows 기여자 — 최초 clone 후 설정

이 저장소는 `.gitattributes` 로 `.sh` 등 텍스트 파일을 LF 로 저장합니다. 그러나 사용자 전역 git 설정이 `core.autocrlf=true` (Git for Windows 기본값) 이면 clone 시점에 워킹트리에 CRLF 로 풀려 hook bash 스크립트가 `'\r': command not found` 류로 실패합니다. 이 저장소에 한정해 LF 를 유지하도록 한 줄 설정하세요:

```powershell
git config core.autocrlf input
```

이미 CRLF 로 풀린 경우 워킹트리를 재구성:

```powershell
git rm --cached -r .claude/hooks
git checkout -- .claude/hooks
```

## 4계층 구성

| 계층 | 무엇 | 위치 | 진입 |
|---|---|---|---|
| **L1 프로세스** (모든 엔진) | 스프린트·리뷰·게이트·릴리스 워크플로 (95 skills — Game-Studios v1.2.0 74 포함) | `.claude/skills/` | `/unity-fullstack`, `/ko-sprint-plan`, `/ko-story-cycle`, `/ko-code-review`, `/ko-perf-profile`, `/ko-prototype`, `/ko-art-gen`, `/ko-diagnose`, `/ko-tdd`, `/ko-grill`, `/ko-agent-retro`, `/studio-*` 등 |
| **L2 C# 코드 패턴** (Unity 전용) | SkillForge 102 skills (FSM, 인벤토리, 능력, Jobs/Burst 등 14 카테고리) | `.agent/skills/` | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 Editor 자동화** (Unity 전용 — Godot · Unreal 은 명령줄 경로) | MCPForUnity 35+ 도구 사용 가이드 | `.claude/docs/mcp-unity-guide.md` | `mcp__UnityMCP__*` (별도 MCPForUnity 설치 필요) |
| **L4 패키징** | 번들·워크플로 정의 | `.claude/data/bundles.json`, `workflows.json` | JSON 직접 참조 |
| **그래픽 · 사운드 생성** | 기획 → 이미지 · 음악 생성 / 효과음 라이브러리 → 검수 → 엔진 승격 (Unity 는 임포트 설정까지 · Godot · Unreal 은 파일까지, 백엔드 중립, 로컬 ComfyUI) | `.agent/tools/artgen/` | `/ko-art-gen` · [도구 문서](.agent/tools/artgen/README.md) |
| **사전 설치** | 도구 · 모델 · 효과음 라이브러리 · 설정 점검과 자동 설치 (SHA256 검증 · 이어받기) | `.agent/tools/setup/` | `/ko-prereq` |
| **외부 카탈로그** | 마케팅 52 · 게임 개발 실무 36 · Android 기기/스토어 4 (포함) + 게임 디자인 렌즈 62 (비상업 라이선스 — 선택 설치). 세션 상시 비용 없이 필요할 때 한 스킬만 로드 | `.agent/marketing/` · `.agent/gamedev/` · `.agent/android/` · (`.agent/gamedesign/`) | `/ext` · [외부 스킬 카탈로그](#외부-스킬-카탈로그--ext) |
| **스튜디오 모드** | 디렉터 + 기획·아트·개발 3세션이 티켓·게이트로 협업하는 자동 개발 (Claude Code 세션 간 알림). 아트는 AI 생성 또는 **사람 아티스트 + 보조 세션** (`artMode`). 역할 쓰기 영역은 엔진별 (`ownsByEngine`) | `.agent/tools/studio/` | `/studio-join <역할>` · `/studio-director` · `/studio-ticket` · `/studio-status` · [프로토콜](.agent/tools/studio/README.md) |

## 엔진 지원

엔진별 차이의 정본은 [`.claude/docs/engine-layers.md`](.claude/docs/engine-layers.md) 입니다. 엔진은 `project.yaml` `engine.name` → 표지 파일(`ProjectSettings/ProjectVersion.txt` · `project.godot` · `*.uproject`) 순으로 판정합니다.

| 기능 | Unity | Godot | Unreal |
|---|---|---|---|
| L1 워크플로 (기획 · 스프린트 · 리뷰 · 게이트 · 릴리스) | ✅ | ✅ | ✅ |
| 엔진 전문가 에이전트 (Game-Studios) | ✅ 5종 | ✅ 5종 | ✅ 5종 |
| 엔진 레퍼런스 (`docs/engine-reference/`) | ✅ Unity 6.3 LTS | ✅ Godot 4.7 | ✅ UE 5.8 |
| `/ko-setup-engine` 실측 | ✅ `measure.sh` | ✅ `measure-godot.sh` | ✅ `measure-unreal.sh` |
| 테스트 실행 (`.claude/scripts/test-run.sh`) · `/ko-tdd` · `/ko-diagnose` | ✅ NUnit | ✅ gdUnit4 | ✅ Automation |
| `/ko-prereq` 엔진 점검 | ✅ 에디터 · MCP · 분석기 | ✅ 실행 파일 · gdUnit4 | ✅ 에디터 |
| 그래픽 · 사운드 승격 (`/ko-art-gen`) | ✅ 임포트 설정까지 | 파일까지 (임포트 수동) | 파일까지 (임포트 수동) |
| 스튜디오 모드 쓰기 영역 | ✅ | ✅ | ✅ |
| L2 코드 패턴 카탈로그 (SkillForge) | ✅ | — | — |
| L3 에디터 자동화 (MCP) | ✅ | — (명령줄) | — (명령줄) |
| 정적 검사 (커밋 훅) | ✅ unity_lint + UNT | — ("검사 안 함" 알림) | — ("검사 안 함" 알림) |

## 그래픽 생성 — `/ko-art-gen`

`/art-bible` 과 `/asset-spec` 이 만든 기획 문서를 실제 이미지로 만들어 게임 엔진 에셋으로 넣습니다 (Unity 는 임포트 설정까지, Godot · Unreal 은 파일까지). 상세: [`.agent/tools/artgen/README.md`](.agent/tools/artgen/README.md)

```
에셋 스펙 ─▶ 생성 요청(JSON) ─▶ 생성 ─▶ 아트 바이블 루브릭 검수 ─(미달)─▶ 프롬프트 수정 후 재생성
                                          └─(통과)─▶ 선택 ─▶ Assets/ 승격 + 임포트 설정 자동 적용
```

- **백엔드 중립.** 이미지 생성 백엔드는 어댑터로 나중에 정합니다. 백엔드를 고르지 않아도 전체 흐름이 돌아갑니다.

  | 어댑터 | 용도 |
  |---|---|
  | `mock` (기본) | 자리표시 이미지. 백엔드 없이 흐름 검증 |
  | `comfyui` | **로컬 ComfyUI 서버**(HTTP API). 기본 SDXL 그래프 또는 직접 만든 워크플로 JSON, BiRefNet 으로 투명 배경 |
  | `command` | 외부 스크립트나 CLI(상용 API 래퍼 등)를 설정만으로 연결 |
  | `manual` | 사람 아티스트가 `production/artgen/_inbox/<ASSET-ID>/` 에 넣은 PNG 를 수령 |
  | Python 어댑터 | `providers/_template.py` 를 복사해 구현 |

- **기획 의도 대조.** 스타일·형태·색·판독성·기술 5개 축을 아트 바이블 근거와 함께 채점합니다. 스타일 토큰은 모든 에셋이 공유해 일관성을 유지합니다.
- **안전한 승격.** 생성 결과는 `Assets/` 밖에 버전별로 쌓이고, 승인한 것만 승격합니다. 교체할 때는 기존 파일을 먼저 백업합니다. Editor 전용 임포터(`ArtGenImportPostprocessor`)가 텍스처 설정을 적용합니다.

```
/ko-art-gen next                 매니페스트에서 다음 Needed 에셋
/ko-art-gen spec:combat --auto   스펙 파일 단위로 일괄 처리
```

**로컬 ComfyUI 연결 (권장 시작점)**
1. [ComfyUI 휴대용(portable)](https://github.com/Comfy-Org/ComfyUI/releases) NVIDIA 판을 여유 공간이 넉넉한 드라이브에 풀고 `run_nvidia_gpu.bat` 으로 실행합니다 (기본 `http://127.0.0.1:8188`).
2. 모델을 넣습니다.
   - `models/checkpoints/` ← SDXL base 1.0 (CreativeML Open RAIL++-M, 상업 이용 가능)
   - `models/vae/` ← `sdxl_vae_fp16_fix` (fp16 GPU 에서 검은 이미지 방지)
   - `models/background_removal/` ← [Comfy-Org/BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet) `birefnet.safetensors` (MIT, 투명 배경용)
3. 프로젝트에서 켭니다: `.agent/tools/artgen/artgen.config.local.json` 에 `{"provider": "comfyui"}` (git 무시) — 확인은 `python .agent/tools/artgen/artgen.py providers`.

- 실측 (RTX 2070 SUPER 8GB): 256px 스프라이트 2장에 약 45~55초, 1024×768 2장에 약 76초 (첫 실행은 모델 로딩 포함).
- **한계:** SDXL 기본 모델은 짧고 단순한 단일 오브젝트(이펙트 · 아이콘)는 잘 만들지만, 긴 프롬프트 · 격자 시트 · 엄격한 시점(탑다운) · 정확한 팔레트는 따르지 못합니다. 캐릭터 스프라이트는 요청을 단일 이미지로 쪼개고, 스타일 LoRA · ControlNet · IP-Adapter 를 쓴 **사용자 워크플로**(`providers.comfyui.workflow`)로 보강하세요.

## 외부 스킬 카탈로그 — `/ext`

외부 스킬 저장소 3개를 **카탈로그**로 붙였습니다. `.claude/skills/` 에 넣으면 스킬 설명 150여 개가 매 세션 컨텍스트에 상시 올라가므로(스튜디오 모드면 세션마다), `.agent/<카탈로그>/` 에 두고 `/ext` 가 필요할 때 한 스킬만 읽어 실행합니다.

| 카탈로그 | 업스트림 | 라이선스 | 템플릿 포함 | 내용 |
|---|---|---|---|---|
| `marketing` | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT | ✅ `.agent/marketing/` | 52개 — ASO · 런칭 · 가격 · 페이월 · 광고 크리에이티브 · 커뮤니티 · 인플루언서 · 분석 등 (B2B 영업 · 웹 SEO 계열은 `fit: low`) |
| `gamedev` | [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | Apache-2.0 | ✅ `.agent/gamedev/` | 36개 — 분야(손맛 · 저장 · 카메라 · AI 등) · 장르 9종 · Unity 6.3 기능 8종 · 배포(Steam · itch.io). Godot · Unreal · Roblox · 웹 엔진 전용 39개는 제외 |
| `gamedesign` | [Stanestane/game-design-skills-bundle](https://github.com/Stanestane/game-design-skills-bundle) | **PolyForm Noncommercial 1.0.0** | ❌ 선택 설치 (git 무시) | 62개 — 플레이어 심리 · 경험 구조 감사, 발상 · 우선순위, 리더보드 · 패스, 예산 · 일정 추정 |

```
/ext                              # 세 카탈로그 상태 · 추천 묶음
/ext list marketing               # 그룹별 목록 (★ = 게임 마케팅 핵심)
/ext info aso                     # 메타 + When to Use
/ext aso 스토어 페이지 점검해 줘    # 그 스킬을 이 프로젝트 규칙으로 실행
```

- **이 프로젝트 규칙이 우선합니다.** 한국어 출력, 게임 컨텍스트는 `game-concept.md` · `game-pillars.md` · `art-bible.md` 에서 먼저 읽고, Unity 코드는 `gameplay-code.md` · `technical-preferences.md` 가 업스트림 예시보다 우선합니다. 기존 스킬과 겹치는 항목은 목록에 `↔ /brainstorm` 처럼 표시됩니다.
- **마케팅 컨텍스트 정본**은 `design/marketing/product-marketing.md` 입니다 (업스트림의 `.agents/product-marketing.md` 대신 — 스튜디오 모드에서 기획 영역).
- **확인 후에만:** 업스트림 연동 문서에는 파트너사 CLI 설치(`npm install -g`, `curl … | sh`)와 API 연동 안내가 있습니다. 외부 설치 · API 호출 · 게시 · 발송 · 스킬 딸린 스크립트 실행은 사용자 확인을 받습니다. 마케팅의 외부 API CLI(JS 66개)는 미러하지 않았습니다.
- 한국어 요약 · 그룹 · 게임 적합도는 로컬에서 쓴 `.agent/catalogs/<카탈로그>.ko.json` 이고, `scripts/sync-catalog.py` 가 업스트림 메타와 합쳐 `catalog.json` 을 만듭니다.

### ⚠ `gamedesign` 라이선스 — 직접 받아야 합니다

PolyForm Noncommercial 1.0.0 입니다. **개인 · 취미 · 학습 · 교육기관 · 비영리는 무료**이고, **게임을 개발 · 퍼블리싱 · 운영하는 회사 안에서의 사용, 외주 · 컨설팅, 유료 교육, 재배포 · 재패키징은 작성자의 상업 라이선스가 필요**합니다 (구매해도 재배포 권리는 없음 — [COMMERCIAL-LICENSE.md](https://github.com/Stanestane/game-design-skills-bundle/blob/main/COMMERCIAL-LICENSE.md), 문의 https://www.stane-island.net/).

그래서 이 템플릿은 번들을 **포함하지 않고**, 라이선스를 확인한 사용자가 직접 받습니다. 받은 파일은 `.agent/gamedesign/` 에만 있고 git 무시 대상이라 커밋 · 다른 프로젝트 설치(`install.ps1` 은 git 추적 파일만 복사)로 퍼지지 않습니다.

```powershell
# 비상업 용도 (개인 · 학습 · 교육 · 비영리)
python scripts/sync-catalog.py gamedesign --fetch --accept-license noncommercial
# 상업 라이선스를 보유한 경우
python scripts/sync-catalog.py gamedesign --fetch --accept-license commercial
# 설치된 게임 프로젝트에 직접
python scripts/sync-catalog.py gamedesign --fetch --accept-license noncommercial --root D:\Projects\MyGame
```
`--accept-license` 가 없으면 라이선스 요약만 보여 주고 멈춥니다. 동의 방식과 시각은 `.agent/gamedesign/UPSTREAM.json` 에 남습니다.

명령을 직접 치지 않아도 됩니다. 번들이 없을 때 `/ext <gamedesign 스킬>` 을 부르면 `/ext` 가 라이선스를 요약해 보여 주고 **`비상업 용도` / `상업 라이선스 보유` / `설치 안 함` 중에서 고르게 한 뒤** 그 값으로 설치합니다. 조건은 사용자가 고르고 에이전트는 고르지 않습니다. 스튜디오 모드에서 planning 이 감사를 쓰려는데 번들이 없으면, planning 이 디렉터에게 설치 요청 티켓을 한 번 내고 디렉터(세션)가 사용자에게 물어 설치합니다 (`roles/planning.md` "설계 감사").

### 갱신

`scripts/sync-upstream.ps1` 의 [5/6] 단계가 `marketing` · `gamedev` 를 갱신합니다(형제 폴더에 clone 이 있으면 그것을, 없으면 임시 clone). 단독: `python scripts/sync-catalog.py <marketing|gamedev> --fetch`, 상태: `--status`. 새 스킬이 생기면 "한국어 요약 없음" 이 출력되니 오버레이에 추가하고 `--index-only` 로 다시 만듭니다.

## 스튜디오 모드 — 3세션 자동 개발

사용자가 **디렉터**가 되고, 같은 프로젝트 폴더에서 AI 세션 3개(기획 · 아트 · 개발)가 서로 일을 주고받으며 게임을 만듭니다. 역할마다 **다른 AI 도구**를 쓸 수 있습니다(Claude Code · Codex CLI · Gemini CLI · Cursor · Copilot CLI · OpenCode · Antigravity 등). 상세: [`.agent/tools/studio/README.md`](.agent/tools/studio/README.md)

```
              디렉터 — 게이트 승인 · 판단 요청 답변 · 정지/재개 (/studio-status)
                       또는 디렉터 세션 (/studio-director) ⇄ 사용자와 의견을 나누며 결정
                 ▲
   planning ──티켓──▶ art ──티켓──▶ dev        상태: production/studio/ (티켓·게이트·로스터)
       ◀──질문/리뷰──    ◀──에셋 요청──         깨우기: 티켓 파일 감시 (+ Claude 끼리는 SendMessage)
```

**시작 — 명령 하나로 (권장)**
1. `python .agent/tools/studio/studio.py team init` → `production/studio/team.json` 에서 역할별 도구(`claude` · `codex` 등) · 모델 · 권한 모드(팀 전체 하나)를 정합니다.
2. `/studio-status launch` → VS Code 명령 팔레트 → **Tasks: Run Task → `studio: 전체 기동`**. 역할마다 전용 터미널이 열리고 20초 간격으로 `studio-<역할>` 세션이 떠서 스스로 `/studio-join` 합니다 (`backend: console` 이면 PowerShell 창). 다시 띄울 때 `/studio-status launch --resume` 은 이전 대화를 그대로 잇습니다.
3. 아래 3번부터 같습니다. 상세: 스튜디오 README "시작하기".

**시작 — 터미널마다 직접**
1. 프로젝트 폴더에서 역할마다 터미널을 하나씩 엽니다.
2. 역할을 맡길 도구에 따라 참여시킵니다.

   | 도구 | 참여 방법 |
   |---|---|
   | Claude Code (대화형) | `claude` 실행 후 `/studio-join <역할>`. 세션끼리 **권한 모드를 같게** 둡니다(다르면 SendMessage 가 승인 대기로 묶임) |
   | Codex · Gemini · Cursor · Copilot · OpenCode CLI | `python .agent/tools/studio/studio.py dispatch <역할> --agent <codex · gemini · cursor · copilot · opencode>` — 감독 루프가 티켓이 생길 때마다 그 도구를 헤드리스로 실행 |
   | Antigravity · Windsurf 등 IDE 에이전트 | Antigravity 는 `/studio-join` 워크플로, 그 외에는 `.agent/tools/studio/prompts/agent-loop.md` 를 따르게 함 |

   예: 기획 = Claude Code, 아트 = Claude Code(+사람 아티스트), 개발 = `dispatch dev --agent codex`.
3. 아무 터미널에서 디렉터 지시를 입력합니다: `/studio-ticket planning "컨셉: …" <설명>`.
4. `/studio-status` 로 현황을 봅니다. 게이트 요청이 오면 `/studio-status approve G1 "<메모>"`, 세션이 질문하면 `/studio-status answer T-0007 "<답>"` 으로 처리합니다.
5. (선택) **디렉터 세션**: 터미널을 하나 더 열고 `/studio-director` 를 실행합니다. 다른 폴더에서 지휘하려면 `/studio-director --root <프로젝트 경로>` 입니다. 이 세션이 판단 요청과 게이트를 받아 브리핑하고, 사용자와 의견을 나눈 뒤 실행합니다. 게이트 · 비전(컨셉 · 범위 · 플랫폼 · 비용)은 사용자 합의가 필요하고, 승인된 문서로 답할 수 있는 질문은 디렉터 세션이 혼자 결정한 뒤 보고합니다(`studio.config.json` 의 `director` 로 조정). 결정은 `production/studio/decisions.md` 에 쌓입니다.

**운영 규칙**
- **단계 게이트:** G1 컨셉 선택(후보 2~3안을 화면 시안으로 비교) → G2 아트 디렉션 → G3 프리프로덕션 → M1, M2 … 게이트에 묶인 티켓은 승인 전에는 시작할 수 없습니다. 승인은 디렉터만 합니다.
- **쓰기 영역 분리:** 기획은 `design/`, 아트는 `Assets/*/Art`·`production/artgen`, 개발은 그 외 `Assets/`·기술 문서를 씁니다 (Unity 기준 — Godot · Unreal 은 `studio.config.json` `ownsByEngine` 의 경로). Unity MCP 는 개발 세션만 씁니다. 다른 영역이 필요하면 티켓을 보냅니다.
- **커밋:** 게이트를 통과하거나 티켓을 완료할 때 각 세션이 자기 영역만 커밋합니다. 프로토콜 · 지침 파일(`CLAUDE.md` · `.claude/` · 도구 설정 등)은 **디렉터 영역**이라 디렉터가 커밋합니다(`/studio-status commit`). 푸시는 디렉터가 합니다.
- **유지보수:** `studio.py audit` 이 주인 없는 변경과 역할 겹침을 찾고, 프로토콜 파일이 바뀌면 지문으로 감지해 현황판에 "미승인 변경" 으로 표시합니다(`/studio-status protocol ack`). 템플릿 갱신은 **`studio.py upgrade --from <템플릿>`** 으로만 합니다 — 설정은 프로젝트 값을 보존한 채 병합되고, 역할마다 공지 티켓이 발행됩니다.
- **아트 모드:** `.agent/tools/studio/studio.config.json` 의 `"artMode"` 로 고릅니다.
  - `"ai"`: art 세션이 artgen 으로 생성합니다.
  - `"human"`: art 세션이 **사람 아티스트의 보조**가 됩니다. 티켓을 대화 브리프로 전하고, 질문과 결정을 티켓으로 옮기고, 납품물을 검사해 승격합니다. 기획은 아트 디렉션 브리프부터 쓰고, 개발은 자리표시 그래픽으로 먼저 진행합니다.
- **정지와 재개:** `/studio-status pause` 를 하면 각 세션이 진행 중인 티켓만 마무리하고 멈춥니다. 재개는 `/studio-status resume` 입니다.
- **사용량 자동 정지:** Claude 주간 사용량이 90%(`usageGuard.weeklyPausePercent`)에 닿으면 statusLine 이 감지해 전 세션을 세웁니다. 각 세션은 진행 중 티켓에 `인계:` note 를 남기고 멈추고, `production/studio/HANDOFF.md` 에 인계 기록이 남습니다. 리셋 뒤 `/studio-join` · `/studio-director` 로 이어서 합니다 (claude.ai 구독 로그인에서만 동작).

**여러 도구를 섞을 때**
- 깨우기는 **티켓 파일 감시**(`studio.py watch`)가 기본이라 도구 종류와 무관합니다. 대기 중에는 AI 토큰을 쓰지 않습니다.
- 감독 루프(`dispatch`)는 진전이 없으면 실행 간격을 늘리고(60 → 300 → 900초), 3회 연속이면 디렉터에게 알립니다. 역할당 하나만 돌고, 실행 로그는 `production/studio/logs/` 에 남습니다.
- 헤드리스 실행은 **승인 없이 파일을 고치고 명령을 실행**합니다. 신뢰할 수 있는 프로젝트에서만 쓰세요. CLI 옵션은 버전마다 바뀌므로 `studio.py agents` 와 `--dry-run` 으로 확인하고, 다르면 `studio.config.local.json` 에서 덮어씁니다.

**한계**
- **같은 작업 폴더**를 전제로 합니다. 다른 PC 의 Claude Code 세션도 Remote Control(같은 계정)로 메시지는 주고받을 수 있지만, 티켓 파일이 공유되지 않아 지금 구조로는 다른 PC 에 역할을 둘 수 없습니다. 꺼져 있던 세션은 다음 `/studio-join` 또는 `dispatch` 시작 때 밀린 티켓을 처리합니다.
- 세 세션이 **같은 계정의 사용량 한도**를 함께 써서 단일 세션보다 약 3배 빨리 소모됩니다. 한도가 가까우면 먼저 정지하세요. 한도에 닿으면 세션이 멈추고, 초기화 뒤 `/studio-join <역할>` 로 재개합니다. 반쯤 된 작업은 재개 시 점검합니다.

## 패키지 내용 통계

- **Skills (L1)**: 95개 (Game-Studios v1.2.0 74 + 한국어 wrapper · 스킬 12 + 스튜디오 모드 4 + 마스터 진입 1 + SkillForge 헬퍼 3 + 외부 카탈로그 진입 1)
- **Agents**: 49개 (Tier 1-3, 엔진 전문가 Unity 5 · Godot 5 · Unreal 5 포함)
- **Rules**: 15개 (fork 2 — 엔진별 gameplay-code · doc-writing, GS 13)
- **Hooks**: 21개 (등록 19 · 라이브러리 2 — 세션 시작/종료, validate-commit/push/lint/read/write/registry/assets, notify, log-agent, 스튜디오 가드 · 정지 알림 등)
- **Docs**: `.claude/docs/` — 자체 4개(엔진 계층 표 · MCP 가이드 · 결정 매트릭스 · 출처) + GS 문서 · 템플릿 · 디렉터 게이트 (상류 이름 그대로) · `docs/engine-reference/` (Unity · Godot · Unreal)
- **Scripts**: 35개 (`.claude/scripts/` — GS 도우미: 스토리 · ADR · 레지스트리 · 테스트 실행 · 설정 쓰기)
- **설정**: `project.yaml` (엔진 · 전문가 · 명명 · 모드 · 단계 정본), `project.local.yaml` (개인 · git 무시) — `/settings`
- **Data**: 2개 (bundles.json 6개 번들, workflows.json 5개 워크플로)
- **SkillForge (L2)**: 102개 SKILL.md (14 카테고리) + skills-index.json + README-sync.md
- **Tools**: 4개 — `artgen` (그래픽 · 사운드 생성 CLI · 어댑터 6종 · 사운드 라이브러리 · 엔진별 승격 · Unity 임포터 템플릿), `studio` (스튜디오 모드 CLI · 역할 헌장 5종 · 아트 디렉션 브리프 · 컨셉 후보 템플릿 · 하네스: 래칫 · 지표 · 쓰기 가드), `setup` (사전 설치 점검 · 설치 — 엔진별 · Unity 공식 분석기), `lint` (Unity C# 규칙 검사 UL001~008 · 분석기 ruleset). 모두 테스트 포함 — `python -m pytest .agent/tools/artgen/tests .agent/tools/studio/tests .agent/tools/setup/tests .agent/tools/lint/tests -q`
- **외부 카탈로그**: marketing 52 (MIT) · gamedev 36 (Apache-2.0) · android 4 (Apache-2.0, Google) 포함, gamedesign 62 (PolyForm NC) 선택 설치 — `/ext`, `scripts/sync-catalog.py`

### 요구 사항

아래 표는 **`/ko-prereq` (`python .agent/tools/setup/prereq.py check`) 가 자동으로 점검**한다. 모델 · 효과음 라이브러리 · 로컬 설정 · MCPForUnity 의존성은 `install` 로 자동 설치되고(용량 · 라이선스를 먼저 보여 줌), 시스템 도구는 winget 이 있을 때만 자동이며 없으면 공식 설치 명령을 안내한다. 라이선스 동의가 필요한 것(Stable Audio · gamedesign 카탈로그)은 자동으로 받지 않는다.

| 항목 | 용도 |
|---|---|
| Claude Code | 슬래시 스킬 · 훅 · 서브에이전트 · 스튜디오 모드(세션 간 알림) |
| Windows PowerShell 5.1+ | `install.ps1` · `sync-upstream.ps1` |
| Git for Windows (bash 포함), git 2.25+ | 훅 스크립트 · 스튜디오 모드 역할별 커밋 |
| Python 3.8+ (`python` 이 PATH 에 있을 것) | artgen · studio CLI (표준 라이브러리만 사용). 테스트는 `pytest` 필요 |
| (선택) Codex · Gemini · Cursor · Copilot · OpenCode CLI | 스튜디오 모드에서 역할을 다른 AI 도구에 맡길 때 (`studio.py dispatch`) |
| uv (`uvx`) | Unity MCP 서버 실행 (`.mcp.json`) · 도구 테스트 |
| (선택) ComfyUI 0.42+ 포터블 + NVIDIA GPU (VRAM 8GB 이상 권장) | artgen 로컬 이미지 · 음악 생성 (`comfyui` 어댑터). 모델 저장에 기본 그래프 기준 약 18GB (SDXL 7GB · ACE-Step 10GB · VAE · BiRefNet), Z-Image 를 쓰면 +21GB. 오디오 후처리는 포터블에 딸린 Python(PyAV · numpy)을 쓴다 |
| (Android 대상일 때) Unity Android Build Support 모듈 · adb | 기기 프로파일링 · Play 정책 점검 (`/ext` android 카탈로그). `technical-preferences.md` 의 Target Platforms 에 Android 가 있으면 `/ko-prereq` 가 점검 |
| (선택) 효과음 라이브러리 | Kenney 오디오 팩 8종(CC0, 약 60MB) — `prereq.py install sound-library` 가 받아 색인 |
| 엔진 에디터 — Unity (+ MCPForUnity) · Godot (PATH, + gdUnit4) · Unreal (Epic Games Launcher) | 테스트 실행 · 에셋 임포트 확인 · (Unity) L3 에디터 자동화 |

## 크로스툴 호환 (Claude Code · Codex · Copilot · Cursor · Gemini · OpenCode · Windsurf · Antigravity)

이 패키지는 **Claude Code 전용이 아니다.** `AGENTS.md` 오픈 표준을 정본으로 삼고, 도구마다 다른 규칙 · 명령 형식은 **생성기**가 단일 소스에서 만들어 낸다.

### 도구별로 무엇을 읽는가

| 자산 | Claude Code | Codex CLI | Copilot (CLI · VS Code) | Cursor | Gemini CLI | OpenCode | Windsurf | Antigravity |
|---|---|---|---|---|---|---|---|---|
| **페르소나 · 표준** | `CLAUDE.md`→`AGENTS.md` | `AGENTS.md` | `AGENTS.md` + `.github/copilot-instructions.md` | `AGENTS.md` | `GEMINI.md`→`AGENTS.md` | `AGENTS.md` | `AGENTS.md` | `AGENTS.md` |
| **파일별 자동 적용 룰** | `.claude/rules/` | `AGENTS.md` §8 색인 | `.github/instructions/` (`applyTo`) | `.cursor/rules/*.mdc` | `AGENTS.md` §8 색인 | `AGENTS.md` §8 색인 | `.windsurf/rules/` (`trigger: glob`) | `.agent/rules/` |
| **슬래시 명령 (워크플로 15종)** | `.claude/skills/` 93개 | `.agents/skills/` (Agent Skills) | `.github/prompts/` (VS Code) · `.github/skills/` (CLI) | `.cursor/commands/` | `.gemini/commands/*.toml` | `.opencode/commands/` | `.windsurf/workflows/` | `.agent/workflows/` |
| **L2 C# 코드 패턴** (`.agent/skills/`) | `/sf-add` 등 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 |
| **훅 / 서브에이전트** | ✅ | — | — | — | — | — | — | — |
| **artgen CLI** | `/ko-art-gen` | `/ko-art-gen` 스킬 | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` |
| **스튜디오 모드 참여** | `/studio-join` (대화형) | `dispatch --agent codex` | `dispatch --agent copilot` | `dispatch --agent cursor` | `dispatch --agent gemini` | `dispatch --agent opencode` | `/studio-join` 워크플로 (IDE) | `/studio-join` 워크플로 (IDE) |

**워크플로 15종** — `/ko-sprint-plan` · `/ko-story-cycle` · `/ko-code-review` · `/ko-perf-profile` · `/ko-prototype` · `/ko-setup-engine` · `/ko-art-gen` · `/ko-prereq` · `/ko-diagnose` · `/ko-tdd` · `/ko-grill` · `/ko-agent-retro` · `/unity-fullstack` · `/studio-join` · `/ext`

> **핵심 구분** — **콘텐츠 층**(페르소나 · 룰 · C# 카탈로그 · 워크플로 절차 · artgen · 스튜디오 CLI)은 모든 도구에서 쓴다. Claude Code 외 도구의 슬래시 명령은 `.agent/workflows/<이름>.md` 정본을 가리키는 **얇은 포인터**이고, 절차가 Claude 스킬(`.claude/skills/<이름>/SKILL.md`)을 지시하면 그 파일을 읽어 따른다. **훅 · 서브에이전트 · 나머지 78개 스킬의 슬래시 호출은 Claude Code 전용**이다 (다른 도구에서도 `SKILL.md` 를 읽게 하면 절차는 따라 할 수 있다).

### AGENTS.md 정본 구조

- **`AGENTS.md`** — 도구 중립 정본 (페르소나 §1–§7 + §8 파일별 규칙 색인). Codex · Copilot · Cursor · OpenCode · Windsurf · Antigravity 가 직접 읽는다.
- **`CLAUDE.md`** — `AGENTS.md` 를 가리키고 그 위에 Claude Code 전용 계층(Technology Stack · §7 세션 · §8 4계층 · §9 스튜디오 모드)만 얹음. Technology Stack은 `/setup-engine` · `/gate-check` 가 이 파일에서 읽고 쓰므로 여기에 둔다(다른 도구는 AGENTS.md §4 안내대로 이 섹션을 읽음).
- **`GEMINI.md` · `AGENT.md`(단수) · `.github/copilot-instructions.md`** — `AGENTS.md` 로 가는 얇은 포인터.

### 미러 생성 — 단일 소스에서 파생

정본은 두 곳뿐이다. **룰은 `.claude/rules/`, 절차는 `.agent/workflows/`.** 도구별 파일은 모두 생성물이다.

```bash
python scripts/gen-rule-mirrors.py
#  .claude/rules/*.md     →  .agent/rules/ (Antigravity)  · .cursor/rules/*.mdc (Cursor)
#                         →  .github/instructions/*.instructions.md (Copilot) · .windsurf/rules/ (Windsurf)
#                         →  AGENTS.md §8 파일별 규칙 색인 (Codex · OpenCode · Gemini)
#  .agent/workflows/*.md  →  .cursor/commands · .gemini/commands · .opencode/commands · .github/prompts
#                         →  .github/skills · .agents/skills (Agent Skills) · .windsurf/workflows
```

- 룰을 고치면 `.claude/rules/` 만 수정하고 다시 생성한다.
- 워크플로 미러는 정본 경로만 가리키므로 절차 내용을 고칠 때는 재생성할 필요가 없다. **추가 · 삭제 · description 변경** 때만 다시 생성한다.
- 생성물은 직접 편집하지 않는다. 파일 머리의 `생성물:` 주석이 표시다.

> 도구별 경로 · 형식은 각 도구의 공개 문서와 커뮤니티 자료(2026-10 기준)를 따랐다. 일부는 버전마다 바뀐다 — OpenCode 는 예전 버전이 `.opencode/command/`(단수), Windsurf 는 최신 문서가 `.devin/rules/` 를 우선한다는 보고가 있다. 도구가 파일을 인식하지 못하면 생성기의 경로만 고치면 된다.

### Antigravity 워크플로

`.agent/workflows/*.md` 는 Antigravity 에서 `/파일명` 슬래시로 바로 발동되는 **정본 절차**다. 다른 도구의 슬래시 명령이 모두 이 파일을 가리킨다. 각 워크플로는 Claude Code 의 `.claude/skills/<name>/` 절차를 참조하되 도구 중립으로 조정됨(`/sf-*` 슬래시 대신 `.agent/skills/` 카탈로그 직접 참조). 스튜디오 모드의 디렉터 콘솔(`/studio-status`, `/studio-ticket`)은 Claude Code 전용이지만, 다른 도구에서는 `studio.py status` · `gate approve --by director` 등 CLI 로 같은 일을 한다.

## 다른 프로젝트에 적용하는 방법

### 자동 설치 (권장) — `scripts/install.ps1`

아래 1~4단계를 한 번에 수행합니다. Windows PowerShell 5.1 이상.

```powershell
# 단일 게임 (엔진은 표지 파일로 자동 판정 — Unity · Godot · Unreal)
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"

# 엔진 지정 (표지 파일이 여럿이거나 아직 없을 때)
.\scripts\install.ps1 -Target D:\Projects\MyGodotGame -Engine Godot

# 멀티 게임 + 공유 모듈 + Cursor 병행
.\scripts\install.ps1 -Target D:\Projects\Multi -Games "A=GameA,B=GameB" -SharedModule SharedCore -Tools Claude,Cursor

# 모든 도구 (Claude · Codex · Copilot · Cursor · Gemini · OpenCode · Windsurf · Antigravity)
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame" -Tools All

# 미리보기 (파일 쓰기 없음)
.\scripts\install.ps1 -Target D:\Projects\MyGame -DryRun
```

| 단계 | 하는 일 |
|---|---|
| 엔진 판정 | `ProjectSettings/ProjectVersion.txt` → Unity · `project.godot` → Godot · `*.uproject` → Unreal (`-Engine` 으로 지정 가능). Unity 전용 계층(SkillForge · unity_lint · MCP 가이드 · `sf-*`)은 Unity 일 때만, 엔진 레퍼런스는 그 엔진 것만, `src/CLAUDE.md` 는 Godot 일 때만 복사한다 |
| 복사 | 이 저장소의 **git 추적 파일만** 복사 (로컬 잔재 · `studio-tests/` 제외). `project.yaml` · `docs/registry/` 등 프로젝트 데이터는 대상에 없을 때만 넣는다. `-Tools Claude,Codex,Copilot,Cursor,Gemini,OpenCode,Windsurf,Antigravity` 또는 `All` 로 선택, 공통(`AGENTS.md`·`.agent/`)은 항상. MIT 고지는 `.agent/licenses/`. 대상에 이미 있는 `.github/` · `docs/` · `design/` · `src/` · `production/` 은 **파일 단위로 병합**(CI 워크플로 등 보존, 겹치는 파일만 `-Force` 시 백업 후 교체) |
| 자리표시자 | `AGENTS.md` §6 게임 폴더 매핑 표, `<SharedModule>`(룰 glob 포함), 네임스페이스 예시, 태그 예시를 실제 값으로 — `.claude`·`.agent`·`.cursor` 룰 미러까지. `CLAUDE.md` 엔진 레퍼런스 import 줄을 대상 엔진으로 |
| 권한 (Unity) | `.claude/settings.local.json` 생성, 이미 있으면 **병합**(기존 권한 보존) |
| MCP (Unity) | `Packages/manifest.json`에 MCPForUnity 추가(서식 유지), `.mcp.json` 생성(`uvx` 위치 자동 탐지, `-McpPort`) — `-SkipMcp`로 생략 |
| .gitignore | 백업 폴더 · 머신별 설정 · 런타임 파일 항목 추가 (artgen 생성 원본 · 받은함, 스튜디오 이벤트 로그 · 정지 표시 · 디스패치 로그 · 잠금 포함) |

- `-Games`를 생략하면 엔진 코드 루트(Unity `Assets/` · Godot 프로젝트 루트 · Unreal `Source/`) 하위 후보(소스 파일 수)를 보여 주고 입력받습니다. 입력이 리다이렉트된 환경(CI)에서는 묻지 않고 자리표시자를 유지합니다.
- 기존 `.claude`·`CLAUDE.md`·`AGENTS.md` 등이 있으면 **중단**합니다. `-Force`를 붙이면 `.claude.backup-<시각>/`에 백업한 뒤 덮어씁니다(`settings.local.json`은 보존).
- 설치 후: (Unity) MCPForUnity 확인 → `claude` 실행 → **`/ko-setup-engine`**(6단계) → `/unity-fullstack`.

스크립트를 쓸 수 없는 환경이면 아래 수동 절차를 따르세요.

### 1단계: 자산 복사 (수동)

대상 게임 프로젝트 루트에 자산을 복사 (Unity 가 아니면 `.agent/skills/` · `.agent/tools/lint/` · `sf-*` 는 빼도 된다). 쓰는 도구에 맞춰 선택 복사:

```powershell
$src = "<이 저장소를 clone 한 경로>"      # 예: 이 저장소 루트
$dst = "D:\path\to\YourGameProject"

# 공통(모든 도구) — 페르소나 정본 + L2 코드 패턴 카탈로그 + 룰 소스
Copy-Item "$src\AGENTS.md" $dst -Force
Copy-Item "$src\.agent"    $dst -Recurse -Force   # skills/ + rules/(Antigravity)

# Claude Code 사용 시
Copy-Item "$src\CLAUDE.md" $dst -Force
Copy-Item "$src\.claude"   $dst -Recurse -Force

# Cursor 사용 시
Copy-Item "$src\.cursor"   $dst -Recurse -Force

# Gemini CLI / 단수 AGENT.md 폴백 (선택)
Copy-Item "$src\GEMINI.md" $dst -Force
Copy-Item "$src\AGENT.md"  $dst -Force
Copy-Item "$src\README.md" $dst -Force            # 선택
```

### 2단계: 프로젝트에 맞게 게임 태그 채우기

이 패키지는 **일반화(placeholder)** 상태로 배포됩니다. 특정 게임(EA/NZS/KC 등) 하드코딩은 모두 제거되어 있으므로, clone 후 바로 사용 가능합니다. 멀티 게임 프로젝트라면 아래 **한 곳**만 자기 프로젝트에 맞게 채우면 됩니다:

| 파일 | 채울 부분 |
|---|---|
| `AGENTS.md` | §6 "게임 폴더 매핑" 표의 `[GAME1]/YourFirstGame` 등을 실제 게임/태그로 (정본 — 이 한 곳만 고치면 전 도구 반영) |
| `.claude/rules/doc-writing.md` | 게임 태그 예시(`[GAME1][GAME2][CORE]`)를 실제 태그로 (선택) |
| `.claude/rules/gameplay-code.md` | 네임스페이스 예시 `YourGame.Gameplay.Player` 와 공유 모듈 `<SharedModule>` 을 실제 값으로 (선택) |
| `.claude/settings.json` | `additionalDirectories` (빈 배열) 에 프로젝트 밖 참조 경로가 필요하면 추가 (선택) |

- **단일 게임 프로젝트**면 게임 태그 시스템 자체를 무시하거나 삭제하면 됩니다.
- `ko-code-review`, `ko-perf-profile`, `unity-fullstack`, `sf-add`, `mcp-unity-guide.md`, `ATTRIBUTION.md` 등은 이미 placeholder(`YourGame`, `[GAME1]`)로 일반화되어 별도 수정 불필요합니다.

### 3단계: 로컬 설정 추가 (settings.local.json)

이 패키지에는 `settings.local.json` 이 **빠져 있습니다** (개인 절대 경로·MCP 권한이 들어가 있어 일반화 불가). 대상 프로젝트에 다음을 직접 작성하세요:

```json
{
  "permissions": {
    "allow": [
      "mcp__UnityMCP__manage_scene",
      "mcp__UnityMCP__manage_gameobject",
      "mcp__UnityMCP__manage_components",
      "mcp__UnityMCP__manage_asset",
      "mcp__UnityMCP__manage_editor",
      "mcp__UnityMCP__batch_execute",
      "mcp__UnityMCP__refresh_unity",
      "mcp__UnityMCP__read_console",
      "Bash(mkdir -p production/session-logs)"
    ]
  }
}
```

### 4단계: MCPForUnity 설치 (Unity · L3 사용시)

- 패키지에는 MCPForUnity 자체는 **없음** (Unity Package Manager로 별도 설치)
- 대상 Unity 프로젝트의 `Packages/manifest.json` 에 추가 (Unity 만):
  ```json
  "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"
  ```
- 프로젝트 루트의 `.mcp.json.template` 을 `.mcp.json` 으로 복사한 뒤 `command` 경로/포트를 자기 환경에 맞게 수정 (실제 `.mcp.json` 은 `.gitignore` 처리됨 — 머신별 경로 포함)

### 5단계: 새 Claude Code 세션 시작

```powershell
cd D:\path\to\YourGameProject
claude
```

`session-start.sh` 가 자동 발화하며 한국어 컨텍스트 + 코드 헬스 + 스프린트 정보(있으면) 표시됩니다.

`/unity-fullstack` 호출 → 4계층 메뉴 한국어 안내.

### 6단계: 엔진 설정 (자동·수동 설치 공통) — project.yaml + Technology Stack + technical-preferences.md

L1 스킬 대부분(`code-review`·`dev-story`·`smoke-check`·`test-setup`·`team-*` 등)이 루트 `project.yaml`(정본 — 없으면 `.claude/docs/technical-preferences.md`)에서 엔진·성능 예산·명명 규칙·**엔진 전문가 에이전트 라우팅**(`specialists`)을 읽고, `/gate-check`는 `CLAUDE.md`의 `## Technology Stack`이 `[CHOOSE]` 상태인지 검사합니다. 모두 **비어 있는 상태로 배포**되므로 한 번 채워야 합니다. 비어 있으면 이 스킬들이 "엔진 미설정"으로 판단하고 전문가 에이전트(Unity `unity-*` · Godot `godot-*` · Unreal `unreal-specialist` · `ue-*`)로 넘기지 못합니다.

**`/ko-setup-engine` 한 번 실행하면 됩니다.**

```
/ko-setup-engine                    # 엔진 판정 → 코드 루트 후보를 보여 주고 고르게 함
/ko-setup-engine Assets/YourGame    # Unity 코드 루트 지정 (서드파티 에셋 제외용)
/ko-setup-engine src                # Godot
/ko-setup-engine Source/MyGame      # Unreal 모듈
```

| 엔진 | 자동 실측 | 질문 |
|---|---|---|
| Unity (`measure.sh`) | 엔진 버전 · 렌더 파이프라인 · 패키지 버전 · 물리/NavMesh · UI Toolkit/uGUI 비율 · 입력 바인딩(게임패드 지원) · **명명 규칙 다수결**(`[SerializeField]`/private/const/event 따로) · 테스트 asmdef(EditMode/PlayMode) | 대상 플랫폼 · 목표 프레임 |
| Godot (`measure-godot.sh`) | 버전 · 렌더러 · 3D 물리 엔진 · 2D/3D 근거 · 애드온 · 오토로드 · 입력 액션(게임패드 · 터치) · GDScript 명명 다수결(class_name · func · signal · const · 정적 타입 비율) · gdUnit4 | 같음 (+ 2D/3D 가 모호할 때) |
| Unreal (`measure-unreal.sh`) | EngineAssociation · 모듈 · 활성 플러그인 · `DefaultEngine.ini` 렌더 설정 · `Build.cs` 의존 · GAS/Enhanced Input/UMG/복제 사용 · 접두 규칙(U/A/F/E/I · bool `b`) 준수 · Automation 테스트 루트 | 같음 (+ C++/Blueprint 주력) |

측정하지 못한 항목(Blueprint 내용 · 대상 플랫폼 등)은 리포트의 "측정 안 함" 절에 남고, 미리보기에 그대로 보입니다.

- 결과는 미리보기로 보여 주고 **승인 후에만** 씁니다. 다시 실행해도 사람이 쓴 섹션(금지 패턴·허용 라이브러리·ADR 로그)은 보존하므로, 엔진·패키지를 업그레이드할 때마다 재실행하면 됩니다.
- **코드가 없는 새 프로젝트**는 실측할 것이 없으므로 upstream `/setup-engine`으로 넘깁니다.
- 왜 `/setup-engine`을 그대로 쓰지 않나: upstream은 명명 규칙을 기본값(private 필드 `_camelCase` 하나)으로 채웁니다. 기존 코드가 다른 규칙이면 `/code-review`가 수백 곳을 위반으로 지적합니다.
- `.claude/`는 프로젝트(클론)당 하나이므로 `project.yaml` · `technical-preferences.md`도 하나입니다. 한 프로젝트에 여러 게임이 있으면 코드 루트를 여러 개 넘겨 함께 실측합니다.
- 측정 스크립트만 따로 돌려 볼 수도 있습니다: `bash .claude/skills/ko-setup-engine/measure.sh Assets/YourGame` (Godot `measure-godot.sh src` · Unreal `measure-unreal.sh Source/MyGame`, 파일을 쓰지 않음).

## 문서 운영 규칙 (컨텍스트 비용)

`work_log.md`·`active.md`는 매 세션 읽히므로 커질수록 토큰 비용이 늘어납니다. `AGENTS.md` §6·§6-1에 다음 규칙이 정의돼 있습니다.

- **work_log 월별 분리** — `doc/work_log.md`에는 현재 월만 두고 새 항목은 최상단에 추가(최신순). 지난 달은 `doc/work_log/YYYY-MM.md`로 옮기고 하단 인덱스에 한 줄 추가.
- **active.md 3~5KB** — `production/session-state/active.md`에는 현재 상태·최근 완료분·다음 할 것·블로커만. 지난 이력은 work_log로, 커밋은 해시만, 넘치면 `production/session-state/archive/`로.
- **세션 로그** — 세션 종료 훅이 `active.md` 사본을 월별 파일(`production/session-logs/session-log-YYYY-MM.md`)에 쌓고 최근 3개월만 남긴다 (`session-stop.sh` 의 `KEEP_MONTHS`). `active.md` 가 크면 사본도 커지므로 3~5KB 기준을 지키는 것이 로그 관리의 핵심이다.

`ko-story-cycle`·`ko-sprint-plan`도 이 기준(work_log 최상단 = 최신)을 따릅니다. 일부 GS 스킬(`dev-story`·`story-done` 등)은 active.md에 내용을 덧붙이므로 주기적으로 정리하세요 — upstream 미러라 스킬 자체는 수정하지 않습니다.

## 자동 발화되는 자산

| 트리거 | 발화 | 효과 |
|---|---|---|
| 세션 시작 | `session-start.sh` + `detect-gaps.sh` | 한국어 컨텍스트(엔진 · 세션 상태 3,000자 상한 · 단계 · 스프린트 · 코드 헬스) + 엔진 레퍼런스 불일치 · 설정 스키마 경고 + 신규 프로젝트 안내 |
| 세션 종료 · 매 턴 | `session-stop.sh` | `active.md` 가 바뀌었을 때만 월별 `production/session-logs/session-log-YYYY-MM.md` 에 아카이브, 최근 3개월만 보관 (git 무시 · 읽는 도구 없음 — 오래 남길 이력은 git · `doc/work_log.md`) |
| Bash/PowerShell 명령 직전 | `validate-commit.sh` + `validate-push.sh` + `validate-lint.sh` | git commit/push 정책 점검 + 엔진별 정적 검사 (Unity unity_lint 차단 규칙만 막음, 그 밖의 엔진은 "검사 안 함" 알림) |
| Read 직전 | `validate-read.sh` | 40KB 넘는 설계 문서 통째 읽기를 막고 제목 목록을 돌려줌 (구간 읽기 유도) |
| Write/Edit 직전 | `validate-registry.sh` + `validate-write.sh` + `studio-write-guard.sh` | 레지스트리 · 설정 · 덮어쓰기 경고 + 스튜디오 역할 쓰기 영역 |
| Write/Edit 직후 | `validate-assets.sh` + `validate-skill-change.sh` | 에셋 네이밍/JSON 유효성 점검 |
| Notification | `notify.sh` | Windows balloon tip |
| Compact 전 | `pre-compact.sh` | 컨텍스트 보존 |
| Agent 호출 · 종료 | `log-agent.sh` / `log-agent-stop.sh` + `validate-agent-artifact.sh` | 감사 로그 + 서브에이전트가 지시받은 파일을 안 쓰고 끝나면 경고 |

게임플레이 코드(Unity `Assets/*/Scripts/**/*.cs` · Godot `src/**/*.gd` · Unreal `Source/**/*.cpp|h`) 편집 시 `gameplay-code.md` 룰이 globs 매칭으로 자동 적용됩니다 (공통 절 + 엔진 절).

## 동일 이름 7개 skill 처리

`brainstorm`, `design-review`, `design-system`, `map-systems`, `playtest-report`, `balance-check`, `scope-check` 는 L1(영문 워크플로) 과 L2(SkillForge `11-game-design` 카테고리, 한국어 상세) 양쪽에 존재합니다.

- 슬래시 `/brainstorm` 등 → **L1** 발화
- 한국어 상세 → `/sf-info <name>` (L2 는 Unity 설치에만 들어간다)
- 각 L1 파일 상단에 한국어 안내 한 줄 명시

## 출처·라이선스

`.claude/docs/ATTRIBUTION.md` 참조. 외부 저장소:

1. **Donchitos/Claude-Code-Game-Studios** v1.2.0 — L1 프로세스 (skills, agents — 엔진 전문가 포함, hooks, rules, docs, scripts, 엔진 레퍼런스, `project.yaml` 설정 체계)
2. **nlelouche/Unity-SkillForge** (Unity3D-AntiGravitySkills) — L2 C# 코드 패턴
3. **Besty0728/Unity-Skills** — L3 보조 카탈로그 (현재 미설치, 외부 URL 참조)
4. **sickn33/antigravity-awesome-skills** — L4 패키징 포맷 차용
5. **CoplayDev/unity-mcp (MCPForUnity)** — L3 Editor 실행 백엔드
6. **coreyhaines31/marketingskills** — 외부 카탈로그 `marketing` (MIT, 포함)
7. **gamedev-skills/awesome-gamedev-agent-skills** — 외부 카탈로그 `gamedev` (Apache-2.0, 포함 — LICENSE · NOTICE 동봉)
7-1. **android/skills** (Google) — 외부 카탈로그 `android` (Apache-2.0, 포함 — 기기 · 스토어 단 4개만, LICENSE 동봉)
7-2. **mattpocock/skills** — `ko-diagnose` · `ko-tdd` · `ko-grill` · `ko-agent-retro` 의 원본 (MIT, 한국어 · 엔진 맞춤 재작성 — 고지는 `THIRD_PARTY_LICENSES.md` §9)
8. **Stanestane/game-design-skills-bundle** — 외부 카탈로그 `gamedesign` (PolyForm Noncommercial 1.0.0, **미포함** — 사용자가 직접 받음)

SkillForge upstream 동기화 절차는 `.agent/skills/README-sync.md` 참조.

## Upstream 자동 동기화 — `scripts/sync-upstream.ps1`

두 upstream의 미러 영역을 한 번에 갱신하는 PowerShell 스크립트입니다.

### 전제 조건

두 upstream 저장소를 clone 해두어야 합니다. 스크립트 **기본값은 이 패키지 저장소의 형제 폴더**(`..\Claude-Code-Game-Studios`, `..\Unity3D-AntiGravitySkills`)이며, 다른 위치면 `-GameStudiosClone`/`-SkillForgeClone` 으로 지정합니다.

처음 clone (형제 폴더 규칙을 따르는 예 — `<PARENT>` 는 이 패키지 저장소의 상위 폴더):

```powershell
git clone https://github.com/Donchitos/Claude-Code-Game-Studios.git <PARENT>\Claude-Code-Game-Studios
git clone https://github.com/nlelouche/Unity-SkillForge.git        <PARENT>\Unity3D-AntiGravitySkills
```

### 사용

```powershell
# 기본: upstream pull + 미러 갱신
.\scripts\sync-upstream.ps1

# 미리보기 (실제 변경 없음)
.\scripts\sync-upstream.ps1 -DryRun

# upstream pull 생략 (이미 최신이라 확신할 때)
.\scripts\sync-upstream.ps1 -SkipPull

# Game-Studios 만 (SkillForge · 외부 카탈로그 생략)
.\scripts\sync-upstream.ps1 -GameStudiosOnly -SkipPull

# clone 경로 변경
.\scripts\sync-upstream.ps1 -GameStudiosClone "C:\src\game-studios" -SkillForgeClone "C:\src\skillforge"
```

### 자동 갱신되는 미러 영역

- `.agent/skills/` — SkillForge 전체 (102+ SKILL.md + templates + skills-index.json)
- `.claude/skills/<GS-skill>/` — Game-Studios skill 전부 (v1.2.0 기준 74개 — 자체 skill `ko-*` · `sf-*` · `studio-*` · `unity-fullstack` · `ext` 는 덮어쓰지 않음)
- `.claude/agents/` — 전부 (v1.2.0 기준 49개, 엔진 전문가 Unity · Godot · Unreal 포함)
- `.claude/docs/` · `.claude/rules/` · `.claude/hooks/` · `.claude/scripts/` — 상류 이름 그대로 (아래 fork 제외). 예전 `gs-*` 접두 문서는 지운다
- `docs/engine-reference/` · `docs/*.md` · `design/CLAUDE.md` · `src/CLAUDE.md` · `studio-tests/`
- 씨앗(없을 때만): `project.yaml` · `docs/registry/` · `docs/architecture/tr-registry.yaml` · `design/registry/`
- 상류에서 사라진 훅이 남아 있으면 경고한다 (settings.json 등록과 함께 지울 것)

### 자동 갱신 안 되는 fork 영역

다음 6개 파일은 한국어 톤·로컬 컨텍스트가 머지되어 있어 **수동 검토**가 필요합니다 (스크립트의 `$forkFiles` 목록):

| 파일 | 설명 |
|---|---|
| `.claude/hooks/session-start.sh` | 한국어 본문 + STATUS 블록 + 상류 v1.2.0 판정(루트 · 스키마 · 단계 출처 · 엔진 코드 루트 · 엔진 레퍼런스 불일치 · CHECKPOINT) |
| `.claude/hooks/session-stop.sh` | 한국어 체크리스트 + 상류 해시 중복 방지 |
| `.claude/rules/gameplay-code.md` | 공통 규칙 + Unity · Godot · Unreal 절 |
| `.claude/settings.json` | 권한 머지 + 훅 등록 19개 (상류 v1.2.0 등록 + 스튜디오 · validate-lint) |
| `.claude/statusline.sh` | 한국어 상태줄 |
| `.claude/scripts/test-scaffold.sh` | `/test-setup` 이 만드는 CI 의 기본 브랜치를 `main` → `master` (10곳) |

엔진별 정적 검사(unity_lint)는 상류 `validate-commit.sh` 를 고치지 않고 자체 훅 `validate-lint.sh` 로 분리했다 — `validate-commit.sh` 는 미러로 그대로 갱신된다.

업스트림에서 이 파일들이 의미 있게 변경되었으면 (예: GS의 새 hook 이벤트 추가) 수동으로 우리 fork에 반영해야 합니다. sync 스크립트는 이 영역을 건드리지 않으므로 안전합니다.

### 권장 주기

- **상류 릴리스 때** — Game-Studios 는 릴리스마다 `CHANGELOG.md` · `UPGRADING.md` 에 settings.json 병합 항목을 적는다. fork 5개는 그 항목을 보고 손으로 반영한다
- **새 게임 프로젝트 시작 전** — 가장 최신 상태로 받아 시작

### 자동화 옵션 (선택)

`Windows 작업 스케줄러` 에 등록해 매주 자동 실행 후 변경이 있으면 notification:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -File `"<PACKAGE_ROOT>\scripts\sync-upstream.ps1`""   # <PACKAGE_ROOT> = 이 저장소를 clone 한 경로
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 09:00
Register-ScheduledTask -TaskName "ClaudeSkillsUpstreamSync" -Action $action -Trigger $trigger
```

스크립트는 git commit/push 까지 자동 진행하지 않습니다 — 변경 확인 후 사용자가 직접 결정.

## 마스터 진입

새 세션에서 `/unity-fullstack` — 4계층 메뉴 한국어 안내.

## 디렉토리 구조

```
AGENTS.md                        ★ 크로스툴 정본 (페르소나·표준·문서규칙)
CLAUDE.md                        Claude Code 계층 (→AGENTS.md + Technology Stack + 스킬/훅/서브에이전트)
GEMINI.md / AGENT.md             AGENTS.md 포인터 (Gemini CLI / 단수 폴백)
.mcp.json.template               MCPForUnity 설정 템플릿 (Unity)
project.yaml                     ★ 프로젝트 설정 정본 (엔진 · 전문가 · 명명 · 모드 · 단계 — 씨앗, /ko-setup-engine · /settings 가 채움)
docs/                            상류 GS 루트 자산
├── engine-reference/            엔진 레퍼런스 (unity · godot · unreal — 설치 때 대상 엔진 것만)
├── registry/ · architecture/     ADR · TR-ID 레지스트리 씨앗
└── CLAUDE.md · WORKFLOW-GUIDE.md · COLLABORATIVE-DESIGN-PRINCIPLE.md · skill-flow-diagrams.md
design/                          design/CLAUDE.md · registry/ (엔티티 레지스트리 씨앗)
src/CLAUDE.md                    Godot 코드 루트 지침 (Godot 설치에만)
studio-tests/                    상류 스킬 · 에이전트 시험 (템플릿 유지보수용 — 설치 안 함)
scripts/
├── install.ps1                  대상 게임 프로젝트에 설치 (엔진 판정·복사·치환·권한·MCP·.gitignore)
├── sync-upstream.ps1            upstream 동기화 (Game-Studios · SkillForge · 외부 카탈로그)
└── gen-rule-mirrors.py          크로스툴 미러 생성 (룰 → 4개 형식 + AGENTS.md 색인, 워크플로 → 7개 형식)

.cursor/rules/ · commands/      15개 .mdc 룰 + 15개 명령 (Cursor — 생성물)
.github/instructions/ · prompts/ · skills/ · copilot-instructions.md   Copilot (생성물)
.agents/skills/                  15개 (Codex — Agent Skills, 생성물)
.gemini/commands/                15개 .toml (Gemini CLI — 생성물)
.opencode/commands/              15개 (OpenCode — 생성물)
.windsurf/rules/ · workflows/    15개 룰 + 15개 워크플로 (Windsurf — 생성물)
.agent/rules/                    15개 .md  (Antigravity — .claude/rules verbatim)
.agent/workflows/                15개 (Antigravity 슬래시 — ko-* 12 + unity-fullstack + studio-join + ext)
.agent/tools/artgen/             그래픽 · 사운드 생성 CLI · 백엔드 어댑터 · 사운드 라이브러리 · 엔진별 승격 · Unity 임포터 템플릿 · 테스트
.agent/tools/setup/              사전 설치 점검 · 설치 (prereq.py — 도구 · 엔진 에디터 · 모델 · 라이브러리 · 설정 · Unity 분석기) · 테스트
.agent/tools/lint/               Unity C# 규칙 검사 (unity_lint.py UL001~008 · lint.config.json blocking · Default.ruleset) · 테스트
.agent/tools/studio/             스튜디오 모드 프로토콜 · 역할 헌장 4종(planning · art · art-human · dev) · 도구 공통 업무 루프 프롬프트 · 아트 디렉션 브리프 템플릿 · 티켓/게이트/커밋/감시/디스패치 CLI · 테스트

.claude/
├── settings.json                권한 + 훅 등록 19개 + 플러그인
├── statusline.sh                상태줄 (한국어)
├── hooks/                       21개 (fork 2 + 자체 3 — validate-lint · 스튜디오 2 + GS 16)
├── rules/                       15개 (fork 2 + GS 13)
├── scripts/                     35개 (GS 도우미 — test-run · config-set · registry · story-facts 등)
├── agents/                      49개 (Tier 1-3, 엔진 전문가 Unity · Godot · Unreal 포함)
├── skills/                      95개
│   ├── unity-fullstack/         마스터 진입
│   ├── ko-sprint-plan/          한국어 wrapper · 스킬 12개
│   ├── ko-story-cycle/
│   ├── ko-code-review/
│   ├── ko-perf-profile/
│   ├── ko-prototype/
│   ├── ko-setup-engine/         실측 엔진 설정 (measure.sh · measure-godot.sh · measure-unreal.sh)
│   ├── ko-art-gen/              그래픽 생성 파이프라인 (artgen CLI 오케스트레이션)
│   ├── ko-prereq/               사전 설치 점검 · 설치 (prereq.py)
│   ├── ko-diagnose/             버그 진단 루프 (mattpocock/skills 차용 4종)
│   ├── ko-tdd/
│   ├── ko-grill/
│   ├── ko-agent-retro/
│   ├── studio-join/             스튜디오 모드 4종 (역할 등록·업무 루프 / 디렉터 세션 / 디렉터 지시 / 디렉터 콘솔)
│   ├── studio-director/
│   ├── studio-ticket/
│   ├── studio-status/
│   ├── ext/                     외부 스킬 카탈로그 진입 (marketing · gamedev · gamedesign)
│   ├── sf-list/                 SkillForge 오프라인 헬퍼 3개
│   ├── sf-info/
│   ├── sf-add/
│   └── <74 GS skills>           브레인스토밍·스프린트·리뷰·릴리스·settings·vertical-slice 등
├── docs/
│   ├── engine-layers.md         ★ 엔진 계층 표 (Unity · Godot · Unreal — 엔진별 차이의 정본)
│   ├── mcp-unity-guide.md       MCPForUnity 35 도구 한국어 가이드 (Unity)
│   ├── editor-automation-decision.md  L1/L2/L3 결정 매트릭스 (Unity)
│   ├── ATTRIBUTION.md           출처·라이선스
│   └── <GS 문서>                coding-standards · coordination-rules · config-resolution · technical-preferences · templates/ · director-gates/ 등 (상류 이름 그대로)
├── data/                        2개
│   ├── bundles.json             6 번들 (core / gameplay / perf / process / visuals-ui / devops)
│   └── workflows.json           5 워크플로 (concept-to-prototype / concept-to-art / studio-autodev / feature-implementation / release-cycle)
└── agent-memory/                (git 무시 — 에이전트 작업 메모리, rules/agent-memory.md)

.agent/skills/                   L2 SkillForge 미러
├── 00-core-engineering/         4 skills
├── 00-meta-skills/              3 skills
├── 01-architecture/             13 skills
├── 02-gameplay/                 15 skills
├── 03-simulation-strategy/      6 skills
├── 03-survival-city-builder/    6 skills
├── 04-visuals-audio/            9 skills
├── 05-ui-ux/                    8 skills
├── 06-performance/              8 skills
├── 07-tools-pipeline/           9 skills
├── 08-backend-monetization/     8 skills
├── 09-devops-automation/        2 skills
├── 11-game-design/              7 skills
├── skills-index.json            인덱스
└── README-sync.md               upstream 동기화 절차

README.md                        이 파일
```

## 라이선스

통합 작업과 자체 도구(ko-* wrapper · artgen · studio · 스크립트)는 [MIT](LICENSE). 포함된 상류 구성 요소는 각자의 MIT 라이선스를 따릅니다 — [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md), `.claude/docs/ATTRIBUTION.md`.

---

# Make Game Studio — Game Dev Claude Skills (Unity · Godot · Unreal)

A turnkey agentic scaffolding for **game development on Unity, Godot or Unreal Engine** with
[Claude Code](https://claude.com/claude-code) (also works with Codex CLI,
GitHub Copilot, Cursor, Gemini CLI, OpenCode, Windsurf, and Antigravity —
per-tool rules and slash commands are generated from one source by
`scripts/gen-rule-mirrors.py`). Its goal is to automate the path from a **game
idea → design documents → graphics that match the design intent → an engine
build**. It integrates upstream skill repositories into a single,
engine-neutral **4-layer skill set**, and adds two original tools on top: a
backend-neutral graphics pipeline and a multi-session "studio mode". (The `/unity-fullstack`
entry command keeps its Unity-era name for compatibility.) What each engine gets is listed in
[`.claude/docs/engine-layers.md`](.claude/docs/engine-layers.md): the process
layer, engine specialist agents, engine references (Unity 6.3 LTS · Godot 4.7 ·
UE 5.8), measured engine setup and test running work on all three; the C#
code-pattern catalog, MCP editor automation and the commit-time linter are
Unity-only for now.

> **Mostly an integration/distribution.** The bulk of the skills come from the
> upstreams below (all MIT; `ko-diagnose` · `ko-tdd` · `ko-grill` · `ko-agent-retro`
> are Korean, engine-aware adaptations of [mattpocock/skills](https://github.com/mattpocock/skills)). Original work here: the integration and
> generalization, cross-tool mirroring, the installer, the Korean `ko-*`
> wrappers, **artgen** (graphics pipeline), and **studio mode**. Credits and
> licenses: [`LICENSE`](LICENSE) · [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) ·
> [`.claude/docs/ATTRIBUTION.md`](.claude/docs/ATTRIBUTION.md).

> **Language note:** the core skills and agents (copied from the English
> upstreams) are in **English**. The wrappers (`ko-*`), persona, rules, and this
> guide are written **Korean-first** (the Korean guide is above) — English contributions welcome. English
> reference translations of the persona, the two Korean rules, and the `ko-*`
> wrappers live in [`i18n/en/`](i18n/en/).

## What's inside — 4 layers

| Layer | What | Entry |
|---|---|---|
| **L1 — Process** (all engines) | 95 workflow slash-command skills (sprint / review / gate / release / debug · TDD), incl. Claude-Code-Game-Studios v1.2.0 | `/unity-fullstack`, `/sprint-plan`, `/code-review`, … |
| **L2 — C# code patterns** (Unity) | 102 SkillForge skills (FSM, inventory, abilities, Jobs/Burst — 14 categories) | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 — Editor automation** (Unity) | MCPForUnity (35+ Editor tools) + usage guide | `mcp__UnityMCP__*` |
| **L4 — Packaging** | bundle / workflow definitions | `.claude/data/` |

Plus 21 hooks, 15 rules, 49 agents (Unity · Godot · Unreal specialists), 35 helper scripts, `project.yaml` config — all auto-applied.

### Original tools

| Tool | What | Entry |
|---|---|---|
| **artgen** — graphics pipeline | Asset spec → generation request → image → review against the art bible → promote into the engine project (Unity: `Assets/` with TextureImporter settings applied; Godot / Unreal: file copy, import settings by hand). **Backend-neutral**: `mock` (placeholder), `comfyui` (local ComfyUI server — SDXL graph or your own exported workflow, BiRefNet transparency), `command` (any external script/CLI), `manual` (a human artist's deliveries), or your own Python adapter. | `/ko-art-gen` · [`.agent/tools/artgen/`](.agent/tools/artgen/README.md) |
| **Studio mode** — 3-session auto-dev | You act as **director**; three AI sessions (planning · art · dev) in one project pass work to each other via ticket files. Each role can use a **different AI tool**: interactive Claude Code, or Codex / Gemini / Cursor / Copilot / OpenCode CLIs driven headless by a supervisor loop, or IDE agents (Antigravity, Windsurf). Sessions wake on ticket-file changes, so the tools don't need to talk to each other directly. You approve at stage gates (concept → art direction → pre-production → milestones). Art can be AI-generated or a **human artist** assisted by the art session. | `/studio-join` · `/studio-director` · `/studio-ticket` · `/studio-status` · `studio.py dispatch` · [`.agent/tools/studio/`](.agent/tools/studio/README.md) |

Requirements for the tools: Python 3.8+ as `python` on PATH (stdlib only; `pytest` for their tests), git 2.25+. Studio mode runs all roles in one working tree on one machine; the director console skills need Claude Code, but everything is also available through the `studio.py` CLI.

## Quick start

```powershell
git clone https://github.com/cozrouki/Make-Game-Studio
cd Make-Game-Studio
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"
```

`install.ps1` copies the assets (git-tracked files only, per `-Tools` — `Claude`,
`Codex`, `Copilot`, `Cursor`, `Gemini`, `OpenCode`, `Windsurf`, `Antigravity`, or
`All`) for the detected engine (`-Engine Auto|Unity|Godot|Unreal`; Unity-only
layers are skipped on other engines), fills
the game-folder mapping table in `AGENTS.md` §6 and the `<SharedModule>` /
namespace placeholders, points the engine-reference import in `CLAUDE.md` at your engine, and (Unity only)
creates or merges `.claude/settings.local.json`, adds MCPForUnity to
`Packages/manifest.json` and writes `.mcp.json`; it also updates `.gitignore`. It refuses to overwrite an existing install unless you pass
`-Force` (which backs it up first). Use `-DryRun` to preview. Single-game
project? Omit `-Games` and ignore the game-tag system.

Then record your engine once: run `/ko-setup-engine` in Claude Code. It
measures the project (Unity, Godot or Unreal: engine version, renderer, packages
/ add-ons / plugins, input bindings, and naming conventions from your own code)
and asks only two questions — target platforms and framerate — before writing
`project.yaml` (the primary config), `.claude/docs/technical-preferences.md`
and the `## Technology Stack` section of `CLAUDE.md`. (Brand-new project with no
code yet? It hands off to upstream `/setup-engine`.) Most L1 skills read these to
know the engine, performance budgets, naming conventions, and which engine
specialist agent to route work to.

Studio mode: open one terminal per role in the project. For a Claude Code role,
run `claude` and `/studio-join <role>` (keep Claude sessions in the same
permission mode). For another CLI, run
`python .agent/tools/studio/studio.py dispatch <role> --agent codex` (or
`gemini`, `cursor`, `copilot`, `opencode`). Give the idea with
`/studio-ticket planning "Concept: …"`, and check progress and approve gates
with `/studio-status`. Optionally, run `/studio-director [--root <project>]` in
another session: it acts as director, briefs you on gates and questions, and
executes after you agree (it decides routine questions within the approved
vision on its own and reports them).

See the Korean guide above for the full step-by-step (settings, MCP install,
cross-tool mirrors, upstream sync via `scripts/sync-upstream.ps1`). The artgen
and studio docs are Korean only.

## Credits (upstreams)

- [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) v1.2.0 — L1 process skills, agents (incl. Unity / Godot / Unreal specialists), hooks, scripts, engine references
- [mattpocock/skills](https://github.com/mattpocock/skills) — source of `ko-diagnose` · `ko-tdd` · `ko-grill` · `ko-agent-retro` (MIT, Korean adaptations)
- [Unity-SkillForge](https://github.com/nlelouche/Unity-SkillForge) — L2 code-pattern skills
- [unity-mcp / MCPForUnity](https://github.com/CoplayDev/unity-mcp) — L3 Editor backend (installed as a UPM package)
- antigravity-awesome-skills — L4 packaging format (format only)
- [marketingskills](https://github.com/coreyhaines31/marketingskills) — `marketing` catalog (MIT, bundled)
- [awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) — `gamedev` catalog (Apache-2.0, bundled with LICENSE + NOTICE; Unity / discipline / genre / workflow skills only)
- [game-design-skills-bundle](https://github.com/Stanestane/game-design-skills-bundle) — `gamedesign` catalog (**PolyForm Noncommercial 1.0.0 — not bundled**; fetch it yourself with `scripts/sync-catalog.py gamedesign --fetch --accept-license …` only if your use is noncommercial or you hold a commercial licence)

## License

[MIT](LICENSE) for the original integration work. Bundled upstream components
remain under their own licenses (MIT, Apache-2.0) — see
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
