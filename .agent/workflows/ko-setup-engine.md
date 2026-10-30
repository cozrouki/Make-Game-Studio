---
description: 엔진 설정 자동화 — 기존 Unity · Godot · Unreal 프로젝트 실측으로 project.yaml · technical-preferences.md · Technology Stack 작성
---

# /ko-setup-engine — 실측 기반 엔진 설정

> Antigravity 워크플로. 정본 절차는 `.claude/skills/ko-setup-engine/SKILL.md` (값 도출 규칙·파일 섹션 순서는 그 파일을 따른다).
> 인수: `[코드-루트 ...]`  예) `/ko-setup-engine Assets/YourGame` · `/ko-setup-engine src` · `/ko-setup-engine Source/MyGame`

## 절차

**0. 엔진 판정** — `ProjectSettings/ProjectVersion.txt` → Unity · `project.godot` → Godot · `*.uproject` → Unreal. 하나도 없으면 새 프로젝트이므로 `/setup-engine` 을 안내하고 종료. 측정 스크립트: Unity `measure.sh` · Godot `measure-godot.sh` · Unreal `measure-unreal.sh` (모두 `.claude/skills/ko-setup-engine/`).

**1. 코드 루트** — 인수 → `AGENTS.md` §6 게임 폴더 매핑 → 측정 스크립트(인수 없이)의 후보 목록 순으로 정하고, 서드파티 폴더(`Plugins` · `ThirdParty` · `addons`)는 제외해 사용자에게 확인받는다.

**2. 실측** — `bash .claude/skills/ko-setup-engine/<측정 스크립트> <코드-루트...>` 리포트를 근거로 쓴다. 리포트의 "측정 안 함" 절은 미리보기에 그대로 옮긴다.

**3. 질문** — 대상 플랫폼(현재 + 확장 예정), 목표 프레임(60/30/120). Godot 2D/3D 근거가 엇갈리거나 Unreal C++ 가 거의 없을 때만 추가 질문.

**4. 도출** — 정본 SKILL.md Phase 4 규칙 (공통 + 엔진별 절): 명명은 다수결(소수파 20% 이상이면 병기), Gamepad 는 플랫폼 표, Draw Calls·Memory 는 `[TO BE CONFIGURED]`, 전문가는 `.claude/skills/setup-engine/references/5.5-project-yaml.md` 표에서 실측으로 줄만 뺀다.

**5. 미리보기 → 승인 → 작성** — `project.yaml`(정본 — 5.5.2 · 5.5.3 절차) + `.claude/docs/technical-preferences.md` + `CLAUDE.md` `## Technology Stack` · `ENGINE-REFERENCE-IMPORT` 줄. 기존 파일의 사람 작성 섹션(Forbidden Patterns·Allowed Libraries·ADR 로그)은 보존. `- **Engine**:` 형식 유지.

**6. 후처리** — `doc/work_log.md` 최상단에 `[<tag>] /ko-setup-engine — <엔진 버전> · <렌더러> · 플랫폼 <답>` 한 줄.
