# 변경 이력 (CHANGELOG)

이 템플릿의 버전은 `.agent/VERSION` 에 있다 (설치된 프로젝트에도 복사된다 — 그 프로젝트가 어느 버전에서 왔는지의 기록).
버전 규칙: **주(major)** = 설치된 프로젝트가 따로 손봐야 하는 변경(저장소 이름 · 설정 체계 · 폴더 구조) ·
**부(minor)** = 새 스킬 · 도구 · 기능 · **수(patch)** = 고침.

## 기존 프로젝트 올리기

- **스튜디오 모드를 쓰는 프로젝트**: `python <템플릿>/.agent/tools/studio/studio.py --root <프로젝트> upgrade --from <템플릿> --dry-run` 으로
  미리 보고, 빼고 실행한다. 템플릿 버전 · 엔진을 보고하고, 프로젝트가 고친 파일(`gameplay-code.md` · `doc-writing.md`)은 덮어쓰지 않고
  "직접 병합 필요" 로 알린다. 훅 등록이 바뀌면 세션을 다시 띄운다.
- **스튜디오 모드를 쓰지 않는 프로젝트**: `scripts/install.ps1 -Target <프로젝트> -Force` 로 다시 설치한다 (`.claude.backup-<시각>/` 백업,
  `*.local.json` · `project.yaml` · 레지스트리 보존). AGENTS.md 게임 폴더 매핑은 `-Games` 로 다시 넣는다.

## 2.5.0 — 2026-11-10

GamePorject(이미 만들어진 Unity 게임, 네온 픽셀아트 전환 중)에 스튜디오 모드를 붙여 돌리며 찾은 보완.

**새 기능 (부)**
- **artgen 픽셀아트 후처리 `output.pixelate`** — SDXL 등 생성 결과를 격자 크기 픽셀아트로: 팔레트(아트 바이블 제한 팔레트 ·
  `"prompt"` · 적응 N색)로 양자화하고 칸마다 최빈색(`mode`, 기본 — 윤곽이 또렷) 또는 면적 평균(`average` + 순서 디더), 알파 이진화.
  원본은 `variant_NN.src.png` 로 남고, 승격 때 Unity 임포트 기본값이 Point · 비압축 · 밉맵 끔. 지금까지 `prompt.palette` 는 프롬프트
  힌트였는데, 이제 실제 색 제약이 된다. 표준 라이브러리 PNG 디코더(`pngutil.read_rgba` — 8bit 그레이 · RGB · RGBA · 팔레트, 필터 5종)
  추가. SDXL 1024² → 64² 약 2초
- **pixelfx 시트 다듬기 (기본 켬)** — 모든 프레임에 공통인 빈 여백을 잘라내고(pivot 보정) 한 번 재생 효과 끝의 빈 프레임을 버린다.
  `ice/frost-nova` 288×192 → 257×143 · 시트 24MB → 15MB. `providerOptions.pixelfx.trim` · `trimMargin`
- **스튜디오 — 이미 만들어진 게임의 G1** — 디렉터 · planning · art 헌장과 README 에 "기존 컨셉 고정" 경로: 후보 1안 = 현행 컨셉,
  보드 = 기존 캡처, 컨셉 · 필러는 코드 · 기존 문서에서 역작성, 그래픽 · 장르 방향 전환은 G2 에서

**고침 (수)**
- `studio.py audit` 이 설치가 만든 `.agent/PROVENANCE.md` · `.agent/VERSION` · `.agent/licenses/` 와 Unity 가 만드는 `*.sln` ·
  `*.slnx` · `*.csproj` 를 "주인 없는 변경" 으로 계속 경고하던 것 → 앞의 셋은 디렉터, 뒤의 셋은 dev 영역. 기존 프로젝트는 upgrade 가
  새 영역 항목을 **한 번만** 더하고 `ownsAddsApplied` 에 기록한다 (디렉터가 뺀 항목을 되살리지 않도록 역할 영역은 합집합을 쓰지 않음)
- `/ko-setup-engine` 이 스튜디오 모드에서 `CLAUDE.md` 를 고치면 "프로토콜 미승인 변경" 이 뜨는데 안내가 없던 것 → 디렉터의
  `studio.py protocol ack` 를 안내
- 도구 테스트: artgen 137 (픽셀아트 25 · pixelfx 25 — 실제 pixelfx 렌더 2개는 `PIXELFX_DIR` + Node 가 있을 때만), studio 136.
  새 테스트는 대상 코드를 일부러 깨서 실패하는 것을 확인했다 (Average 필터 · 끝 빈 프레임 · 저장소 연결 · 소유 영역 · upgrade 1회 추가)

## 2.4.1 — 2026-11-10

**고침 (수)**
- `install.ps1 -Force`: 이미 설치된 프로젝트에 다시 설치할 때 `.agent` · `.claude` 를 통째로 지우고 `*.local.json` 만 되살려서,
  **프로젝트가 직접 만든 파일**(예: `.agent/rules/<게임>.md` 프로젝트 규칙 · `.claude/agent-memory/` 에이전트 메모리)이 사라지던 것
  (백업에는 남았음) → 템플릿 git 이력에 한 번이라도 있었던 파일만 지우고(폐지 · 이름 바뀐 옛 템플릿 파일 정리는 그대로), 나머지는 보존하며
  목록을 출력한다. 설치가 다시 만드는 `.agent/PROVENANCE.md` · `.agent/licenses/` 와 `__pycache__` 는 정리 대상. `-DryRun` 에서도 보존 목록이
  보인다. 실제 프로젝트(GamePorject) 재설치에서 발견. 수정 전 스크립트로 같은 시나리오를 돌려 사용자 파일이 지워지는 것을 확인한 뒤 고쳤고,
  짧은 경로(`UNITY0~1`)와 긴 경로 대상 모두에서 확인 (짧은 경로에서 상대경로가 어긋나 정리가 통째로 안 되던 첫 구현의 문제도 함께 잡음)
- `studio.py upgrade` 는 원래 명시한 폐기 목록만 지워서 영향 없음

## 2.4.0 — 2026-11-10

**새 기능 (부)**
- **artgen `pixelfx` 어댑터 — 픽셀아트 애니메이션 VFX 시트 (GPU 불필요)** — [patch-gg/pixelfx](https://github.com/patch-gg/pixelfx)(MIT)의
  코드 효과 244종(불 · 폭발 · 마법 · 타격 · 날씨 · UI 등) 중 하나를 시드 · 팔레트로 렌더해 투명 스프라이트 시트 + 프레임 JSON 을 굽는다.
  요청 `providerOptions.pixelfx`: `effect`(필수) · `fps` · `options`. `prompt.palette` 를 밝기 순 색 램프로 넘겨 **실제로 그 색으로** 그린다.
  같은 시드면 같은 바이트. 생성 뒤 상류 `check.mjs` 결과를 `run.json` 경고로 남기고, 출처(커밋 · Sprite Fusion 표기 포함)는 승격 때
  `credits.json` 으로. 없는 효과 id 에도 상류 도구가 성공으로 끝나서 어댑터가 파일로 먼저 확인한다
- **스프라이트 시트 승격 · Unity 시트 자르기** — `run.json` 출력에 `sheet` 요약이 있으면 승격이 PNG 옆에 프레임 `.json` 을 함께 두고
  (둘 다 `--force` · 백업 대상), Unity 임포트 맵에 시트 기본값(Multiple · Point · 비압축 · 밉맵 끔 · 시트를 담는 `maxSize`)과 격자를 쓴다.
  `maxSize` 를 시트보다 작게 주면 거부한다. 임포터는 `com.unity.2d.sprite` 의 `ISpriteEditorDataProvider` 로 `<이름>_000` … 을 자르고
  다시 승격해도 spriteID 를 유지한다 (Unity 6.3 에서 `TextureImporter.spritesheet` 는 지원 중단). 패키지가 없으면 asmdef `versionDefines` 로
  그 코드를 빼고 경고만 낸다. Unity 6000.3.24f1 batchmode 로 두 경우 모두 확인 (103프레임 좌표 · pivot · 재임포트 ID 유지)
- `/ko-prereq` 선택 항목 `pixelfx` (art) — 고정 커밋 zip 을 크기 · SHA256 확인 후 `art-source/pixelfx/` 에 푼다 (MIT 밖인 갤러리 폰트는 받지 않음).
  Node 18+ · 고정 커밋 여부를 점검한다
- 어댑터 계약 추가(기존 어댑터 영향 없음): `Provider.project_root` · `sized_by_source` · `run_warnings`
- 도구 테스트 449개 (pixelfx 22 — 실제 렌더 결정론 1개는 `PIXELFX_DIR` + Node 가 있을 때만, prereq 4)

**기존 프로젝트**: `.gitignore` 에 `art-source/pixelfx/` 를 직접 추가한다 (`studio.py upgrade` 는 `.gitignore` 를 고치지 않는다 — `install.ps1 -Force` 는 넣는다).
Unity 프로젝트는 승격할 때 `Assets/ArtGen/Editor/` 의 임포터 · asmdef 를 템플릿 것으로 다시 복사해야 시트가 잘린다.

## 2.3.1 — 2026-11-05

**고침 (수)**
- `/ko-prereq` Unreal MCP: UE 5.7 이하 프로젝트에서 `ue-mcp-json`(서버 등록) · `ue-claude-plugin`(Epic 공식 Claude Code 플러그인)이
  쓸 수 없는데도 `missing` 으로 뜨던 것 → 세 항목 모두 "UE 5.8 부터 — 하지 않음"(`skip`). 엔진 버전을 모르는 소스 빌드(GUID)는
  세 항목 모두 막지 않고 점검하되 "5.8+ 인지 직접 확인" 메모를 붙인다 (전에는 `ue-mcp-plugins` 에만).
  회귀 테스트 `test_prereq_ue_mcp_all_items_skip_old_engine_with_reason` · `test_prereq_ue_mcp_unknown_version_still_checked_with_note` (수정 전 실패 확인)

## 2.3.0 — 2026-11-04

**새 기능 (부)**
- **Unreal MCP (UE 5.8+ L3 에디터 자동화, 선택 설치)** — 엔진 플러그인 `ModelContextProtocol` · `AllToolsets`(UE 5.8 Experimental)와
  Epic 공식 Claude Code 플러그인 `unreal-engine-skills-for-claude-code`(MIT, 공식 마켓)를 템플릿에 넣지 않고 점검 · 안내로 붙였다.
  `/ko-prereq` 의 Unreal 묶음에 선택 항목 3개: `ue-mcp-plugins`(확인 후 `.uproject` 에 두 플러그인 켜기) · `ue-mcp-json` · `ue-claude-plugin`.
  5.7 이하는 "UE 5.8 부터 — 하지 않음". 안내: `.claude/docs/mcp-unreal-guide.md`. UE 5.8.4 에서 빈 프로젝트로 서버 기동 · 도구 묶음 67개 · MCP 호출까지 실측 확인(Claude Code
  플러그인 · 에셋 편집은 미검증). 실측에서 찾은 것: 서버가 로그에 남기는 UE EULA 6(e) 경고(LLM 학습 사용 책임) · 엔진 분석 연결 ·
  프로젝트가 엔진과 다른 드라이브면 시작 직후 죽는 함정 — 가이드에 적었다
- **스튜디오 모드 장치 — 에디터 MCP + 승인 없는 실행 차단**: Unreal `ModelContextProtocol` 이나 Godot `godot_mcp` 가 켜진 프로젝트에서
  `dispatch` 프리셋이 `--dangerously-skip-permissions` · `--yolo` · `--force` · `--full-auto` 를 쓰거나 `team.json` `permissionMode` 가
  `bypassPermissions` 면 `dispatch` · `launch` 가 거부한다 (두 MCP 모두 에디터 안 임의 코드 실행 도구가 있다). 대화형 `/studio-join` 은 그대로.
  사람이 `studio.config.local.json` `guards.allowUnattendedEditorMcp: true` 로 열 수 있다
- `scene-files.md` 에 Unreal 절 (`.uasset` · `.umap` 은 손 편집 금지, 5.8+ 는 MCP 경로)

## 2.2.0 — 2026-11-04

**새 기능 (부)**
- **Godot MCP (Godot .NET 판 L3 에디터 자동화, 선택 설치)** — IvanMurzak/Godot-MCP (Apache-2.0)를 템플릿에 넣지 않고 점검 · 안내로 붙였다.
  `/ko-prereq` 의 Godot 묶음에 선택 항목 3개: `dotnet-sdk`(.NET 8+) · `godot-mcp-addon`(확인 후 `npx godot-cli@0.34.0 install-plugin --path`) ·
  `godot-mcp-json`(Claude Code 등록). GDScript 전용 프로젝트에서는 "GDScript 전용 — 하지 않음" 으로 이유를 밝히고 건너뛴다.
  **로컬 서버(Custom 모드)가 기본** — 상류 기본값인 ai-game.dev 클라우드 등록은 실패가 아니라 경고로 알린다. 안내: `.claude/docs/mcp-godot-guide.md`.
  실제 Godot 에디터 연결은 검증하지 않았다 (가이드에 명시)
- **`/ko-godot-doc`** — Godot 게임 코드 문서화. Godot 기여 문서(CC BY 3.0)의 원칙(아는 것만 쓴다 · 모르면 비워 두고 표시 · 이름 되풀이 금지 ·
  금지어)과 GDScript 문서 주석(`##`) 문법으로 설명을 쓰고, `.agent/tools/godot/godot_doc_audit.py` 가 빠진 공개 멤버(GD001) ·
  `class_name` 스크립트 설명(GD002) · 무효 태그(GD003) 등을 찾는다. 판정 PASS · CONCERNS · NOT ASSESSED, C# 은 "검사 안 함" 으로 보고
- **`/ko-godot-ref`** — Godot 공식 문서 근거 찾기. 엔진 레퍼런스에 없는 API 질문을 고정 버전 문서(`/en/<버전>/`, `stable` · `latest` 는 출처로
  쓰지 않음)에서 찾아 주장마다 URL 을 달고, 없으면 NOT SOURCEABLE. 설치된 에디터가 있으면 `godot --doctool` 덤프로 대조. 승인 후 레퍼런스에 보충
- **`/ko-godot-license`** — 출시 전 라이선스 고지 점검 (Godot 4.7 "Complying with licenses" 기준). `.agent/tools/godot/godot_license_check.py` 가
  엔진 MIT 고지(GL001) · 제3자 구성 요소 고지(GL002) · iOS 인데 로그뿐(GL003) · 라이선스 없는 애드온(GL004) · 파일 배포뿐(GL005)을 찾는다.
  `add` 는 `Engine.get_license_text()` · `get_copyright_info()` · `get_license_info()` 로 크레딧 화면 뼈대를 승인 후 넣는다 (반환 구조는 클래스 참조로 확인)
- `/ko-godot-doc` 2-5: 에디터 없이 `godot --headless --gdscript-docs <경로>` 로 문서가 만들어지는지 확인하는 방법
- `scene-files.md` Godot 절: Godot MCP 로 에디터가 연결돼 있으면 `.tscn` 을 손으로 고치지 않고 에디터를 거쳐 바꾼다

**설치 · 업그레이드**
- Godot 전용 자산(`.agent/tools/godot/` · `ko-godot-doc` · `ko-godot-ref` · `ko-godot-license` · `mcp-godot-guide.md`)은 Godot 프로젝트에만 설치 · `upgrade` 된다

## 2.1.0 — 2026-10-30

**새 기능 (부)**
- **출처 지문** `.agent/PROVENANCE.md` — 설치 · `upgrade` 때 이 프로젝트가 어느 템플릿 · 버전 · 커밋 · 엔진에서 왔는지 남긴다.
  라이선스(PolyForm Noncommercial)와 상업 이용 안내 위치를 함께 적는다. **외부로 아무것도 보내지 않고**(텔레메트리 아님),
  설치하는 사람 · PC 정보도 담지 않는다 — 템플릿 쪽 사실만. 지우거나 고쳐도 된다. 출처가 드러나 있어야 라이선스 준수를
  확인할 수 있다는 취지다. `upgrade` 는 지문을 새 버전으로 갱신한다

## 2.0.2 — 2026-10-30

**고침 (수)**
- `studio.py upgrade` 가 프로젝트가 고쳐 쓰는 설정 `.agent/tools/design/standard.json`(기획 검증 기준값) ·
  `.agent/tools/lint/lint.config.json`(차단 규칙)을 템플릿 판으로 교체하던 것 — 이제 깊은 병합(프로젝트 값 우선, 새 키만 추가)
- 출처 표시: `AGENTS.md` 의 아키텍트 페르소나는 Unity-SkillForge(MIT)의 `AGENT.md` 를 옮겨 고쳐 쓴 것이다 —
  `ATTRIBUTION.md` §2 · `THIRD_PARTY_LICENSES.md` §2 · `LICENSE` 머리말에 적음 (이전 기록은 원저작물로 분류했었다. MIT 고지는 이미 보존돼 있었다)
- `scripts/sync-catalog.py` 설명의 옛 진입 명령(`/mk` · `/gd` → `/ext`)과 "Unity 전용" 문구

## 2.0.1 — 2026-10-30

**고침 (수)** — 영어 Windows(cp1252)에서 드러난 인코딩 문제 (템플릿 CI 첫 실행 실패로 발견)
- 외부 명령 출력을 읽는 곳에 `encoding="utf-8"` · `errors="replace"` 지정 (artgen `command` 어댑터 · prereq · 스튜디오 git · tasklist · 테스트)
- `audio_post.py` 표준 입출력을 UTF-8 로 고정 — 부모(store · library)와 인코딩이 어긋나 한글 파일 이름에서 깨질 수 있었다 (한국어 Windows 포함)
- `gen-rule-mirrors.py` 표준 출력 UTF-8 고정
- 스튜디오 launch 테스트가 개발 PC 의 `claude` 설치에 기대던 것 — 픽스처에서 '있음' 으로 고정하고, '없으면 막는다' 는 테스트를 따로 둠 (CI 러너에는 Claude Code 가 없다)
- CI: 실패한 테스트 · 오류 줄을 주석(annotation)으로 남김, 테스트가 실패해도 나머지 검사 실행, `actions/checkout@v5` · `setup-python@v6`

## 2.0.0 — 2026-10-30

저장소 이름 · 기본 브랜치 · 설정 체계가 바뀌었다. **1.x 에서 올리는 프로젝트는 위 "기존 프로젝트 올리기" 를 따른다.**

**바뀐 것 (주)**
- **라이선스** MIT → **PolyForm Noncommercial 1.0.0** — 비상업 목적은 자유, 상업 목적은 저작권자 허락(`COMMERCIAL-LICENSE.md`). 포함된 제3자 구성 요소는 각자의 라이선스(MIT · Apache-2.0) 유지. 1.x 판은 MIT 로 남는다
- 저장소 `cozrouki/unity-fullstack-claude-skills` → `cozrouki/Make-Game-Studio`, 기본 브랜치 `main` → `master`
- 엔진 중립 재편 — Unity · Godot · Unreal. 엔진별 차이의 정본 `.claude/docs/engine-layers.md`, 엔진 판정 = `project.yaml` `engine.name` → 표지 파일
- Claude-Code-Game-Studios **v1.2.0** 동기화 — `project.yaml` 설정 체계(엔진 · 전문가 · 명명 정본), 에이전트 49(엔진 전문가 Godot · Unreal 추가),
  GS 스킬 74, `.claude/scripts/` 35, 엔진 레퍼런스(Unity 6.3 LTS · Godot 4.7 · UE 5.8), 새 훅(읽기 · 쓰기 · 레지스트리 · 산출물 검사)
- `.claude/docs/gs-*` 접두 문서 폐지 → 상류 이름 그대로 (GS 스킬 참조 11곳이 깨져 있던 것 수리). `post-compact.sh` 제거
- Unity 정적 검사는 상류 `validate-commit.sh` 대신 자체 훅 `validate-lint.sh` (엔진별 — 그 밖의 엔진은 "검사 안 함" 알림)

**새 기능 (부)**
- 설치 `install.ps1 -Engine Auto|Unity|Godot|Unreal` — Unity 전용 계층은 Unity 만, 엔진 레퍼런스는 그 엔진만, 프로젝트 데이터는 씨앗
- `/ko-setup-engine` Godot · Unreal 실측(`measure-godot.sh` · `measure-unreal.sh`), `project.yaml` 이중 쓰기
- `/ko-prereq` 엔진별 점검(Godot 실행 파일 · gdUnit4 · Unreal 에디터 · `engine.path`), artgen 엔진별 승격, 스튜디오 쓰기 영역 `ownsByEngine`
- 기획 검증 6종 `/ko-design-graph` · `/ko-design-decision` · `/ko-balance-sim` · `/ko-data-schema` · `/ko-narrative-lint` · `/ko-content-pattern` + `.agent/tools/design/`
  (eremes81/game-design-ai-practice 방법론 참고 — 원문 미포함) · 외부 카탈로그 `gdpractice` (CC BY-NC-SA, 선택 설치)
- mattpocock/skills 4종 `/ko-diagnose` · `/ko-tdd` · `/ko-grill` · `/ko-agent-retro`
- `studio.py upgrade` 가 상류 GS 자산 · 엔진 레퍼런스 · 훅 등록 · deny 권한까지 올림 (엔진 필터 · 씨앗 · 직접 병합 안내 · 사라진 파일 정리 · 템플릿 버전 기록)
- 템플릿 CI (`.github/workflows/template-tests.yml` — 도구 테스트)

**고침 (수)**
- 세션 시작 훅 출력 3,000자 상한, 세션 종료 훅 중복 기록 방지 · 월별 로그 · 3개월 보관
- 미러 생성기 glob 중괄호 펼치기 (Cursor · Windsurf · Copilot 미러 glob 깨짐)
- `sync-upstream.ps1` Windows PowerShell 5.1 · 8.3 경로 버그, `-GameStudiosOnly`
- `test-scaffold.sh` 생성 CI 기본 브랜치 `master`

## 1.0.0 — 2026-10-29 (태그 소급)

Unity 전용 마지막 상태. 2026-05-13 첫 통합부터의 누적:
- 4계층 통합 — L1 Claude-Code-Game-Studios 프로세스 스킬 · L2 Unity-SkillForge C# 패턴 · L3 MCP for Unity · L4 번들, 한국어 wrapper(`ko-*`)
- 크로스툴 8종 (Claude Code · Codex · Copilot · Cursor · Gemini · OpenCode · Windsurf · Antigravity) — 룰 · 워크플로 미러 생성
- 설치 자동화 `install.ps1`, 실측 엔진 설정 `/ko-setup-engine`, 사전 설치 `/ko-prereq`
- 그래픽 · 사운드 생성 artgen (ComfyUI · 라이브러리 · 사람 아티스트), 3세션 스튜디오 모드 + 디렉터 세션 · launch · 사용량 가드
- 외부 카탈로그 `/ext` (marketing · gamedev · android · gamedesign 선택 설치)
- 하네스 — 래칫 · 지표 · unity_lint · Unity 공식 분석기 · 쓰기 시점 가드
