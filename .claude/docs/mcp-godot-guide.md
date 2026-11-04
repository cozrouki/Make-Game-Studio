# Godot MCP 사용 가이드 (한국어)

> **Godot .NET(C#) 판 프로젝트 전용 · 선택 설치.** GDScript 전용 Godot 프로젝트는 이 애드온을 컴파일하지 못한다 — 그때의
> 에디터 자동화는 `.claude/docs/engine-layers.md` 의 명령줄 경로(`godot --headless --script` · `@tool` 스크립트)를 쓴다.
> Unity 는 `.claude/docs/mcp-unity-guide.md`.

**Godot-MCP** (IvanMurzak/Godot-MCP, Apache-2.0) 는 Claude 가 실행 중인 Godot 에디터를 직접 조회 · 수정하게 하는 애드온이다.
이 문서의 사실은 상류 README · CLI 문서(2026-11-04 확인, 애드온 v0.34.0)에서 왔다.

| 검증 범위 (2026-11-04) | 결과 |
|---|---|
| `prereq.py install godot-mcp-addon` → 애드온 · `.csproj` · `project.godot` 변경 | ✅ 빈 Godot .NET 프로젝트에서 확인 |
| 애드온 포함 프로젝트 `dotnet build` (.NET SDK 10, `net8.0`) | ✅ 오류 0 |
| Godot 에디터에서 애드온 로드 · 로컬 서버 · Claude 도구 호출 | ❌ **검증 안 함** (그 PC 에 Godot 없음) |

처음 쓰는 PC 에서 아래 "연결 확인" 을 꼭 거친다.

## 개요

| 항목 | 값 |
|---|---|
| 저장소 | https://github.com/IvanMurzak/Godot-MCP (애드온) · https://github.com/IvanMurzak/GameDev-MCP-Server (서버) — 둘 다 Apache-2.0 |
| 요구 | Godot **4.3 이상 .NET(mono) 판** · **.NET 8 SDK** · 설치 도구용 Node.js(`npx`) |
| 설치 위치 | `addons/godot_mcp/` + 프로젝트 `.csproj` 의 NuGet 참조(0.34.0 에서 6개 — 일부는 내보내기 구성에서 빠지게 조건이 붙음) · `<EmbeddedResource>` · `<EnableDynamicLoading>` + `project.godot` `[editor_plugins]` |
| 템플릿 고정 버전 | `prereq.py` 의 `GODOT_MCP_VERSION` (애드온 · `godot-cli` 를 같은 버전으로) |
| 연결 방식 (템플릿 기본) | **로컬 서버** (Custom 모드, `localhost`) |
| 점검 | `/ko-prereq` 의 Godot 묶음 — `dotnet-sdk` · `godot-mcp-addon` · `godot-mcp-json` (모두 선택 항목) |

### 왜 로컬 서버가 기본인가

상류의 기본값은 **ai-game.dev 클라우드** 연결이다 — `godot-cli login` 으로 계정에 로그인하고, 에디터와 Claude 사이의 도구 호출이
외부 서버를 거친다. 이 템플릿은 외부로 프로젝트 정보를 보내지 않는 것을 원칙으로 하므로(출처 지문 · 생성 도구와 같은 기준) **로컬
서버(Custom 모드)** 를 안내한다. 애드온이 GitHub 릴리스에서 버전이 고정된 서버 실행 파일을 받아 내 PC 에서만 띄운다.
클라우드를 쓰기로 했다면 그것은 사용자 결정이다 — `/ko-prereq` 는 클라우드 등록을 실패가 아니라 경고로 알린다.

## 설치

1. **점검** — `/ko-prereq` (또는 `python .agent/tools/setup/prereq.py check --role dev`). GDScript 전용 프로젝트면 세 항목이
   "GDScript 전용 프로젝트 — 하지 않음" 으로 건너뛴다. `.csproj` 가 없으면 Godot .NET 에디터로 C# 프로젝트 파일을
   먼저 만든다 (Godot 문서 "C# basics" — https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_basics.html).
2. **애드온 설치** — `/ko-prereq` 가 확인을 받고 실행하거나, 직접:

   ```bash
   npx -y godot-cli@0.34.0 install-plugin --path <프로젝트>
   ```

   애드온 버전은 CLI 버전(`@0.34.0`)을 따른다. 상류 문서의 `install-plugin --version x` 는 0.34.0 에서 전역 "버전 출력" 옵션에
   가로채여 **아무것도 설치하지 않고 성공(0)으로 끝난다** (2026-11-04 실측) — 쓰지 않는다.

   GitHub 릴리스에서 `addons/godot_mcp/` 를 받고, `.csproj` 에 NuGet 참조(`com.IvanMurzak.ReflectorNet` · `McpPlugin` · `Rql` · `CodeExec` ·
   `CodeExec.Roslyn` · `Microsoft.CodeAnalysis.CSharp` — 뒤의 넷은 `ExportDebug` · `ExportRelease` 구성에서 빠진다)와 확장 카탈로그 `<EmbeddedResource>` · `<EnableDynamicLoading>true</EnableDynamicLoading>` 를 넣고, 플러그인을 켠다. 다시 실행해도
   바뀌는 것이 없다(멱등). **바뀌는 파일**: `addons/godot_mcp/**` · `*.csproj` · `project.godot` — dev 영역에서 커밋한다.
3. **빌드 후 에디터 열기** — C# 어셈블리가 없으면 애드온이 첫 실행에 꺼진다. `npx -y godot-cli@0.34.0 open <프로젝트> --mode Custom`
   은 빌드 → 에디터 실행을 한 번에 한다. 직접 열 때는 먼저 `dotnet build` 한다.
4. **로컬 서버 켜기** — 에디터의 Godot MCP 독 → **Server** 카드에서 연결 방식을 **Custom** 으로 두고 **Start Server**. 첫 실행 때
   고정 버전의 `gamedev-mcp-server` 를 GitHub 에서 받아 `.godot/mcp-server/` 에 둔다(깃 무시). 독에 나온 **Server URL** 을 적어 둔다.
5. **Claude Code 에 등록** —

   ```bash
   npx -y godot-cli@0.34.0 setup-mcp claude-code <프로젝트> --url <독의 Server URL>
   ```

   로컬 주소(`--url http://localhost:…`)로 쓴 설정에는 계정 키가 들어가지 않는다. 등록 뒤 Claude Code 세션을 다시 띄운다.

### 연결 확인

```bash
npx -y godot-cli@0.34.0 wait-for-ready <프로젝트>   # 서버가 ping 에 답할 때까지 기다림
npx -y godot-cli@0.34.0 status <프로젝트>           # 실행 중 에디터 · 서버 상태
```

그다음 Claude 에게 "현재 씬의 노드 목록을 보여 줘" 처럼 읽기만 하는 요청부터 한다. `/ko-prereq` 의 `godot-mcp-json` 이 `ok (로컬)`
인지도 본다. 연결이 안 되면 에디터가 켜져 있는지, 독이 Custom 모드인지, `.mcp.json` 주소가 독의 Server URL 과 같은지 확인한다.

## 도구 (상류 v0.34.0 기준 9계열)

| 계열 | 도구 | 쓰는 곳 |
|---|---|---|
| rql | `rql-query` · `rql-mutate` · `rql-schema` | 씬 노드 · 속성 · 리소스 · 파일 · 프로젝트 설정 · 입력 맵을 질의 언어(RQL) 한 줄로 읽고 바꾼다. 바꾸기는 되돌리기(Ctrl+Z) 가능, `dry_run` 미리보기 |
| script | `script-read` · `script-create` · `script-update` · `script-delete` · `script-attach-to-node` · `script-validate` · `script-build` · `script-execute` | `.gd` · `.cs` 파일, GDScript 검증, C# 빌드, 에디터 안 C# 실행 |
| screenshot | `screenshot-viewport` · `screenshot-camera` · `screenshot-isolated` | 뷰포트 · 카메라 · 노드 단독 렌더를 PNG 로 — 시각 확인 |
| console · reflection · runtime-errors | 로그 읽기 · C# 메서드 찾기/호출 · 게임 실행 중 오류 | **실행 중인 게임** 대상. 게임 코드에서 켜야 한다(기본 꺼짐) |

`ping` · `session-close` · skills 계열은 시스템 도구라 Claude 에게 보이지 않는다. 정확한 인수는 `rql-schema` 와 상류 `docs/rql.md` 를 본다.

## 이 템플릿에서 쓰는 법

- **결정 기준**은 `.claude/docs/editor-automation-decision.md` 와 같다 — 반복되는 에디터 조작 · 씬 일괄 변경 · 시각 확인은 MCP,
  게임 로직은 코드와 테스트(`/ko-tdd`), 엔진 API 사실은 `docs/engine-reference/godot/`.
- **씬은 에디터를 거쳐 바꾼다**(`.claude/rules/scene-files.md`) — 에디터가 연결돼 있으면 `.tscn` 텍스트를 손으로 고치지 않고 `rql-mutate`
  로 바꾼 뒤 `editor | call SaveScene()` 로 저장하고 diff 를 본다.
- **테스트는 MCP 가 아니라 테스트 러너로** — `bash .claude/scripts/test-run.sh godot` (gdUnit4). MCP 화면 확인은 테스트를 대신하지 않는다.
- 스튜디오 모드의 dev 역할이 쓰는 도구다. 아트 · 기획 역할은 쓰지 않는다.

## 보안 — 알고 켜기

- **에디터 안 C# 실행(`script-execute`)은 임의 코드 실행이다.** 승인 없이 돌리지 않는다.
- **토큰이 평문으로 저장된다** — 애드온 설정 `user://godot-mcp-config.json`. 로컬 모드에서 토큰을 쓰지 않으면 비어 있다. 커밋 · 공유하지 않는다.
- **출시 빌드에 MCP 를 넣지 않는다.** 게임 쪽 런타임 연결 · 오류 수집 · C# 실행은 상류에서 기본으로 꺼져 있고 코드로 켜야만 켜진다 —
  켜는 코드는 개발 빌드에만 둔다 (`/release-checklist` 에서 확인). RQL · C# 실행 패키지는 `.csproj` 조건으로 내보내기 구성에서 빠지지만,
  `GodotMcpCodeExecInGame=true` 를 켜면 게임 빌드에도 들어간다 — 켜지 않는다.
- **.NET 10 SDK 만 있는 PC**: C# 어셈블리를 다시 불러올 때 에디터가 죽거나 멈추는 .NET 런타임 결함이 상류에 보고돼 있다. `godot-cli open` 은
  우회 환경 변수(`DOTNET_ThreadPool_ThreadsToKeepAlive=-1`)를 자동으로 넣는다. 에디터를 직접 열면 그 변수를 직접 설정한다.

## 지우기

`npx -y godot-cli@0.34.0 remove-plugin <프로젝트>` 는 플러그인을 끄기만 한다. 완전히 지우려면 `addons/godot_mcp/` · `.csproj` 의 `com.IvanMurzak.*` ·
`Microsoft.CodeAnalysis.CSharp` 참조와 `<EmbeddedResource>` 줄 · `.mcp.json` 등록을 지운다.

## 버전 올리기

`prereq.py` 의 `GODOT_MCP_VERSION` 과 이 문서의 명령 버전을 함께 바꾼다. 상류 릴리스 노트에서 서버 · 도구 이름 변경을 확인한 뒤 올린다.
