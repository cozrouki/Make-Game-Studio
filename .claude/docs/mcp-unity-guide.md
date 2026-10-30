# MCPForUnity 사용 가이드 (한국어)

> **Unity 전용.** Godot · Unreal 의 에디터 자동화 · 테스트 · 로그 경로는 `.claude/docs/engine-layers.md`.

**MCPForUnity** (CoplayDev/unity-mcp) 의 35+ 도구를 카테고리별로 정리하고 사용 시나리오를 안내합니다. (별도 설치 필요 — README 4단계 참조)

## 개요

- **레포**: https://github.com/CoplayDev/unity-mcp
- **설치 경로**: `Packages/manifest.json` 의 `com.coplaydev.unity-mcp`
- **MCP 설정**: `.mcp.json` (`.mcp.json.template` 복사 후 수정, stdio 전송, 포트 6401)
- **권한 설정**: `.claude/settings.local.json` 의 `mcp__UnityMCP__*` 항목

Unity Editor가 켜져있을 때만 도구 호출이 성공합니다. Editor가 꺼져있으면 stdio 연결 실패.

## 도구 카테고리별 매트릭스

### 1. 씬·게임오브젝트 조작 (Core)

| 도구 | 용도 | 시나리오 |
|---|---|---|
| `mcp__UnityMCP__manage_scene` | 씬 로드/저장/생성/계층 조회 | 새 레벨 씬 만들기, 빌드용 씬 묶기 |
| `mcp__UnityMCP__manage_gameobject` | GameObject 생성/이동/회전/스케일/active 토글 | 적 스폰 포인트 배치, 라이팅 더미 추가 |
| `mcp__UnityMCP__find_gameobjects` | 이름/태그/레이어/컴포넌트 기준 검색 | 모든 Light를 찾아 일괄 intensity 조정 |
| `mcp__UnityMCP__manage_components` | 컴포넌트 추가/제거/속성 변경 | RigidBody mass 일괄 변경 |

### 2. 에셋·프리팹·ScriptableObject

| 도구 | 용도 | 시나리오 |
|---|---|---|
| `mcp__UnityMCP__manage_asset` | 에셋 import 설정 / 메타 변경 | 텍스처 압축 형식 일괄 변경 |
| `mcp__UnityMCP__manage_prefabs` | 프리팹 생성/인스턴스화/override 관리 | 적 프리팹 100개 자동 생성 |
| `mcp__UnityMCP__manage_scriptable_object` | SO 인스턴스 생성/필드 수정 | 무기 데이터 SO 일괄 튜닝 |

### 3. 에디터 상태·콘솔·새로고침

| 도구 | 용도 | 시나리오 |
|---|---|---|
| `mcp__UnityMCP__manage_editor` | 에디터 모드 전환 (Play / Pause / Edit), 현재 씬·선택 객체 조회 | 자동 테스트 전 Play 모드 진입 |
| `mcp__UnityMCP__refresh_unity` | Asset Database 새로고침 + 스크립트 컴파일 트리거 | 외부 스크립트 추가 후 Unity가 인식하도록 |
| `mcp__UnityMCP__read_console` | Console 로그/경고/에러 읽기 | 컴파일 에러 진단, 런타임 에러 추적 |
| `mcp__UnityMCP__execute_menu_item` | 메뉴 아이템 실행 (예: `Window/Package Manager`) | 자동화 시퀀스의 일부 |

### 4. 일괄 처리·고급

| 도구 | 용도 | 시나리오 |
|---|---|---|
| `mcp__UnityMCP__batch_execute` | 여러 명령을 1회 RPC로 일괄 실행 (10-100배 빠름) | 100개 GameObject 위치 + 컴포넌트 + 머티리얼 일괄 변경 |

### 5. 스크립트·빌드·테스트

| 도구 | 용도 | 시나리오 |
|---|---|---|
| `manage_script` 계열 (create/delete) | C# 스크립트 파일 생성/삭제 | SkillForge 템플릿 주입 후 자동 컴파일 |
| `apply_text_edits` | 파일 부분 수정 (큰 파일 안전 편집) | 기존 스크립트에 메서드 추가 |
| `manage_build` | 헤드리스 빌드 실행 | CI에서 Android/iOS 빌드 |
| `manage_profiler` | Profiler 캡처 + 분석 | `/ko-perf-profile` 의 데이터 수집 |
| `run_tests` | Edit/Play 모드 테스트 실행 | TDD 사이클의 RED → GREEN 검증 |

### 6. 도메인 특화

| 도구 | 용도 |
|---|---|
| `manage_animation` | Animator 컨트롤러·클립 조작 |
| `manage_camera` | 카메라 설정·뷰포트 |
| `manage_physics` | Physics 설정 (3D/2D) |
| `manage_shader`, `manage_graphics` | 그래픽 설정 |
| `manage_ui`, `manage_probuilder` | UI 빌드, ProBuilder 메시 |
| `unity_reflect`, `unity_docs` | 리플렉션·문서 조회 |

## 사용 시나리오 5가지

### 시나리오 A: 새 씬 만들고 라이팅 자동화

1. `manage_scene` — `action: "create"`, `name: "BridgeArea_v2"`
2. `manage_gameobject` — Directional Light 1개 추가
3. `manage_components` — Light.intensity = 1.2, color = (255,240,200)
4. `manage_scene` — `action: "save"`

### 시나리오 B: 컴파일 에러 진단

1. `refresh_unity` — 컴파일 트리거
2. `read_console` — `level: "error"` 필터
3. 결과를 사용자에게 한국어로 요약 + 수정 제안

### 시나리오 C: 일괄 프리팹 변경

1. `find_gameobjects` — `tag: "Enemy"` 로 모든 적 검색
2. `batch_execute` — 한 RPC로:
   - 각 적의 Rigidbody mass 변경
   - SpawnEffect 컴포넌트 추가
   - 활성 토글

### 시나리오 D: Profiler 데이터 수집

1. `manage_editor` — Play 모드 진입
2. `manage_profiler` — 30초 캡처
3. 사용자에게 GC 할당량 / 프레임 시간 요약
4. `/ko-perf-profile` 또는 SkillForge 06-performance 카탈로그 매칭 안내

### 시나리오 E: 자동 빌드

1. `manage_build` — `target: "Android"`, `output: "Builds/android/"`
2. `read_console` — 빌드 워닝/에러 확인
3. 빌드 산출물 경로 + 빌드 시간 보고

## 권한 추가하기

새 MCP 도구를 쓰려면 `.claude/settings.local.json` 의 `allow[]` 에 추가:

```json
"mcp__UnityMCP__manage_animation",
"mcp__UnityMCP__manage_build",
"mcp__UnityMCP__run_tests"
```

도구 이름은 사용 시도 시 권한 거부 메시지에 표시됨.

## 트러블슈팅

| 증상 | 원인 | 대처 |
|---|---|---|
| `stdio connection failed` | Unity Editor 종료 상태 | Unity 열기 |
| `Method not found` | 도구 이름 오타 또는 패키지 버전 미스매치 | `manifest.json` 의 unity-mcp 버전 확인, `unity-mcp.git#main` 으로 최신화 |
| 무응답 (timeout) | Domain Reload 진행 중 | 5-15초 대기 후 재시도 |
| 권한 거부 | `settings.local.json` 의 `mcp__UnityMCP__*` 누락 | 해당 도구를 `allow[]` 에 추가 |

## 관련 문서

- 결정 매트릭스: `.claude/docs/editor-automation-decision.md` (씬 조작 vs 코드 패턴 vs 문서 안내)
- SkillForge 패턴 카탈로그: `/sf-list` 후 `.agent/skills/<카테고리>/<skill>/SKILL.md`
- Unity-Skills (Besty0728) — REST API 카탈로그. 현재 미설치, 필요시 별도 clone.
