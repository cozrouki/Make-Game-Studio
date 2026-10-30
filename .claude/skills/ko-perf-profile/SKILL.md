---
name: ko-perf-profile
description: 성능 프로파일링 (한국어 wrapper) — Unity · Godot · Unreal 프로파일러 수치로 병목 진단 + 해결 패턴 매칭 (Unity 는 SkillForge 06-performance)
argument-hint: "<범위: scene | system | full> [게임-태그]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, mcp__UnityMCP__manage_profiler
agent: performance-analyst
---

# /ko-perf-profile — 한국어 성능 프로파일링

게임(Unity · Godot · Unreal)의 성능 병목을 진단하고 해결 패턴을 매칭합니다. Unity 는 SkillForge 카탈로그, Godot · Unreal 은 `docs/engine-reference/<engine>/` 와 엔진 전문가 에이전트가 근거입니다 (`.claude/docs/engine-layers.md`).

## 사용법

```
/ko-perf-profile scene             # 활성 씬만
/ko-perf-profile system GAME1      # 특정 게임 한정 (멀티 게임 프로젝트)
/ko-perf-profile full              # 전체 프로젝트
```

## Phase 1: 범위 + 컨텍스트

- `$1` = 범위
- `$2` = 게임 태그 (옵션) — 있으면 엔진 코드 루트(`Assets/` · `src/` · `Source/`)의 해당 게임 폴더 한정

## Phase 2: 프로파일러 데이터 수집

엔진별 수집 경로:
- **Unity**: 가능하면 MCPForUnity `manage_profiler`. 불가하면 Profiler 창 캡처를 붙여 달라고 요청
- **Godot**: Debugger > Profiler · Monitors (FPS · 프로세스 시간 · 물리 시간 · 오브젝트 수 · 드로우 콜 · 메모리) 값을 붙여 달라고 요청
- **Unreal**: `stat unit` · `stat game` · `stat rhi` 값, 또는 Unreal Insights 트레이스(`-trace=cpu,gpu,frame`) 요약을 붙여 달라고 요청

공통 지표:
- CPU 프레임 시간 (Main / Render / Physics / Scripts)
- 할당량 / 빈도 (Unity GC · Godot 오브젝트 · Unreal 메모리 증가)
- Draw call / Batch count
- 메모리 사용량 (Texture / Mesh / 스크립트 힙)

수치를 받지 못하면 "프로파일러 데이터 없음 — 정적 점검만" 이라고 보고 첫 줄에 적는다 (추정치를 측정치처럼 쓰지 않는다).

## Phase 3: 병목 분석

본 `.claude/skills/perf-profile/SKILL.md` 절차 따름. 추가:

### 메트릭별 의심 패턴
- **할당 多** → `gameplay-code.md` 핫 패스 할당 0 규칙 위반 의심. Unity: LINQ · string concat · `new` in `Update` / Godot: `_process` 의 배열 · 딕셔너리 · 문자열 생성 / Unreal: `Tick` 의 `TArray` 증가 · `FName` 생성
- **Draw call 多** → 배칭 · 인스턴싱 미적용 / 머티리얼 인스턴스 분기 (Godot MultiMesh · Unreal HISM · Nanite)
- **Physics overhead** → 물리 틱 빈도 / 잠들지 않는 강체 잔존
- **Script CPU** → 탐색 비캐싱 (Unity `GetComponent` · `Find` / Godot `get_node` / Unreal `GetAllActorsOfClass`), 필요 없는 Tick

## Phase 4: SkillForge 패턴 추천

**Unity 만** — 병목 유형별로 `.agent/skills/06-performance/` 카탈로그에서 해당 skill 추천 (Godot · Unreal 은 이 Phase 를 "카탈로그 없음 — 엔진 레퍼런스 · 전문가 에이전트로 대체" 로 보고하고 `docs/engine-reference/<engine>/modules/rendering.md` 등에서 근거를 인용한다):

- GC / Hot Path → `06-performance/jobs-burst-optimization`, `csharp-gc-best-practices`
- 렌더링 / Draw call → `06-performance/gpu-instancing-expert`, `lod-system`
- 메모리 / 텍스처 → `06-performance/texture-streaming-expert`, `addressables-management`
- 프로파일링 자체 → `06-performance/profiling-analysis`

추천 형식:
```
🔍 병목: <범주> (<수치>)
   → SkillForge: /sf-info 06-performance/<skill>
   → 적용: /sf-add 06-performance/<skill>
```

## Phase 5: 결과 저장

`production/perf-reports/perf-$(date +%Y%m%d).md` 로 저장 (사용자 승인 후).

## 관련

- 본 skill: `/perf-profile`
- 기술 부채 진단: `/tech-debt`
- SkillForge 성능 카테고리: `/sf-list 06-performance`
