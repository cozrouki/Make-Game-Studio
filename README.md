# Unity 풀스택 통합 스킬 패키지

Unity 게임 개발용 Claude Code 통합 환경. 4개 외부 저장소를 흡수해 만든 **4계층 스킬 셋**입니다.

원본 통합 시점: **2026-05-13**
원본 적용 프로젝트: `D:\works\projects\github\TikiProject\`

## 4계층 구성

| 계층 | 무엇 | 위치 | 진입 |
|---|---|---|---|
| **L1 프로세스** | 스프린트·리뷰·게이트·릴리스 워크플로 (81 skills) | `.claude/skills/` | `/unity-fullstack`, `/ko-sprint-plan`, `/ko-story-cycle`, `/ko-code-review`, `/ko-perf-profile`, `/ko-prototype` 등 |
| **L2 C# 코드 패턴** | SkillForge 102 skills (FSM, 인벤토리, 능력, Jobs/Burst 등 14 카테고리) | `.agent/skills/` | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 Editor 자동화** | MCPForUnity 35+ 도구 사용 가이드 | `.claude/docs/mcp-unity-guide.md` | `mcp__UnityMCP__*` (별도 MCPForUnity 설치 필요) |
| **L4 패키징** | 번들·워크플로 정의 | `.claude/data/bundles.json`, `workflows.json` | JSON 직접 참조 |

## 패키지 내용 통계

- **Skills (L1)**: 81개 (Game-Studios 72 + 한국어 wrapper 5 + 마스터 진입 1 + SkillForge 헬퍼 3)
- **Agents**: 39개 (Tier 1-3, Godot/UE 11개 제외)
- **Rules**: 12개 (Unity gameplay-code, doc-writing, GS 10개)
- **Hooks**: 12개 (SessionStart/Stop, validate-commit/push/assets, notify, log-agent 등)
- **Docs**: 9개 (MCP 가이드, 결정 매트릭스, GS 원본 6개, 출처 1개)
- **Data**: 2개 (bundles.json 6개 번들, workflows.json 3개 워크플로)
- **SkillForge (L2)**: 102개 SKILL.md (14 카테고리) + skills-index.json + README-sync.md

## 다른 Unity 프로젝트에 적용하는 방법

### 1단계: 자산 복사

대상 Unity 프로젝트 루트에 `.claude/` 와 `.agent/` 를 복사:

```powershell
$src = "D:\works\projects\CodeAI\UnityGame"
$dst = "D:\path\to\YourUnityProject"
Copy-Item "$src\.claude" $dst -Recurse -Force
Copy-Item "$src\.agent"  $dst -Recurse -Force
Copy-Item "$src\README.md" $dst -Force   # 선택
```

### 2단계: TikiProject 특화 부분 일반화

다음 파일들은 **TikiProject 컨텍스트**를 가지고 있어 다른 프로젝트에서 수정이 필요합니다:

| 파일 | 일반화 필요 부분 |
|---|---|
| `.claude/settings.json` | `additionalDirectories` 항목의 `Assets\SharedAssets\Scripts\Runtime` 경로를 자기 프로젝트 경로로 |
| `.claude/rules/doc-writing.md` | 게임 태그 `[NZS][EA][MMC][NJM][KC][CORE]` 를 자기 프로젝트 태그로 (또는 통째로 삭제) |
| `.claude/rules/gameplay-code.md` | 네임스페이스 예시 `KickleCubicle.Gameplay.Player` 를 자기 프로젝트 네임스페이스로 |
| `.claude/skills/ko-code-review/SKILL.md` | 게임 태그 자동 분류 표 (Tiki 5게임) 를 자기 프로젝트 폴더 구조로 |
| `.claude/skills/ko-prototype/SKILL.md` | 게임 태그 `[KC][EA]` 예시 |
| `.claude/skills/unity-fullstack/SKILL.md` | 게임 태그 안내 한 줄 |
| `.claude/docs/mcp-unity-guide.md` | 결정 매트릭스의 `Assets/KickleCubicle/` `Assets/ElevatorAction/` 경로 |
| `.claude/docs/ATTRIBUTION.md` | "TikiProject" 언급들 |

단일 게임 프로젝트면 게임 태그 시스템 자체를 제거하면 됩니다.

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

### 4단계: MCPForUnity 설치 (L3 사용시)

- 패키지에는 MCPForUnity 자체는 **없음** (Unity Package Manager로 별도 설치)
- 대상 Unity 프로젝트의 `Packages/manifest.json` 에 추가:
  ```json
  "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"
  ```
- 프로젝트 루트에 `.mcp.json` 작성하여 stdio 서버 설정

### 5단계: 새 Claude Code 세션 시작

```powershell
cd D:\path\to\YourUnityProject
claude
```

`session-start.sh` 가 자동 발화하며 한국어 컨텍스트 + 코드 헬스 + 스프린트 정보(있으면) 표시됩니다.

`/unity-fullstack` 호출 → 4계층 메뉴 한국어 안내.

## 자동 발화되는 자산

| 트리거 | 발화 | 효과 |
|---|---|---|
| 세션 시작 | `session-start.sh` + `detect-gaps.sh` | 한국어 컨텍스트 + 신규 프로젝트 안내 |
| 세션 종료 | `session-stop.sh` | `production/session-logs/session-log.md` 아카이브 |
| Bash 명령 직전 | `validate-commit.sh` + `validate-push.sh` | git commit/push 정책 점검 (non-blocking) |
| Write/Edit 직후 | `validate-assets.sh` + `validate-skill-change.sh` | 에셋 네이밍/JSON 유효성 점검 |
| Notification | `notify.sh` | Windows balloon tip |
| Compact 전/후 | `pre-compact.sh` / `post-compact.sh` | 컨텍스트 보존 |
| Agent 호출 | `log-agent.sh` / `log-agent-stop.sh` | 감사 로그 |

`.cs` 파일 편집 시 `gameplay-code.md` 룰이 globs 매칭으로 자동 적용됩니다.

## 동일 이름 7개 skill 처리

`brainstorm`, `design-review`, `design-system`, `map-systems`, `playtest-report`, `balance-check`, `scope-check` 는 L1(영문 워크플로) 과 L2(SkillForge `11-game-design` 카테고리, 한국어 상세) 양쪽에 존재합니다.

- 슬래시 `/brainstorm` 등 → **L1** 발화
- 한국어 상세 → `/sf-info <name>`
- 각 L1 파일 상단에 한국어 안내 한 줄 명시

## 출처·라이선스

`.claude/docs/ATTRIBUTION.md` 참조. 4개 외부 저장소:

1. **Donchitos/Claude-Code-Game-Studios** — L1 프로세스 (skills, agents, hooks, rules, docs)
2. **nlelouche/Unity-SkillForge** (Unity3D-AntiGravitySkills) — L2 C# 코드 패턴
3. **Besty0728/Unity-Skills** — L3 보조 카탈로그 (현재 미설치, 외부 URL 참조)
4. **sickn33/antigravity-awesome-skills** — L4 패키징 포맷 차용
5. **CoplayDev/unity-mcp (MCPForUnity)** — L3 Editor 실행 백엔드

SkillForge upstream 동기화 절차는 `.agent/skills/README-sync.md` 참조.

## Upstream 자동 동기화 — `scripts/sync-upstream.ps1`

두 upstream의 미러 영역을 한 번에 갱신하는 PowerShell 스크립트입니다.

### 전제 조건

다음 위치에 upstream clone이 있어야 합니다 (기본값, `-GameStudiosClone`/`-SkillForgeClone` 으로 변경 가능):

- `D:\works\projects\github\Claude-Code-Game-Studios`
- `D:\works\projects\github\Unity3D-AntiGravitySkills`

처음 clone:

```powershell
git clone https://github.com/Donchitos/Claude-Code-Game-Studios.git D:\works\projects\github\Claude-Code-Game-Studios
git clone https://github.com/nlelouche/Unity-SkillForge.git        D:\works\projects\github\Unity3D-AntiGravitySkills
```

### 사용

```powershell
# 기본: upstream pull + 미러 갱신
.\scripts\sync-upstream.ps1

# 미리보기 (실제 변경 없음)
.\scripts\sync-upstream.ps1 -DryRun

# upstream pull 생략 (이미 최신이라 확신할 때)
.\scripts\sync-upstream.ps1 -SkipPull

# clone 경로 변경
.\scripts\sync-upstream.ps1 -GameStudiosClone "C:\src\game-studios" -SkillForgeClone "C:\src\skillforge"
```

### 자동 갱신되는 미러 영역

- `.agent/skills/` — SkillForge 전체 (102+ SKILL.md + templates + skills-index.json)
- `.claude/skills/<GS-skill>/` — Game-Studios 72개 skill (한국어 wrapper `ko-*/sf-*/unity-fullstack` 은 자동 보존)
- `.claude/agents/` — 39개 (Godot/UE 패턴 자동 제외)
- `.claude/docs/gs-*` — 6개 GS docs
- `.claude/rules/<10 GS rules>` — `gameplay-code.md` 자동 보존
- `.claude/hooks/<10 GS hooks>` — `session-start.sh`/`session-stop.sh` 자동 보존

### 자동 갱신 안 되는 fork 영역

다음 4개 파일은 한국어 톤·로컬 컨텍스트가 머지되어 있어 **수동 검토**가 필요합니다:

| 파일 | 설명 |
|---|---|
| `.claude/hooks/session-start.sh` | 한국어 본문 + GS 코드헬스/스프린트 섹션 머지 |
| `.claude/hooks/session-stop.sh` | 한국어 체크리스트 + GS archival 머지 |
| `.claude/rules/gameplay-code.md` | Unity-specific 본문 + GS 원칙 append |
| `.claude/settings.json` | 권한 머지 + 12 hook wiring |

업스트림에서 이 파일들이 의미 있게 변경되었으면 (예: GS의 새 hook 이벤트 추가) 수동으로 우리 fork에 반영해야 합니다. sync 스크립트는 이 영역을 건드리지 않으므로 안전합니다.

### 권장 주기

- **월 1회** — Game-Studios 와 SkillForge 모두 활발한 개발 단계가 아니므로 빈번한 동기화 불필요
- **새 게임 프로젝트 시작 전** — 가장 최신 상태로 받아 시작

### 자동화 옵션 (선택)

`Windows 작업 스케줄러` 에 등록해 매주 자동 실행 후 변경이 있으면 notification:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -File `"D:\works\projects\CodeAI\UnityGame\scripts\sync-upstream.ps1`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 09:00
Register-ScheduledTask -TaskName "ClaudeSkillsUpstreamSync" -Action $action -Trigger $trigger
```

스크립트는 git commit/push 까지 자동 진행하지 않습니다 — 변경 확인 후 사용자가 직접 결정.

## 마스터 진입

새 세션에서 `/unity-fullstack` — 4계층 메뉴 한국어 안내.

## 디렉토리 구조

```
.claude/
├── settings.json                권한 + 12 hook wiring + 플러그인
├── statusline.sh                상태줄 (한국어)
├── hooks/                       12개 (Tiki 머지 2 + GS 신규 10)
├── rules/                       12개 (Tiki 2 + GS 10)
├── agents/                      39개 (Tier 1-3, Godot/UE 제외)
├── skills/                      81개
│   ├── unity-fullstack/         마스터 진입
│   ├── ko-sprint-plan/          한국어 wrapper 5개
│   ├── ko-story-cycle/
│   ├── ko-code-review/
│   ├── ko-perf-profile/
│   ├── ko-prototype/
│   ├── sf-list/                 SkillForge 오프라인 헬퍼 3개
│   ├── sf-info/
│   ├── sf-add/
│   └── <72 GS skills>           브레인스토밍·스프린트·리뷰·릴리스 등
├── docs/                        9개
│   ├── mcp-unity-guide.md       MCPForUnity 35 도구 한국어 가이드
│   ├── editor-automation-decision.md  L1/L2/L3 결정 매트릭스
│   ├── ATTRIBUTION.md           출처·라이선스
│   └── gs-*.md                  GS 원본 docs 6개
├── data/                        2개
│   ├── bundles.json             6 번들 (core / gameplay / perf / process / visuals-ui / devops)
│   └── workflows.json           3 워크플로 (concept-to-prototype / feature-implementation / release-cycle)
└── agent-memory/                (빈 디렉토리, GS hook 출력처)

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

각 상류 저장소의 라이선스를 따름. 통합 자체에 별도 라이선스는 부여하지 않음. 자세한 내용은 `.claude/docs/ATTRIBUTION.md`.
