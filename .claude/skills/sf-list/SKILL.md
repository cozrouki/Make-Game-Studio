---
name: sf-list
description: SkillForge 카탈로그 목록 출력 (한국어, 오프라인) — `.agent/skills/skills-index.json` 사용
argument-hint: "[카테고리 prefix — 예: 02-gameplay, 06-performance, all]"
user-invocable: true
allowed-tools: Read, Bash
---

# /sf-list — SkillForge 카탈로그 목록

`.agent/skills/skills-index.json` 를 읽어 사용 가능한 C# 코드 패턴 102개를 한국어로 출력합니다. **오프라인 동작 — npx 의존 없음.**

## 사용법

```
/sf-list                  # 카테고리별로 그룹화하여 전체 출력
/sf-list 02-gameplay      # 게임플레이 카테고리만
/sf-list 06               # 06으로 시작하는 카테고리만
/sf-list all              # 평탄화하여 전체
```

## Phase 1: 인덱스 로드

`.agent/skills/skills-index.json` 을 Read.

- 파일이 없으면 사용자에게 `.agent/skills/README-sync.md` 의 동기화 절차 안내 후 종료.

## Phase 2: 필터링

- 인수 없으면 → 카테고리별 그룹화
- `02-gameplay` 같은 정확한 카테고리 → 해당 카테고리만
- `02` 같은 prefix → startswith 매칭
- `all` → 평탄화

## Phase 3: 출력 (한국어)

카테고리별로 그룹 헤더 + 각 skill 한 줄:

```
📂 02-gameplay (N개)
  • ability-skill-system — ScriptableObject 정의, 쿨다운, 자원 비용, 타게팅을 갖춘 데이터 드리븐 어빌리티 시스템.
  • advanced-character-controller — 지면 감지, 점프, 경사면, 상태 기반 이동을 포함한 완전한 3D 캐릭터 컨트롤러.
  • ...

📂 06-performance (M개)
  • gpu-instancing-expert — GPU 인스턴싱과 간접 렌더링으로 수천 개의 동일 메시를 효율적으로 렌더링.
  • job-system-burst — Unity Job System과 Burst Compiler를 활용한 고성능 병렬 CPU 작업.
  • ...
```

## Phase 4: 후속 안내

출력 끝에 한 줄:

```
ℹ 상세: /sf-info <skill-name>   |   주입: /sf-add <skill-name>
```

## 관련

- 상세 보기: `/sf-info`
- 템플릿 주입: `/sf-add`
- 업스트림 동기화: `.agent/skills/README-sync.md`
