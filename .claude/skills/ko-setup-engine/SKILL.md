---
name: ko-setup-engine
description: 엔진 설정 자동화 (한국어 wrapper) — 기존 Unity · Godot · Unreal 프로젝트를 실측해 project.yaml · technical-preferences.md · CLAUDE.md Technology Stack 을 작성
argument-hint: "[코드-루트 ...]  예: Assets/YourGame · src · Source/MyGame"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-setup-engine — 실측 기반 엔진 설정

`/setup-engine`(upstream)은 새 프로젝트용이라 엔진·명명 규칙을 **기본값으로** 채운다. 이미 코드가 있는 프로젝트에서 그 기본값을 그대로 쓰면 실제 규칙과 어긋나 `/code-review`가 기존 코드를 대량 위반으로 지적한다. 이 스킬은 **프로젝트를 실측**해서 설정을 채우고, 코드로 알 수 없는 것(플랫폼·목표 fps)만 묻는다.

채우는 파일 (upstream `/setup-engine` 과 같은 이중 쓰기):
- `project.yaml` → `engine` · `specialists` · `naming` · `commands` 블록 (**정본** — L1 스킬이 `resolve_config` 로 먼저 읽음)
- `.claude/docs/technical-preferences.md` (사람이 읽는 미러 · Forbidden Patterns · Allowed Libraries 의 유일한 자리)
- `CLAUDE.md` → `## Technology Stack` + `ENGINE-REFERENCE-IMPORT` 줄 (`/gate-check`가 `[CHOOSE]` 여부를 검사)

엔진별 차이(코드 루트 · 테스트 · 전문가)는 `.claude/docs/engine-layers.md`.

## 사용법

```
/ko-setup-engine                       # 엔진 판정 → 코드 루트 후보를 보여 주고 고르게 함
/ko-setup-engine Assets/YourGame       # Unity 코드 루트 지정
/ko-setup-engine src                   # Godot
/ko-setup-engine Source/MyGame         # Unreal 모듈
```

## Phase 0: 엔진 판정

표지 파일로 판정한다: `ProjectSettings/ProjectVersion.txt` → **Unity**, `project.godot` → **Godot**, `*.uproject` → **Unreal**.

- 하나만 있으면 그 엔진. `project.yaml` `engine.name` 이 이미 있고 다르면 멈추고 사용자에게 어느 쪽이 맞는지 묻는다.
- **하나도 없으면** 실측할 프로젝트가 없다 → "새 프로젝트이므로 `/setup-engine`을 쓰세요" 라고 안내하고 종료.
- 둘 이상이면 `AskUserQuestion` 으로 고르게 한다.

| 엔진 | 측정 스크립트 | 코드 루트 후보 |
|---|---|---|
| Unity | `measure.sh` | `Assets/` 하위 (.cs 수) |
| Godot | `measure-godot.sh` | 최상위 폴더 (.gd · .cs 수, `addons/` 제외) |
| Unreal | `measure-unreal.sh` | `Source/` 하위 모듈 (.cpp · .h 수) |

## Phase 1: 코드 루트 결정

명명 통계를 서드파티가 오염시키지 않도록 **프로젝트 자체 코드 폴더**만 측정한다.

1. 인수가 있으면 그대로 쓴다.
2. 없으면 `AGENTS.md` §6 "게임 폴더 매핑" 표가 채워져 있는지 본다(`[GAME1]` 같은 자리표시자가 아니면) → 그 폴더(+ 공유 모듈)를 후보로 제안.
3. 그래도 없으면 해당 측정 스크립트를 인수 없이 실행해 후보 목록을 받고, `AskUserQuestion`(multiSelect)으로 고르게 한다. 서드파티로 보이는 폴더(에셋 스토어 벤더명 · `Plugins` · `ThirdParty` · `addons`)는 기본 선택에서 뺀다.

## Phase 2: 실측

```bash
bash .claude/skills/ko-setup-engine/<측정 스크립트> <코드-루트...>
```

- 리포트(마크다운)를 받아 이후 단계의 근거로 쓴다. 스크립트는 파일을 쓰지 않는다.
- 소스 파일이 0개면(Unreal 은 Blueprint 전용일 수 있다) 명명 통계 없이 진행하되 미리보기에 "명명 실측 없음 — 기본값" 을 적는다.
- 리포트의 **"측정 안 함"** 절은 미리보기에 그대로 옮긴다 — 측정하지 못한 값을 추측으로 채우지 않는다.

## Phase 3: 질문 (AskUserQuestion, 한 번에)

1. **대상 플랫폼** (multiSelect): PC / Console(Switch·PS·Xbox) / Mobile / Web — "현재 + 확장 예정"을 구분해 적을 수 있게 Other 허용. Godot 은 `export_presets.cfg`, Unreal 은 `Config/<플랫폼>/` 이 있으면 그 플랫폼을 기본 선택으로 제안한다.
2. **목표 프레임**: 60fps (권장) / 30fps / 120fps 이상.
3. (Godot 에서 2D/3D 근거가 엇갈릴 때만) **2D / 3D** — upstream `references/5.5-project-yaml.md` 가 렌더러 · 물리 기본값을 이 답으로 고른다.
4. (Unreal 에서 C++ 파일이 거의 없을 때만) **주 언어** — C++ / Blueprint 주력.

## Phase 4: 값 도출 규칙

### 공통

- **Performance Budgets**: Target Framerate · Frame Budget 은 질문 답 (60 → 16.6ms, 30 → 33.3ms, 120 → 8.3ms). Draw Calls · Memory Ceiling 은 `[TO BE CONFIGURED — 타깃 하드웨어 확정 시 실측]` (추측 금지). Hot Path: 매 프레임 코드 할당 0 (`.claude/rules/gameplay-code.md`).
- **Input & Platform** (upstream `/setup-engine` 표를 따름):

| 플랫폼 | Gamepad | Touch |
|---|---|---|
| PC만 | Partial | None |
| Console 포함 | Full | None |
| Mobile 포함 | — | Full |
| Web | Partial | Partial |

  확장 예정 플랫폼이 Console이면 "Partial → Full 목표"로 적고 Platform Notes에 "호버 전용 UI 금지·모든 메뉴 D-pad 포커스 이동"을 넣는다. 게임패드 바인딩이 0이면 "Gamepad 바인딩 없음 — 콘솔 확장 시 추가 필요"를 적는다.
- **명명 규칙**: **다수결**, 소수파가 20% 이상이면 함께 적는다. 실측 수치를 HTML 주석으로 남겨 근거를 보존한다.
- **Forbidden Patterns**: `.claude/rules/gameplay-code.md` 의 공통 규칙 + 해당 엔진 절을 한 줄씩 요약하고 상세는 그 파일을 가리킨다. 그 외는 추가하지 않는다.
- **Allowed Libraries / Addons**: 실사용 패키지 · 애드온 · 플러그인만 (개발 도구 제외). 추측성 추가 금지.
- **Engine Specialists**: upstream `references/5.5-project-yaml.md` 의 `specialists` 표 그대로 — 실측 결과로 줄을 빼기만 한다 (아래 엔진별).
- **commands**: upstream `references/5.5-project-yaml.md` 의 엔진별 `commands` 기본값을 쓰고, 테스트는 `bash .claude/scripts/test-run.sh <engine>` 이 읽을 수 있는 형식인지 확인한다.

### Unity (`measure.sh`)

- **Engine**: `m_EditorVersion` (예: `Unity 6000.3.24f1`) · **Rendering**: 렌더 파이프라인 판정 + 버전 · **Physics**: Rigidbody2D > 0 이면 2D, 아니면 PhysX 3D (CharacterController · NavMeshAgent 가 있으면 함께)
- 입력: `.inputactions` 파일별 바인딩 수 (`_old` · `_backup` 사본 제외), 레거시 `Input.Get*` 줄이 있으면 Platform Notes 에 "레거시 Input 매니저 사용 N곳"
- 명명: `[SerializeField] private` 와 그 외 private 를 따로 판정 (camelCase / `_camelCase` / `m_Xxx`), Constants (PascalCase / UPPER_SNAKE / `kXxx`), Events (`On*` 과반이면 "`On` 접두 PascalCase"), Namespaces `{Root}.{Category}.{Subsystem}`, Scenes/Prefabs 샘플 패턴
- Testing: 테스트 asmdef(EditMode/PlayMode, 위치). 없으면 "테스트 asmdef 없음 — `/test-setup` 권장"
- Specialists: UI 메모 — UI Toolkit 파일 > uGUI 파일이면 "UI Toolkit 위주", 반대면 "uGUI 위주". ECS 파일 0이면 `unity-dots-specialist` 에 "(ECS/Jobs/Burst 도입 시에만)", addressables 패키지가 없으면 `unity-addressables-specialist` 를 뺀다
- Technology Stack: `- **Engine**: Unity <버전>` · `- **Language**: C#` · `- **Render Pipeline**: <URP|HDRP|Built-in> <버전>` · `- **Key Packages**: <실사용 + 버전>` · `- **Build System**: Unity Build Pipeline` · `- **Asset Pipeline**: Unity Asset Import Pipeline (+ Addressables — 설치 시)`

### Godot (`measure-godot.sh`)

- **Engine**: `config/features` 의 버전 (예: `Godot 4.7`) · **Language**: `.cs`/`*.csproj` 가 있으면 "Both" 또는 "C#" (`.gd` 대비 비율로), 없으면 GDScript — upstream `references/godot-language-config.md` 의 변형을 따른다
- **Rendering**: `rendering_method` 설정값, 없으면 Forward+ (기본) · **Physics**: `3d/physics_engine` 설정값, 없으면 2D 프로젝트는 Godot Physics 2D, 3D 는 버전 기본값 (`docs/engine-reference/godot/modules/physics.md`)
- 입력: `[input]` 액션 수와 키보드 · 게임패드 · 터치 이벤트 수
- 명명: class_name (PascalCase 기본), func · var snake_case, signal 과거형 비율, const UPPER_SNAKE, private `_` 접두, 파일명 snake_case 비율, 정적 타입 사용 비율 (낮으면 Platform Notes 대신 Forbidden Patterns 에 "새 코드는 정적 타입" 제안만 — 강제 아님)
- Testing: gdUnit4 설치 여부 · `*_test.gd` 수. 없으면 "gdUnit4 없음 — `/test-setup` 권장"
- Specialists: GDExtension 이 없으면 `godot-gdextension-specialist` 에 "(GDExtension 도입 시에만)"
- Technology Stack: upstream `references/godot-language-config.md` **A1** 템플릿 (언어 변형별)

### Unreal (`measure-unreal.sh`)

- **Engine**: `EngineAssociation` (예: `Unreal Engine 5.8`) · **Language**: C++ 파일이 있으면 C++ (Blueprint 는 보조), 거의 없으면 질문 답
- **Rendering**: `DefaultEngine.ini` 의 GI · 반사 · VSM 설정, 비어 있으면 엔진 기본(Lumen + Nanite — upstream 표) · **Physics**: Chaos
- 기능: GAS · Enhanced Input · UMG/CommonUI · 복제 사용 파일 수 → Allowed Libraries 와 Specialists 근거
- 명명: Unreal 접두 규칙(U/A/F/E/I, bool `b`) 준수 비율 — 위반 의심이 있으면 숫자만 적고 고치라고 하지 않는다. UPROPERTY 없는 UObject 원시 포인터 의심 수는 Platform Notes 가 아니라 미리보기의 "주의" 로 보고
- Testing: Automation 테스트 수와 테스트 이름 루트(`<Project>.`). 없으면 "Automation 테스트 없음 — `/test-setup` 권장". 루트가 엔진 영역 이름(`Audio` · `Core` 등)과 겹치면 upstream `/setup-engine` 처럼 별도 루트를 제안
- Specialists: GAS 0 이면 `ue-gas-specialist`, 복제 0 이면 `ue-replication-specialist` 를 "(도입 시에만)" 으로. Blueprint 추정 수가 많으면 `ue-blueprint-specialist` 유지
- Technology Stack: `- **Engine**: Unreal Engine <버전>` · `- **Language**: C++ (primary), Blueprint (...)` · `- **Build System**: Unreal Build Tool (UBT)` · `- **Asset Pipeline**: Unreal Content Pipeline` (+ 주요 플러그인을 Key Packages 에)

## Phase 5: 미리보기 → 승인 → 작성

1. 세 파일의 **완성본 초안**을 보여 준다. 기존 파일이 있으면 바뀌는 줄만 diff로. Phase 2 의 "측정 안 함" 항목을 함께 보여 준다.
2. "이대로 쓸까요?" 승인 후에만 쓴다.
3. 쓰는 방법:
   - `project.yaml`: upstream `.claude/skills/setup-engine/references/5.5-project-yaml.md` 의 **5.5.2 · 5.5.3** 을 읽고 그대로 따른다 (파일 상태별 쓰기 방법 · 이중 쓰기 검증). 값은 기본값이 아니라 Phase 4 실측값을 쓴다.
   - `technical-preferences.md`: 기존 파일이 있으면 **Forbidden Patterns · Allowed Libraries · Architecture Decisions Log 에 사람이 쓴 내용은 보존**하고 실측 섹션만 갱신한다.
   - `CLAUDE.md`: `## Technology Stack` 의 줄을 바꾸고, `ENGINE-REFERENCE-IMPORT` 주석 아래 `@docs/engine-reference/<engine>/VERSION.md` 줄을 판정 엔진으로 바꾼다 (upstream `references/4-claude-md-stack.md` "Engine reference import"). 섹션이 없으면 첫 `---` 구분선 뒤에 추가한다.
4. `docs/engine-reference/<engine>/` 가 없으면 만들지 말고 "엔진 레퍼런스 없음 — `/setup-engine` 7절로 채우거나 템플릿 `scripts/install.ps1` 재실행" 을 보고한다.

technical-preferences.md 섹션 순서 (upstream 스킬들이 이 제목으로 찾는다 — 제목 변경 금지):

```
# Technical Preferences
## Engine & Language        (- **Engine**: / **Language**: / **Rendering**: / **Physics**:)
## Input & Platform         (Target Platforms / Input Methods / Primary Input / Gamepad Support / Touch Support / Platform Notes)
## Naming Conventions       (Classes / Variables / Signals/Events / Files / Scenes/Prefabs / Constants / Namespaces)
## Performance Budgets      (Target Framerate / Frame Budget / Draw Calls / Memory Ceiling / Hot Path)
## Testing                  (Framework / Minimum Coverage / Required Tests)
## Forbidden Patterns
## Allowed Libraries / Addons
## Architecture Decisions Log
## Engine Specialists       (Primary / Language/Code Specialist / Shader Specialist / UI Specialist / Additional Specialists / Routing Notes)
### File Extension Routing  (표)
```

- 줄 형식은 `- **Engine**: 값` 처럼 **굵은 키 + 콜론**을 지킨다 — 훅 `detect-gaps.sh` 와 `yaml-helper.sh` `resolve_code_root` 가 `**Engine**:` 로 읽는다.

## Phase 6: 후처리

- 세션 시작 훅의 `🛠️ 엔진:` 줄과 엔진 레퍼런스 불일치 경고가 사라졌는지 다음 세션에서 확인하라고 안내한다.
- `doc/work_log.md` 최상단에 한 줄 기록 제안: `[<tag>] /ko-setup-engine — <엔진 버전> · <렌더러> · 명명 실측 · 플랫폼 <답>`
- 엔진·패키지를 업그레이드하면 이 스킬을 다시 실행하라고 안내 (기존 사람 작성 섹션은 보존됨).

## 관련

- 새 프로젝트(코드 없음): `/setup-engine`
- 설정 값 보기 · 한 개 바꾸기: `/settings`
- 테스트 프레임워크 스캐폴드: `/test-setup`
- 단계 게이트: `/gate-check`
