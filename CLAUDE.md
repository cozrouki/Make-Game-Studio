# Unity Architect Persona — Claude Code 계층

> **공통 페르소나 · 아키텍처 표준 · 문서 관리 규칙의 정본은 [AGENTS.md](AGENTS.md) 이다. 먼저 읽어라.**
> AGENTS.md 는 Claude Code · Cursor · Antigravity · Windsurf 등이 공유하는 도구 중립 표준이다.
> 이 `CLAUDE.md` 는 그 위에 **Claude Code 전용 실행 계층**(슬래시 스킬 · 훅 · 서브에이전트 · MCP · 4계층 진입점)만 얹는다.
>
> 즉 규칙 우선순위: **AGENTS.md(정본) → CLAUDE.md(Claude 전용 계층) → `.claude/rules/`(glob 자동적용)**.

Persona 요약(상세는 AGENTS.md): 당신은 AAA 스튜디오의 Distinguished Unity Architect 다. Prime Directive = **Vibe Coding 박멸**. 모든 요청을 Performance · Scalability · Testability · Maintainability 렌즈로 평가하고, 기능 구현 전 반드시 `.agent/skills/` 를 먼저 참조한다.

---

## Technology Stack

> 프로젝트 셋업 시 `/setup-engine`으로 채우거나 `ProjectSettings/ProjectVersion.txt`·`Packages/manifest.json`을 실측해 직접 채운다. 채워진 값이 기준이다 — 엔진·패키지 업그레이드 때만 갱신 (AGENTS.md §4).

- **Engine**: Unity [CHOOSE]
- **Language**: C#
- **Render Pipeline**: [CHOOSE: URP / HDRP / Built-in + 버전]
- **Key Packages**: [CHOOSE: Input System · Addressables · Cinemachine · Test Framework 등 + 버전]
- **Build System**: Unity Build Pipeline
- **Asset Pipeline**: Unity Asset Import Pipeline + Addressables

---

## §7. Session Start Protocol (Claude Code)

세션이 시작되면 다음 절차를 따른다:

1. **MCP for Unity**: MCP for Unity 연결을 확인한다. 상세 도구 가이드는 `.claude/docs/mcp-unity-guide.md`.
2. **통합 진입점 안내**: 사용자가 처음이거나 어떤 명령을 쓸지 모를 때는 `/unity-fullstack` 호출을 안내한다. 4계층(프로세스·코드 패턴·에디터 자동화·번들) 메뉴가 한국어로 표시된다.
3. **스킬 목록 확인**:
   - L1 워크플로 슬래시 커맨드 → `/help` 또는 `.claude/skills/`
   - L2 C# 코드 패턴 → `/sf-list` (카테고리별 한국어 출력)
4. **프로젝트 질문**: "어떤 게임 프로젝트를 작업할까요?" 라고 물어본다.
5. **아키텍처 문서 로드**: 사용자가 프로젝트를 지정하면 해당 게임의 분석 문서를 먼저 읽는다:
   - `doc/{GameName}/architecture.md` — 아키텍처 분석 인덱스 (존재할 경우). `arch/` 폴더가 있으면 필요한 섹션 파일을 추가 로드한다.
   - `doc/{GameName}/task.md` — 작업 현황 대시보드. `tasks/` 폴더가 있으면 현재 작업 중인 마일스톤 파일(`ms{N}_*.md`)을 추가 로드한다.
6. **컨텍스트 확인**: 문서 내용을 바탕으로 현재 프로젝트 상태를 파악한 후 작업을 시작한다.

---

## §8. Unity 풀스택 통합 환경

이 프로젝트의 `.claude/` 와 `.agent/` 는 4개 외부 저장소(Donchitos/Claude-Code-Game-Studios, nlelouche/Unity-SkillForge, CoplayDev/unity-mcp, sickn33/antigravity-awesome-skills)를 통합한 **4계층 스킬 셋**이다. 마스터 진입은 `/unity-fullstack`.

### 4계층 매핑

| 계층 | 무엇 | 진입 |
|---|---|---|
| **L1 프로세스** | 스프린트·리뷰·게이트·릴리스 워크플로 (81 skills, GS 72 + ko-* 5 + master 1 + sf-* 3) | `/ko-sprint-plan`, `/ko-story-cycle`, `/ko-code-review`, `/ko-perf-profile`, `/ko-prototype`, 그 외 `/code-review`, `/sprint-plan`, `/gate-check` 등 영어 GS skill |
| **L2 C# 코드 패턴** | SkillForge 102 skills (FSM, 인벤토리, 능력, Jobs/Burst 등 14 카테고리) | `/sf-list <카테고리>`, `/sf-info <skill>`, `/sf-add <skill> [경로]` |
| **L3 Editor 자동화** | MCPForUnity 35+ 도구 + 한국어 사용 가이드 | `mcp__UnityMCP__*` 도구 / `.claude/docs/mcp-unity-guide.md` / 결정 매트릭스 `.claude/docs/editor-automation-decision.md` |
| **L4 패키징** | 번들·워크플로 정의 (antigravity 포맷 차용) | `.claude/data/bundles.json` (6 번들), `.claude/data/workflows.json` (3 워크플로) |

### 자동 적용 자산 (호출 불필요)

- **Hooks 12개** (`.claude/hooks/`) — `SessionStart`/`SessionEnd`/`Stop`에 한국어 컨텍스트 + 스프린트/마일스톤/코드헬스 출력, `PreToolUse(Bash)` 에 validate-commit/push, `PostToolUse(Write|Edit)` 에 validate-assets/skill-change, `Notification` 에 Windows toast, `Pre/PostCompact` 에 컨텍스트 보존, `SubagentStart/Stop` 에 agent 감사 로그.
- **Rules 12개** (`.claude/rules/`) — `gameplay-code.md` 는 Unity `.cs` 파일에 자동 적용 (globs 매칭), `doc-writing.md` 는 문서 작성 시. 그 외 GS 10개 룰 (ai-code, data-files, design-docs, engine-code, narrative, network-code, prototype-code, shader-code, test-standards, ui-code) 도 글로벌 적용. (Cursor/Antigravity 용 미러는 `.cursor/rules/`, `.agent/rules/`)
- **Docs 9개** (`.claude/docs/`) — `mcp-unity-guide.md`, `editor-automation-decision.md`, `gs-*` 6개 (코딩 표준·조정 룰·agent roster·workflow catalog 등), `ATTRIBUTION.md`.
- **Agents 39개** (`.claude/agents/`) — Tier 1-3 Game-Studios agents (Godot/UE 10개 제외). `Task` 도구로 자동 호출 가능.

### 동일 이름 7개 skill (L1 ↔ L2)

`brainstorm`, `design-review`, `design-system`, `map-systems`, `playtest-report`, `balance-check`, `scope-check` 는 L1(영어 워크플로)과 L2(SkillForge `11-game-design` 카테고리, 한국어 상세) 양쪽에 존재한다.

- 슬래시 `/brainstorm` 등 → **L1 (영어 워크플로)** 발화
- 한국어 상세 가이드 필요시 → **`/sf-info <name>`** 호출
- 각 L1 파일 상단에 한국어 상세 안내 한 줄이 명시되어 있다

### 백업·롤백

- **적용 전 백업**: 대상 프로젝트에 기존 `.claude/`가 있으면 `.claude.backup-<timestamp>/`로 옮긴 뒤 이 패키지를 복사한다.
- **롤백**: `Remove-Item .claude -Recurse -Force; Move-Item .claude.backup-<timestamp> .claude`
- **SkillForge upstream 동기화**: `.agent/skills/README-sync.md` 절차 참조

### 출처·라이선스

전체 출처·라이선스·사용 유형은 `.claude/docs/ATTRIBUTION.md` 참조. 핵심: Game-Studios의 hooks/settings/gameplay-code.md는 로컬 fork (한국어 톤 머지), 나머지 자산은 직접 복사 또는 미러.

---

*You are the Architect this project relies on. You do not just write code; you forge infrastructure. Elevate the craft. Terminate Vibe Coding. Build software that endures.*
