"""ComfyUI 어댑터 테스트 — 가짜 ComfyUI HTTP 서버로 API 흐름을 검증 (실제 GPU 불필요)."""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

from artgen_lib import ArtgenError  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402
from artgen_lib.pngutil import read_info, write_rgba  # noqa: E402
from artgen_lib.providers.comfyui import build_default_graph, fill_workflow, gen_size  # noqa: E402
from artgen_lib.request import load_request  # noqa: E402
from artgen_lib.store import Store  # noqa: E402


class FakeComfy:
    """POST /prompt 로 받은 그래프를 기록하고, SaveImage 크기의 PNG 를 돌려주는 최소 서버."""

    def __init__(self, tmp_path, fail_with=None):
        self.prompts, self.fail_with = [], fail_with
        self.png = str(tmp_path / "out.png")
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, code, obj):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/system_stats":
                    return self._json(200, {"devices": [{"name": "cuda:0 Fake GPU"}]})
                if self.path.startswith("/history/"):
                    pid = self.path.rsplit("/", 1)[1]
                    if fake.fail_with:
                        return self._json(200, {pid: {"status": {"status_str": "error", "messages": [
                            ["execution_error", {"exception_message": fake.fail_with}]]}, "outputs": {}}})
                    return self._json(200, {pid: {"status": {"status_str": "success", "completed": True},
                                                  "outputs": {"save": {"images": [
                                                      {"filename": "a.png", "subfolder": "", "type": "output"}]}}}})
                if self.path.startswith("/view?"):
                    data = open(fake.png, "rb").read()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(data)
                    return None
                return self._json(404, {})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                graph = body["prompt"]
                if any("Bogus" in json.dumps(n) for n in graph.values()):
                    return self._json(400, {"error": {"message": "Invalid node"},
                                            "node_errors": {"x": {"errors": [{"message": "unknown class Bogus"}]}}})
                fake.prompts.append(graph)
                save = graph.get("scale", graph.get("decode"))
                w = save["inputs"].get("width", 32) if save else 32
                h = save["inputs"].get("height", 32) if save else 32
                write_rgba(fake.png, w, h, [(10, 20, 30, 255)] * (w * h))
                return self._json(200, {"prompt_id": f"p{len(fake.prompts)}"})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def project(tmp_path):
    (tmp_path / "Assets").mkdir()
    with open(os.path.join(TOOL_DIR, "schema", "example-request.json"), encoding="utf-8") as f:
        req = json.load(f)
    req["output"].update(width=64, height=64, variants=2, seed=100, transparent=False)
    path = tmp_path / "ASSET-001.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    return tmp_path, str(path)


def _cfg(url, **extra):
    cfg = load_config()
    cfg["providers"]["comfyui"] = dict({"url": url, "checkpoint": "sd_xl_base_1.0.safetensors"}, **extra)
    return cfg


def test_comfyui_gen_size_keeps_ratio_near_sdxl_area():
    assert gen_size(256, 256) == (1024, 1024)
    w, h = gen_size(512, 256)
    assert w % 64 == 0 and h % 64 == 0 and abs(w / h - 2) < 0.1


def test_comfyui_default_graph_scales_to_requested_size_and_uses_vae():
    g = build_default_graph({"checkpoint": "c.safetensors", "vae": "v.safetensors"}, "p", "n", 7, 256, 256, False)
    assert g["sample"]["inputs"]["seed"] == 7
    assert g["decode"]["inputs"]["vae"] == ["vae", 0]
    assert g["scale"]["inputs"]["width"] == 256 and g["save"]["inputs"]["images"] == ["scale", 0]
    assert "rmbg" not in g


def test_comfyui_default_graph_inserts_background_removal_when_transparent():
    g = build_default_graph({"checkpoint": "c", "removeBackground": {"model": "birefnet.safetensors"}},
                            "p", "n", 1, 256, 256, True)
    assert g["bg_model"]["inputs"]["bg_removal_name"] == "birefnet.safetensors"
    assert g["bg_mask"]["inputs"]["image"] == ["decode", 0]          # 축소 전 원본 해상도에서 제거
    assert g["bg_threshold"]["inputs"] == {"mask": ["bg_mask", 0], "value": 0.5}   # 내부 알파 254 → 255
    assert g["bg_invert"]["inputs"]["mask"] == ["bg_threshold", 0]   # JoinImageWithAlpha 가 1-mask 하므로 반전
    assert g["bg_join"]["inputs"] == {"image": ["decode", 0], "alpha": ["bg_invert", 0]}
    assert g["scale"]["inputs"]["image"] == ["bg_join", 0]


def test_comfyui_threshold_can_be_disabled():
    g = build_default_graph({"checkpoint": "c", "removeBackground": {"model": "b", "threshold": None}},
                            "p", "n", 1, 256, 256, True)
    assert "bg_threshold" not in g and g["bg_invert"]["inputs"]["mask"] == ["bg_mask", 0]


def test_comfyui_prompt_adapted_for_background_removal():
    g = build_default_graph({"checkpoint": "c", "removeBackground": {"model": "b"}},
                            "ice burst, isolated on transparent background", "text", 1, 256, 256, True)
    assert "plain flat white background" in g["pos"]["inputs"]["text"]
    assert "transparent" not in g["pos"]["inputs"]["text"]
    assert g["neg"]["inputs"]["text"].startswith("text, ") and "landscape" in g["neg"]["inputs"]["text"]


def test_comfyui_default_graph_skips_background_removal_when_opaque_requested():
    g = build_default_graph({"checkpoint": "c", "removeBackground": {"model": "b"}}, "p", "n", 1, 256, 256, False)
    assert "bg_mask" not in g


def test_comfyui_fill_workflow_keeps_numeric_tokens_numeric():
    wf = {"3": {"class_type": "KSampler", "inputs": {"seed": "{{seed}}", "note": "seed={{seed}}"}},
          "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{positive}}, extra"}}}
    out = fill_workflow(wf, {"positive": "a cat", "negative": "", "seed": 42, "width": 1, "height": 1,
                             "gen_width": 1, "gen_height": 1})
    assert out["3"]["inputs"]["seed"] == 42 and out["3"]["inputs"]["note"] == "seed=42"
    assert out["6"]["inputs"]["text"] == "a cat, extra"


def test_comfyui_generate_one_prompt_per_seed(project, tmp_path):
    root, req_path = project
    fake = FakeComfy(tmp_path)
    try:
        run = Store(str(root), _cfg(fake.url)).generate(load_request(req_path), req_path, provider_name="comfyui")
    finally:
        fake.close()
    assert [p["sample"]["inputs"]["seed"] for p in fake.prompts] == [100, 101]
    assert [o["file"] for o in run["outputs"]] == ["variant_01.png", "variant_02.png"]
    assert read_info(str(root / run["outDir"] / "variant_01.png"))[:2] == (64, 64)
    assert run["warnings"] == []


def test_comfyui_reports_execution_error(project, tmp_path):
    root, req_path = project
    fake = FakeComfy(tmp_path, fail_with="CUDA out of memory")
    try:
        with pytest.raises(ArtgenError, match="out of memory"):
            Store(str(root), _cfg(fake.url)).generate(load_request(req_path), req_path, provider_name="comfyui")
    finally:
        fake.close()


def test_comfyui_reports_rejected_workflow(project, tmp_path):
    root, req_path = project
    fake = FakeComfy(tmp_path)
    rb = {"model": "Bogus.safetensors"}
    req = json.loads(open(req_path, encoding="utf-8").read())
    req["output"]["transparent"] = True
    open(req_path, "w", encoding="utf-8").write(json.dumps(req))
    try:
        with pytest.raises(ArtgenError, match="Bogus"):
            Store(str(root), _cfg(fake.url, removeBackground=rb)).generate(load_request(req_path), req_path,
                                                                          provider_name="comfyui")
    finally:
        fake.close()


def test_comfyui_check_fails_cleanly_when_server_down():
    from artgen_lib.providers.comfyui import ComfyUIProvider
    ok, msg = ComfyUIProvider({"url": "http://127.0.0.1:9", "checkpoint": "c"}).check()
    assert not ok and "run_nvidia_gpu" in msg
