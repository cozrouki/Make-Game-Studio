"""pixelfx 어댑터 테스트 — python -m pytest .agent/tools/artgen/tests -q

Node 없이: `node` 자리에 현재 Python 을 넣고 render.mjs · check.mjs 를 같은 계약의 Python 스크립트로 바꾼다.
실제 pixelfx: 환경변수 PIXELFX_DIR(prereq.py install pixelfx 로 받은 폴더)과 PATH 의 Node 18+ 가 있을 때만 돈다.
"""
import json
import os
import shutil
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

from artgen_lib import ArtgenError  # noqa: E402
from artgen_lib import providers as registry  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402
from artgen_lib.providers import pixelfx as pfx  # noqa: E402
from artgen_lib.store import Store, sheet_summary  # noqa: E402

# 가짜 render.mjs — 2열 × 2행, 프레임 4x3, 시드가 픽셀 값에 들어간다. 받은 인자를 argv.log 에 남긴다
FAKE_RENDER = r'''
import json, os, sys
sys.path.insert(0, {tool_dir!r})
from artgen_lib.pngutil import write_rgba
args = sys.argv[1:]
effect = args[0]
flags = {{}}
i = 1
while i < len(args):
    if args[i] in ("--sheet", "--no-actor"):
        flags[args[i][2:]] = True
        i += 1
    else:
        flags[args[i][2:]] = args[i + 1]
        i += 2
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(root, "argv.log"), "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")
cat, name = effect.split("/")
out = os.path.join(flags["out"], cat, name)
os.makedirs(out, exist_ok=True)
seed = int(flags.get("seed", 0))
fps = int(flags.get("fps", 30))
write_rgba(os.path.join(out, name + ".png"), 8, 6, [(seed % 256, 10, 20, 255)] * 48)
frames = [{{"filename": f"{{name}} {{k}}", "frame": {{"x": (k % 2) * 4, "y": (k // 2) * 3, "w": 4, "h": 3}},
           "duration": 1000 // fps}} for k in range(4)]
meta = {{"image": name + ".png", "size": {{"w": 8, "h": 6}},
        "pixelfx": {{"id": effect, "fps": fps, "loop": True, "frames": 4, "frameSize": [4, 3], "pivot": [2, 3],
                    "columns": 2}}}}
with open(os.path.join(out, name + ".json"), "w", encoding="utf-8") as f:
    json.dump({{"frames": frames, "meta": meta}}, f)
'''

# 가짜 check.mjs — 루트의 check_mode 파일(ok · warn · fail)대로 출력
FAKE_CHECK = r'''
import os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mode = open(os.path.join(root, "check_mode")).read().strip() if os.path.exists(os.path.join(root, "check_mode")) else "ok"
if mode == "ok":
    print("ok    " + sys.argv[1])
elif mode == "warn":
    print("warn  " + sys.argv[1] + "\n      loop seam: 3 px")
else:
    print("FAIL  " + sys.argv[1] + "\n      draws 12 px outside the canvas")
    sys.exit(1)
'''


@pytest.fixture
def fake_pixelfx(tmp_path, monkeypatch):
    root = tmp_path / "art-source" / "pixelfx"
    (root / "tools").mkdir(parents=True)
    (root / "src" / "fx" / "ice").mkdir(parents=True)
    (root / "src" / "fx" / "arcane").mkdir(parents=True)
    (root / "tools" / "render.mjs").write_text(FAKE_RENDER.format(tool_dir=TOOL_DIR), encoding="utf-8")
    (root / "tools" / "check.mjs").write_text(FAKE_CHECK, encoding="utf-8")
    (root / "src" / "fx" / "ice" / "frost-nova.js").write_text("// frost\n", encoding="utf-8")
    (root / "src" / "fx" / "arcane" / "arcane-beam.js").write_text(
        "// adapted from Sprite Fusion's open-source energy beam, MIT License\n", encoding="utf-8")
    (root / ".pixelfx-commit").write_text("044e12a45dc9cc312cec50ee606dfc98afe5adc2\n", encoding="utf-8")
    monkeypatch.setattr(pfx, "_node_version", lambda node: (22, 14))
    return root


@pytest.fixture
def cfg():
    c = load_config()
    c["provider"] = "mock"
    c.setdefault("providers", {})["pixelfx"] = {"node": sys.executable}
    return c


def _project(tmp_path, engine="unity", effect="ice/frost-nova", **pfx_opts):
    if engine == "unity":
        (tmp_path / "Assets").mkdir(exist_ok=True)
        dest = "Assets/Art/Vfx/frost.png"
    else:
        (tmp_path / "project.godot").write_text("", encoding="utf-8")
        dest = "art/vfx/frost.png"
    req = {"schema": "artgen-request/1", "assetId": "ASSET-010", "name": "Frost nova", "category": "vfx",
           "prompt": {"subject": "frost nova", "palette": ["#FFFFFF", "#000000", "#4FA8D8"]},
           "output": {"width": 64, "height": 64, "transparent": True, "variants": 2, "seed": 7},
           "unity": {"dest": dest}, "providerOptions": {"pixelfx": dict(effect=effect, **pfx_opts)}}
    path = tmp_path / "ASSET-010.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    return str(path)


def _load(path):
    from artgen_lib.request import load_request
    return load_request(path)


def _argv_log(root):
    return [json.loads(ln) for ln in (root / "argv.log").read_text(encoding="utf-8").splitlines()]


# ---- 순수 함수 ----
def test_palette_ramp_sorts_dark_to_bright():
    assert pfx.palette_ramp(["#FFFFFF", "#000000", "#4FA8D8"]) == ["#000000", "#4FA8D8", "#FFFFFF"]


def test_sheet_summary_reports_grid_mismatch():
    sheet = {"frames": [{}] * 4, "meta": {"pixelfx": {"frameSize": [4, 3], "columns": 2, "frames": 4, "pivot": [2, 3]}}}
    summary, problems = sheet_summary(sheet, 8, 6)
    assert summary["frames"] == 4 and problems == []
    _, problems = sheet_summary(sheet, 16, 6)
    assert any("격자" in p for p in problems)
    _, problems = sheet_summary({"frames": [], "meta": {}}, 8, 6)
    assert any("frameSize" in p for p in problems)


def test_registry_discovers_pixelfx():
    assert "pixelfx" in registry.discover()


# ---- 준비 상태 ----
def test_check_reports_missing_install(tmp_path, cfg):
    p = registry.create("pixelfx", cfg, project_root=str(tmp_path))
    ok, msg = p.check()
    assert not ok and "prereq.py install pixelfx" in msg


def test_check_rejects_old_node(tmp_path, cfg, fake_pixelfx, monkeypatch):
    monkeypatch.setattr(pfx, "_node_version", lambda node: (16, 20))
    ok, msg = registry.create("pixelfx", cfg, project_root=str(tmp_path)).check()
    assert not ok and "18" in msg


# ---- 생성 ----
def test_generate_writes_sheet_sidecars_without_size_warning(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path)
    run = Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx")
    assert [o["file"] for o in run["outputs"]] == ["variant_01.png", "variant_02.png"]
    assert run["warnings"] == []  # 64x64 요청이어도 크기는 효과가 정한다
    out = run["outputs"][0]
    assert out["sheet"] == {"frames": 4, "columns": 2, "frameWidth": 4, "frameHeight": 3, "fps": 30, "loop": True,
                            "pivot": [2, 3], "effect": "ice/frost-nova"}
    assert out["source"]["license"] == "MIT" and out["source"]["commit"].startswith("044e12a")
    vdir = tmp_path / run["outDir"]
    sheet = json.loads((vdir / "variant_02.sheet.json").read_text(encoding="utf-8"))
    assert sheet["meta"]["image"] == "variant_02.png" and sheet["meta"]["pixelfx"]["seed"] == 8
    assert not (vdir / "_pixelfx").exists()
    calls = _argv_log(fake_pixelfx)
    assert [c[c.index("--seed") + 1] for c in calls] == ["7", "8"]
    # 팔레트는 밝기 순으로 효과에 전달된다
    assert json.loads(calls[0][calls[0].index("--opts") + 1])["palette"] == ["#000000", "#4FA8D8", "#FFFFFF"]


def test_explicit_options_palette_wins_and_fps_is_passed(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path, options={"palette": ["#112233"], "light": 0.5}, fps=12)
    run = Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx", variants=1)
    call = _argv_log(fake_pixelfx)[0]
    assert json.loads(call[call.index("--opts") + 1]) == {"palette": ["#112233"], "light": 0.5}
    assert call[call.index("--fps") + 1] == "12"
    assert run["outputs"][0]["sheet"]["fps"] == 12


@pytest.mark.parametrize("effect, needle", [
    (None, "effect 필수"),
    ("ice/*", "effect 필수"),          # 패턴 · 분류 전체 렌더 차단
    ("ice", "effect 필수"),
    ("ice/no-such", "효과 없음"),       # render.mjs 는 없는 id 에도 exit 0
])
def test_bad_effect_is_rejected_before_render(tmp_path, cfg, fake_pixelfx, effect, needle):
    req_path = _project(tmp_path, effect=effect)
    with pytest.raises(ArtgenError, match=needle):
        Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx")
    assert not (fake_pixelfx / "argv.log").exists()


def test_bad_fps_is_rejected(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path, fps=0)
    with pytest.raises(ArtgenError, match="fps"):
        Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx")


def test_upstream_notice_is_added_to_attribution(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path, effect="arcane/arcane-beam")
    run = Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx", variants=1)
    assert "Hugo Duprez" in run["outputs"][0]["source"]["attribution"]


@pytest.mark.parametrize("mode, expect", [("ok", []), ("warn", ["pixelfx check: loop seam: 3 px"])])
def test_effect_check_notes_become_warnings(tmp_path, cfg, fake_pixelfx, mode, expect):
    (fake_pixelfx / "check_mode").write_text(mode, encoding="utf-8")
    req_path = _project(tmp_path)
    run = Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx", variants=1)
    assert run["warnings"] == expect


def test_effect_check_failure_is_a_warning_not_an_error(tmp_path, cfg, fake_pixelfx):
    (fake_pixelfx / "check_mode").write_text("fail", encoding="utf-8")
    req_path = _project(tmp_path)
    run = Store(str(tmp_path), cfg).generate(_load(req_path), req_path, provider_name="pixelfx", variants=1)
    assert len(run["warnings"]) == 1 and "check 실패" in run["warnings"][0] and "outside" in run["warnings"][0]


# ---- 승격 ----
def _generate_and_select(tmp_path, cfg, req_path):
    store = Store(str(tmp_path), cfg)
    run = store.generate(_load(req_path), req_path, provider_name="pixelfx")
    store.select("ASSET-010", run["version"], "variant_02.png")
    return store


def test_promote_unity_writes_sheet_import_entry_json_and_credit(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path)
    store = _generate_and_select(tmp_path, cfg, req_path)
    state = store.promote(_load(req_path))
    assert state["promoted"]["sheetJson"] == "Assets/Art/Vfx/frost.json"
    sheet = json.loads((tmp_path / "Assets/Art/Vfx/frost.json").read_text(encoding="utf-8"))
    assert sheet["meta"]["image"] == "frost.png"
    entry = json.loads((tmp_path / "production/artgen/import-map.json").read_text(encoding="utf-8"))["entries"][0]
    assert entry["spriteMode"] == "Multiple" and entry["filterMode"] == "Point" and entry["compression"] == "None"
    assert entry["mipmaps"] is False and entry["maxSize"] == 32
    assert (entry["sheetFrames"], entry["sheetColumns"], entry["frameWidth"], entry["frameHeight"]) == (4, 2, 4, 3)
    assert (entry["pivotX"], entry["pivotY"]) == (0.5, 0.0)  # 왼쪽 위 (2,3) → Unity 왼쪽 아래 기준
    assert entry["sheetName"] == "frost"
    credit = json.loads((tmp_path / "production/artgen/credits.json").read_text(encoding="utf-8"))["entries"][0]
    assert credit["library"] == "pixelfx" and credit["path"] == "Assets/Art/Vfx/frost.png"


def test_promote_request_import_overrides_sheet_defaults_but_not_below_sheet_size(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path)
    req = json.loads(open(req_path, encoding="utf-8").read())
    req["unity"]["import"] = {"filterMode": "Bilinear", "pixelsPerUnit": 16}
    open(req_path, "w", encoding="utf-8").write(json.dumps(req))
    store = _generate_and_select(tmp_path, cfg, req_path)
    store.promote(_load(req_path))
    entry = json.loads((tmp_path / "production/artgen/import-map.json").read_text(encoding="utf-8"))["entries"][0]
    assert entry["filterMode"] == "Bilinear" and entry["pixelsPerUnit"] == 16 and entry["spriteMode"] == "Multiple"


def test_promote_refuses_max_size_smaller_than_sheet(tmp_path, cfg, fake_pixelfx, monkeypatch):
    req_path = _project(tmp_path)
    store = _generate_and_select(tmp_path, cfg, req_path)
    # 큰 시트를 흉내 — run.json 의 시트 요약을 키운다
    run_path = next((tmp_path / "production/artgen/ASSET-010").glob("v*/run.json"))
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["outputs"][1]["sheet"].update(frameWidth=288, frameHeight=192, frames=103, columns=9)
    run_path.write_text(json.dumps(run), encoding="utf-8")
    req = _load(req_path)
    req["unity"]["import"] = {"maxSize": 2048}
    with pytest.raises(ArtgenError, match="maxSize 2048 < 시트 2592"):
        store.promote(req)
    assert not (tmp_path / "Assets/Art/Vfx/frost.png").exists()
    req["unity"]["import"] = {}
    store.promote(req)
    entry = json.loads((tmp_path / "production/artgen/import-map.json").read_text(encoding="utf-8"))["entries"][0]
    assert entry["maxSize"] == 4096


def test_promote_sheet_pair_needs_force_and_backs_up_both(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path)
    store = _generate_and_select(tmp_path, cfg, req_path)
    (tmp_path / "Assets/Art/Vfx").mkdir(parents=True)
    (tmp_path / "Assets/Art/Vfx/frost.json").write_text("{}", encoding="utf-8")  # PNG 없이 JSON 만 있어도 막는다
    with pytest.raises(ArtgenError, match="frost.json"):
        store.promote(_load(req_path))
    state = store.promote(_load(req_path), force=True)
    assert [os.path.basename(b).split("-", 2)[-1] for b in state["promoted"]["backups"]] == ["frost.json"]
    state = store.promote(_load(req_path), force=True)
    assert sorted(os.path.basename(b).split("-", 2)[-1] for b in state["promoted"]["backups"]) == ["frost.json", "frost.png"]


def test_promote_godot_copies_png_and_json_without_import_map(tmp_path, cfg, fake_pixelfx):
    req_path = _project(tmp_path, engine="godot")
    store = _generate_and_select(tmp_path, cfg, req_path)
    state = store.promote(_load(req_path))
    assert state["promoted"]["importManual"] is True
    assert (tmp_path / "art/vfx/frost.png").is_file() and (tmp_path / "art/vfx/frost.json").is_file()
    assert not (tmp_path / "production/artgen/import-map.json").exists()


# ---- 실제 pixelfx (선택) ----
REAL = os.environ.get("PIXELFX_DIR")


@pytest.mark.skipif(not REAL or not shutil.which("node"), reason="PIXELFX_DIR 와 Node 18+ 가 있을 때만")
def test_real_pixelfx_same_seed_same_bytes(tmp_path):
    c = load_config()
    c.setdefault("providers", {})["pixelfx"] = {"dir": REAL}
    (tmp_path / "Assets").mkdir()
    req_path = _project(tmp_path, effect="fire/torch", fps=12)
    store = Store(str(tmp_path), c)
    a = store.generate(_load(req_path), req_path, provider_name="pixelfx", variants=1)
    b = store.generate(_load(req_path), req_path, provider_name="pixelfx", variants=1)
    assert a["outputs"][0]["sha256"] == b["outputs"][0]["sha256"]
    assert a["outputs"][0]["sheet"]["fps"] == 12
    assert not [w for w in a["warnings"] if "실패" in w]
