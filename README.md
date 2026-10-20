# Unity 풀스택 통합 스킬 패키지

> **English:** [jump to the English summary](#unity-full-stack-claude-skills)

Unity 게임 개발용 Claude Code 통합 환경입니다. 목표는 **게임 아이디어를 기획으로 만들고, 기획 의도대로 그래픽을 만들고, Unity로 개발하는 과정을 자동화**하는 것입니다.
4개 외부 저장소를 흡수해 만든 **4계층 스킬 셋** 위에, 자체 도구 두 가지(그래픽 생성 파이프라인 · 스튜디오 모드)를 얹었습니다.

```
아이디어 ─▶ 기획 ──────────────────▶ 그래픽 ─────────────────▶ Unity 개발
          /brainstorm · /map-systems   /art-bible · /asset-spec      /ko-setup-engine
          /design-system (GDD)         /ko-art-gen (artgen)          /ko-story-cycle · MCP
          ─────────── 한 세션에서 순서대로, 또는 스튜디오 모드(3세션 + 디렉터)로 병렬 ───────────
```

원본 통합 시점: **2026-05-13** (Unity 멀티 게임 프로젝트에서 추출·일반화)

## 빠른 시작

설치 스크립트 한 번 + Claude Code에서 엔진 설정 한 번이면 끝납니다.

```powershell
# 1. 템플릿 받기
git clone https://github.com/cozrouki/unity-fullstack-claude-skills
cd unity-fullstack-claude-skills

# 2. 대상 Unity 프로젝트에 설치 (복사·자리표시자·권한·MCP·.gitignore)
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"
```

3. **Unity 에디터**에서 프로젝트를 열고 `Window > MCP for Unity`에서 브리지 연결을 확인합니다 (패키지는 2에서 manifest에 추가됨).
4. 프로젝트 루트에서 Claude Code를 실행합니다.
   ```powershell
   cd D:\Projects\MyGame
   claude
   ```
5. **`/ko-setup-engine`** — 최초 1회. 엔진·패키지·입력·명명 규칙을 실측하고 플랫폼·목표 fps 두 가지만 물은 뒤 `CLAUDE.md` Technology Stack과 `technical-preferences.md`를 씁니다. 엔진·패키지를 업그레이드할 때마다 다시 실행합니다.
6. **`/unity-fullstack`** — 이후 작업 메뉴 (스프린트·스토리·리뷰·코드 패턴·에디터 자동화·그래픽 생성).
7. 진행 방식을 고릅니다.
   - **한 세션**: 위 흐름의 스킬을 순서대로 직접 호출합니다.
   - **스튜디오 모드**: 터미널 3개로 기획·아트·개발 세션을 띄우고, 디렉터로서 게이트에서만 승인합니다 → [스튜디오 모드](#스튜디오-모드--3세션-자동-개발)

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
| **L1 프로세스** | 스프린트·리뷰·게이트·릴리스 워크플로 (86 skills) | `.claude/skills/` | `/unity-fullstack`, `/ko-sprint-plan`, `/ko-story-cycle`, `/ko-code-review`, `/ko-perf-profile`, `/ko-prototype`, `/ko-art-gen`, `/studio-*` 등 |
| **L2 C# 코드 패턴** | SkillForge 102 skills (FSM, 인벤토리, 능력, Jobs/Burst 등 14 카테고리) | `.agent/skills/` | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 Editor 자동화** | MCPForUnity 35+ 도구 사용 가이드 | `.claude/docs/mcp-unity-guide.md` | `mcp__UnityMCP__*` (별도 MCPForUnity 설치 필요) |
| **L4 패키징** | 번들·워크플로 정의 | `.claude/data/bundles.json`, `workflows.json` | JSON 직접 참조 |
| **그래픽 생성** | 기획 → 이미지 생성 → 아트 바이블 검수 → Unity 임포트 (백엔드 중립, 어댑터로 나중에 연결) | `.agent/tools/artgen/` | `/ko-art-gen` · [도구 문서](.agent/tools/artgen/README.md) |
| **스튜디오 모드** | 디렉터 + 기획·아트·개발 3세션이 티켓·게이트로 협업하는 자동 개발 (Claude Code 세션 간 알림). 아트는 AI 생성 또는 **사람 아티스트 + 보조 세션** (`artMode`) | `.agent/tools/studio/` | `/studio-join <역할>` · `/studio-ticket` · `/studio-status` · [프로토콜](.agent/tools/studio/README.md) |

## 그래픽 생성 — `/ko-art-gen`

`/art-bible` 과 `/asset-spec` 이 만든 기획 문서를 실제 이미지로 만들어 Unity 에셋으로 넣습니다. 상세: [`.agent/tools/artgen/README.md`](.agent/tools/artgen/README.md)

```
에셋 스펙 ─▶ 생성 요청(JSON) ─▶ 생성 ─▶ 아트 바이블 루브릭 검수 ─(미달)─▶ 프롬프트 수정 후 재생성
                                          └─(통과)─▶ 선택 ─▶ Assets/ 승격 + 임포트 설정 자동 적용
```

- **백엔드 중립.** 이미지 생성 백엔드는 어댑터로 나중에 정합니다. 백엔드를 고르지 않아도 전체 흐름이 돌아갑니다.

  | 어댑터 | 용도 |
  |---|---|
  | `mock` (기본) | 자리표시 이미지. 백엔드 없이 흐름 검증 |
  | `command` | 외부 스크립트나 CLI(ComfyUI 호출 스크립트, 상용 API 래퍼 등)를 설정만으로 연결 |
  | `manual` | 사람 아티스트가 `production/artgen/_inbox/<ASSET-ID>/` 에 넣은 PNG 를 수령 |
  | Python 어댑터 | `providers/_template.py` 를 복사해 구현 |

- **기획 의도 대조.** 스타일·형태·색·판독성·기술 5개 축을 아트 바이블 근거와 함께 채점합니다. 스타일 토큰은 모든 에셋이 공유해 일관성을 유지합니다.
- **안전한 승격.** 생성 결과는 `Assets/` 밖에 버전별로 쌓이고, 승인한 것만 승격합니다. 교체할 때는 기존 파일을 먼저 백업합니다. Editor 전용 임포터(`ArtGenImportPostprocessor`)가 텍스처 설정을 적용합니다.

```
/ko-art-gen next                 매니페스트에서 다음 Needed 에셋
/ko-art-gen spec:combat --auto   스펙 파일 단위로 일괄 처리
```

## 스튜디오 모드 — 3세션 자동 개발

사용자가 **디렉터**가 되고, 같은 프로젝트 폴더에서 AI 세션 3개(기획 · 아트 · 개발)가 서로 일을 주고받으며 게임을 만듭니다. 역할마다 **다른 AI 도구**를 쓸 수 있습니다(Claude Code · Codex CLI · Gemini CLI · Cursor · Copilot CLI · OpenCode · Antigravity 등). 상세: [`.agent/tools/studio/README.md`](.agent/tools/studio/README.md)

```
              디렉터 — 게이트 승인 · 판단 요청 답변 · 정지/재개 (/studio-status)
                 ▲
   planning ──티켓──▶ art ──티켓──▶ dev        상태: production/studio/ (티켓·게이트·로스터)
       ◀──질문/리뷰──    ◀──에셋 요청──         깨우기: 티켓 파일 감시 (+ Claude 끼리는 SendMessage)
```

**시작**
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

**운영 규칙**
- **단계 게이트:** G1 컨셉 → G2 아트 디렉션 → G3 프리프로덕션 → M1, M2 … 게이트에 묶인 티켓은 승인 전에는 시작할 수 없습니다. 승인은 디렉터만 합니다.
- **쓰기 영역 분리:** 기획은 `design/`, 아트는 `Assets/*/Art`·`production/artgen`, 개발은 그 외 `Assets/`·기술 문서를 씁니다. Unity MCP 는 개발 세션만 씁니다. 다른 영역이 필요하면 티켓을 보냅니다.
- **커밋:** 게이트를 통과하거나 티켓을 완료할 때 각 세션이 자기 영역만 커밋합니다. 프로토콜 · 지침 파일(`CLAUDE.md` · `.claude/` · 도구 설정 등)은 **디렉터 영역**이라 디렉터가 커밋합니다(`/studio-status commit`). 푸시는 디렉터가 합니다.
- **유지보수:** `studio.py audit` 이 주인 없는 변경과 역할 겹침을 찾고, 프로토콜 파일이 바뀌면 지문으로 감지해 현황판에 "미승인 변경" 으로 표시합니다(`/studio-status protocol ack`). 템플릿 갱신은 **`studio.py upgrade --from <템플릿>`** 으로만 합니다 — 설정은 프로젝트 값을 보존한 채 병합되고, 역할마다 공지 티켓이 발행됩니다.
- **아트 모드:** `.agent/tools/studio/studio.config.json` 의 `"artMode"` 로 고릅니다.
  - `"ai"`: art 세션이 artgen 으로 생성합니다.
  - `"human"`: art 세션이 **사람 아티스트의 보조**가 됩니다. 티켓을 대화 브리프로 전하고, 질문과 결정을 티켓으로 옮기고, 납품물을 검사해 승격합니다. 기획은 아트 디렉션 브리프부터 쓰고, 개발은 자리표시 그래픽으로 먼저 진행합니다.
- **정지와 재개:** `/studio-status pause` 를 하면 각 세션이 진행 중인 티켓만 마무리하고 멈춥니다. 재개는 `/studio-status resume` 입니다.

**여러 도구를 섞을 때**
- 깨우기는 **티켓 파일 감시**(`studio.py watch`)가 기본이라 도구 종류와 무관합니다. 대기 중에는 AI 토큰을 쓰지 않습니다.
- 감독 루프(`dispatch`)는 진전이 없으면 실행 간격을 늘리고(60 → 300 → 900초), 3회 연속이면 디렉터에게 알립니다. 역할당 하나만 돌고, 실행 로그는 `production/studio/logs/` 에 남습니다.
- 헤드리스 실행은 **승인 없이 파일을 고치고 명령을 실행**합니다. 신뢰할 수 있는 프로젝트에서만 쓰세요. CLI 옵션은 버전마다 바뀌므로 `studio.py agents` 와 `--dry-run` 으로 확인하고, 다르면 `studio.config.local.json` 에서 덮어씁니다.

**한계**
- **같은 작업 폴더**를 전제로 합니다. 다른 PC 의 Claude Code 세션도 Remote Control(같은 계정)로 메시지는 주고받을 수 있지만, 티켓 파일이 공유되지 않아 지금 구조로는 다른 PC 에 역할을 둘 수 없습니다. 꺼져 있던 세션은 다음 `/studio-join` 또는 `dispatch` 시작 때 밀린 티켓을 처리합니다.
- 세 세션이 **같은 계정의 사용량 한도**를 함께 써서 단일 세션보다 약 3배 빨리 소모됩니다. 한도가 가까우면 먼저 정지하세요. 한도에 닿으면 세션이 멈추고, 초기화 뒤 `/studio-join <역할>` 로 재개합니다. 반쯤 된 작업은 재개 시 점검합니다.

## 패키지 내용 통계

- **Skills (L1)**: 86개 (Game-Studios 72 + 한국어 wrapper 7 + 스튜디오 모드 3 + 마스터 진입 1 + SkillForge 헬퍼 3)
- **Agents**: 39개 (Tier 1-3, Godot/UE 11개 제외)
- **Rules**: 12개 (Unity gameplay-code, doc-writing, GS 10개)
- **Hooks**: 12개 (SessionStart/Stop, validate-commit/push/assets, notify, log-agent 등)
- **Docs**: 9개 (MCP 가이드, 결정 매트릭스, GS 원본 6개, 출처 1개)
- **Data**: 2개 (bundles.json 6개 번들, workflows.json 5개 워크플로)
- **SkillForge (L2)**: 102개 SKILL.md (14 카테고리) + skills-index.json + README-sync.md
- **Tools**: 2개 — `artgen` (그래픽 생성 CLI · 어댑터 4종 · Unity 임포터 템플릿), `studio` (스튜디오 모드 CLI · 역할 헌장 4종 · 아트 디렉션 브리프 템플릿). 둘 다 테스트 포함

### 요구 사항

| 항목 | 용도 |
|---|---|
| Claude Code | 슬래시 스킬 · 훅 · 서브에이전트 · 스튜디오 모드(세션 간 알림) |
| Windows PowerShell 5.1+ | `install.ps1` · `sync-upstream.ps1` |
| Git for Windows (bash 포함), git 2.25+ | 훅 스크립트 · 스튜디오 모드 역할별 커밋 |
| Python 3.8+ (`python` 이 PATH 에 있을 것) | artgen · studio CLI (표준 라이브러리만 사용). 테스트는 `pytest` 필요 |
| (선택) Codex · Gemini · Cursor · Copilot · OpenCode CLI | 스튜디오 모드에서 역할을 다른 AI 도구에 맡길 때 (`studio.py dispatch`) |
| Unity + MCPForUnity (선택) | L3 에디터 자동화 · 승격 에셋 임포트 확인 |

## 크로스툴 호환 (Claude Code · Codex · Copilot · Cursor · Gemini · OpenCode · Windsurf · Antigravity)

이 패키지는 **Claude Code 전용이 아니다.** `AGENTS.md` 오픈 표준을 정본으로 삼고, 도구마다 다른 규칙 · 명령 형식은 **생성기**가 단일 소스에서 만들어 낸다.

### 도구별로 무엇을 읽는가

| 자산 | Claude Code | Codex CLI | Copilot (CLI · VS Code) | Cursor | Gemini CLI | OpenCode | Windsurf | Antigravity |
|---|---|---|---|---|---|---|---|---|
| **페르소나 · 표준** | `CLAUDE.md`→`AGENTS.md` | `AGENTS.md` | `AGENTS.md` + `.github/copilot-instructions.md` | `AGENTS.md` | `GEMINI.md`→`AGENTS.md` | `AGENTS.md` | `AGENTS.md` | `AGENTS.md` |
| **파일별 자동 적용 룰** | `.claude/rules/` | `AGENTS.md` §8 색인 | `.github/instructions/` (`applyTo`) | `.cursor/rules/*.mdc` | `AGENTS.md` §8 색인 | `AGENTS.md` §8 색인 | `.windsurf/rules/` (`trigger: glob`) | `.agent/rules/` |
| **슬래시 명령 (워크플로 9종)** | `.claude/skills/` 86개 | `.agents/skills/` (Agent Skills) | `.github/prompts/` (VS Code) · `.github/skills/` (CLI) | `.cursor/commands/` | `.gemini/commands/*.toml` | `.opencode/commands/` | `.windsurf/workflows/` | `.agent/workflows/` |
| **L2 C# 코드 패턴** (`.agent/skills/`) | `/sf-add` 등 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 | 파일 참조 |
| **훅 / 서브에이전트** | ✅ | — | — | — | — | — | — | — |
| **artgen CLI** | `/ko-art-gen` | `/ko-art-gen` 스킬 | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` | `/ko-art-gen` |
| **스튜디오 모드 참여** | `/studio-join` (대화형) | `dispatch --agent codex` | `dispatch --agent copilot` | `dispatch --agent cursor` | `dispatch --agent gemini` | `dispatch --agent opencode` | `/studio-join` 워크플로 (IDE) | `/studio-join` 워크플로 (IDE) |

**워크플로 9종** — `/ko-sprint-plan` · `/ko-story-cycle` · `/ko-code-review` · `/ko-perf-profile` · `/ko-prototype` · `/ko-setup-engine` · `/ko-art-gen` · `/unity-fullstack` · `/studio-join`

> **핵심 구분** — **콘텐츠 층**(페르소나 · 룰 · C# 카탈로그 · 워크플로 절차 · artgen · 스튜디오 CLI)은 모든 도구에서 쓴다. Claude Code 외 도구의 슬래시 명령은 `.agent/workflows/<이름>.md` 정본을 가리키는 **얇은 포인터**이고, 절차가 Claude 스킬(`.claude/skills/<이름>/SKILL.md`)을 지시하면 그 파일을 읽어 따른다. **훅 · 서브에이전트 · 나머지 77개 스킬의 슬래시 호출은 Claude Code 전용**이다 (다른 도구에서도 `SKILL.md` 를 읽게 하면 절차는 따라 할 수 있다).

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

## 다른 Unity 프로젝트에 적용하는 방법

### 자동 설치 (권장) — `scripts/install.ps1`

아래 1~4단계를 한 번에 수행합니다. Windows PowerShell 5.1 이상.

```powershell
# 단일 게임
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"

# 멀티 게임 + 공유 모듈 + Cursor 병행
.\scripts\install.ps1 -Target D:\Projects\Multi -Games "A=GameA,B=GameB" -SharedModule SharedCore -Tools Claude,Cursor

# 모든 도구 (Claude · Codex · Copilot · Cursor · Gemini · OpenCode · Windsurf · Antigravity)
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame" -Tools All

# 미리보기 (파일 쓰기 없음)
.\scripts\install.ps1 -Target D:\Projects\MyGame -DryRun
```

| 단계 | 하는 일 |
|---|---|
| 복사 | 이 저장소의 **git 추적 파일만** 복사 (로컬 잔재 제외). `-Tools Claude,Codex,Copilot,Cursor,Gemini,OpenCode,Windsurf,Antigravity` 또는 `All` 로 선택, 공통(`AGENTS.md`·`.agent/`)은 항상. MIT 고지는 `.agent/licenses/`. 대상에 이미 있는 `.github/` 는 **파일 단위로 병합**(CI 워크플로 등 보존, 겹치는 파일만 `-Force` 시 백업 후 교체) |
| 자리표시자 | `AGENTS.md` §6 게임 폴더 매핑 표, `<SharedModule>`(룰 glob 포함), 네임스페이스 예시, 태그 예시를 실제 값으로 — `.claude`·`.agent`·`.cursor` 룰 미러까지 |
| 권한 | `.claude/settings.local.json` 생성, 이미 있으면 **병합**(기존 권한 보존) |
| MCP | `Packages/manifest.json`에 MCPForUnity 추가(서식 유지), `.mcp.json` 생성(`uvx` 위치 자동 탐지, `-McpPort`) — `-SkipMcp`로 생략 |
| .gitignore | 백업 폴더 · 머신별 설정 · 런타임 파일 항목 추가 (artgen 생성 원본 · 받은함, 스튜디오 이벤트 로그 · 정지 표시 · 디스패치 로그 · 잠금 포함) |

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

### 6단계: 엔진 설정 (자동·수동 설치 공통) — Technology Stack + technical-preferences.md

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

`.claude/docs/ATTRIBUTION.md` 참조. 외부 저장소:

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
- `.claude/skills/<GS-skill>/` — Game-Studios 72개 skill (자체 skill `ko-*` · `sf-*` · `studio-*` · `unity-fullstack` 은 덮어쓰지 않음)
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
└── gen-rule-mirrors.py          크로스툴 미러 생성 (룰 → 4개 형식 + AGENTS.md 색인, 워크플로 → 7개 형식)

.cursor/rules/ · commands/      12개 .mdc 룰 + 9개 명령 (Cursor — 생성물)
.github/instructions/ · prompts/ · skills/ · copilot-instructions.md   Copilot (생성물)
.agents/skills/                  9개 (Codex — Agent Skills, 생성물)
.gemini/commands/                9개 .toml (Gemini CLI — 생성물)
.opencode/commands/              9개 (OpenCode — 생성물)
.windsurf/rules/ · workflows/    12개 룰 + 9개 워크플로 (Windsurf — 생성물)
.agent/rules/                    12개 .md  (Antigravity — .claude/rules verbatim)
.agent/workflows/                9개 (Antigravity 슬래시 — ko-* 7 + unity-fullstack + studio-join)
.agent/tools/artgen/             그래픽 생성 CLI · 백엔드 어댑터 · Unity 임포터 템플릿 · 테스트
.agent/tools/studio/             스튜디오 모드 프로토콜 · 역할 헌장 4종(planning · art · art-human · dev) · 도구 공통 업무 루프 프롬프트 · 아트 디렉션 브리프 템플릿 · 티켓/게이트/커밋/감시/디스패치 CLI · 테스트

.claude/
├── settings.json                권한 + 12 hook wiring + 플러그인
├── statusline.sh                상태줄 (한국어)
├── hooks/                       12개 (로컬 머지 2 + GS 신규 10)
├── rules/                       12개 (로컬 fork 2 + GS 10)
├── agents/                      39개 (Tier 1-3, Godot/UE 제외)
├── skills/                      86개
│   ├── unity-fullstack/         마스터 진입
│   ├── ko-sprint-plan/          한국어 wrapper 7개
│   ├── ko-story-cycle/
│   ├── ko-code-review/
│   ├── ko-perf-profile/
│   ├── ko-prototype/
│   ├── ko-setup-engine/         실측 엔진 설정 (measure.sh)
│   ├── ko-art-gen/              그래픽 생성 파이프라인 (artgen CLI 오케스트레이션)
│   ├── studio-join/             스튜디오 모드 3종 (역할 등록·업무 루프 / 디렉터 지시 / 디렉터 콘솔)
│   ├── studio-ticket/
│   ├── studio-status/
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
│   └── workflows.json           5 워크플로 (concept-to-prototype / concept-to-art / studio-autodev / feature-implementation / release-cycle)
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

통합 작업과 자체 도구(ko-* wrapper · artgen · studio · 스크립트)는 [MIT](LICENSE). 포함된 상류 구성 요소는 각자의 MIT 라이선스를 따릅니다 — [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md), `.claude/docs/ATTRIBUTION.md`.

---

# Unity Full-Stack Claude Skills

A turnkey agentic scaffolding for **Unity game development** with
[Claude Code](https://claude.com/claude-code) (also works with Codex CLI,
GitHub Copilot, Cursor, Gemini CLI, OpenCode, Windsurf, and Antigravity —
per-tool rules and slash commands are generated from one source by
`scripts/gen-rule-mirrors.py`). Its goal is to automate the path from a **game
idea → design documents → graphics that match the design intent → a Unity
build**. It integrates four upstream skill repositories into a single,
generalized **4-layer skill set**, and adds two original tools on top: a
backend-neutral graphics pipeline and a multi-session "studio mode".

> **Mostly an integration/distribution.** The bulk of the skills come from the
> upstreams below (all MIT). Original work here: the integration and
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
| **L1 — Process** | 86 workflow slash-command skills (sprint / review / gate / release) | `/unity-fullstack`, `/sprint-plan`, `/code-review`, … |
| **L2 — C# code patterns** | 102 SkillForge skills (FSM, inventory, abilities, Jobs/Burst — 14 categories) | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 — Editor automation** | MCPForUnity (35+ Editor tools) + usage guide | `mcp__UnityMCP__*` |
| **L4 — Packaging** | bundle / workflow definitions | `.claude/data/` |

Plus 12 hooks, 12 rules, 39 agents, 9 docs — all auto-applied.

### Original tools

| Tool | What | Entry |
|---|---|---|
| **artgen** — graphics pipeline | Asset spec → generation request → image → review against the art bible → promote into `Assets/` with TextureImporter settings applied. **Backend-neutral**: `mock` (placeholder), `command` (any external script/CLI), `manual` (a human artist's deliveries), or your own Python adapter. | `/ko-art-gen` · [`.agent/tools/artgen/`](.agent/tools/artgen/README.md) |
| **Studio mode** — 3-session auto-dev | You act as **director**; three AI sessions (planning · art · dev) in one project pass work to each other via ticket files. Each role can use a **different AI tool**: interactive Claude Code, or Codex / Gemini / Cursor / Copilot / OpenCode CLIs driven headless by a supervisor loop, or IDE agents (Antigravity, Windsurf). Sessions wake on ticket-file changes, so the tools don't need to talk to each other directly. You approve at stage gates (concept → art direction → pre-production → milestones). Art can be AI-generated or a **human artist** assisted by the art session. | `/studio-join` · `/studio-ticket` · `/studio-status` · `studio.py dispatch` · [`.agent/tools/studio/`](.agent/tools/studio/README.md) |

Requirements for the tools: Python 3.8+ as `python` on PATH (stdlib only; `pytest` for their tests), git 2.25+. Studio mode runs all roles in one working tree on one machine; the director console skills need Claude Code, but everything is also available through the `studio.py` CLI.

## Quick start

```powershell
git clone https://github.com/cozrouki/unity-fullstack-claude-skills
cd unity-fullstack-claude-skills
.\scripts\install.ps1 -Target D:\Projects\MyGame -Games "MG=MyGame"
```

`install.ps1` copies the assets (git-tracked files only, per `-Tools` — `Claude`,
`Codex`, `Copilot`, `Cursor`, `Gemini`, `OpenCode`, `Windsurf`, `Antigravity`, or
`All`), fills
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

Studio mode: open one terminal per role in the project. For a Claude Code role,
run `claude` and `/studio-join <role>` (keep Claude sessions in the same
permission mode). For another CLI, run
`python .agent/tools/studio/studio.py dispatch <role> --agent codex` (or
`gemini`, `cursor`, `copilot`, `opencode`). Give the idea with
`/studio-ticket planning "Concept: …"`, and check progress and approve gates
with `/studio-status`.

See the Korean guide above for the full step-by-step (settings, MCP install,
cross-tool mirrors, upstream sync via `scripts/sync-upstream.ps1`). The artgen
and studio docs are Korean only.

## Credits (upstreams — all MIT)

- [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) — L1 process skills
- [Unity-SkillForge](https://github.com/nlelouche/Unity-SkillForge) — L2 code-pattern skills
- [unity-mcp / MCPForUnity](https://github.com/CoplayDev/unity-mcp) — L3 Editor backend (installed as a UPM package)
- antigravity-awesome-skills — L4 packaging format (format only)

## License

[MIT](LICENSE) for the original integration work. Bundled upstream components
remain under their own MIT licenses — see
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
