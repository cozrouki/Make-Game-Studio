---
description: 사전 설치 점검 · 설치 — 자동화 실행 전에 필요한 도구 · 모델 · 효과음 라이브러리 · 설정을 점검하고 자동 설치
---

# 사전 설치 점검 · 설치

> 정본: `.claude/skills/ko-prereq/SKILL.md`. 결정적 작업은 `python .agent/tools/setup/prereq.py` 가 한다.

**1. 점검** — `python .agent/tools/setup/prereq.py check --json [--roles planning,art,dev]`. 이 PC 가 맡지 않을 역할은 `--roles` 에서 뺀다.

**2. 보고** — 묶음별(기본 · 엔진 — 프로젝트 엔진만 점검, 나머지는 이유 붙은 skip · 생성 · 사용자 결정)로 상태와 해결 방법을 보여 준다. `auto: true` 인 항목은 용량 · 라이선스와 함께 자동 설치 후보로 표시한다.

**3. 확인 후 설치** — 사용자에게 설치할 항목을 확인받고 `python .agent/tools/setup/prereq.py install <항목...> --yes` 를 실행한다. 끊긴 다운로드는 같은 명령으로 이어받는다.

**4. 재점검** — `check` 를 다시 실행해 남은 항목을 보고한다.

라이선스 동의가 필요한 항목(`decide` — Stable Audio · gamedesign)은 설명만 하고 설치하지 않는다. 시스템 도구는 winget 이 있을 때만 자동, 없으면 공식 명령을 안내한다.
