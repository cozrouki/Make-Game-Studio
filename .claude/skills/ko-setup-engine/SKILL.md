---
name: ko-setup-engine
description: 엔진 설정 자동화 (한국어 wrapper) — 기존 Unity 프로젝트를 실측해 CLAUDE.md Technology Stack과 technical-preferences.md를 작성
argument-hint: "[코드-루트 ...]  예: Assets/YourGame"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

# /ko-setup-engine — 실측 기반 엔진 설정

`/setup-engine`(upstream)은 새 프로젝트용이라 엔진·명명 규칙을 **기본값으로** 채운다. 이미 코드가 있는 프로젝트에서 그 기본값을 그대로 쓰면 실제 규칙과 어긋나 `/code-review`가 기존 코드를 대량 위반으로 지적한다. 이 스킬은 **프로젝트를 실측**해서 두 파일을 채우고, 코드로 알 수 없는 것(플랫폼·목표 fps)만 묻는다.

채우는 파일:
- `CLAUDE.md` → `## Technology Stack` (`/gate-check`가 `[CHOOSE]` 여부를 검사)
- `.claude/docs/technical-preferences.md` (L1 스킬 20여 개가 엔진·성능 예산·명명·**전문가 라우팅**을 읽음)

## 사용법

```
/ko-setup-engine                       # 코드 루트 후보를 보여 주고 고르게 함
/ko-setup-engine Assets/YourGame       # 코드 루트 지정
/ko-setup-engine Assets/GameA Assets/SharedModule
```

## Phase 1: 코드 루트 결정

명명 통계를 서드파티 에셋이 오염시키지 않도록 **프로젝트 자체 코드 폴더**만 측정한다.

1. 인수가 있으면 그대로 쓴다.
2. 없으면 `AGENTS.md` §6 "게임 폴더 매핑" 표가 채워져 있는지 본다(`[GAME1]` 같은 자리표시자가 아니면) → `Assets/<GameName>` + 공유 모듈 폴더를 후보로 제안.
3. 그래도 없으면 `bash .claude/skills/ko-setup-engine/measure.sh` 를 인수 없이 실행해 `.cs` 수 기준 후보 목록을 받고, `AskUserQuestion`(multiSelect)으로 고르게 한다. 서드파티로 보이는 폴더(에셋 스토어 벤더명, `Plugins`, `ThirdParty`)는 기본 선택에서 뺀다.

## Phase 2: 실측

```bash
bash .claude/skills/ko-setup-engine/measure.sh <코드-루트...>
```

- 리포트(마크다운)를 받아 이후 단계의 근거로 쓴다. 스크립트는 파일을 쓰지 않는다.
- **`.cs`가 0개면** 실측할 코드가 없다 → "새 프로젝트이므로 `/setup-engine`을 쓰세요"라고 안내하고 종료.

## Phase 3: 질문 2개 (AskUserQuestion, 한 번에)

1. **대상 플랫폼** (multiSelect): PC / Console(Switch·PS·Xbox) / Mobile / Web — "현재 + 확장 예정"을 구분해 적을 수 있게 Other 허용.
2. **목표 프레임**: 60fps (권장) / 30fps / 120fps 이상.

## Phase 4: 값 도출 규칙

### Engine & Language
- **Engine**: `m_EditorVersion` (예: `Unity 6000.3.24f1`)
- **Rendering**: 리포트의 렌더 파이프라인 판정 + 버전
- **Physics**: Rigidbody2D > 0 이면 2D, 아니면 PhysX 3D. CharacterController·NavMeshAgent가 있으면 함께 적는다.

### Input & Platform (upstream `/setup-engine` 표를 따름)

| 플랫폼 | Gamepad | Touch |
|---|---|---|
| PC만 | Partial | None |
| Console 포함 | Full | None |
| Mobile 포함 | — | Full |
| Web | Partial | Partial |

- 확장 예정 플랫폼이 Console이면 "Partial → Full 목표"로 적고 Platform Notes에 "호버 전용 UI 금지·모든 메뉴 D-pad 포커스 이동"을 넣는다.
- 바인딩 수는 **실제 사용 중인 파일** 기준(`_old`·`_backup` 사본은 제외). Gamepad 바인딩이 0이면 "Gamepad 바인딩 없음 — 콘솔 확장 시 추가 필요"를 적는다.
- 레거시 `Input.Get*` 줄이 있으면 Platform Notes에 "레거시 Input 매니저 사용 N곳"을 기록.

### Naming Conventions — **다수결**, 소수파가 20% 이상이면 함께 적기
- `[SerializeField] private`: camelCase / `_camelCase` / `m_Xxx` 중 최다
- 그 외 private: 같은 방식으로 따로 판정 (둘이 다를 수 있다 — 예: SerializeField=camelCase, 그 외=`_camelCase`)
- Constants: PascalCase / UPPER_SNAKE / `kXxx` 중 최다
- Events: `On*` 비율이 과반이면 "`On` 접두 PascalCase"
- Namespaces: 상위 namespace 패턴을 `{Root}.{Category}.{Subsystem}` 형태로 요약
- Scenes/Prefabs: 샘플에서 접두·구분자 패턴을 요약 (예: `Enemy_Guard_M1`, `PascalCase_언더스코어`)
- 실측 수치를 HTML 주석으로 남겨 근거를 보존한다.

### Performance Budgets
- Target Framerate·Frame Budget: 질문 답 (60 → 16.6ms, 30 → 33.3ms, 120 → 8.3ms)
- Draw Calls·Memory Ceiling: `[TO BE CONFIGURED — 타깃 하드웨어 확정 시 실측]` (추측 금지)
- Hot Path: `Update()`/`FixedUpdate()` GC 할당 0 바이트 (`.claude/rules/gameplay-code.md`)

### Testing
- 리포트의 테스트 asmdef(EditMode/PlayMode, 위치). 없으면 "테스트 asmdef 없음 — `/test-setup` 권장".
- Minimum Coverage: 수치 기준 없으면 "구조 로직은 TDD 필수 (AGENTS.md §5)".

### Forbidden Patterns
- `.claude/rules/gameplay-code.md`의 필수 규칙을 한 줄씩 요약하고 상세는 그 파일을 가리킨다. 그 외는 추가하지 않는다.

### Allowed Libraries / Addons
- manifest의 **실사용 패키지**만 (IDE·학습용·`device-simulator` 등 개발 도구는 제외). 추측성 추가 금지.

### Engine Specialists
- 기본 Unity 라우팅 (upstream `/setup-engine`과 동일): Primary `unity-specialist`, Shader `unity-shader-specialist`, UI `unity-ui-specialist`, Additional `unity-addressables-specialist`·`unity-dots-specialist`.
- UI Specialist 메모: UI Toolkit 파일 > uGUI 파일이면 "UI Toolkit 위주(UXML/USS)", 반대면 "uGUI(Canvas) 위주".
- `unity-dots-specialist`: ECS 파일이 0이면 "(ECS/Jobs/Burst 도입 시에만)".
- addressables 패키지가 없으면 Addressables Specialist 줄을 뺀다.

### CLAUDE.md Technology Stack
```markdown
- **Engine**: Unity <버전>
- **Language**: C#
- **Render Pipeline**: <URP|HDRP|Built-in> <버전>
- **Key Packages**: <실사용 주요 패키지 + 버전>
- **Build System**: Unity Build Pipeline
- **Asset Pipeline**: Unity Asset Import Pipeline (+ Addressables — 설치 시)
```

## Phase 5: 미리보기 → 승인 → 작성

1. 두 파일의 **완성본 초안**을 보여 준다 (technical-preferences.md는 아래 섹션 순서). 기존 파일이 있으면 바뀌는 줄만 diff로.
2. "이대로 쓸까요?" 승인 후에만 쓴다.
3. 기존 `technical-preferences.md`가 있으면 **Forbidden Patterns·Allowed Libraries·Architecture Decisions Log에 사람이 쓴 내용은 보존**하고 실측 섹션만 갱신한다.
4. `CLAUDE.md`에 `## Technology Stack`이 없으면 첫 `---` 구분선 뒤에 추가한다.

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

- 줄 형식은 `- **Engine**: 값` 처럼 **굵은 키 + 콜론**을 지킨다 — 훅 `detect-gaps.sh`가 `^- **Engine**:` 로 읽는다.

## Phase 6: 후처리

- `doc/work_log.md` 최상단에 한 줄 기록 제안: `[<tag>] /ko-setup-engine — <엔진 버전> · <RP> · 명명 실측 · 플랫폼 <답>`
- 엔진·패키지를 업그레이드하면 이 스킬을 다시 실행하라고 안내 (기존 사람 작성 섹션은 보존됨).

## 관련

- 새 프로젝트(코드 없음): `/setup-engine`
- 테스트 프레임워크 스캐폴드: `/test-setup`
- 단계 게이트: `/gate-check`
