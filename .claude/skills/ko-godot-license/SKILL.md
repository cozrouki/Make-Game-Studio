---
name: ko-godot-license
description: Godot 게임 출시 전 라이선스 고지 점검 (한국어) — 게임에 Godot 엔진(MIT) 고지와 엔진에 든 제3자 구성 요소 고지가 들어갔는지, iOS 처럼 로그 고지가 안 되는 플랫폼은 없는지, 애드온 · 에셋 저작자 표시가 빠지지 않았는지 찾고, 없으면 크레딧 화면 구현을 돕는다. "라이선스 고지", "크레딧에 Godot", "출시 전 라이선스", "오픈소스 라이선스 화면" 요청 시 (Godot 전용)
argument-hint: "[check|add] [프로젝트 루트 — 기본: 현재 폴더]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

# /ko-godot-license — 출시 전 Godot 라이선스 고지 점검

> 근거: Godot 4.7 문서 "Complying with licenses" (https://docs.godotengine.org/en/4.7/about/complying_with_licenses.html,
> 2026-11-04 확인). 이 문서 스스로 **법률 자문이 아니라고** 밝힌다 — 이 스킬도 마찬가지다. 상업 출시 전 판단은 사람이 한다.

Godot 은 MIT 라이선스라 게임을 어떤 조건으로 팔아도 되지만, **라이선스 문구를 사용자가 볼 수 있게 게임 어딘가에 넣어야 한다.** 엔진에 들어 있는 제3자 구성 요소도 저작권 고지가 필요하다. 빠뜨리기 쉬운 출시 항목이라 기계로 먼저 훑는다.

## 0. 엔진 확인

`project.yaml` `engine.name`(없으면 `project.godot`)이 Godot 이 아니면 **"엔진이 Godot 이 아니라 하지 않음 — <엔진>"** 으로 끝낸다. Unity · Unreal 의 출시 고지는 `/release-checklist`.

## 1. check — 고지 경로 찾기

```bash
python .agent/tools/godot/godot_license_check.py <프로젝트 루트>
python .agent/tools/godot/godot_license_check.py --json <프로젝트 루트>
```

도구는 게임 코드 · 데이터(`.gd` · `.cs` · `.tscn` · `.tres` · 텍스트)에서 고지의 흔적을 찾는다. 숨김 폴더(`.godot` · `.claude` 등)는 게임이 아니라서 보지 않는다.

| 고지할 것 | 인정하는 흔적 |
|---|---|
| **Godot 엔진 (MIT)** | `Engine.get_license_text()` (C# `GetLicenseText()`) · 문구 "This game uses Godot Engine" · `godotengine.org/license` 링크 · 함께 배포할 `GODOT_LICENSE*.txt` |
| **엔진의 제3자 구성 요소** | `Engine.get_license_info()` · `get_copyright_info()` (C# `GetLicenseInfo()` · `GetCopyrightInfo()`) · 함께 배포할 `GODOT_COPYRIGHT.txt` (에디터의 `COPYRIGHT.txt` 를 이름만 바꾼 것) |

| 규칙 | 무엇 | 등급 |
|---|---|---|
| GL001 | Godot 고지 경로가 없다 | FAIL |
| GL002 | 제3자 구성 요소 고지 경로가 없다 | FAIL |
| GL003 | 고지가 출력 로그(`print`)뿐인데 iOS 내보내기 프리셋이 있다 — iOS 는 로그로 안 된다 | CONCERNS |
| GL004 | `addons/<이름>` 에 라이선스 파일이 없다 — 조건을 모른다 | CONCERNS |
| GL005 | 고지가 "함께 배포하는 파일" 뿐이다 — 배포 꾸러미에 들어가는지 도구가 모른다 | NOT ASSESSED |

**판정**: FAIL > CONCERNS > NOT ASSESSED > PASS. `project.godot` 이 없으면 NOT ASSESSED(이유 함께). 도구 결과를 그대로 옮기고, 아래 "사람이 확인할 것" 을 보고서에 반드시 붙인다 — **PASS 는 "흔적이 있다" 이지 "화면에 뜬다" 가 아니다.**

**사람이 확인할 것** (도구가 못 본다)
- 고지가 실제 게임 화면(크레딧 · 설정의 라이선스 메뉴)에서 열리는가 — 내보낸 빌드로 한 번 연다.
- 파일 경로(GL005)면 내보낸 폴더 · 설치 꾸러미에 그 파일이 들어갔는가.
- 폰트 · 음악 · 효과음 · 텍스처 · 모델 등 **제3자 에셋**의 저작자 표시 — 무료 에셋도 표시를 요구할 수 있다. `/ko-art-gen` 으로 받은 효과음 라이브러리(Kenney CC0)는 표시 의무가 없지만, 생성 모델 · 다른 출처는 각 조건을 본다.
- 라이선스 파일이 있는 애드온(도구가 목록을 낸다)이 고지를 요구하는가 — 개발 전용 애드온(예: 테스트 프레임워크)이 출시 빌드에 안 들어가면 고지도 필요 없다.

## 2. add — 고지 넣기 (승인 후)

check 가 FAIL 이면 가장 단순한 경로를 제안한다: **크레딧(또는 라이선스) 화면에 엔진이 주는 문구를 그대로 띄운다.** 문구를 손으로 붙여 넣지 않는다 — 엔진 버전을 올려도 `Engine` 메서드가 최신 문구를 준다(문서가 권하는 방법).

```gdscript
# 크레딧 화면 — 구현: Godot "Complying with licenses" (엔진 고지 · 제3자 고지)
extends Control
## 게임 · 엔진 · 제3자 구성 요소의 라이선스를 보여 주는 화면.

@onready var _engine_label: RichTextLabel = %EngineLicense
@onready var _third_party_label: RichTextLabel = %ThirdPartyLicenses


func _ready() -> void:
	_engine_label.text = "This game uses Godot Engine, available under the following license:\n\n" + Engine.get_license_text()
	_third_party_label.text = _third_party_text()


## 구성 요소마다 저작권자와 라이선스 이름, 그 뒤에 라이선스 본문을 한 번씩 이어 붙인 글을 반환한다.
func _third_party_text() -> String:
	var lines: PackedStringArray = []
	for component in Engine.get_copyright_info():
		lines.append("- " + str(component["name"]))
		for part in component["parts"]:
			lines.append("  © " + ", ".join(PackedStringArray(part["copyright"])) + " — " + str(part["license"]))
	lines.append("")
	var licenses: Dictionary = Engine.get_license_info()
	for license_name in licenses:
		lines.append("[" + license_name + "]")
		lines.append(str(licenses[license_name]))
		lines.append("")
	return "\n".join(lines)
```

- 반환 구조의 근거: 클래스 참조 `Engine` (https://docs.godotengine.org/en/4.7/classes/class_engine.html, 2026-11-04 확인) — `get_copyright_info()` 는 사전 배열이고 각 사전에 `name` 과 `parts`(항목마다 `files` · `copyright`(소유자 배열) · `license`), `get_license_info()` 는 라이선스 이름 → 본문 사전, `get_license_text()` 는 Godot 라이선스 전문. 프로젝트 Godot 버전이 4.7 이 아니면 `/ko-godot-ref Engine` 으로 그 버전 페이지를 다시 확인한다.
- 이 코드는 이 템플릿이 실제 에디터에서 실행해 보지 않았다 — 넣은 뒤 크레딧 화면을 한 번 열어 확인한다. 글이 길어 `RichTextLabel` 을 스크롤 컨테이너에 넣는다.
- 넣을 파일 · 장면 경로와 코드를 먼저 보여 주고 "May I write this credits screen to `<경로>`?" 로 승인을 받은 뒤에만 Write · Edit 한다. 장면(`.tscn`)은 에디터에서 만드는 것이 원칙이다(`.claude/rules/scene-files.md`) — 스크립트만 쓰고, 노드 배치는 사용자에게 안내하거나 Godot MCP 로 한다.
- UI 는 게임플레이 코드가 아니라 메뉴 흐름에서 연다 (`.claude/rules/gameplay-code.md` — UI 직접 참조 금지).

넣은 뒤 check 를 다시 돌려 판정을 확인한다.

## 3. 보고서

```
## Godot 라이선스 고지 — <프로젝트>
판정: PASS | CONCERNS | FAIL | NOT ASSESSED (<이유>)
- Godot 고지: <경로 — screen · link · log · file> (<파일:줄>)
- 제3자 고지: <경로> (<파일:줄>)
- 지적: GL00x …
- 라이선스 파일이 있는 애드온: <목록> — 출시 빌드 포함 여부 · 고지 요구 확인
- 사람이 확인할 것: 화면에 실제로 뜨는지 · 배포 꾸러미 · 제3자 에셋 표시
이 점검은 법률 자문이 아니다.
```

## 4. 다음 단계

- FAIL → `/ko-godot-license add` 로 크레딧 화면을 넣고 다시 check.
- `Engine` API 세부(사전 키 등) 확인 → `/ko-godot-ref Engine`.
- PASS · CONCERNS 정리 후 → `/release-checklist` 로 출시 점검 전체를 이어 간다.
