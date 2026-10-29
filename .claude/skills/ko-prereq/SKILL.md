---
name: ko-prereq
description: 사전 설치 점검 · 설치 (한국어) — 자동화(스튜디오 모드 · 그래픽/사운드 생성 · Unity MCP)를 돌리기 전에 필요한 도구 · 모델 · 효과음 라이브러리 · 설정을 점검하고, 자동으로 고칠 수 있는 것은 사용자 확인 후 설치
argument-hint: "[check | install] [--roles planning,art,dev] [--comfyui-home DIR] [--library-dir DIR]"
user-invocable: true
allowed-tools: Read, Bash, AskUserQuestion
---

# /ko-prereq — 자동화 사전 설치

결정적 작업(점검 · 다운로드 · 검증 · 설정 병합)은 `python .agent/tools/setup/prereq.py` 가 한다. 이 스킬은 결과를 설명하고 사용자 확인을 받는다.

## 언제

- 템플릿을 새 Unity 프로젝트에 설치한 직후 (`scripts/install.ps1` 다음)
- `studio launch` 사전 점검에 "사전 설치 누락" 경고가 나왔을 때
- 다른 PC 에서 같은 프로젝트를 처음 열 때, 또는 설정(그래프 · 오디오 매핑)을 바꾼 뒤

## 절차

1. **점검** — `python .agent/tools/setup/prereq.py check --json [--roles ..]` 을 실행한다.
   - `--roles`: 이 PC 가 맡을 역할. 사용자가 말하지 않았으면 전부(planning,art,dev). art 를 다른 PC 가 맡으면 빼야 모델을 받지 않는다.
2. **보고** — 묶음(기본 · Unity · 생성 · 사용자 결정)별 표로 보여 준다: 상태 · 내용 · 해결 방법. 상태 기호: ✔ ok · ✖ missing · ! warn · ? 사용자 결정 · · 사용 안 함.
   - `auto: true` 인 missing 은 자동 설치 후보다. 용량(`size`) · 라이선스(`license`)를 함께 적는다.
   - 제목이 `(선택)` 인 항목(VS Code · pytest · graphify · adb 기기 · protobuf)은 없어도 실패가 아니고, `install` 을 항목 없이 실행하면 설치하지 않는다. 사용자가 원할 때만 `install <항목>` 으로 설치한다 (graphify 는 dev 가 기존 C# 코드 구조를 파악할 때 — 실행은 항상 `GRAPHIFY_BACKEND=none`)
   - 자동 설치가 안 되는 missing 은 `manual` 안내를 그대로 보여 준다 (Unity 에디터는 `unityhub://` 링크, ComfyUI 본체는 릴리스 페이지).
3. **확인** — 자동 설치 후보가 있으면 `AskUserQuestion` 으로 묻는다:
   - `[A] 모두 설치 (Recommended)` / `[B] 일부만` (항목을 다시 물음) / `[C] 설치 안 함`
   - 대용량 모델(GB 단위)이 있으면 질문에 총 용량과 저장 위치(ComfyUI models 폴더)를 적는다.
4. **설치** — `python .agent/tools/setup/prereq.py install <항목...> --yes` 를 백그라운드로 실행한다 (모델은 수 GB · 수십 분). 끝나면 출력의 ✖ 를 그대로 보고한다.
   - 다운로드가 끊겨도 `.part` 에서 이어받는다. 실패한 항목은 같은 명령으로 다시 실행하면 된다.
5. **재점검** — `check` 를 다시 실행해 남은 항목을 보고한다. 필수 누락이 0 이면 다음 단계(`/studio-status launch` 또는 `/ko-setup-engine`)를 안내한다.

## 하지 않는 것

- **라이선스 동의를 대신하지 않는다.** `decide` 항목(Stable Audio · gamedesign 카탈로그)은 조건을 설명만 하고 설치하지 않는다. 사용자가 직접 받거나 `/ext` 의 설치 돕기를 쓴다.
- 시스템 도구(git · Claude Code · uv · Unity · ComfyUI 본체 · GPU 드라이버)를 원격 스크립트로 몰래 설치하지 않는다. winget 이 있으면 `prereq.py` 가 winget 으로 설치하고, 없으면 공식 명령을 안내만 한다.
- 받은 모델 파일을 지우지 않는다. 크기나 SHA256 이 맞지 않으면 보고하고 사용자에게 맡긴다.

## 관련

- 도구 문서: `prereq.py` 상단 docstring · `README.md` §요구 사항
- 생성 파이프라인: `/ko-art-gen` · `.agent/tools/artgen/README.md`
- 스튜디오 기동: `/studio-status launch` (사전 점검이 이 결과를 경고로 함께 보여 준다)
