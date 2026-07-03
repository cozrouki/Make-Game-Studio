---
description: 한국어 성능 프로파일링 — 병목 진단 + SkillForge 06-performance 패턴 매칭
---

# /ko-perf-profile — 한국어 성능 프로파일링

> Antigravity 워크플로. Unity 성능 병목을 진단하고 해결 패턴을 매칭한다.
> 인수: `<scene | system | full> [게임-태그]`  예) `/ko-perf-profile system GAME1`

## 절차

**1. 범위 + 컨텍스트** — `$1`=범위, `$2`=게임 태그(옵션, 있으면 `Assets/<Game>/` 한정).

**2. 프로파일러 데이터 수집** — MCP for Unity 사용 가능하면 profiler 도구로 수집, 아니면 사용자에게 Unity Profiler 캡처 결과 paste 요청:
- CPU 프레임 시간(Main/Render/Physics/Scripts), GC 할당량·빈도, Draw call/Batch, 메모리(Managed/Native/Texture/Mesh)

**3. 병목 분석** — `.claude/skills/perf-profile/SKILL.md` 절차 + 메트릭별 의심 패턴:
- **GC 할당 多** → `gameplay-code.md` Zero-GC 위반(LINQ·string concat·new in Update)
- **Draw call 多** → 정적 batching 미적용 / Material 인스턴스 분기
- **Physics overhead** → FixedUpdate 빈도 / 비활성 Rigidbody 잔존
- **Script CPU** → GetComponent 비캐싱, 비효율 Find 호출

**4. SkillForge 패턴 추천** — 병목 유형별로 `.agent/skills/06-performance/` 카탈로그의 해당 SKILL.md 를 참조·추천:
- GC/Hot Path → `jobs-burst-optimization`, `csharp-gc-best-practices`
- 렌더/Draw call → `gpu-instancing-expert`, `lod-system`
- 메모리/텍스처 → `texture-streaming-expert`, `addressables-management`
- 프로파일링 → `profiling-analysis`

적용 방법: 해당 skill 폴더의 `SKILL.md` 를 먼저 읽고, `templates/` 의 `.cs.txt` 를 대상 경로로 복사·주입.

**5. 결과 저장** — `production/perf-reports/perf-<날짜>.md` 로 저장(사용자 승인 후).
