---
name: unity-fullstack
description: Unity 풀스택 통합 진입점 — L1 프로세스 / L2 코드 패턴 / L3 에디터 자동화 / L4 번들 안내
argument-hint: "[layer] — 선택값: process | code | editor | bundle"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion
---

# /unity-fullstack — Unity 풀스택 통합 진입점

Unity 풀스택 4계층 스킬 셋입니다. 무엇을 할지 알려주시면 적절한 레이어로 안내합니다.

## 레이어 선택

| 인수 | 레이어 | 다루는 일 | 자주 쓰는 진입 |
|---|---|---|---|
| `process` | **L1** 워크플로 (Game-Studios) | 스프린트·리뷰·게이트·릴리스 | `/ko-sprint-plan`, `/ko-code-review`, `/sprint-status` |
| `code` | **L2** C# 코드 패턴 (SkillForge) | FSM·인벤토리·능력·Job System | `/sf-list <카테고리>`, `/sf-info <skill>`, `/sf-add <skill>` |
| `editor` | **L3** Editor 자동화 | 씬·프리팹·빌드 자동 조작 | `mcp__UnityMCP__*` 도구, `.claude/docs/mcp-unity-guide.md` |
| `bundle` | **L4** 번들·워크플로 | 카테고리화된 작업 묶음 안내 | `.claude/data/bundles.json`, `workflows.json` |

## 인수 없이 호출된 경우

다음 질문을 사용자에게 합니다 (한국어):

1. **지금 무엇을 하고 싶은가요?**
   - (a) 기능 구현 → process + code
   - (b) 시스템 패턴 찾기 → code
   - (c) 에디터 조작 → editor
   - (d) 프로세스/계획 관리 → process
   - (f) 기획 의도대로 그래픽 생성 → `/ko-art-gen`
   - (g) 3세션 자동 개발 (디렉터 모드) → `/studio-join <planning|art|dev>` 각 세션 + `/studio-status`
   - (e) 어디부터 시작할지 모르겠다 → 아래 "자주 쓰는 작업" 안내

## 자주 쓰는 작업

- **새 기능 구현 사이클**: `/ko-story-cycle <스토리-id>` (L1 process) + `/sf-info <관련-skill>` (L2 code 참조)
- **성능 문제 진단**: `/ko-perf-profile <범위>` + `.agent/skills/06-performance/` 카탈로그
- **씬·에셋 자동화**: MCPForUnity 도구 (`.claude/docs/mcp-unity-guide.md` 참조)
- **새 게임 온보딩**: `/onboard` → `/start` → 게임 태그 결정 (프로젝트 `CLAUDE.md`의 게임 폴더 매핑 표 참조)
- **엔진 설정 (최초 1회)**: 기존 코드가 있으면 `/ko-setup-engine` (실측), 새 프로젝트면 `/setup-engine` — Technology Stack·`technical-preferences.md`를 채워 전문가 에이전트 라우팅을 켬
- **프로토타입 만들기**: `/ko-prototype <게임-태그> <컨셉>`
- **기획대로 그래픽 생성**: `/art-bible` → `/asset-spec system:<이름>` → `/ko-art-gen <ASSET-NNN | spec:<target> | next>` (백엔드 중립 — `.agent/tools/artgen/README.md`)
- **3세션 자동 개발 (스튜디오 모드)**: 터미널 3개에서 `/studio-join planning|art|dev` → `/studio-ticket planning "컨셉: …"` → `/studio-status` 로 게이트 승인 (`.agent/tools/studio/README.md`)

## 관련 문서

- 결정 매트릭스: `.claude/docs/editor-automation-decision.md` (Phase 4에서 작성)
- 번들·워크플로: `.claude/data/bundles.json`, `.claude/data/workflows.json` (Phase 5에서 작성)
- 룰: `.claude/rules/gameplay-code.md`, `doc-writing.md`
- GS 참조 문서: `.claude/docs/gs-*.md`

## Phase N: 사용자 의도 파악

1. argument-hint의 `[layer]`가 전달되면 → 해당 행의 자주 쓰는 진입 명령을 보여주고 사용자에게 다음 행동을 묻는다.
2. 인수 없으면 → 위 "인수 없이 호출된 경우"의 질문을 AskUserQuestion으로 제시.
3. 사용자 답변에 따라 적절한 슬래시 커맨드(`/ko-*`, `/sf-*`) 또는 MCP 도구로 라우팅.
