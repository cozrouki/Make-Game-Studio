"""godot_doc_audit 테스트 — python -m pytest .agent/tools/godot/tests -q"""
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import godot_doc_audit as G  # noqa: E402


def _rules(src):
    return [(f["rule"], f.get("name")) for f in G.audit_source(src)]


GOOD = '''extends CharacterBody2D
class_name Player
## 플레이어가 조작하는 캐릭터. 입력을 받아 이동하고 점프한다.
##
## 이동 수치는 [member move_speed] · [member jump_velocity] 로 조정한다.

## 땅에 닿을 때마다 내보낸다.
signal landed

## 수평 이동 속도 (픽셀/초).
@export var move_speed: float = 200.0

## 점프 시작 속도 (픽셀/초, 위쪽이 음수).
@export
var jump_velocity: float = -400.0

@onready var _sprite: Sprite2D = $Sprite2D
@onready var anim: AnimationPlayer = $AnimationPlayer

## 공중에서 쓸 수 있는 점프 횟수.
const MAX_AIR_JUMPS := 1

enum State { IDLE, RUN } ## 이동 상태.

## 남은 체력이 0 이하가 되면 [code]true[/code] 를 반환한다.
func is_dead() -> bool:
    var hp := 0
    return hp <= 0

func _physics_process(delta: float) -> void:
    var velocity_x := 0.0
'''


def test_good_script_has_no_findings():
    assert _rules(GOOD) == []


def test_missing_docs_on_public_members():
    src = '''extends Node
signal died
const SPEED := 3
enum Kind { A, B }
@export var hp := 10
var score := 0
func heal(amount: int) -> void:
    var local := amount
class Inner:
    var x := 1
'''
    names = {n for r, n in _rules(src) if r == "GD001"}
    assert names == {"died", "SPEED", "Kind", "hp", "score", "heal", "Inner", "x"}
    assert "local" not in names


def test_private_and_onready_are_skipped():
    src = "extends Node\nvar _cache := {}\nfunc _ready() -> void:\n    pass\n@onready var label: Label = $Label\n"
    assert _rules(src) == []


def test_class_name_needs_script_description():
    assert ("GD002", None) in _rules("extends Node\nclass_name Foo\n\n## 점수.\nvar score := 0\n")
    assert ("GD002", None) not in _rules("extends Node\n## 점수를 센다.\nclass_name Foo\n")
    # class_name 이 없으면 스크립트 설명은 요구하지 않는다
    assert ("GD002", None) not in _rules("extends Node\n## 점수.\nvar score := 0\n")


def test_tag_with_space_before_colon_is_invalid():
    src = "extends Node\n## 설명.\n## @tutorial  : https://example.com\n## @deprecated: 다음 판에서 지운다.\nvar a := 1\n"
    assert [r for r, _ in _rules(src)] == ["GD003"]


def test_deprecated_and_experimental_together():
    src = "extends Node\n## 옛 경로.\n## @deprecated\n## @experimental\nfunc old_path() -> void:\n    pass\n"
    assert ("GD004", "old_path") in _rules(src)


def test_tab_inside_codeblock():
    src = "extends Node\n## 예:\n## [codeblock]\n## if ok:\n## \tprint(1)\n## [/codeblock]\nfunc f() -> void:\n    pass\n"
    assert ("GD005", None) in _rules(src)


def test_banned_words_warn_but_code_spans_are_ignored():
    src = "extends Node\n## 그냥 체력을 채운다.\nfunc heal() -> void:\n    pass\n## [code]just[/code] 를 출력한다.\nfunc say() -> void:\n    pass\n"
    rules = [r for r, _ in _rules(src)]
    assert rules.count("GD006") == 1


def test_description_that_only_repeats_the_name():
    src = "extends Node\n## Sets the speed.\nfunc set_speed(v: float) -> void:\n    pass\n## speed\nvar speed := 1.0\n"
    names = {n for r, n in _rules(src) if r == "GD007"}
    assert names == {"set_speed", "speed"}


def test_ignore_comment():
    src = "extends Node\n# godot-doc: ignore GD001\nvar internal_flag := false\n"
    assert _rules(src) == []


def test_run_not_assessed_without_gd(tmp_path):
    (tmp_path / "Player.cs").write_text("public partial class Player {}", encoding="utf-8")
    r = G.run([str(tmp_path)])
    assert r["verdict"] == "NOT ASSESSED"
    assert r["cs_files_not_checked"] == 1


def test_run_skips_addons_and_hidden_folders(tmp_path):
    (tmp_path / "addons" / "x").mkdir(parents=True)
    (tmp_path / "addons" / "x" / "a.gd").write_text("extends Node\nvar a := 1\n", encoding="utf-8")
    (tmp_path / "b.gd").write_text("extends Node\n## 개수.\nvar b := 1\n", encoding="utf-8")
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "example.gd").write_text("extends Node\nvar c := 1\n", encoding="utf-8")
    r = G.run([str(tmp_path)])
    assert r["gd_files"] == 1 and r["verdict"] == "PASS"
