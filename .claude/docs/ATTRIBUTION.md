# 출처 및 라이선스 (ATTRIBUTION)

이 통합 스킬 환경은 4개의 외부 저장소에서 자산을 차용·통합했습니다. 각 자산의 출처·라이선스·사용 유형을 명시합니다.

## 1. Claude-Code-Game-Studios (L1 프로세스)

- **저장소**: https://github.com/Donchitos/Claude-Code-Game-Studios
- **라이선스**: 상류 LICENSE 파일 (MIT 추정 — 원 저장소에서 확인 필요)
- **사용 유형**: 일부 직접 복사 + 일부 로컬 fork
- **차용 자산**:
  - 72 skills (`.claude/skills/<name>/SKILL.md`) — **직접 복사, 원본 그대로**
  - 49 → 39 agents (Godot/UE specialist 10개 제외) — **직접 복사**
  - 12 hooks 중 10개 (`session-*` 제외) — **직접 복사**
  - `session-start.sh`, `session-stop.sh` — **로컬 fork (TikiProject 한국어 톤에 머지)**
  - 11 rules 중 10개 (`gameplay-code.md` 제외) — **직접 복사**
  - `gameplay-code.md` — **로컬 fork (Tiki 기존 룰 + GS 원칙 머지)**
  - 6 docs (`gs-` prefix로 복사) — **직접 복사**
  - `settings.json` hook wiring — **로컬 fork (TikiProject 권한 + GS hook 머지)**
- **분기 정책**: hooks/settings/gameplay-code.md 는 로컬 fork 상태. 다른 모든 자산은 직접 복사 — 업스트림 변경 시 수동 sync.

## 2. Unity-SkillForge / Unity3D-AntiGravitySkills (L2 C# 코드 패턴)

- **저장소**: https://github.com/nlelouche/Unity-SkillForge
- **로컬 클론**: `D:\works\projects\github\Unity3D-AntiGravitySkills\`
- **라이선스**: MIT (상류 LICENSE 확인 — 미발견 시 클론 디렉토리에서 검증 필요)
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

## 통합 시점

- **Phase 1-2 완료**: 2026-05-13
- **Phase 3-5 완료**: 2026-05-13

## 라이선스 의무 이행

- 각 상류 저장소의 LICENSE 파일을 보존하는 것이 권장됨:
  - Game-Studios: 본 미러는 복사된 파일 일부만 포함 — LICENSE는 상류 참조
  - SkillForge: `.agent/skills/LICENSE` 가 상류에 있으면 미러에 포함 (확인 필요)
  - MCPForUnity: UPM 패키지로 설치되므로 패키지 내부에 라이선스 포함

LICENSE 누락이 발견되면 다음 sync 사이클에 포함시킬 것.

## 변경 이력

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-05-13 | 최초 통합 — 4개 저장소 흡수, 5 Phase 완료 | Phase 1-5 모두 적용 |
