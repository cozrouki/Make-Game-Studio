"""prereq 테스트 — python -m pytest .agent/tools/setup/tests -q (네트워크 · GPU 불필요)."""
import hashlib
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import prereq  # noqa: E402


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Game"
    (root / "ProjectSettings").mkdir(parents=True)
    (root / "Packages").mkdir()
    (root / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.3.24f1\nm_EditorVersionWithRevision: 6000.3.24f1 (4e7b9b5b6244)\n", encoding="utf-8")
    (root / "Packages" / "manifest.json").write_text('{\n  "dependencies": {\n    "com.unity.ugui": "2.0.0"\n  }\n}\n',
                                                     encoding="utf-8")
    return root


def _ctx(root, **kw):
    return prereq.Ctx(str(root), kw.pop("roles", prereq.ROLES), **kw)


# ---- Unity ----
def test_prereq_unity_editor_found_in_secondary_install_path(project, tmp_path, monkeypatch):
    # Arrange
    editors = tmp_path / "Unity"
    (editors / "6000.3.24f1" / "Editor").mkdir(parents=True)
    (editors / "6000.3.24f1" / "Editor" / "Unity.exe").write_bytes(b"")
    monkeypatch.setattr(prereq, "unity_editor_dirs", lambda: [str(editors)])
    # Act
    status, detail = prereq.c_unity_editor(_ctx(project))
    # Assert
    assert status == "ok" and "6000.3.24f1" in detail


def test_prereq_unity_editor_missing_gives_hub_deep_link(project, monkeypatch):
    monkeypatch.setattr(prereq, "unity_editor_dirs", lambda: [])
    assert prereq.c_unity_editor(_ctx(project))[0] == "missing"
    assert prereq.m_unity_editor(_ctx(project)) == "Unity Hub 로 설치: unityhub://6000.3.24f1/4e7b9b5b6244"


def test_prereq_unity_mcp_package_is_inserted_once(project):
    ctx = _ctx(project)
    assert prereq.c_unity_mcp_pkg(ctx)[0] == "missing"
    prereq.i_unity_mcp_pkg(ctx, dry=False)
    manifest = json.loads((project / "Packages" / "manifest.json").read_text(encoding="utf-8"))
    assert "com.coplaydev.unity-mcp" in manifest["dependencies"] and "com.unity.ugui" in manifest["dependencies"]
    assert prereq.c_unity_mcp_pkg(ctx)[0] == "ok"


def test_prereq_mcp_server_found_in_claude_project_local_config(project, tmp_path, monkeypatch):
    # 회귀: 리허설은 .mcp.json 없이 ~/.claude.json projects.<경로>.mcpServers.UnityMCP 로 등록돼 있었는데 missing 으로 나왔다
    home = tmp_path / "home"
    home.mkdir()
    key = str(project).replace("\\", "/")
    (home / ".claude.json").write_text(json.dumps({"projects": {key: {"mcpServers": {"UnityMCP": {}}}}}), encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    status, detail = prereq.c_mcp_json(_ctx(project))
    assert status == "ok" and "UnityMCP" in detail


# ---- 생성 설정 ----
def test_prereq_needed_models_follow_config(project):
    ctx = _ctx(project)
    ctx.cfg["providers"]["comfyui"].update(graph="sdxl", removeBackground={"model": "birefnet.safetensors"})
    ctx.cfg["audio"]["providerByCategory"] = {"sfx": "library"}
    assert ctx.needed_models() == ["sdxl-base", "sdxl-vae", "birefnet", "ace-step-1.5"]
    ctx.cfg["providers"]["comfyui"]["graph"] = "z-image-turbo"
    ctx.cfg["audio"]["providerByCategory"] = {"sfx": "library", "music": "library", "ambience": "library"}
    assert ctx.needed_models() == ["z-image-unet", "z-image-clip", "z-image-vae", "birefnet"]


def test_prereq_model_size_mismatch_is_missing(project, tmp_path):
    home = tmp_path / "ComfyUI_windows_portable"
    (home / "ComfyUI" / "models" / "vae").mkdir(parents=True)
    (home / "ComfyUI" / "models" / "vae" / "sdxl_vae_fp16_fix.safetensors").write_bytes(b"partial")
    ctx = _ctx(project, comfyui_home=str(home))
    status, detail = prereq.c_model("sdxl-vae")(ctx)
    assert status == "missing" and "크기 불일치" in detail
    assert prereq.c_model("z-image-unet")(ctx)[0] == "skip"     # 기본 sdxl 설정에서는 안 씀


def test_prereq_local_config_merge_keeps_existing_keys(project, tmp_path):
    ctx = _ctx(project, comfyui_home=str(tmp_path / "Comfy"))
    os.makedirs(os.path.dirname(ctx.local_path))
    with open(ctx.local_path, "w", encoding="utf-8") as f:
        json.dump({"providers": {"comfyui": {"graph": "z-image-turbo"}}, "audio": {"python": "x"}}, f)
    ctx.local = prereq._read_json(ctx.local_path)
    prereq.i_local_config(ctx, dry=False)
    saved = prereq._read_json(ctx.local_path)
    assert saved["provider"] == "comfyui" and saved["providers"]["comfyui"]["graph"] == "z-image-turbo"
    assert saved["providers"]["comfyui"]["home"].endswith("Comfy") and saved["audio"]["python"] == "x"


def test_prereq_install_never_installs_license_decision_items(project, capsys):
    ctx = _ctx(project)
    args = type("A", (), {"items": ["stable-audio", "gamedesign"], "yes": True, "dry_run": True})()
    assert prereq.cmd_install(ctx, args) == 0
    out = capsys.readouterr().out
    assert "사용자 결정 항목이라 자동 설치하지 않음" in out and "설치할 항목 없음" in out


def test_prereq_roles_limit_items(project):
    rows = prereq.run_checks(_ctx(project, roles=["planning"]))
    ids = {r["id"] for r in rows}
    assert "gamedesign" in ids and "git" in ids
    assert not ids & {"unity-editor", "gpu", "sound-library"}     # dev · art 항목은 빠진다


# ---- 다운로드 ----
class _Files:
    """Range 를 지원하는 최소 서버. fail_once 면 첫 요청을 절반만 보내고 끊는다 (이어받기 확인)."""

    def __init__(self, data, fail_once=False):
        self.data, self.fail_once, self.ranges = data, fail_once, []
        files = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                start = int(self.headers["Range"].split("=")[1].rstrip("-")) if self.headers.get("Range") else 0
                files.ranges.append(start)
                body = files.data[start:]
                self.send_response(206 if start else 200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if files.fail_once:
                    files.fail_once = False
                    self.wfile.write(body[:len(body) // 2])
                    self.wfile.flush()
                    self.connection.close()
                    return
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/f.bin"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def test_prereq_download_resumes_after_cut_and_verifies_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(prereq.time, "sleep", lambda s: None)
    data = os.urandom(300_000)
    srv = _Files(data, fail_once=True)
    dest = tmp_path / "m" / "model.safetensors"
    prereq.download(srv.url, str(dest), len(data), hashlib.sha256(data).hexdigest())
    srv.server.shutdown()
    assert dest.read_bytes() == data and not (tmp_path / "m" / "model.safetensors.part").exists()
    assert srv.ranges[0] == 0 and srv.ranges[-1] > 0                # 두 번째 요청은 이어받기


def test_prereq_download_rejects_sha_mismatch(tmp_path):
    data = b"x" * 1000
    srv = _Files(data)
    dest = tmp_path / "model.safetensors"
    with pytest.raises(RuntimeError, match="SHA256 불일치"):
        prereq.download(srv.url, str(dest), len(data), "0" * 64)
    srv.server.shutdown()
    assert not dest.exists()                                         # 손상 파일을 최종 이름으로 두지 않는다


# ---- Android ----
def _prefs(root, platforms_line):
    docs = root / ".claude" / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "technical-preferences.md").write_text(f"## Input & Platform\n\n- **Target Platforms**: {platforms_line}\n",
                                                   encoding="utf-8")


def test_prereq_android_items_skip_when_not_targeted(project):
    _prefs(project, "PC (Windows)")
    rows = {r["id"]: r for r in prereq.run_checks(_ctx(project, roles=["dev"]))}
    assert {rows[i]["status"] for i in ("android-module", "adb", "android-catalog")} == {"skip"}


def test_prereq_android_target_detected_from_technical_preferences(project, tmp_path, monkeypatch):
    # Arrange — Android 모듈 · adb 가 있는 Unity 설치, 카탈로그 미러 없음
    _prefs(project, "iOS, Android (세로 고정)")
    editors = tmp_path / "Unity"
    tools = editors / "6000.3.24f1" / "Editor" / "Data" / "PlaybackEngines" / "AndroidPlayer" / "SDK" / "platform-tools"
    tools.mkdir(parents=True)
    (tools / ("adb.exe" if os.name == "nt" else "adb")).write_bytes(b"")
    monkeypatch.setattr(prereq, "unity_editor_dirs", lambda: [str(editors)])
    monkeypatch.setattr(prereq.shutil, "which", lambda name: None)
    # Act
    rows = {r["id"]: r for r in prereq.run_checks(_ctx(project, roles=["dev"]))}
    # Assert
    assert rows["android-module"]["status"] == "ok" and rows["adb"]["status"] == "ok"
    assert rows["android-catalog"]["status"] == "missing" and "sync-catalog.py android" in rows["android-catalog"]["manual"]


def test_prereq_platforms_flag_overrides_document(project):
    _prefs(project, "iOS, Android")
    ctx = _ctx(project, roles=["dev"], platforms=["ios"])
    assert not prereq.android_target(ctx)
    assert prereq.android_target(_ctx(project, roles=["dev"], platforms=["android"]))


def test_prereq_missing_editor_shows_hub_link_in_manual(project, monkeypatch):
    # 회귀: unity-editor 항목의 안내가 빈 문자열이라 unityhub:// 링크가 출력되지 않았다
    monkeypatch.setattr(prereq, "unity_editor_dirs", lambda: [])
    row = next(r for r in prereq.run_checks(_ctx(project, roles=["dev"])) if r["id"] == "unity-editor")
    assert row["manual"] == "Unity Hub 로 설치: unityhub://6000.3.24f1/4e7b9b5b6244"


# ---- 선택 항목 (graphify) ----
def test_prereq_optional_items_not_installed_by_default(project, monkeypatch, capsys):
    # Arrange — graphify 가 없어 자동 설치 후보가 되지만 선택 항목이다
    monkeypatch.setattr(prereq.shutil, "which", lambda name: "uv" if name == "uv" else None)
    ctx = _ctx(project, roles=["dev"])
    args = type("A", (), {"items": [], "yes": True, "dry_run": True})()
    # Act
    prereq.cmd_install(ctx, args)
    out = capsys.readouterr().out
    # Assert
    assert "graphify" not in out
    args.items = ["graphify"]
    prereq.cmd_install(ctx, args)
    assert "uv tool install graphifyy" in capsys.readouterr().out   # 이름을 주면 설치 대상


def test_prereq_graphify_warns_without_backend_none(project, monkeypatch):
    monkeypatch.setattr(prereq.shutil, "which", lambda name: "/bin/graphify" if name == "graphify" else None)
    monkeypatch.delenv("GRAPHIFY_BACKEND", raising=False)
    assert prereq.c_graphify(_ctx(project))[0] == "warn"
    monkeypatch.setenv("GRAPHIFY_BACKEND", "none")
    assert prereq.c_graphify(_ctx(project))[0] == "ok"


# ---- Unity 공식 분석기 ----
def test_prereq_unity_analyzers_requires_roslyn_label_and_ruleset(project):
    (project / "Assets" / "Analyzers").mkdir(parents=True)
    dll = project / "Assets" / "Analyzers" / "Microsoft.Unity.Analyzers.dll"
    dll.write_bytes(b"x")
    ctx = _ctx(project, roles=["dev"])
    assert prereq.c_unity_analyzers(ctx)[0] == "missing"                 # .meta 라벨 없음 → 분석기로 안 씀
    (project / "Assets" / "Analyzers" / "Microsoft.Unity.Analyzers.dll.meta").write_text(
        prereq.ANALYZER_META.format(guid=prereq.UNITY_ANALYZERS["guid"]), encoding="utf-8")
    assert prereq.c_unity_analyzers(ctx)[0] == "warn"                    # ruleset 없음
    (project / "Assets" / "Default.ruleset").write_text("<RuleSet/>", encoding="utf-8")
    assert prereq.c_unity_analyzers(ctx)[0] == "ok"


def test_prereq_unity_analyzers_meta_is_valid_roslyn_plugin():
    meta = prereq.ANALYZER_META.format(guid=prereq.UNITY_ANALYZERS["guid"])
    assert "- RoslynAnalyzer" in meta and "guid: b9fbeda283c554d29f25b4ebf23983c8" in meta
    assert meta.count("enabled: 0") == 2                                  # 모든 플랫폼 · 에디터에서 끔 (분석기 전용)


# ---- 엔진별 (Godot · Unreal — Unity 항목은 이름을 밝히고 건너뛴다) ----
@pytest.fixture
def godot_project(tmp_path):
    root = tmp_path / "GodotGame"
    root.mkdir()
    (root / "project.godot").write_text('config_version=5\n[application]\nconfig/features=PackedStringArray("4.7", "Forward Plus")\n',
                                        encoding="utf-8")
    return root


@pytest.fixture
def unreal_project(tmp_path):
    root = tmp_path / "UeGame"
    root.mkdir()
    (root / "UeGame.uproject").write_text('{\n  "FileVersion": 3,\n  "EngineAssociation": "5.8"\n}\n', encoding="utf-8")
    return root


def test_prereq_unity_items_skip_with_reason_on_godot(godot_project):
    rows = {r["id"]: r for r in prereq.run_checks(_ctx(godot_project, roles=["dev"]))}
    for i in ("unity-editor", "unity-mcp-pkg", "unity-analyzers", "mcp-json"):
        assert rows[i]["status"] == "skip"
        assert "godot" in rows[i]["detail"].lower()


def test_prereq_godot_editor_version_must_match_project(godot_project, tmp_path, monkeypatch):
    exe = tmp_path / ("godot.exe" if os.name == "nt" else "godot")
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(prereq.shutil, "which", lambda name: str(exe) if name.startswith("godot") else None)
    monkeypatch.setattr(prereq, "_run", lambda argv, timeout=20: (0, "4.6.2.stable.official.71f334935"))
    row = {r["id"]: r for r in prereq.run_checks(_ctx(godot_project, roles=["dev"]))}["godot-editor"]
    assert row["status"] == "missing" and "4.7" in row["detail"]

    monkeypatch.setattr(prereq, "_run", lambda argv, timeout=20: (0, "4.7.2.stable.official.abc"))
    row = {r["id"]: r for r in prereq.run_checks(_ctx(godot_project, roles=["dev"]))}["godot-editor"]
    assert row["status"] == "ok"


def test_prereq_gdunit4_missing_is_reported(godot_project):
    row = {r["id"]: r for r in prereq.run_checks(_ctx(godot_project, roles=["dev"]))}["gdunit4"]
    assert row["status"] == "missing"
    (godot_project / "addons" / "gdUnit4" / "bin").mkdir(parents=True)
    (godot_project / "addons" / "gdUnit4" / "bin" / "GdUnitCmdTool.gd").write_text("", encoding="utf-8")
    row = {r["id"]: r for r in prereq.run_checks(_ctx(godot_project, roles=["dev"]))}["gdunit4"]
    assert row["status"] == "ok"


def test_prereq_unreal_editor_found_for_engine_association(unreal_project, tmp_path, monkeypatch):
    base = tmp_path / "Epic Games"
    exe = base / "UE_5.8" / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(prereq, "UNREAL_INSTALL_DIRS", (str(base),))
    rows = {r["id"]: r for r in prereq.run_checks(_ctx(unreal_project, roles=["dev"]))}
    assert rows["unreal-editor"]["status"] == "ok"
    assert rows["unity-editor"]["status"] == "skip"
    assert rows["godot-editor"]["status"] == "skip"


def test_prereq_engine_items_skip_named_when_engine_unknown(tmp_path):
    rows = {r["id"]: r for r in prereq.run_checks(_ctx(tmp_path, roles=["dev"]))}
    assert rows["unity-editor"]["status"] == "skip"
    assert "엔진 미설정" in rows["unity-editor"]["detail"]


def test_prereq_engine_path_in_project_yaml_is_used(godot_project, tmp_path, monkeypatch):
    exe = tmp_path / "tools" / "Godot_v4.7.exe"
    exe.parent.mkdir()
    exe.write_text("", encoding="utf-8")
    (godot_project / "project.yaml").write_text(f'engine:\n  name: "Godot"\n  path: "{exe.as_posix()}"\n', encoding="utf-8")
    monkeypatch.setattr(prereq.shutil, "which", lambda name: None)
    monkeypatch.setattr(prereq, "_run", lambda argv, timeout=20: (0, "4.7.2.stable.official.abc"))
    row = {r["id"]: r for r in prereq.run_checks(_ctx(godot_project, roles=["dev"]))}["godot-editor"]
    assert row["status"] == "ok" and "Godot_v4.7.exe" in row["detail"]


def test_prereq_unreal_engine_path_root_is_used(unreal_project, tmp_path, monkeypatch):
    monkeypatch.setattr(prereq, "UNREAL_INSTALL_DIRS", ())   # 이 PC 의 실제 설치에 기대지 않게
    root = tmp_path / "UE_src"
    exe = root / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    (unreal_project / "project.yaml").write_text(f'engine:\n  name: "Unreal"\n  path: "{root.as_posix()}"\n', encoding="utf-8")
    row = {r["id"]: r for r in prereq.run_checks(_ctx(unreal_project, roles=["dev"]))}["unreal-editor"]
    assert row["status"] == "ok"
