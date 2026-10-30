# 출처 및 라이선스 (ATTRIBUTION)

이 통합 스킬 환경은 4개의 외부 저장소에서 자산을 차용·통합했습니다. 각 자산의 출처·라이선스·사용 유형을 명시합니다.

## 1. Claude-Code-Game-Studios (L1 프로세스)

- **저장소**: https://github.com/Donchitos/Claude-Code-Game-Studios
- **라이선스**: **MIT** ✅ (2026-07-20 GitHub API 확인 — `Copyright (c) 2026 Donchitos`). 고지는 `THIRD_PARTY_LICENSES.md`에 보존.
- **기준 버전**: **v1.2.0** (2026-10-19, 커밋 `05ad7c8`) — 2026-10-30 동기화
- **사용 유형**: 대부분 직접 복사 + 일부 로컬 fork
- **차용 자산**:
  - 74 skills (`.claude/skills/<name>/`) — **직접 복사, 원본 그대로** (11-game-design 겹침 7개에 한국어 안내 한 줄만 삽입)
  - 49 agents — **직접 복사** (엔진 전문가 Unity 5 · Godot 5 · Unreal 5 포함 — 엔진 중립화로 Godot/UE 제외를 없앴다)
  - hooks 18개 중 16개 — **직접 복사** (`session-start.sh` · `session-stop.sh` 는 fork). 상류에서 사라진 `post-compact.sh` 는 지웠다
  - 14 rules 중 13개 — **직접 복사** (`gameplay-code.md` 는 fork)
  - `.claude/docs/` 전부 (templates · director-gates · hooks-reference 포함) — **직접 복사, 상류 이름 그대로** (예전 `gs-` 접두 복사는 GS 스킬의 참조 경로를 깨뜨려 폐지)
  - `.claude/scripts/` 35개 · `docs/engine-reference/` (Unity · Godot · Unreal) · `docs/*.md` · `design/CLAUDE.md` · `src/CLAUDE.md` · `studio-tests/` — **직접 복사**
  - `project.yaml` · `docs/registry/` · `docs/architecture/tr-registry.yaml` · `design/registry/` — **씨앗 복사** (없을 때만)
  - `session-start.sh`, `session-stop.sh` — **로컬 fork** (한국어 출력 · STATUS 블록 + 상류 판정 · 해시 중복 방지 병합)
  - `gameplay-code.md` — **로컬 fork** (한국어 공통 규칙 + Unity · Godot · Unreal 절)
  - `settings.json` · `statusline.sh` — **로컬 fork** (권한 + 상류 v1.2.0 훅 등록 병합 + 스튜디오 · validate-lint)
- **분기 정책**: fork 5개(`scripts/sync-upstream.ps1` `$forkFiles`)는 상류 `CHANGELOG.md` · `UPGRADING.md` 를 보고 손으로 반영. 나머지는 `sync-upstream.ps1 -GameStudiosOnly` 로 미러. unity_lint 연동은 상류 `validate-commit.sh` 를 고치지 않고 자체 훅 `validate-lint.sh` 로 분리했다.

## 2. Unity-SkillForge / Unity3D-AntiGravitySkills (L2 C# 코드 패턴)

- **저장소**: https://github.com/nlelouche/Unity-SkillForge
- **로컬 클론**: 임의 위치 (sync 스크립트 기본값 = 이 패키지 저장소의 형제 폴더 `..\Unity3D-AntiGravitySkills\`)
- **라이선스**: **MIT** ✅ (2026-07-20 GitHub API 확인 — `Copyright (c) 2025 AntiGravity Contributors`). 고지는 `THIRD_PARTY_LICENSES.md`에 보존.
- **사용 유형**: **정적 미러 (오프라인 복사)**
- **차용 자산**:
  - `.agent/skills/` 하위 102개 SKILL.md + templates/ — **직접 미러**
  - `skills-index.json` — **직접 복사**
- **분기 정책**: 미러 디렉토리(`.agent/skills/`) **수정 금지**. 한국어 customization은 `.claude/skills/ko-*/` 또는 `.claude/skills/sf-*/` 에. 동기화 절차는 `.agent/skills/README-sync.md` 참조.

## 3. Unity-Skills / Besty0728 (L3 보조 카탈로그 — 옵션)

- **저장소**: https://github.com/Besty0728/Unity-Skills
- **라이선스**: 상류 LICENSE 확인 필요
- **사용 유형**: **참조 URL만 (현재 미설치)**
- **차용 자산**:
  - 본 통합 환경은 Unity-Skills의 REST API 서버를 사용하지 **않음**.
  - 714 skill의 도메인 지식은 필요 시 외부 URL로 참조 (`https://github.com/Besty0728/Unity-Skills/tree/master/SkillsForUnity/unity-skills~/skills`).
  - 사용자가 원할 경우 별도 clone + `.claude/docs/unity-skills-catalog/` 로 미러 가능 (현재는 미수행).
- **분기 정책**: 미설치 상태 — 미래 통합 옵션.

## 4. Antigravity-Awesome-Skills / sickn33 (L4 패키징 포맷)

- **저장소**: https://github.com/sickn33/antigravity-awesome-skills
- **라이선스**: 상류 LICENSE 확인 필요
- **사용 유형**: **포맷 차용만 (skill 콘텐츠는 미사용)**
- **차용 자산**:
  - `data/bundles.json` / `data/workflows.json` 의 **스키마 구조**를 참조해 `.claude/data/` 작성
  - 1,453 skill 카탈로그 콘텐츠는 **미사용** (게임 도메인이 아니므로)
- **분기 정책**: 포맷만 차용 — 콘텐츠 동기화 불필요.

## 5. MCPForUnity (L3 Editor 실행 백엔드)

- **저장소**: https://github.com/CoplayDev/unity-mcp
- **라이선스**: MIT
- **사용 유형**: **외부 패키지 설치 (Packages/manifest.json 의존)**
- **차용 자산**:
  - Unity Editor 에 UPM 패키지로 설치됨 (`com.coplaydev.unity-mcp`)
  - MCP 도구 사용 가이드를 `.claude/docs/mcp-unity-guide.md` 에 작성
- **분기 정책**: 패키지 자체는 `Packages/manifest.json` 의 URL로 관리. 본 통합 환경은 사용 가이드만 작성.

## 6. marketingskills / coreyhaines31 (외부 카탈로그 `marketing`)

- **저장소**: https://github.com/coreyhaines31/marketingskills
- **라이선스**: MIT (Copyright (c) 2025 Corey Haines) — `.agent/marketing/LICENSE` 동봉
- **사용 유형**: **카탈로그 미러** (`.agent/marketing/`, `.claude/skills/` 에 넣지 않음 — `/ext` 가 필요할 때 로드)
- **미러 범위**: `skills/*` 52개 (평가 데이터 `evals/` 제외), `tools/*.md` · `tools/integrations/*.md` · `tools/composio/*.md` · `tools/aisa/*.md`. **제외**: 외부 API CLI `tools/clis/*.js` 66개
- **로컬 추가**: 한국어 요약 · 그룹 · 게임 적합도 `.agent/catalogs/marketing.ko.json`
- **분기 정책**: 원문 수정 없음. `scripts/sync-catalog.py marketing` 으로 재미러

## 7. awesome-gamedev-agent-skills / gamedev-skills (외부 카탈로그 `gamedev`)

- **저장소**: https://github.com/gamedev-skills/awesome-gamedev-agent-skills
- **라이선스**: Apache-2.0 (Copyright 2026 Abhishek Barali and contributors) — `.agent/gamedev/LICENSE` · `NOTICE` 동봉
- **사용 유형**: **카탈로그 미러** (`.agent/gamedev/`)
- **미러 범위**: `skills/{disciplines,genres,unity,workflows}/*` 36개. **제외**: Godot · Unreal · Roblox · 웹 엔진 전용 39개, `router/`, 저장소 스크립트 · 테스트 (템플릿이 Unity 전용 — Game-Studios Godot/UE 에이전트 제외와 같은 정책)
- **로컬 추가**: `.agent/catalogs/gamedev.ko.json`. 원문 수정 없음 (Apache-2.0 §4 — 변경 고지 대상 아님)

## 7-1. android/skills / Google (외부 카탈로그 `android`)

- **저장소**: https://github.com/android/skills
- **라이선스**: Apache-2.0 (Google LLC) — `.agent/android/LICENSE.txt` 동봉 (업스트림에 NOTICE 없음)
- **사용 유형**: **카탈로그 미러** (`.agent/android/`, 약 0.5MB — `studio upgrade` 범위에 포함)
- **미러 범위**: `profilers/android-profiler` · `play/play-policy-insights` · `performance/anr-audit-and-fix` · `performance/r8-analyzer` 4개. **제외**: Compose · Navigation · Wear · TV · Cars · CameraX · Media3 · device-ai · xr 등 네이티브 앱 전용 (Unity Android 빌드에 통하는 기기 · 스토어 단만)
- **로컬 추가**: `.agent/catalogs/android.ko.json`. 원문 수정 없음. 대상 플랫폼에 Android 가 있을 때만 쓴다 (`prereq.py` [Android] 묶음 · dev 헌장 스킬 사용 맵)

## 7-2. andrej-karpathy-skills / multica-ai (지침 차용)

- **저장소**: https://github.com/multica-ai/andrej-karpathy-skills
- **라이선스**: MIT
- **사용 유형**: **지침 재작성** — 파일을 복사하지 않고, 4원칙(생각 먼저 · 단순함 · 수술적 변경 · 목표 중심)을 `AGENTS.md` §3-1 로 한국어로 다시 쓰고 §1 · §3 과 충돌하지 않게 범위를 조정했다 (분리 원칙은 시스템 경계에만). `/ko-code-review` 점검 항목 · dev 헌장 작업 태스크(`가정:` · `발견:`)에 연결

## 7-3. Microsoft.Unity.Analyzers (참조 · 사용자 설치)

- **저장소**: https://github.com/microsoft/Microsoft.Unity.Analyzers — NuGet `Microsoft.Unity.Analyzers`
- **라이선스**: MIT
- **사용 유형**: **재배포하지 않음.** `prereq.py install unity-analyzers` 가 NuGet 에서 고정 버전(1.28.0, SHA256 확인)을 받아 대상 프로젝트 `Assets/Analyzers/` 에 둔다. 템플릿에는 규칙 심각도 파일(`.agent/tools/lint/Default.ruleset`, 자체 작성)만 있다. 2026-10-29 Unity 6000.3.24f1 에서 UNT 경고 출력 확인

## 7-4. mattpocock/skills (엔지니어링 스킬 차용)

- **저장소**: https://github.com/mattpocock/skills
- **라이선스**: MIT (`Copyright (c) 2026 Matt Pocock`). 고지는 `THIRD_PARTY_LICENSES.md` 에 보존
- **사용 유형**: **번역 · Unity 맞춤 재작성** — 원문 구조를 따르되 한국어로 옮기고 Unity 테스트(EditMode/PlayMode, MCP `run_tests` · `read_console` · `manage_profiler`) · 이 템플릿 파일 구조에 맞췄다
  - `diagnosing-bugs` → `.claude/skills/ko-diagnose/`
  - `grilling` + `grill-me` → `.claude/skills/ko-grill/`
  - `tdd` (+ `tests.md` · `mocking.md` 를 C# 예시로 합침) → `.claude/skills/ko-tdd/`
  - `retro` + `writing-for-agents` → `.claude/skills/ko-agent-retro/` (`WRITING.md`)
- **들이지 않은 것**: 이슈 트래커 전제 스킬(`to-spec` · `to-tickets` · `triage` · `wayfinder` · `implement*`)은 GS 파이프라인 · 스튜디오 티켓과 겹치고, `code-review` · `prototype` 은 기존 스킬과 이름이 겹쳐 제외. 플러그인 설치(`mattpocock-skills`)는 이름 충돌 때문에 권하지 않는다

## 8. game-design-skills-bundle / Stanestane (외부 카탈로그 `gamedesign` — **미포함**)

- **저장소**: https://github.com/Stanestane/game-design-skills-bundle
- **라이선스**: **PolyForm Noncommercial 1.0.0** (Required Notice: Copyright Stanislav Stankovic, https://www.stane-island.net/). 상업 사용 · 재배포 · 재패키징은 작성자의 상업 라이선스 필요 (`COMMERCIAL-LICENSE.md` — 구매해도 재배포 권리 없음)
- **사용 유형**: **참조 · 선택 설치만.** 템플릿에 파일을 포함하지 않는다. 사용자가 `scripts/sync-catalog.py gamedesign --fetch --accept-license <noncommercial|commercial>` 로 직접 받고, `.agent/gamedesign/` 은 `.gitignore` 대상이다 (`install.ps1` 은 git 추적 파일만 복사하므로 다른 프로젝트로도 퍼지지 않는다)
- **로컬 추가**: `.agent/catalogs/gamedesign.ko.json` — 스킬 이름과 용도를 로컬에서 짧게 설명한 것 (원문 번역 · 복제 아님)

## 통합 시점

- **Phase 1-2 완료**: 2026-05-13
- **Phase 3-5 완료**: 2026-05-13

## 라이선스 의무 이행 (2026-07-20 완료)

- **재배포 대상(콘텐츠 번들) 2종 모두 MIT 확인** → 저작권+허가 고지 보존 의무를 루트 `THIRD_PARTY_LICENSES.md`에 이행:
  - Game-Studios (L1): MIT — 고지 포함 ✅
  - SkillForge (L2): MIT — 고지 포함 ✅
- **미재배포(설치/참조만)**: MCPForUnity(UPM 설치, 패키지 내부 라이선스), Besty0728(미설치), sickn33(포맷만) — 재배포 의무 없음, 크레딧만 표기.
- 저장소 자체 원저작물(통합 레이어·wrapper·스크립트·문서)은 루트 `LICENSE`(MIT).

## 변경 이력

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-05-13 | 최초 통합 — 4개 저장소 흡수, 5 Phase 완료 | Phase 1-5 모두 적용 |
| 2026-07-20 | 라이선스 4종 GitHub API 확인(전부 MIT), 루트 `LICENSE` + `THIRD_PARTY_LICENSES.md` 신설, 영문 README 헤더 추가 | 공개 준비 |
| 2026-10-30 | Game-Studios v1.2.0 동기화 + 엔진 중립 재편 (Unity · Godot · Unreal): 에이전트 49 · 스킬 74 · scripts · 엔진 레퍼런스 · `project.yaml`, `gs-*` 문서 폐지, `engine-layers.md` · `validate-lint.sh` · Godot/Unreal 측정 스크립트 · 엔진별 prereq · artgen 승격 · 스튜디오 쓰기 영역 | `scripts/sync-upstream.ps1` 갱신 |
| 2026-10-30 | mattpocock/skills (MIT) 4종 번역 · Unity 맞춤: `ko-diagnose` · `ko-grill` · `ko-tdd` · `ko-agent-retro` | `THIRD_PARTY_LICENSES.md` §9 |
| 2026-10-23 | 외부 카탈로그 3종: marketingskills (MIT, 포함) · awesome-gamedev-agent-skills (Apache-2.0, Unity 관련만 포함) · game-design-skills-bundle (PolyForm NC, 미포함 — 선택 설치). `/ext` 진입 스킬 · `scripts/sync-catalog.py` | 라이선스는 각 저장소 LICENSE 원문으로 확인 |
