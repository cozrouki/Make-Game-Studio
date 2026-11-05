# Unreal MCP 사용 가이드 (한국어)

> **Unreal Engine 5.8 이상 · 선택 설치.** 5.7 이하는 엔진에 MCP 서버 플러그인이 없다 — 그때의 에디터 자동화는
> `.claude/docs/engine-layers.md` 의 명령줄 경로(에디터 Python `-ExecutePythonScript` · 커맨드렛)를 쓴다.
> Unity 는 `.claude/docs/mcp-unity-guide.md`, Godot 은 `.claude/docs/mcp-godot-guide.md`.

Unreal 의 에디터 자동화는 두 조각으로 되어 있다.

| 조각 | 무엇 | 출처 · 라이선스 |
|---|---|---|
| **엔진 플러그인** `ModelContextProtocol` · `AllToolsets` | 에디터 안에서 MCP 서버를 열고(앞의 것), 30개 넘는 도구 묶음 — 액터 · 블루프린트 · 머티리얼 · Niagara · Sequencer · GAS · 자동화 테스트 · Live Coding 등 — 을 내놓는다(뒤의 것). **UE 5.8 에서 Experimental** | 엔진에 들어 있음 (Unreal Engine EULA) |
| **Claude Code 플러그인** `unreal-engine-skills-for-claude-code` | 도구를 어떻게 찾고 부를지 알려 주는 스킬 3개(`unreal-mcp` · `create-toolset` · `unreal-skill`)와 세션 시작 때 "Unreal 프로젝트" 라고 알려 주는 훅 | EpicGames/unreal-engine-skills-for-claude-code-plugin (MIT), Claude Code 공식 플러그인 마켓 |

MCP 연결은 엔진 플러그인만으로도 된다. Claude Code 플러그인은 사용 규칙이라 함께 켜는 것을 권한다. 이 템플릿은 둘 다 **복사하지 않는다** — 점검(`/ko-prereq`)과 이 안내만 둔다.

이 문서의 사실은 Epic 플러그인 저장소의 README · `skills/unreal-mcp/references/setup.md` (2026-11-04 확인, 플러그인 3.1.2), `docs/engine-reference/unreal/PLUGINS.md`, 그리고 아래 실측에서 왔다.

| 검증 (2026-11-04, UE 5.8.4 런처 설치본) | 결과 |
|---|---|
| 두 엔진 플러그인 존재 · 성격 | ✅ `Engine/Plugins/Experimental/ModelContextProtocol` · `.../Toolsets/AllToolsets` — 둘 다 Experimental, 기본 꺼짐 |
| 빈 프로젝트(`.uproject` 에 두 플러그인만 켬)를 `-nullrhi -ModelContextProtocolStartServer -ModelContextProtocolPort=8765` 로 실행 | ✅ 서버 기동, 도구 묶음 67개 등록 |
| HTTP MCP `initialize` → `tools/list` → `list_toolsets` · `describe_toolset` 호출 | ✅ 메타 도구 3개. 도구 묶음 설명은 에디터 언어(한국어)로 온다 |
| `ProgrammaticToolset.execute_tool_script`(에디터 안 Python) 존재 | ✅ 있음 — 아래 보안 절 |
| Claude Code 플러그인 · `GenerateClientConfig` · 실제 에셋 편집 | ❌ 검증 안 함 |

**함정**: 프로젝트가 엔진과 **다른 드라이브**에 있으면(예: 엔진 `D:` · 프로젝트 `C:\Users\...\Temp`) 에디터가 시작하자마자 `FilenameToLongPackageName ... illegal characters ':'` 로 죽었다. 같은 드라이브로 옮기니 됐다 (런처 설치본, 이 PC 에서 1회 관찰).

## 설치

1. **점검** — `/ko-prereq` 의 Unreal 묶음에 선택 항목 셋이 보인다: `ue-mcp-plugins` · `ue-mcp-json` · `ue-claude-plugin`. 프로젝트 `.uproject` 의 `EngineAssociation` 이 5.7 이하면 세 항목 모두 "UE 5.8 부터 — 하지 않음" 으로 건너뛴다. 소스 빌드(값이 GUID)는 버전을 모르므로 세 항목 모두 점검하되 "5.8+ 인지 직접 확인" 메모가 붙는다.
2. **엔진 플러그인 켜기** — `.uproject` 의 `Plugins` 배열에 `ModelContextProtocol` · `AllToolsets` 를 `"Enabled": true` 로 넣는다. `/ko-prereq` 가 확인을 받고 고친다 (`prereq.py install ue-mcp-plugins`). `AllToolsets` 는 기본으로 꺼져 있다 — 이것 없이 서버만 켜면 도구가 하나도 없다.
3. **서버 시작** — 에디터를 다시 열고 콘솔에서 `ModelContextProtocol.StartServer`. 매번 자동으로 켜려면 개인 설정 파일 `<프로젝트>/Saved/Config/<플랫폼>Editor/EditorPerProjectUserSettings.ini` 에:

   ```ini
   [/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
   bAutoStartServer=True
   ```

   이 파일은 사람마다 다르고 버전 관리에 넣지 않는다. 기본 주소는 `127.0.0.1:8000/mcp` 이고, 포트가 겹치면 `ServerPortNumber` 로 바꾼다.
4. **Claude Code 에 등록** — 에디터 콘솔에서 `ModelContextProtocol.GenerateClientConfig ClaudeCode`. 런처 설치 엔진이면 `.uproject` 옆에, 소스 빌드면 `Engine/` 이 있는 작업 루트에 `.mcp.json` 을 쓴다. 포트를 바꾸면 다시 실행한다.
5. **Claude Code 플러그인** — Claude Code 에서:

   ```
   /plugin install unreal-engine-skills-for-claude-code@claude-plugins-official
   ```

   팀 전체가 쓰려면 `.claude/settings.json` 의 `enabledPlugins` 에 넣는다. 그러면 이 폴더를 신뢰한 사람마다 설치를 묻는다 — 템플릿은 이것을 기본으로 넣지 않는다(엔진이 Unreal 이 아니거나 5.8 미만인 프로젝트에 묻지 않게).

### 연결 확인

1. 에디터 출력 로그에서 MCP 서버 시작 메시지를 본다.
2. Claude Code 에서 `/mcp` — `unreal-mcp` 가 연결돼 있는지 본다.
3. 읽기만 하는 요청부터: "현재 레벨의 액터 목록을 보여 줘".

도구는 처음부터 다 보이지 않는다. 서버는 기본으로 도구 찾기용 세 개(`list_toolsets` · `describe_toolset` · `call_tool`)만 내놓고, 필요한 도구 묶음을 그때 찾아 부른다. Claude Code 플러그인의 `unreal-mcp` 스킬이 그 절차를 안다.

## 이 템플릿에서 쓰는 법

- **결정 기준**은 `.claude/docs/editor-automation-decision.md` 와 같다 — 반복 에디터 조작 · 에셋 일괄 변경 · 화면 확인은 MCP, 게임 로직은 C++ 코드와 테스트(`/ko-tdd`), 엔진 API 사실은 `docs/engine-reference/unreal/`.
- **`.uasset` · `.umap` 은 여전히 손으로 고치지 않는다** (`.claude/rules/scene-files.md`). MCP 는 에디터를 거쳐 바꾸므로 그 규칙의 대안이다.
- **테스트는 테스트 러너로** — `bash .claude/scripts/test-run.sh unreal --filter <루트>`. MCP 의 자동화 테스트 도구는 에디터 안에서 돌려 보는 보조 수단이다.
- 스튜디오 모드에서는 dev 역할만 쓴다.

## 보안 — 알고 켜기

- **UE EULA — 보낸 데이터의 학습 사용.** 서버가 켜질 때 에디터 로그에 경고가 찍힌다: 이 플러그인으로 LLM 서비스에 보내는 데이터는 UE EULA 상 "Licensed Technology" 이고, LLM 제공자가 그것을 학습 입력으로 쓰지 않게 하는 책임은 사용자에게 있다 (EULA 6(e)). 쓰는 LLM 서비스(Claude 요금제 · API)의 데이터 학습 설정을 확인하고 기록해 둔다.
- **사용 분석.** 같은 로그에 MCP 분석 공급자로 엔진 분석(`FEngineAnalytics`)이 등록된다고 나온다. 무엇을 보내는지는 이 템플릿이 확인하지 않았다 — 엔진 분석 설정을 에디터 환경설정에서 확인한다.

- **에디터 안 Python 실행이 있다** (`ProgrammaticToolset.execute_tool_script`). 프로젝트 파일 · 에셋을 승인 없이 바꾸고 지울 수 있다. 실행 전 승인을 끄지 않는다.
- **같은 PC 의 다른 프로그램도 접속할 수 있다.** 서버는 `localhost` 에만 열리지만, 같은 사용자로 도는 프로세스는 붙을 수 있다. 공용 · 신뢰할 수 없는 PC 에서 켜지 않고, 포트를 밖으로 열지 않는다.
- **긴 작업 전에 저장 · 커밋한다.** MCP 편집은 되돌리기가 안 될 때가 있다.
- **스튜디오 모드 장치** — 이 엔진 플러그인(또는 Godot MCP)이 켜진 프로젝트에서는 승인 없이 도는 실행을 `studio.py` 가 막는다: `dispatch` 프리셋에 `--dangerously-skip-permissions` · `--yolo` · `--force` · `--full-auto` 가 있거나, 팀 정의 `permissionMode` 가 `bypassPermissions` 일 때. 대화형 세션(`/studio-join`)은 그대로 된다. 꼭 필요하면 사람이 `.agent/tools/studio/studio.config.local.json` 에 `{"guards": {"allowUnattendedEditorMcp": true}}` 를 넣어 연다. 장치가 아는 표시는 위 넷뿐이다 — 다른 도구 프리셋은 그 도구의 승인 방식을 직접 확인한다.

## 출시 빌드

`ModelContextProtocol.uplugin`(UE 5.8.4 설치본)의 모듈 중 `ModelContextProtocol` · `ModelContextProtocolEngine` 은 `Runtime` 형식이다 — 에디터 전용이 아니다. 패키징한 게임에 MCP 서버가 따라 들어가는지는 이 템플릿이 확인하지 않았다. 출시 전 `/release-checklist` 에서 패키지 로그와 플러그인 목록으로 확인하고, 필요하면 출시 구성에서 이 플러그인을 끈다.

## 지우기

`.uproject` 에서 두 플러그인을 `"Enabled": false` 로 하고, `.mcp.json` 의 `unreal-mcp` 등록과 `EditorPerProjectUserSettings.ini` 의 자동 시작 줄을 지운다. Claude Code 플러그인은 `/plugin` 에서 끈다.
