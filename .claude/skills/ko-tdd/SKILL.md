---
name: ko-tdd
description: 테스트 주도 개발 (한국어) — 합의한 접점(seam)에서 red → green 을 수직 조각 하나씩 반복. 기능 · 버그 수정을 테스트 먼저 하거나 "TDD", "red-green", 단위 · 통합 테스트를 원할 때
argument-hint: "<구현할 기능 또는 고칠 버그> [게임-태그]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, mcp__UnityMCP__run_tests, mcp__UnityMCP__read_console
---

# /ko-tdd — 테스트 주도 개발

> 출처: mattpocock/skills `tdd` (MIT) 를 게임 엔진(Unity NUnit · Godot gdUnit4 · Unreal Automation)용으로 옮기고 조정했다 — `.claude/docs/ATTRIBUTION.md`.

TDD 는 red → green 루프다. 이 스킬은 그 루프가 **남길 가치가 있는 테스트**를 만들게 하는 기준이다: 좋은 테스트란 무엇인가, 테스트를 어디에 두는가, 피할 패턴, 루프의 규칙. 모든 절은 매 사이클에 적용된다 — 루프가 끝난 뒤가 아니라 루프 전과 도중에 참고한다.

시작 전에 해당 게임의 `doc/{GameName}/architecture.md` 와 손대는 영역의 ADR 을 읽어 테스트 이름과 인터페이스 용어를 프로젝트 용어에 맞춘다. 테스트 프레임워크가 아직 없으면 `/test-setup` 을 먼저 돌린다. 공용 헬퍼는 `/test-helpers`.

## 좋은 테스트

테스트는 구현 세부가 아니라 **공개 인터페이스를 통한 동작**을 검증한다. 내부를 통째로 갈아엎어도 테스트는 그대로여야 한다. 좋은 테스트는 명세처럼 읽힌다 — `PlayerCanRespawnAtNearestElevatorWhenOnEscapeFloor` 는 어떤 능력이 있는지 정확히 말하고, 내부 구조에 관심이 없으니 리팩터링에도 살아남는다.

예시와 대역(mock · fake) 기준은 [tests.md](tests.md) (Unity C# 예시). 엔진별 테스트 이름 · 구조 예시는 `.claude/rules/test-standards.md` (Godot · Unity · Unreal).

## 접점(seam): 테스트를 두는 곳

**접점**은 내부를 들여다보지 않고 동작을 관찰하는 공개 경계다. 테스트는 접점에만 둔다.

**합의한 접점에서만 테스트한다.** 테스트를 쓰기 전에 대상 접점을 적어 사용자와 확인한다. 확인하지 않은 접점에는 테스트를 쓰지 않는다. 전부 테스트할 수는 없으니, 접점을 먼저 합의하는 것이 테스트 노력을 핵심 경로와 복잡한 로직에 모으는 방법이다.

묻기: "공개 인터페이스는 무엇이고, 어떤 접점을 테스트할까요?" 제안하는 접점마다 무엇을 잡고 무엇을 놓치는지 한 줄씩 붙인다.

엔진 공통 접점 기준:

- **우선 엔진을 띄우지 않는 단위 테스트** — 게임 로직을 엔진 객체(MonoBehaviour · Node · Actor) 밖의 순수 클래스로 분리하고(험블 오브젝트) 그 공개 메서드를 접점으로 삼는다. 빠르고 결정적이다
- **엔진 통합 테스트는 필요할 때만** — 생명주기 · 물리 · 코루틴/await · 씬 로딩 자체가 검증 대상일 때
- 시간 · 랜덤 · 입력 · 저장소는 주입받는 인터페이스로 둔다 (`gameplay-code.md` — static 싱글톤 금지, DI). 이것이 대역을 끼울 수 있는 경계다

엔진별:

| | Unity | Godot | Unreal |
|---|---|---|---|
| 단위 | EditMode (NUnit) — 순수 C# 클래스 | gdUnit4 — `RefCounted` · `Resource` 기반 클래스, 노드는 `auto_free` | Automation (`IMPLEMENT_SIMPLE_AUTOMATION_TEST` · Spec) — `F` 구조체 · 일반 C++ |
| 통합 | PlayMode | gdUnit4 씬 러너 (`scene_runner`) | Automation 에서 월드 생성 · Functional Test |
| 배치 | 테스트 asmdef (`Tests/EditMode`, `Tests/PlayMode`) — 대상 어셈블리만 참조 | `tests/` (또는 `test/`) 아래 `*_test.gd` | `Source/<Module>/Private/Tests/` + `WITH_DEV_AUTOMATION_TESTS` |
| 실행 | `bash .claude/scripts/test-run.sh unity [--platform playmode]` · 에디터가 열려 있으면 `mcp__UnityMCP__run_tests` | `bash .claude/scripts/test-run.sh godot` | `bash .claude/scripts/test-run.sh unreal --filter <루트>` |

인터페이스 모양 자체가 문제라면(모듈 깊이, 접점 위치, 무엇을 노출할지) 먼저 `/ko-grill` 로 결정을 정리하거나 `/architecture-decision` 으로 남긴다.

## 피할 패턴

- **구현 결합**: 내부 협력 객체를 대역으로 바꾸거나, private 메서드를 리플렉션으로 시험하거나, 인터페이스가 아닌 옆길(내부 필드 · 직접 만든 저장 파일 읽기)로 검증한다. 징후: 동작은 그대로인데 리팩터링하면 테스트가 깨진다
- **동어반복**: 기대값을 코드와 같은 방식으로 다시 계산한다 (`Assert.AreEqual(a + b, Add(a, b))`). 정의상 항상 통과하니 코드와 어긋날 수 없다. 기대값은 독립된 출처에서 온다 — 알려진 리터럴, 손으로 푼 예시, GDD 의 수치
- **수평 분할**: 테스트를 전부 먼저 쓰고 구현을 나중에 전부 한다. 몰아 쓴 테스트는 **상상한** 동작을 검증한다 — 실제 동작이 아니라 모양을 시험하게 되고, 구현을 이해하기 전에 테스트 구조에 묶인다. 대신 **수직 조각**으로 간다: 테스트 하나 → 구현 하나 → 반복. 각 테스트는 직전 사이클에서 배운 것에 반응하는 **예광탄(tracer bullet)** 이다

## 루프 규칙

- **green 전에 red.** 실패하는 테스트를 먼저 쓰고, 통과할 만큼만 코드를 쓴다. 다음 테스트를 앞질러 짐작하거나 쓰일지 모를 기능을 넣지 않는다
- **한 번에 한 조각.** 사이클마다 접점 하나, 테스트 하나, 최소 구현 하나
- **red 를 직접 본다.** 위 실행 명령 결과에서 그 테스트가 **기대한 이유로** 실패하는지 확인한다. 컴파일 · 파싱 오류는 red 가 아니다 — 콘솔 · 로그(`.claude/docs/engine-layers.md`)로 확인하고 먼저 빌드되게 만든다. `test-run.sh` 가 "테스트 0개 실행" 을 보고하면 그것도 red 가 아니다
- **리팩터링은 루프 밖이다.** 리뷰 단계(`/ko-code-review`)에서 한다

## 완료

합의한 접점의 테스트가 모두 green 이고, 대상 게임의 단위(필요하면 통합) 전체 테스트를 다시 돌려 기존 테스트도 green 일 때 끝난다. 통과 수를 보고에 적는다 (예: `EditMode 389/389`). 엔진 실행 파일이 없어 돌리지 못했으면 "테스트 실행 안 함 — <이유>" 로 보고하고 green 이라고 쓰지 않는다.
