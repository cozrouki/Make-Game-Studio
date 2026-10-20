# Unity Full-Stack Claude Skills

A turnkey agentic scaffolding for **Unity game development** with
[Claude Code](https://claude.com/claude-code) (also works with Cursor,
Antigravity, Codex, and Gemini). It integrates four upstream skill repositories
into a single, generalized **4-layer skill set** so you don't have to wire them
together yourself.

> **This is an integration/distribution, not original skills.** The substantive
> skills come from the upstreams below (all MIT); the value added here is the
> integration, generalization, cross-tool mirroring, and onboarding. Credits and
> licenses: [`LICENSE`](LICENSE) · [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) ·
> [`.claude/docs/ATTRIBUTION.md`](.claude/docs/ATTRIBUTION.md).

> **Language note:** the core skills and agents (copied from the English
> upstreams) are in **English**. The wrappers (`ko-*`), persona, rules, and this
> guide are written **Korean-first** — English contributions welcome. English
> reference translations of the persona, the two Korean rules, and the `ko-*`
> wrappers live in [`i18n/en/`](i18n/en/).

## What's inside — 4 layers

| Layer | What | Entry |
|---|---|---|
| **L1 — Process** | 82 workflow slash-command skills (sprint / review / gate / release) | `/unity-fullstack`, `/sprint-plan`, `/code-review`, … |
| **L2 — C# code patterns** | 102 SkillForge skills (FSM, inventory, abilities, Jobs/Burst — 14 categories) | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 — Editor automation** | MCPForUnity (35+ Editor tools) + usage guide | `mcp__UnityMCP__*` |
| **L4 — Packaging** | bundle / workflow definitions | `.claude/data/` |

Plus 12 hooks, 12 rules, 39 agents, 9 docs — all auto-applied.

## Quick start

```powershell
git clone https://github.com/cozrouki/unity-fullstack-claude-skills
cd unity-fullstack-claude-skills
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"
```

`install.ps1` copies the assets (git-tracked files only, per `-Tools`), fills
the game-folder mapping table in `AGENTS.md` §6 and the `<SharedModule>` /
namespace placeholders, creates or merges `.claude/settings.local.json`, adds
MCPForUnity to `Packages/manifest.json`, writes `.mcp.json`, and updates
`.gitignore`. It refuses to overwrite an existing install unless you pass
`-Force` (which backs it up first). Use `-DryRun` to preview. Single-game
project? Omit `-Games` and ignore the game-tag system.

Then record your engine once: run `/ko-setup-engine` in Claude Code. It
measures the project (engine version, render pipeline, packages, input
bindings, UI framework, and naming conventions from your own code) and asks only
two questions — target platforms and framerate — before writing the
`## Technology Stack` section of `CLAUDE.md` and
`.claude/docs/technical-preferences.md`. (Brand-new project with no code yet?
It hands off to upstream `/setup-engine`.) About 20 L1 skills read these files
to know the engine, performance budgets, naming conventions, and which Unity
specialist agent to route work to.

See the Korean guide below for the full step-by-step (settings, MCP install,
cross-tool mirrors, upstream sync via `scripts/sync-upstream.ps1`).

## Credits (upstreams — all MIT)

- [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) — L1 process skills
- [Unity-SkillForge](https://github.com/nlelouche/Unity-SkillForge) — L2 code-pattern skills
- [unity-mcp / MCPForUnity](https://github.com/CoplayDev/unity-mcp) — L3 Editor backend (installed as a UPM package)
- antigravity-awesome-skills — L4 packaging format (format only)

## License

[MIT](LICENSE) for the original integration work. Bundled upstream components
remain under their own MIT licenses — see
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

# Unity 풀스택 통합 스킬 패키지 (한국어)

Unity 게임 개발용 Claude Code 통합 환경. 4개 외부 저장소를 흡수해 만든 **4계층 스킬 셋**입니다.

원본 통합 시점: **2026-05-13** (Unity 멀티 게임 프로젝트에서 추출·일반화)

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
| **L1 프로세스** | 스프린트·리뷰·게이트·릴리스 워크플로 (82 skills) | `.claude/skills/` | `/unity-fullstack`, `/ko-sprint-plan`, `/ko-story-cycle`, `/ko-code-review`, `/ko-perf-profile`, `/ko-prototype` 등 |
| **L2 C# 코드 패턴** | SkillForge 102 skills (FSM, 인벤토리, 능력, Jobs/Burst 등 14 카테고리) | `.agent/skills/` | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 Editor 자동화** | MCPForUnity 35+ 도구 사용 가이드 | `.claude/docs/mcp-unity-guide.md` | `mcp__UnityMCP__*` (별도 MCPForUnity 설치 필요) |
| **L4 패키징** | 번들·워크플로 정의 | `.claude/data/bundles.json`, `workflows.json` | JSON 직접 참조 |

## 패키지 내용 통계

- **Skills (L1)**: 82개 (Game-Studios 72 + 한국어 wrapper 6 + 마스터 진입 1 + SkillForge 헬퍼 3)
- **Agents**: 39개 (Tier 1-3, Godot/UE 11개 제외)
- **Rules**: 12개 (Unity gameplay-code, doc-writing, GS 10개)
- **Hooks**: 12개 (SessionStart/Stop, validate-commit/push/assets, notify, log-agent 등)
- **Docs**: 9개 (MCP 가이드, 결정 매트릭스, GS 원본 6개, 출처 1개)
- **Data**: 2개 (bundles.json 6개 번들, workflows.json 3개 워크플로)
- **SkillForge (L2)**: 102개 SKILL.md (14 카테고리) + skills-index.json + README-sync.md

## 크로스툴 호환 (Claude Code · Cursor · Antigravity)

이 패키지는 **Claude Code 전용이 아니다.** `AGENTS.md` 오픈 표준(Agentic AI Foundation)을 정본으로 삼아 여러 에이전트 도구에서 쓸 수 있게 구성돼 있다.

### 도구별로 무엇을 읽는가

| 자산 | Claude Code | Cursor | Antigravity | Gemini CLI |
|---|---|---|---|---|
| **페르소나·표준·문서규칙** | `CLAUDE.md`→`AGENTS.md` | `AGENTS.md` | `AGENTS.md` | `GEMINI.md`→`AGENTS.md` |
| **glob 자동적용 룰** | `.claude/rules/` | `.cursor/rules/*.mdc` | `.agent/rules/*.md` | — |
| **L2 C# 코드 패턴** (`.agent/skills/`) | `/sf-add` 등 | 파일 참조 | 파일 참조 | 파일 참조 |
| **슬래시 워크플로** | `.claude/skills/` 82개 ✅ | ❌ (자체 명령) | `.agent/workflows/` 7개 ✅ | ❌ |
| **훅 / 서브에이전트** | `.claude/` ✅ | ❌ | ❌ | ❌ |

> **핵심 구분** — **콘텐츠 층**(페르소나·룰·C# 카탈로그·docs)은 어느 도구든 즉시 사용 가능. **자동화 층** 중 슬래시 워크플로는 Claude Code(`.claude/skills/` 전체) + Antigravity(`.agent/workflows/` 핵심 7개 = `ko-*` 6 + `unity-fullstack`)가 커버하고, **훅·서브에이전트는 Claude Code 네이티브 전용**이다. Cursor는 콘텐츠 층 + `.cursor/rules/` 자동적용 룰까지 사용한다.

### AGENTS.md 정본 구조

- **`AGENTS.md`** — 도구 중립 정본 (페르소나 §1–§7). Claude Code·Cursor·Antigravity·Windsurf·Codex 가 공통으로 읽음.
- **`CLAUDE.md`** — `AGENTS.md` 를 가리키고 그 위에 Claude Code 전용 계층(Technology Stack·§7 세션·§8 4계층·훅·서브에이전트)만 얹음. Technology Stack은 `/setup-engine`·`/gate-check`가 이 파일에서 읽고 쓰므로 여기에 둔다(다른 도구는 AGENTS.md §4 안내대로 이 섹션을 읽음).
- **`GEMINI.md` / `AGENT.md`(단수)** — `AGENTS.md` 로 가는 얇은 포인터.

### 룰 미러 — 단일 소스에서 파생

`.claude/rules/*.md` 가 **소스 오브 트루스**이며, 스크립트로 두 도구용 미러를 생성한다:

```bash
python scripts/gen-rule-mirrors.py
#  .claude/rules/*.md  →  .agent/rules/*.md    (Antigravity, verbatim)
#                      →  .cursor/rules/*.mdc  (Cursor, frontmatter 변환)
```

룰을 고칠 때는 **`.claude/rules/` 만 수정 후 재생성**한다. `.agent/rules/`·`.cursor/rules/` 는 생성물이므로 직접 편집 금지.

### Antigravity 워크플로 (슬래시 커맨드)

`.agent/workflows/*.md` 는 Antigravity에서 `/파일명` 슬래시로 발동된다. L1 핵심 7종을 포팅:

- `/ko-sprint-plan` · `/ko-story-cycle` · `/ko-code-review` · `/ko-perf-profile` · `/ko-prototype` · `/ko-setup-engine` · `/unity-fullstack`

각 워크플로는 Claude Code의 `.claude/skills/<name>/` 절차를 참조하되, Antigravity용으로 조정됨(`/sf-*` 슬래시 대신 `.agent/skills/` 카탈로그 직접 참조). 훅·서브에이전트가 필요한 나머지 75개 skill은 Claude Code 전용으로 남는다.

## 다른 Unity 프로젝트에 적용하는 방법

### 자동 설치 (권장) — `scripts/install.ps1`

아래 1~4단계를 한 번에 수행합니다. Windows PowerShell 5.1 이상.

```powershell
# 단일 게임
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"

# 멀티 게임 + 공유 모듈 + Cursor 병행
.\scripts\install.ps1 -Target D:\Projects\Multi -Games "A=GameA,B=GameB" -SharedModule SharedCore -Tools Claude,Cursor

# 미리보기 (파일 쓰기 없음)
.\scripts\install.ps1 -Target D:\Projects\MyGame -DryRun
```

| 단계 | 하는 일 |
|---|---|
| 복사 | 이 저장소의 **git 추적 파일만** 복사 (로컬 잔재 제외). `-Tools Claude,Cursor,Antigravity,Gemini` 로 선택, 공통(`AGENTS.md`·`.agent/`)은 항상. MIT 고지는 `.agent/licenses/` |
| 자리표시자 | `AGENTS.md` §6 게임 폴더 매핑 표, `<SharedModule>`(룰 glob 포함), 네임스페이스 예시, 태그 예시를 실제 값으로 — `.claude`·`.agent`·`.cursor` 룰 미러까지 |
| 권한 | `.claude/settings.local.json` 생성, 이미 있으면 **병합**(기존 권한 보존) |
| MCP | `Packages/manifest.json`에 MCPForUnity 추가(서식 유지), `.mcp.json` 생성(`uvx` 위치 자동 탐지, `-McpPort`) — `-SkipMcp`로 생략 |
| .gitignore | 백업 폴더·머신별 설정·런타임 파일 항목 추가 |

- `-Games`를 생략하면 `Assets/` 하위 후보(.cs 수)를 보여 주고 입력받습니다. 입력이 리다이렉트된 환경(CI)에서는 묻지 않고 자리표시자를 유지합니다.
- 기존 `.claude`·`CLAUDE.md`·`AGENTS.md` 등이 있으면 **중단**합니다. `-Force`를 붙이면 `.claude.backup-<시각>/`에 백업한 뒤 덮어씁니다(`settings.local.json`은 보존).
- 설치 후: Unity에서 MCPForUnity 확인 → `claude` 실행 → **`/ko-setup-engine`**(6단계) → `/unity-fullstack`.

스크립트를 쓸 수 없는 환경이면 아래 수동 절차를 따르세요.

### 1단계: 자산 복사 (수동)

대상 Unity 프로젝트 루트에 자산을 복사. 쓰는 도구에 맞춰 선택 복사:

```powershell
$src = "<이 저장소를 clone 한 경로>"      # 예: 이 저장소 루트
$dst = "D:\path\to\YourUnityProject"

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

### 4단계: MCPForUnity 설치 (L3 사용시)

- 패키지에는 MCPForUnity 자체는 **없음** (Unity Package Manager로 별도 설치)
- 대상 Unity 프로젝트의 `Packages/manifest.json` 에 추가:
  ```json
  "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"
  ```
- 프로젝트 루트의 `.mcp.json.template` 을 `.mcp.json` 으로 복사한 뒤 `command` 경로/포트를 자기 환경에 맞게 수정 (실제 `.mcp.json` 은 `.gitignore` 처리됨 — 머신별 경로 포함)

### 5단계: 새 Claude Code 세션 시작

```powershell
cd D:\path\to\YourUnityProject
claude
```

`session-start.sh` 가 자동 발화하며 한국어 컨텍스트 + 코드 헬스 + 스프린트 정보(있으면) 표시됩니다.

`/unity-fullstack` 호출 → 4계층 메뉴 한국어 안내.

### 6단계: 엔진 설정 (Technology Stack + technical-preferences.md)

L1 스킬 20여 개(`code-review`·`dev-story`·`smoke-check`·`test-setup`·`team-*` 등)가 `.claude/docs/technical-preferences.md`에서 엔진·성능 예산·명명 규칙·**Unity 전문가 에이전트 라우팅**을 읽고, `/gate-check`는 `CLAUDE.md`의 `## Technology Stack`이 `[CHOOSE]` 상태인지 검사합니다. 두 파일 모두 **비어 있는 상태로 배포**되므로 한 번 채워야 합니다. 비어 있으면 이 스킬들이 "엔진 미설정"으로 판단하고 전문가 에이전트(`unity-specialist`·`unity-shader-specialist`·`unity-ui-specialist` 등)로 넘기지 못합니다.

**`/ko-setup-engine` 한 번 실행하면 됩니다.**

```
/ko-setup-engine                    # 코드 루트 후보를 보여 주고 고르게 함
/ko-setup-engine Assets/YourGame    # 코드 루트 지정 (서드파티 에셋 제외용)
```

| 자동 실측 (`measure.sh`) | 질문 (2개) |
|---|---|
| 엔진 버전 · 렌더 파이프라인 · 패키지 버전 · 물리/NavMesh · UI Toolkit/uGUI 비율 · 입력 바인딩(게임패드 지원) · **명명 규칙 다수결**(`[SerializeField]`/private/const/event 따로) · 테스트 asmdef(EditMode/PlayMode) | 대상 플랫폼(현재 + 확장 예정) · 목표 프레임 |

- 결과는 미리보기로 보여 주고 **승인 후에만** 씁니다. 다시 실행해도 사람이 쓴 섹션(금지 패턴·허용 라이브러리·ADR 로그)은 보존하므로, 엔진·패키지를 업그레이드할 때마다 재실행하면 됩니다.
- **코드가 없는 새 프로젝트**는 실측할 것이 없으므로 upstream `/setup-engine`으로 넘깁니다.
- 왜 `/setup-engine`을 그대로 쓰지 않나: upstream은 명명 규칙을 기본값(private 필드 `_camelCase` 하나)으로 채웁니다. 기존 코드가 다른 규칙이면 `/code-review`가 수백 곳을 위반으로 지적합니다.
- `.claude/`는 프로젝트(클론)당 하나이므로 `technical-preferences.md`도 하나입니다. 한 Unity 프로젝트에 여러 게임이 있으면 코드 루트를 여러 개 넘겨 함께 실측합니다.
- 측정 스크립트만 따로 돌려 볼 수도 있습니다: `bash .claude/skills/ko-setup-engine/measure.sh Assets/YourGame` (파일을 쓰지 않음).

## 문서 운영 규칙 (컨텍스트 비용)

`work_log.md`·`active.md`는 매 세션 읽히므로 커질수록 토큰 비용이 늘어납니다. `AGENTS.md` §6·§6-1에 다음 규칙이 정의돼 있습니다.

- **work_log 월별 분리** — `doc/work_log.md`에는 현재 월만 두고 새 항목은 최상단에 추가(최신순). 지난 달은 `doc/work_log/YYYY-MM.md`로 옮기고 하단 인덱스에 한 줄 추가.
- **active.md 3~5KB** — `production/session-state/active.md`에는 현재 상태·최근 완료분·다음 할 것·블로커만. 지난 이력은 work_log로, 커밋은 해시만, 넘치면 `production/session-state/archive/`로.

`ko-story-cycle`·`ko-sprint-plan`도 이 기준(work_log 최상단 = 최신)을 따릅니다. 일부 GS 스킬(`dev-story`·`story-done` 등)은 active.md에 내용을 덧붙이므로 주기적으로 정리하세요 — upstream 미러라 스킬 자체는 수정하지 않습니다.

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
.mcp.json.template               MCPForUnity 설정 템플릿
scripts/
├── install.ps1                  대상 Unity 프로젝트에 설치 (복사·치환·권한·MCP·.gitignore)
├── sync-upstream.ps1            upstream 2종 동기화
└── gen-rule-mirrors.py          .claude/rules → .agent/rules + .cursor/rules 생성

.cursor/rules/                   12개 .mdc (Cursor — .claude/rules 에서 생성)
.agent/rules/                    12개 .md  (Antigravity — .claude/rules verbatim)
.agent/workflows/                7개 (Antigravity 슬래시 — ko-* 6 + unity-fullstack)

.claude/
├── settings.json                권한 + 12 hook wiring + 플러그인
├── statusline.sh                상태줄 (한국어)
├── hooks/                       12개 (로컬 머지 2 + GS 신규 10)
├── rules/                       12개 (로컬 fork 2 + GS 10)
├── agents/                      39개 (Tier 1-3, Godot/UE 제외)
├── skills/                      82개
│   ├── unity-fullstack/         마스터 진입
│   ├── ko-sprint-plan/          한국어 wrapper 6개
│   ├── ko-story-cycle/
│   ├── ko-code-review/
│   ├── ko-perf-profile/
│   ├── ko-prototype/
│   ├── ko-setup-engine/         실측 엔진 설정 (measure.sh)
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
