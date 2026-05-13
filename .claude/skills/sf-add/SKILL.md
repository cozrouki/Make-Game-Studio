---
name: sf-add
description: SkillForge skill 템플릿을 사용자 지정 경로에 복사 (오프라인 주입)
argument-hint: "<skill-name> [대상-경로=Assets/<Game>/Scripts/<Subsystem>/]"
user-invocable: true
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# /sf-add — SkillForge skill 주입

`.agent/skills/<카테고리>/<skill-name>/templates/` 의 C# 파일을 사용자 프로젝트의 적절한 위치로 복사합니다. **오프라인 — npx 의존 없음.**

## 사용법

```
/sf-add ability-skill-system
/sf-add advanced-character-controller Assets/KickleCubicle/Scripts/Player
/sf-add job-system-burst Assets/SharedCore/Scripts/Performance
```

## Phase 1: 인수 + 검증

- `$1` = skill 이름 (필수)
- `$2` = 대상 디렉토리 (옵션, 미지정시 Phase 3에서 묻는다)
- `.agent/skills/skills-index.json` 에서 `$1` 메타 조회

매치 실패 시 `/sf-info` 의 fuzzy 후보 흐름과 동일하게 처리.

## Phase 2: 컨텍스트 발견

skill의 SKILL.md frontmatter에서:
- `requirements.unity_version` — TikiProject Unity 버전과 비교
- `requirements.render_pipeline` — `Packages/manifest.json` 의 URP/HDRP 확인
- `requirements.dependencies` — 누락 패키지 있는지 manifest.json 스캔

부적합하면 한국어로 경고 + 사용자에게 진행 여부 묻기 (AskUserQuestion).

## Phase 3: 대상 경로 결정

`$2` 가 비어있으면 사용자에게 묻기:

```
대상 경로를 선택하세요:
1) Assets/KickleCubicle/Scripts/<권장 서브폴더>/
2) Assets/ElevatorAction/Scripts/<권장 서브폴더>/
3) Assets/SharedCore/Scripts/<권장 서브폴더>/
4) 직접 입력
```

권장 서브폴더는 skill의 카테고리에서 유추 (02-gameplay → Gameplay, 06-performance → Performance, 01-architecture → Core/Patterns).

## Phase 4: 충돌 확인

대상 경로에 동일 파일명이 이미 존재하면:
- 한국어로 사용자에게 alert: "<파일명> 이 이미 존재. 덮어쓸까요? (예 / 아니오 / 새 이름으로)"
- 모든 충돌 해소 후 진행

## Phase 5: 복사 실행

`templates/` 의 `.cs.txt` 파일들을 대상 경로로 복사:
- `{{NAMESPACE}}` placeholder 치환 — 게임 prefix 기반 자동 결정 (`KickleCubicle.<Category>.<Subsystem>` 등)
- `.cs.txt` → `.cs` 로 확장자 변경
- 사용자 승인 후 Write 도구로 각 파일 생성

## Phase 6: 결과 리포트 (한국어)

```
✅ 주입 완료: <skill-name>
   파일 N개 → <대상 경로>/
   네임스페이스: <적용된 NS>

ℹ 다음 단계:
   1. Unity 에디터 새로고침 (또는 mcp__UnityMCP__refresh_unity)
   2. SKILL.md 의 "## Best Practices" 섹션 검토
   3. TDD-first skill인 경우: 테스트 먼저 작성 후 Red→Green→Refactor

📖 SKILL.md 본문: <path>
```

## Phase 7: 후처리

- `doc/work_log.md` 에 한 줄 기록 제안: `[<game-tag>] /sf-add <skill-name> → <path>`
- 관련 SkillForge skill이 있으면 `## Related Skills` 안내

## 관련

- 목록: `/sf-list`
- 상세: `/sf-info`
- 업스트림 동기화: `.agent/skills/README-sync.md`
