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
