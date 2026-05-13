---
name: ko-perf-profile
description: 성능 프로파일링 (한국어 wrapper) — SkillForge 06-performance 카탈로그 연계
argument-hint: "<범위: scene | system | full> [게임-태그]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, mcp__UnityMCP__manage_profiler
agent: performance-analyst
---

# /ko-perf-profile — 한국어 성능 프로파일링

Unity 게임의 성능 병목을 진단하고 SkillForge 카탈로그의 해결 패턴을 매칭합니다.

## 사용법

```
/ko-perf-profile scene             # 활성 씬만
/ko-perf-profile system KC         # KickleCubicle 게임 한정
/ko-perf-profile full              # 전체 프로젝트
```

## Phase 1: 범위 + 컨텍스트

- `$1` = 범위
- `$2` = 게임 태그 (옵션) — 있으면 해당 `Assets/<Game>/` 한정

## Phase 2: 프로파일러 데이터 수집

가능하면 MCPForUnity `manage_profiler` 사용:
- CPU 프레임 시간 (Main / Render / Physics / Scripts)
- GC 할당량 / 빈도
- Draw call / Batch count
- 메모리 사용량 (Managed / Native / Texture / Mesh)

MCP 사용 불가하면 사용자에게 Profiler 캡처 안내 후 결과 paste 요청.

## Phase 3: 병목 분석

본 `.claude/skills/perf-profile/SKILL.md` 절차 따름. 추가:

### 메트릭별 의심 패턴
- **GC 할당 多** → `gameplay-code.md` Zero-GC 룰 위반 의심. LINQ, string concat, new in Update 점검
- **Draw call 多** → 정적 batching 미적용 / Material 인스턴스 분기
- **Physics overhead** → FixedUpdate 빈도 / 비활성 Rigidbody 잔존
- **Script CPU** → `GetComponent` 비캐싱, 비효율적 Find 호출

## Phase 4: SkillForge 패턴 추천

병목 유형별로 `.agent/skills/06-performance/` 카탈로그에서 해당 skill 추천:

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
