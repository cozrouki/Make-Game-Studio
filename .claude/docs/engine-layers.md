# 엔진 계층 표 (Unity · Godot · Unreal)

이 템플릿은 엔진 중립이다. 엔진마다 달라지는 것은 **이 표 한 곳**에만 적고, 스킬 · 규칙 · 역할 헌장은 이 표를 가리킨다. 엔진 API 사실(버전별 변경 · 폐기 API)은 여기가 아니라 `docs/engine-reference/<engine>/` 이 정본이다.

## 현재 엔진 판정

순서대로 보고 처음 나온 값을 쓴다.

1. `project.yaml` 의 `engine.name` (`/setup-engine` · `/ko-setup-engine` 이 쓴다 — 정본)
2. 표지 파일: `ProjectSettings/ProjectVersion.txt` → Unity · `project.godot` → Godot · `*.uproject` → Unreal
3. 둘 다 없으면 **엔진 미설정**이다. 엔진별 단계는 건너뛰지 말고 "엔진 미설정이라 하지 않음" 을 보고에 적는다 (`.claude/rules/skill-authoring.md` — 건너뛴 단계는 스스로 알린다).

## 계층별 표

| 계층 | Unity | Godot | Unreal |
|---|---|---|---|
| 코드 루트 (`resolve_code_root`) | `Assets/` | `src/` | `Source/` |
| 주 언어 | C# | GDScript (· C#) | C++ (· Blueprint) |
| 버전 확인 | `ProjectSettings/ProjectVersion.txt` `m_EditorVersion` | `project.godot` `config/features` | `*.uproject` `EngineAssociation` |
| 엔진 레퍼런스 | `docs/engine-reference/unity/` | `docs/engine-reference/godot/` | `docs/engine-reference/unreal/` |
| 전문가 에이전트 (`project.yaml` `specialists`) | `unity-specialist` · `unity-shader-specialist` · `unity-ui-specialist` · `unity-dots-specialist` · `unity-addressables-specialist` | `godot-gdscript-specialist` · `godot-csharp-specialist` · `godot-shader-specialist` · `godot-specialist` · `godot-gdextension-specialist` | `unreal-specialist` · `ue-umg-specialist` · `ue-gas-specialist` · `ue-blueprint-specialist` · `ue-replication-specialist` |
| 테스트 프레임워크 | Unity Test Framework (NUnit) — EditMode / PlayMode | gdUnit4 (`addons/gdUnit4/`) | Automation (Spec / `IMPLEMENT_SIMPLE_AUTOMATION_TEST`) |
| 테스트 실행 (공통 진입점) | `bash .claude/scripts/test-run.sh unity [--platform playmode]` | `bash .claude/scripts/test-run.sh godot` | `bash .claude/scripts/test-run.sh unreal [--filter <루트>]` |
| 테스트 실행 (에디터가 열려 있을 때) | MCP `mcp__UnityMCP__run_tests` | — | — |
| 콘솔 · 로그 | MCP `read_console` · `Editor.log` · `Player.log` | 에디터 출력 · `user://logs/godot.log` | `Saved/Logs/<프로젝트>.log` |
| 프로파일러 | MCP `manage_profiler` · Profiler 창 | Debugger > Profiler · Monitors | Unreal Insights · `stat unit` / `stat game` |
| 에디터 자동화 | MCP for Unity (`.claude/docs/mcp-unity-guide.md`) | `godot --headless --script` · `@tool` 스크립트 | 에디터 Python (`-ExecutePythonScript`) · 커맨드렛 |
| 정적 검사 (커밋 훅 `validate-lint.sh`) | `unity_lint.py` (UL001~) + Unity 공식 분석기(UNT) | **없음** — 리뷰에서 `gameplay-code.md` Godot 절 확인 | **없음** — 리뷰에서 `gameplay-code.md` Unreal 절 확인 |
| 코드 패턴 카탈로그 (L2) | SkillForge `.agent/skills/` (`/sf-list` · `/sf-add`) | **없음** — 엔진 레퍼런스 + 전문가 에이전트 | **없음** — 엔진 레퍼런스 + 전문가 에이전트 |
| 장르 · 분야 실무 카탈로그 | `/ext list gamedev` (Unity 6.3 기능 포함) | `/ext list gamedev` 의 엔진 무관 항목만 | `/ext list gamedev` 의 엔진 무관 항목만 |
| 그래픽 · 사운드 생성 승격 (`/ko-art-gen`) | Unity 임포트 설정까지 자동 (`unity-import-setup`) | 파일 승격까지 — 임포트 설정은 수동 | 파일 승격까지 — 임포트(.uasset 변환)는 수동 |
| 사전 설치 점검 (`/ko-prereq`) | Unity 에디터 · MCP · 분석기 점검 | Godot 실행 파일 점검 | Unreal 에디터 점검 |
| 씬 · 에셋 파일 (`scene-files.md`) | `.unity` · `.prefab` · `.asset` — 에디터로 수정 | `.tscn` · `.tres` — `uid://` 를 지어내지 않는다 | `.uasset` · `.umap` — 수정 금지(설정 deny) |

**없음** 칸은 이 템플릿이 아직 그 엔진용 도구를 갖추지 못했다는 뜻이다. 그 단계는 "엔진에 도구 없음 — 하지 않음" 으로 보고하고, 같은 일을 사람이 할 방법(리뷰 · 수동 임포트)을 적는다.

## 엔진별 하지 않는 것

- **Godot · Unreal 에서 SkillForge 의 C# 템플릿을 쓰지 않는다** — Unity API(MonoBehaviour · ScriptableObject)에 묶여 있다. 설계 아이디어만 참고하고 코드는 엔진 레퍼런스로 다시 쓴다.
- **Unity 이외 엔진에서 `unity_lint.py` 를 돌리지 않는다** — Godot C# 의 `_Process` 는 UL 규칙이 보는 `Update()` 와 다르다.

## 이 표를 바꿀 때

엔진 도구를 추가하면(예: Godot 정적 검사기) 이 표의 칸 → 그 도구를 부르는 스킬 · 훅 → `README.md` 엔진 지원 표 순서로 고친다. 엔진 API 사실은 이 표에 적지 않는다.
