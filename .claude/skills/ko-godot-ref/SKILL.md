---
name: ko-godot-ref
description: Godot 공식 문서 근거 찾기 (한국어) — 엔진 레퍼런스(docs/engine-reference/godot)에 없는 Godot API · 동작 질문을 고정 버전(기본 4.7) 공식 문서에서 찾아 출처 URL 을 달아 답하고, 찾지 못한 것은 NOT SOURCEABLE 로 남기며, 승인을 받아 레퍼런스에 보충한다. "Godot 에서 이거 되나", "이 API 4.7 에 있나", "공식 문서 근거", "클래스 레퍼런스 찾아 줘" 요청 시 (Godot 전용)
argument-hint: "[질문 · 클래스 · 메서드 이름]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, WebFetch, Edit
---

# /ko-godot-ref — Godot 공식 문서 근거 찾기

> 출처: Godot 공식 문서(docs.godotengine.org, CC BY 3.0 — Juan Linietsky, Ariel Manzur, and the Godot Engine community)의
> 구성(소개 페이지 "문서의 구성")과 명령줄 문서의 `--doctool` · `--gdscript-docs` 를 근거로 했다 (2026-11-04 확인).

이 템플릿은 엔진 사실을 학습 지식으로 채우지 않는다 (`.claude/rules/skill-authoring.md` 의무 4 · `docs/CLAUDE.md`). 이 스킬은 그 빈칸을 **공식 문서로** 메우는 절차다. 답의 문장마다 출처가 붙거나, "출처 없음" 이 붙는다 — 둘 중 하나다.

## 0. 엔진 · 버전 확인

1. `project.yaml` `engine.name`(없으면 `project.godot`)이 Godot 이 아니면 **"엔진이 Godot 이 아니라 하지 않음 — <엔진>"** 으로 끝낸다.
2. 기준 버전을 정한다 — 첫 번째로 나온 것:
   - `project.godot` 의 `config/features` 첫 값 (프로젝트가 실제로 쓰는 버전 — 예 `"4.6"`)
   - `docs/engine-reference/godot/VERSION.md` 의 고정 버전 (템플릿 기본 4.7)
3. 둘이 다르면 보고서 머리에 적는다: "프로젝트 4.6 · 레퍼런스 고정 4.7 — 4.6 문서로 답함". `VERSION.md` 의 `Installed at pin time` 이 `NOT DETERMINED` 면 설치된 에디터 버전은 모른다는 것도 적는다.

## 1. 저장소 레퍼런스 먼저

`docs/engine-reference/godot/` 를 Grep 한다 — `VERSION.md` · `breaking-changes.md` · `deprecated-apis.md` · `current-best-practices.md` · `modules/*.md`. 거기 답이 있으면 그 파일을 출처로 쓰고 2단계는 건너뛴다. 단, 그 파일의 확인 날짜(`Last Docs Verified` 또는 절 머리의 날짜)를 함께 적는다.

## 2. 공식 문서에서 찾기

**어디를 볼지** — 문서는 네 부분이다:

| 부분 | 경로 (`https://docs.godotengine.org/en/<버전>/` 아래) | 무엇을 찾나 |
|---|---|---|
| 클래스 참조 | `classes/class_<클래스 이름 소문자>.html` (예: `classes/class_characterbody2d.html`) | 메서드 · 속성 · 시그널 · 상수의 정확한 이름과 설명 — **API 사실의 1순위** |
| 설명서(Manual) | `tutorials/...` | 기능별 사용법 · 주의점 (예: `tutorials/scripting/gdscript/...`) |
| 시작하기 | `getting_started/...` | 입문 개념 |
| 엔진 상세 · 소개 | `engine_details/...` · `about/...` | 엔진 내부 · 라이선스 · FAQ |

**버전 주소** — `/en/<버전>/` 을 쓴다 (`/en/4.7/` · `/en/4.6/` 은 열린다, 2026-11-04 확인). `/en/stable/` · `/en/latest/` 는 시간이 지나면 다른 버전을 가리키므로 **출처로 적지 않는다**. 한국어 `/ko/4.x/` 는 최신(불안정) 판이라 읽기 보조로만 쓰고, 근거는 같은 내용의 영어 버전 페이지로 단다.

**절차**

1. 후보 URL 을 만들고 열리는지 먼저 확인한다: `curl -s -o /dev/null -w "%{http_code}" <URL>` — 200 이 아니면 그 URL 을 출처로 쓰지 않는다.
2. WebFetch 로 해당 절만 읽는다. 질문에 답하는 문장을 찾고, 그 문장의 요지와 URL(앵커 포함)을 기록한다.
3. 클래스 참조에 이름이 없으면 그 버전에 **없는 것**일 수 있다. 바로 "없다" 고 단정하지 않는다 — 이전 · 다음 버전 페이지와 `deprecated-apis.md` 를 보고 "4.7 클래스 참조에 없음 (4.6 에는 있음)" 처럼 확인한 범위를 적는다.
4. **설치된 에디터가 있으면 그것이 최종 근거다.** `godot --doctool <임시 폴더>` 는 설치된 엔진의 API 레퍼런스를 XML 로 덤프한다. 문서와 설치본이 다르면 설치본을 따르고 차이를 보고한다. 이 명령은 파일을 쓰므로 저장소 밖 임시 폴더에만 쓴다.

## 3. 답하기

```
## Godot 근거 — <질문>
기준: Godot <버전> (<project.godot | VERSION.md>) · 판정: COMPLETE | CONCERNS | NOT ASSESSED
- <주장 1> — 출처: <URL 또는 저장소 파일> (확인 2026-11-04)
- <주장 2> — NOT SOURCEABLE: <무엇을> <어디까지 찾았는지> (문서 · 레퍼런스에 없음)
설치본 대조: 함 (godot <버전> --doctool) | 안 함 (에디터 없음)
```

- **COMPLETE** — 모든 주장에 출처가 있다.
- **CONCERNS** — 한 주장이라도 NOT SOURCEABLE 이거나, 문서와 설치본이 다르다. 출처 없는 주장으로 코드를 쓰지 않는다 — 그 부분은 "확인 필요" 로 남기거나 설치본에서 직접 시험할 것을 제안한다.
- **NOT ASSESSED** — 문서에 닿지 못했다 (네트워크 실패 · 페이지 200 아님). 이유를 적는다. 학습 지식으로 대신 답하지 않는다.

## 4. 레퍼런스에 보충 (선택, 승인 후)

찾은 사실이 다음에도 쓰일 만하면 `docs/engine-reference/godot/` 의 알맞은 파일(`modules/<분야>.md` 등)에 한 줄로 보충할 것을 제안한다. 넣을 문장 · 파일 · 출처 URL · 확인 날짜를 보여 주고 "May I write this to `docs/engine-reference/godot/<파일>`?" 로 승인을 받은 뒤에만 Edit 한다. 보충한 줄에는 반드시 URL 과 날짜를 붙인다. `VERSION.md` 의 버전 · 날짜 칸은 이 스킬이 바꾸지 않는다 (`/setup-engine` 몫).

## 5. 다음 단계

- 답이 COMPLETE → 구현은 `/ko-tdd` (테스트부터) 또는 해당 `godot-*-specialist` 에이전트.
- CONCERNS (출처 없음 · 설치본과 다름) → 설치된 에디터에서 작은 시험 장면으로 확인하거나 `/ko-diagnose`.
- 버전 차이가 크게 드러남 → `/setup-engine` 으로 고정 버전 · 레퍼런스를 다시 맞춘다.
