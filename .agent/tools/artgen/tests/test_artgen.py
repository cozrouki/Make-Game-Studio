"""artgen 단위 테스트 — python -m pytest .agent/tools/artgen/tests -q"""
import json
import os
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

from artgen_lib import ArtgenError  # noqa: E402
from artgen_lib import providers as registry  # noqa: E402
from artgen_lib.cli import main  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402
from artgen_lib.pngutil import read_info  # noqa: E402
from artgen_lib.request import compile_prompt, load_request, normalize_request, validate_request  # noqa: E402
from artgen_lib.store import Store  # noqa: E402

EXAMPLE = os.path.join(TOOL_DIR, "schema", "example-request.json")


def _example():
    with open(EXAMPLE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def project(tmp_path):
    """Assets/ 가 있는 가짜 Unity 프로젝트 + 작은 요청 파일."""
    (tmp_path / "Assets").mkdir()
    req = _example()
    req["output"].update(width=32, height=32, variants=2, seed=7)
    path = tmp_path / "ASSET-001.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    return tmp_path, str(path)


@pytest.fixture
def cfg():
    c = load_config()
    c["provider"] = "mock"
    return c


# ---- 요청 검증 ----
def test_example_request_is_valid():
    assert validate_request(_example()) == []


@pytest.mark.parametrize("mutate, needle", [
    (lambda r: r.update(assetId="A1"), "assetId"),
    (lambda r: r.update(category="mesh"), "category"),
    (lambda r: r["prompt"].update(subject=""), "subject"),
    (lambda r: r["prompt"].update(palette=["blue"]), "palette"),
    (lambda r: r["output"].update(width=8), "output.width"),
    (lambda r: r["output"].update(variants=0), "variants"),
    (lambda r: r["unity"].update(dest="../outside.png"), "unity.dest"),
    (lambda r: r["unity"].update(dest="Assets/../x.png"), "unity.dest"),
    (lambda r: r["unity"]["import"].update(filterMode="Nearest"), "filterMode"),
    (lambda r: r["unity"]["import"].update(maxSize=300), "maxSize"),
    (lambda r: r["unity"]["import"].update(bogus=1), "bogus"),
])
def test_invalid_requests_are_rejected(mutate, needle):
    req = _example()
    mutate(req)
    errors = validate_request(req)
    assert any(needle in e for e in errors), errors


def test_compile_prompt_includes_style_palette_and_transparency():
    p = compile_prompt(normalize_request(_example()))
    assert p["positive"].startswith("a burst of jagged ice shards")
    assert "thick dark outline" in p["positive"]
    assert "#4FA8D8" in p["positive"]
    assert "transparent background" in p["positive"]
    assert "watermark" in p["negative"]


# ---- 레지스트리 ----
def test_registry_discovers_builtin_adapters_but_not_template():
    names = set(registry.discover())
    assert {"mock", "command"} <= names
    assert "template" not in names


def test_command_provider_not_ready_without_argv(cfg):
    ok, msg = registry.create("command", cfg).check()
    assert not ok and "argv" in msg


def test_unknown_provider_raises(cfg):
    with pytest.raises(ArtgenError):
        registry.create("nope", cfg)


# ---- 저장소: 생성 → 선택 → 승격 ----
def test_generate_select_promote_roundtrip(project, cfg):
    root, req_path = project
    store = Store(str(root), cfg)
    req = load_request(req_path)

    run = store.generate(req, req_path)
    assert run["version"] == "v001"
    assert [o["seed"] for o in run["outputs"]] == [7, 8]
    assert run["warnings"] == []
    first = os.path.join(root, run["outDir"], run["outputs"][0]["file"])
    assert read_info(first) == (32, 32, True)

    run2 = store.generate(req, req_path)
    assert run2["version"] == "v002"

    store.select("ASSET-001", "v002", "variant_02.png")
    state = store.promote(req)
    dest = root / "Assets" / "MyGame" / "Art" / "VFX" / "vfx_frost_hit_01.png"
    assert dest.is_file()
    assert state["status"] == "promoted"

    imap = json.loads((root / "production" / "artgen" / "import-map.json").read_text(encoding="utf-8"))
    entry = imap["entries"][0]
    assert entry["path"] == "Assets/MyGame/Art/VFX/vfx_frost_hit_01.png"
    assert entry["maxSize"] == 256          # 요청값
    assert entry["wrapMode"] == "Clamp"     # 기본값이 빠짐없이 채워짐
    assert entry["sRGB"] is True


def test_promote_refuses_overwrite_without_force_and_backs_up_with_force(project, cfg):
    root, req_path = project
    store = Store(str(root), cfg)
    req = load_request(req_path)
    store.generate(req, req_path)
    store.select("ASSET-001", "v001", "variant_01.png")
    store.promote(req)
    with pytest.raises(ArtgenError, match="--force"):
        store.promote(req)
    state = store.promote(req, force=True)
    assert state["promoted"]["backup"]
    assert os.path.isfile(os.path.join(root, state["promoted"]["backup"]))
    imap = json.loads((root / "production" / "artgen" / "import-map.json").read_text(encoding="utf-8"))
    assert len(imap["entries"]) == 1        # 같은 경로는 upsert


def test_promote_requires_selection(project, cfg):
    root, req_path = project
    store = Store(str(root), cfg)
    req = load_request(req_path)
    store.generate(req, req_path)
    with pytest.raises(ArtgenError, match="select"):
        store.promote(req)


def test_promote_requires_unity_project(tmp_path, cfg):
    req = _example()
    req["output"].update(width=16, height=16, variants=1)
    path = tmp_path / "r.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    store = Store(str(tmp_path), cfg)
    r = load_request(str(path))
    store.generate(r, str(path))
    store.select("ASSET-001", "v001", "variant_01.png")
    with pytest.raises(ArtgenError, match="Assets"):
        store.promote(r)


def test_dry_run_writes_nothing(project, cfg):
    root, req_path = project
    plan = Store(str(root), cfg).generate(load_request(req_path), req_path, dry_run=True)
    assert plan["dryRun"] and plan["version"] == "v001"
    assert not (root / "production").exists()


def test_reject_then_select_clears_reason(project, cfg):
    root, req_path = project
    store = Store(str(root), cfg)
    store.generate(load_request(req_path), req_path)
    assert store.reject("ASSET-001", "실루엣이 약함")["status"] == "rejected"
    state = store.select("ASSET-001", "v001", "variant_01.png")
    assert "rejectReason" not in state


# ---- command 어댑터: 외부 프로그램 계약 ----
def test_command_provider_runs_external_program(project, cfg, tmp_path_factory):
    root, req_path = project
    script = tmp_path_factory.mktemp("backend") / "fake_backend.py"
    script.write_text(
        "import json, sys, os\n"
        f"sys.path.insert(0, {TOOL_DIR!r})\n"
        "from artgen_lib.pngutil import write_rgba\n"
        "job = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "for i, s in enumerate(job['seeds']):\n"
        "    write_rgba(os.path.join(sys.argv[2], f'out_{i}.png'), job['width'], job['height'],\n"
        "               [(s % 256, 0, 0, 255)] * (job['width'] * job['height']), alpha=False)\n",
        encoding="utf-8")
    cfg["providers"]["command"]["argv"] = [sys.executable, str(script), "{job_file}", "{out_dir}"]
    run = Store(str(root), cfg).generate(load_request(req_path), req_path, provider_name="command")
    assert [o["file"] for o in run["outputs"]] == ["out_0.png", "out_1.png"]
    assert any("알파 채널 없음" in w for w in run["warnings"])  # transparent 요청 vs RGB 출력 → 경고만 (차단 X)


def test_command_provider_failure_is_reported(project, cfg):
    root, req_path = project
    cfg["providers"]["command"]["argv"] = [sys.executable, "-c", "import sys; sys.exit(3)"]
    with pytest.raises(ArtgenError, match="exit 3"):
        Store(str(root), cfg).generate(load_request(req_path), req_path, provider_name="command")
    run = json.loads((root / "production" / "artgen" / "ASSET-001" / "v001" / "run.json").read_text(encoding="utf-8"))
    assert "error" in run


# ---- manual 어댑터: 사람 아티스트 납품 ----
def test_manual_provider_empty_inbox_reports_drop_location(project, cfg):
    root, req_path = project
    with pytest.raises(ArtgenError, match=r"_inbox"):
        Store(str(root), cfg).generate(load_request(req_path), req_path, provider_name="manual")
    assert (root / "production" / "artgen" / "_inbox" / "ASSET-001").is_dir()   # 넣을 곳을 만들어 둠


def test_manual_provider_moves_delivery_into_version_without_count_warning(project, cfg):
    from artgen_lib.pngutil import write_rgba
    root, req_path = project
    inbox = root / "production" / "artgen" / "_inbox" / "ASSET-001"
    inbox.mkdir(parents=True)
    write_rgba(str(inbox / "frost_hit_a.png"), 32, 32, [(0, 0, 0, 0)] * 1024)   # 요청 variants=2 인데 1장 납품

    run = Store(str(root), cfg).generate(load_request(req_path), req_path, provider_name="manual")

    assert [o["file"] for o in run["outputs"]] == ["frost_hit_a.png"]
    assert run["warnings"] == []
    assert not list(inbox.glob("*.png"))                                         # 받은함은 비워짐
    assert (root / run["outDir"] / "frost_hit_a.png").is_file()


# ---- CLI ----
def test_cli_json_error_exit_code(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--json", "validate", str(tmp_path / "missing.json")]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["results"][0]["ok"] is False


# ---- 엔진별 승격 (Godot · Unreal — 파일 승격까지, 임포트 설정은 엔진 쪽 수동) ----
def _generated_store(tmp_path, cfg, marker, dest):
    marker(tmp_path)
    req = _example()
    req["output"].update(width=16, height=16, variants=1)
    req["unity"]["dest"] = dest
    path = tmp_path / "r.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    store = Store(str(tmp_path), cfg)
    r = load_request(str(path))
    store.generate(r, str(path))
    store.select("ASSET-001", "v001", "variant_01.png")
    return store, r


def test_promote_godot_copies_file_without_unity_import_map(tmp_path, cfg):
    store, r = _generated_store(tmp_path, cfg, lambda p: (p / "project.godot").write_text("", encoding="utf-8"),
                                "assets/vfx/frost_hit.png")
    state = store.promote(r)
    assert (tmp_path / "assets" / "vfx" / "frost_hit.png").is_file()
    assert state["promoted"]["engine"] == "godot"
    assert not os.path.exists(store.import_map_path)


def test_promote_unreal_copies_file_and_marks_manual_import(tmp_path, cfg):
    store, r = _generated_store(tmp_path, cfg, lambda p: (p / "Game.uproject").write_text("{}", encoding="utf-8"),
                                "Content/Import/VFX/frost_hit.png")
    state = store.promote(r)
    assert (tmp_path / "Content" / "Import" / "VFX" / "frost_hit.png").is_file()
    assert state["promoted"]["engine"] == "unreal"
    assert state["promoted"]["importManual"] is True


def test_promote_unity_dest_outside_assets_is_refused(tmp_path, cfg):
    store, r = _generated_store(tmp_path, cfg, lambda p: (p / "Assets").mkdir(), "Content/x.png")
    with pytest.raises(ArtgenError, match="Assets"):
        store.promote(r)


def test_project_yaml_engine_wins_over_markers(tmp_path):
    from artgen_lib.store import detect_engine
    (tmp_path / "Assets").mkdir()
    (tmp_path / "project.yaml").write_text('engine:\n  name: "Godot"\n  version: "4.7"\n', encoding="utf-8")
    assert detect_engine(str(tmp_path)) == "godot"
