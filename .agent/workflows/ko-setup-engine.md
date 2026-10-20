---
description: 엔진 설정 자동화 — 기존 Unity 프로젝트 실측으로 Technology Stack·technical-preferences.md 작성
---

# /ko-setup-engine — 실측 기반 엔진 설정

> Antigravity 워크플로. 정본 절차는 `.claude/skills/ko-setup-engine/SKILL.md` (값 도출 규칙·파일 섹션 순서는 그 파일을 따른다).
> 인수: `[코드-루트 ...]`  예) `/ko-setup-engine Assets/YourGame`

## 절차

**1. 코드 루트** — 인수 → `AGENTS.md` §6 게임 폴더 매핑 → `bash .claude/skills/ko-setup-engine/measure.sh`(인수 없이)의 후보 목록 순으로 정하고, 서드파티 폴더는 제외해 사용자에게 확인받는다.

**2. 실측** — `bash .claude/skills/ko-setup-engine/measure.sh <코드-루트...>` 리포트를 근거로 쓴다. `.cs`가 0개면 새 프로젝트이므로 엔진 기본값으로 직접 채우도록 안내하고 종료.

**3. 질문 2개** — 대상 플랫폼(현재 + 확장 예정), 목표 프레임(60/30/120).

**4. 도출** — 정본 SKILL.md Phase 4 규칙: 명명은 다수결(소수파 20% 이상이면 병기), Gamepad는 플랫폼 표, Draw Calls·Memory는 `[TO BE CONFIGURED]`, 전문가 라우팅은 UI Toolkit/uGUI 비율로 메모.

**5. 미리보기 → 승인 → 작성** — `CLAUDE.md` `## Technology Stack` + `.claude/docs/technical-preferences.md`. 기존 파일의 사람 작성 섹션(Forbidden Patterns·Allowed Libraries·ADR 로그)은 보존. `- **Engine**:` 형식 유지.

**6. 후처리** — `doc/work_log.md` 최상단에 `[<tag>] /ko-setup-engine — <엔진> · <RP> · 플랫폼 <답>` 한 줄.
