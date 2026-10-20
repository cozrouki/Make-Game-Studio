---
trigger: glob
globs: doc/**/*.md, production/**/*.md
description: 문서 작성 규칙
---
<!-- 생성물: scripts/gen-rule-mirrors.py — 직접 편집 금지 · 정본: .claude/rules/doc-writing.md -->

# 문서 작성 규칙

## 공통 규칙

- **언어**: 한국어 (코드 블록 내 주석 포함)
- **게임 태그**: `work_log.md` 항목에 반드시 포함 (멀티 게임 프로젝트)
  - 태그 셋은 프로젝트에서 정의한다. 예: `[GAME1]`, `[GAME2]`, `[CORE]`(공유 모듈, 예: `<SharedModule>`)
  - 단일 게임 프로젝트면 태그를 생략하거나 `[GAME]`/`[CORE]` 만 사용
- **날짜 형식**: `YYYY-MM-DD`

## task.md 형식

```markdown
# {GameName} 태스크

## 진행 중
- [ ] 태스크 설명 (YYYY-MM-DD)

## 완료
- [x] 태스크 설명 (완료: YYYY-MM-DD)

## 백로그
- [ ] 태스크 설명
```

## work_log.md 형식

현재 월만 `doc/work_log.md`에 두고 새 항목은 최상단에 추가(최신순), 지난 달은 `doc/work_log/YYYY-MM.md` (AGENTS.md §6).

```markdown
## YYYY-MM-DD

### [TAG] 작업 제목
- 변경 내용 요약
- 결정 사항 및 이유
```

## active.md 규칙

- `<!-- STATUS -->` 블록 항상 최신 유지
- 세션 종료 전 `_마지막 업데이트:` 날짜 갱신
- "다음 할 것"은 구체적인 액션으로 기술
- 3~5KB 유지 — 현재 상태·최근 완료분·다음 할 것·블로커만 (AGENTS.md §6-1)

## architecture.md 필수 섹션

1. `## 파일 구조`
2. `## 아키텍처 패턴`
3. `## 핵심 시스템`
4. `## 알려진 이슈`
5. `## 설계 결정 기록`
