---
description: 게임 개발 풀스택 통합 진입점 (Unity · Godot · Unreal) — 4계층(프로세스·코드패턴·에디터·번들) 안내
---

# /unity-fullstack — 게임 개발 풀스택 진입점 (Antigravity)

> 무엇을 할지 알려주시면 적절한 계층으로 안내합니다. (도구 중립 정본은 `AGENTS.md`)
> 엔진별 차이(코드 루트 · 테스트 · 자동화 · 정적 검사 · 카탈로그)는 `.claude/docs/engine-layers.md`. L2 · L3 는 Unity 전용이다.

## 4계층 매핑 (Antigravity 기준)

| 계층 | 다루는 일 | Antigravity 진입 |
|---|---|---|
| **L1 프로세스** | 스프린트·스토리·리뷰·성능·프로토타입 | 워크플로 슬래시: `/ko-sprint-plan`, `/ko-story-cycle`, `/ko-code-review`, `/ko-perf-profile`, `/ko-prototype`, `/ko-setup-engine`, `/ko-art-gen` |
| **L2 C# 코드 패턴** (Unity 전용) | FSM·인벤토리·능력·Jobs/Burst 등 102개 | `.agent/skills/<카테고리>/<skill>/SKILL.md` 읽고 `templates/` 복사·주입 |
| **L3 Editor 자동화** | 씬·프리팹·빌드 조작 | Unity: MCP for Unity 도구 (`.mcp.json` 설정 시) · Godot · Unreal: `.claude/docs/engine-layers.md` 의 명령줄 경로 |
| **L4 룰/표준** | 자동 적용 코딩 규칙 | `.agent/rules/*.md` (glob 자동적용) |

## 인수 없이 호출된 경우 — 사용자에게 질문

1. 지금 무엇을 하고 싶은가요?
   - (a) 기능 구현 → L1 `/ko-story-cycle` + L2 코드 패턴 참조
   - (b) 시스템 패턴 찾기 → L2 `.agent/skills/` 카탈로그
   - (c) 성능 문제 진단 → `/ko-perf-profile`
   - (d) 새 컨셉 프로토타입 → `/ko-prototype`
   - (e) 스프린트/계획 관리 → `/ko-sprint-plan`, `/sprint-status`
   - (f) 기획대로 그래픽 생성 → `/ko-art-gen`

## 자주 쓰는 작업
- **새 기능 구현 사이클**: `/ko-story-cycle <스토리-id>`
- **성능 진단**: `/ko-perf-profile <범위>` + `.agent/skills/06-performance/` 카탈로그
- **새 게임 온보딩**: 게임 태그 결정(`AGENTS.md` §6 매핑) → 어셈블리 구조 설계
- **엔진 설정 (최초 1회)**: `/ko-setup-engine` — 프로젝트 실측으로 Technology Stack·`technical-preferences.md` 작성
- **그래픽 생성**: 아트 바이블 → 에셋 스펙 → `/ko-art-gen <ASSET-NNN | spec:<target> | next>` (`.agent/tools/artgen/README.md`)
