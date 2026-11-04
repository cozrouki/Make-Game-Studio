"""godot_license_check 테스트 — python -m pytest .agent/tools/godot/tests -q"""
import os
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import godot_license_check as L  # noqa: E402


@pytest.fixture
def game(tmp_path):
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    return tmp_path


def _rules(root):
    return sorted(f["rule"] for f in L.run(str(root))["findings"])


def test_no_notice_at_all_fails(game):
    r = L.run(str(game))
    assert r["verdict"] == "FAIL"
    assert _rules(game) == ["GL001", "GL002"]


def test_credits_screen_with_engine_text_passes(game):
    (game / "src" / "credits.gd").write_text(
        "extends Control\n## 크레딧 화면.\nfunc _ready() -> void:\n"
        "    $Godot.text = Engine.get_license_text()\n"
        "    $Third.text = str(Engine.get_copyright_info())\n", encoding="utf-8")
    r = L.run(str(game))
    assert r["verdict"] == "PASS" and r["findings"] == []


def test_csharp_api_names_count(game):
    (game / "src" / "Credits.cs").write_text(
        "label.Text = Engine.GetLicenseText();\nthird.Text = Engine.GetLicenseInfo().ToString();\n", encoding="utf-8")
    assert L.run(str(game))["verdict"] == "PASS"


def test_print_only_with_ios_preset_is_a_concern(game):
    (game / "src" / "boot.gd").write_text(
        "func _ready() -> void:\n    print(Engine.get_license_text())\n    print(Engine.get_license_info())\n", encoding="utf-8")
    assert L.run(str(game))["verdict"] == "PASS"   # iOS 가 없으면 로그도 된다
    (game / "export_presets.cfg").write_text('[preset.0]\nname="iPhone"\nplatform="iOS"\n', encoding="utf-8")
    assert _rules(game) == ["GL003", "GL003"]


def test_commented_out_call_does_not_count(game):
    (game / "src" / "credits.gd").write_text("# $L.text = Engine.get_license_text()\n", encoding="utf-8")
    assert "GL001" in _rules(game)


def test_shipped_files_only_is_not_assessed(game):
    (game / "GODOT_LICENSE.txt").write_text("This game uses Godot Engine ...", encoding="utf-8")
    (game / "GODOT_COPYRIGHT.txt").write_text("...", encoding="utf-8")
    r = L.run(str(game))
    # 파일 안의 문구 자체가 godot:text 근거가 되므로 godot 쪽은 화면 경로로도 잡힌다 — 제3자 쪽만 파일뿐
    assert r["verdict"] == "NOT ASSESSED"
    assert _rules(game) == ["GL005"]


def test_addon_without_license_is_a_concern(game):
    (game / "src" / "credits.gd").write_text(
        "var a = Engine.get_license_text()\nvar b = Engine.get_license_info()\n", encoding="utf-8")
    (game / "addons" / "gdUnit4").mkdir(parents=True)
    (game / "addons" / "gdUnit4" / "LICENSE").write_text("MIT", encoding="utf-8")
    (game / "addons" / "mystery").mkdir()
    r = L.run(str(game))
    assert _rules(game) == ["GL004"]
    assert r["addons_licensed"] == ["gdUnit4"] and r["verdict"] == "CONCERNS"


def test_not_a_godot_project(tmp_path):
    r = L.run(str(tmp_path))
    assert r["verdict"] == "NOT ASSESSED" and "project.godot" in r["reason"]


def test_hidden_tool_folders_are_not_evidence(game):
    (game / ".claude" / "skills" / "x").mkdir(parents=True)
    (game / ".claude" / "skills" / "x" / "SKILL.md").write_text("Engine.get_license_text() godotengine.org/license",
                                                                encoding="utf-8")
    assert _rules(game) == ["GL001", "GL002"]


def test_license_link_in_credits_counts_as_godot_notice(game):
    (game / "src" / "credits.tscn").write_text('[node name="Link" type="LinkButton"]\nuri = "https://godotengine.org/license"\n',
                                               encoding="utf-8")
    (game / "src" / "credits.gd").write_text("var third = Engine.get_copyright_info()\n", encoding="utf-8")
    assert L.run(str(game))["verdict"] == "PASS"
