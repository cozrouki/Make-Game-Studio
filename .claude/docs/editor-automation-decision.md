# Editor 자동화 / 코드 패턴 / 문서 — 결정 매트릭스

작업을 하려고 할 때 **어느 백엔드를 써야 할지** 빠르게 결정하는 가이드.

## 4계층 요약

| 계층 | 무엇 | 어디 | 진입 |
|---|---|---|---|
| **L1 프로세스** | 스프린트·리뷰·게이트·릴리스 | `.claude/skills/` (Game-Studios 72 + ko-* 5 + master 1) | `/ko-sprint-plan`, `/ko-code-review`, `/unity-fullstack process` |
| **L2 C# 패턴** | FSM·인벤토리·능력·Job System 등 102개 | `.agent/skills/<카테고리>/<스킬>/` (SkillForge 미러) | `/sf-list`, `/sf-info`, `/sf-add` |
| **L3 Editor 자동화** | 씬·프리팹·빌드·콘솔 등 실시간 조작 | MCPForUnity (35+ 도구) | `mcp__UnityMCP__*` |
| **L3 보조 카탈로그** | Cinemachine/ShaderGraph/XR 등 도메인 지식 (옵션) | `.claude/docs/unity-skills-catalog/` (미설치) | 외부 URL: github.com/Besty0728/Unity-Skills |
| **L4 패키징** | 번들·워크플로 정의 | `.claude/data/` | `.claude/data/bundles.json`, `workflows.json` |

## 의사결정 매트릭스

### 질문 1: 무엇을 하려고 하는가?

| 의도 | 가야 할 곳 | 첫 명령 |
|---|---|---|
| **씬에 GameObject를 추가/변경** | L3 MCPForUnity | `mcp__UnityMCP__manage_gameobject` |
| **컴포넌트 속성 일괄 변경** | L3 MCPForUnity | `mcp__UnityMCP__batch_execute` |
| **빌드 트리거** | L3 MCPForUnity | `mcp__UnityMCP__manage_build` |
| **Profiler 데이터 수집** | L3 MCPForUnity | `mcp__UnityMCP__manage_profiler` |
| **콘솔 에러 확인** | L3 MCPForUnity | `mcp__UnityMCP__read_console` |
| **시스템 설계 (전투, AI, 인벤토리 등)** | L2 SkillForge | `/sf-list 02-gameplay` |
| **아키텍처 패턴 (FSM, MVVM, DI)** | L2 SkillForge | `/sf-list 01-architecture` |
| **성능 최적화 (Jobs, GPU instancing)** | L2 SkillForge | `/sf-list 06-performance` |
| **UI Toolkit / 입력 / 접근성** | L2 SkillForge | `/sf-list 05-ui-ux` |
| **빌드 파이프라인 / CI** | L2 SkillForge or L1 | `/sf-list 09-devops-automation` 또는 `/release-checklist` |
| **스토리 / 스프린트 진행** | L1 Game-Studios | `/ko-story-cycle <id>` |
| **코드 리뷰** | L1 Game-Studios | `/ko-code-review <PR>` |
| **버그 트리아지** | L1 Game-Studios | `/bug-triage` |
| **새 게임 컨셉 시작** | L1 Game-Studios | `/onboard` 또는 `/ko-prototype` |
| **번들 단위로 묶어서 보기** | L4 | `.claude/data/bundles.json` 읽기 |

### 질문 2: L2 코드 패턴이 필요한 경우 — 어느 카테고리?

| 도메인 | 카테고리 |
|---|---|
| 캐릭터 컨트롤, 점프, 이동 | `02-gameplay/advanced-character-controller` |
| 능력 시스템 (마법, 스킬, 쿨다운) | `02-gameplay/ability-skill-system` |
| 인벤토리, 제작, 아이템 | `02-gameplay/inventory-crafting-logic` |
| 버프/디버프, 상태 효과 | `02-gameplay/status-effect-system` |
| 대화, 퀘스트 | `02-gameplay/dialogue-quest-system` |
| 리플레이, 결정론 입력 | `02-gameplay/replay-system` |
| Player + NPC 통합 에이전트 | `02-gameplay/unified-agent-controller` |
| 물리, Rigidbody, Raycast | `02-gameplay/physics-logic` |
| SOLID, GoF 패턴 | `01-architecture/advanced-design-patterns` |
| ScriptableObject 아키텍처 | `01-architecture/scriptableobject-architecture` |
| 인터페이스 기반 모듈성 | `01-architecture/interface-driven-development` |
| GPU 인스턴싱, 대량 메시 | `06-performance/gpu-instancing-expert` |
| Jobs + Burst | `06-performance/job-system-burst` |
| LOD, 오클루전 | `06-performance/lod-occlusion-culling` |
| 커스텀 에디터, 인스펙터 | `07-tools-pipeline/custom-editor-scripting` |
| 에이전트 코드 리뷰 자동화 | `07-tools-pipeline/ai-code-reviewer` |
| 프로젝트 환경 자동 감지 | `07-tools-pipeline/context-discovery-agent` |
| Cinemachine 카메라 | `04-visuals-audio/cinemachine-specialist` |
| 오디오 시스템 | `04-visuals-audio/audio-soundscape-architect` |
| 라이팅·포스트프로세싱 | `04-visuals-audio/lighting-post-processing` |
| 게임 피드백·주스 | `04-visuals-audio/juice-game-feel` |
| UI Toolkit + MVVM | `05-ui-ux/ui-toolkit-architect-legacy` |
| 새 Input System | `05-ui-ux/input-system-new` |
| 접근성 (WCAG, 색맹) | `05-ui-ux/accessibility-hci` |
| 반응형 UI | `05-ui-ux/responsive-ui-design` |
| PlayFab Economy | `08-backend-monetization/playfab-economy-v2` |
| 분석·히트맵 | `08-backend-monetization/analytics-heatmaps` |
| 광고 미디에이션 | `08-backend-monetization/ads-mediation-ironsource` |
| 빌드 자동화 CLI | `09-devops-automation/unity-build-commander` 또는 `build-pipeline-manager` |

전체 목록: `/sf-list` 또는 `.agent/skills/skills-index.json`

### 질문 3: 둘 이상이 필요할 때 (예: "성능 문제 + 적 AI 일괄 변경")

조합 원칙:

1. **먼저 L1 워크플로**로 컨텍스트 정리 → `/ko-perf-profile system` 또는 `/code-review`
2. **L2에서 패턴 식별** → `/sf-info <skill>` 로 적용 가능한 코드 패턴 확인
3. **L3로 실제 변경** → MCP 도구로 Editor 조작 (씬 변경, 컴포넌트 수정, 빌드)
4. **L1로 사이클 종료** → `/story-done` 또는 `/sprint-status`

## 안티 패턴

| 하지 말 것 | 이유 | 대안 |
|---|---|---|
| Editor 작업을 채팅으로 수동 지시 | 비효율, 휴먼 에러 | MCPForUnity 도구 사용 |
| SkillForge SKILL.md를 그대로 수정 | 업스트림과 분기 | `.claude/skills/ko-*/` 에 wrapper |
| C# 코드 패턴을 그때그때 새로 작성 | "Vibe Coding" 회피 | `/sf-list` 먼저 확인 |
| 같은 작업을 매 세션마다 반복 | 워크플로 미정의 | `.claude/data/workflows.json` 에 등록 |
| 게임 간 직접 참조 | Assembly 의존 역전 | `<SharedModule>` 경유, `gameplay-code.md` 룰 확인 |

## 관련 문서

- MCP 도구 상세: `.claude/docs/mcp-unity-guide.md`
- 코딩 표준: `.claude/rules/gameplay-code.md`, `.claude/docs/gs-coding-standards.md`
- 문서 작성 기준: `.claude/rules/doc-writing.md`
- 번들 / 워크플로: `.claude/data/bundles.json`, `workflows.json`
- SkillForge 동기화: `.agent/skills/README-sync.md`
- 마스터 진입: `/unity-fullstack`
