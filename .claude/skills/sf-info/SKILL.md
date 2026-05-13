---
name: sf-info
description: SkillForge skill 상세 정보 — 인덱스 메타 + SKILL.md 헤드 출력
argument-hint: "<skill-name>"
user-invocable: true
allowed-tools: Read
---

# /sf-info — SkillForge skill 상세

특정 skill의 메타데이터와 SKILL.md 첫 부분을 한국어 헤더와 함께 표시합니다.

## 사용법

```
/sf-info ability-skill-system
/sf-info job-system-burst
/sf-info advanced-character-controller
```

## Phase 1: 인수 + 인덱스 조회

- `$1` = skill 이름 (필수, kebab-case)
- `.agent/skills/skills-index.json` 에서 해당 키 검색

매치 실패 시:
- 정확히 일치하는 키 없으면 → fuzzy 후보 3개 제시 (한국어): "이 중 하나를 의도하셨나요?"
- 후보도 없으면 → `/sf-list` 호출 안내

## Phase 2: 메타 출력 (한국어)

```
🔧 <skill-name>
   카테고리: <category>
   TDD 우선: <true/false>
   설명: <description>
   경로: <path>
```

## Phase 3: SKILL.md 헤드 출력

`<path>` 를 Read 하여 다음을 추출:
- YAML frontmatter 전체 (requirements, performance_budget, dependencies)
- 본문 첫 두 섹션 (`## Overview`, `## When to Use`) — 한국어 번역 가능하면 같이 병기, 아니면 원문

## Phase 4: 템플릿 안내

`<path>` 의 부모 디렉토리에서 `templates/` 폴더 확인:
- 존재 → `📦 템플릿 N개: <목록>` + "`/sf-add` 로 주입 가능"
- 없음 → "이 skill은 가이드만 제공. 코드는 SKILL.md 본문을 참고하여 직접 작성."

## Phase 5: 관련 skill 추천

SKILL.md 본문에 `## Related Skills` 섹션이 있으면 같이 출력.

## 관련

- 목록: `/sf-list`
- 주입: `/sf-add`
- 마스터: `/unity-fullstack code`
