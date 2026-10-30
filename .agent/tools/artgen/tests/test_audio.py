"""artgen 오디오 테스트 — 요청 검증 · mock 생성 · 승격 · ComfyUI 오디오 그래프 · 후처리.

후처리(audio_post)는 PyAV + numpy 가 있는 인터프리터가 필요하다. ARTGEN_TEST_AUDIO_PYTHON 이나
ComfyUI 포터블 기본 경로에서 찾고, 없으면 그 테스트만 건너뛴다.
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

from artgen_lib import ArtgenError  # noqa: E402
from artgen_lib.audioutil import analyze, write_wav  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402
from artgen_lib.providers.base import Job  # noqa: E402
from artgen_lib.providers.comfyui import build_audio_graph  # noqa: E402
from artgen_lib.request import compile_prompt, load_request, normalize_request, validate_request  # noqa: E402
from artgen_lib.store import AUDIO_POST, Store  # noqa: E402

EXAMPLE = os.path.join(TOOL_DIR, "schema", "example-audio-request.json")


def _example():
    with open(EXAMPLE, encoding="utf-8") as f:
        return json.load(f)


def _audio_python():
    cands = [os.environ.get("ARTGEN_TEST_AUDIO_PYTHON", ""),
             r"D:\AI\ComfyUI_windows_portable\python_embeded\python.exe"]
    for exe in cands:
        if exe and os.path.isfile(exe):
            ok = subprocess.run([exe, "-c", "import av, numpy"], capture_output=True).returncode == 0
            if ok:
                return exe
    return None


AUDIO_PY = _audio_python()
needs_audio_py = pytest.mark.skipif(AUDIO_PY is None, reason="PyAV + numpy 인터프리터 없음")


@pytest.fixture
def cfg():
    c = load_config()
    c["provider"] = "mock"
    c["audio"]["providerByCategory"] = {}  # 효과음 → library 자동 연결은 test_library.py 에서 본다
    return c


def _write_request(tmp_path, mutate=None, name="ASSET-201.json"):
    req = _example()
    req["output"].update(durationSec=1.5, variants=1, seed=3)
    if mutate:
        mutate(req)
    path = tmp_path / name
    path.write_text(json.dumps(req), encoding="utf-8")
    return str(path)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "Assets").mkdir()
    return tmp_path


# ---- 요청 ----
def test_example_audio_request_is_valid():
    assert validate_request(_example()) == []


@pytest.mark.parametrize("mutate, needle", [
    (lambda r: r["output"].pop("durationSec"), "durationSec"),
    (lambda r: r["output"].update(durationSec=0), "durationSec"),
    (lambda r: r["output"].update(width=64), "output.width"),
    (lambda r: r["output"].update(channels=6), "channels"),
    (lambda r: r["output"].update(sampleRate=22050), "sampleRate"),
    (lambda r: r["prompt"].update(palette=["#FFFFFF"]), "palette"),
    (lambda r: r["prompt"].update(tempo=500), "tempo"),
    (lambda r: r["prompt"].update(key="Dmaj"), "prompt.key"),
    (lambda r: r["unity"].update(dest="Assets/a.png"), ".wav"),
    (lambda r: r["unity"]["import"].update(textureType="Sprite"), "textureType"),
    (lambda r: r["unity"]["import"].update(loadType="Stream"), "loadType"),
    (lambda r: r["unity"]["import"].update(quality=2), "quality"),
])
def test_invalid_audio_requests_are_rejected(mutate, needle):
    req = _example()
    mutate(req)
    assert any(needle in e for e in validate_request(req)), validate_request(req)


def test_image_request_cannot_use_wav_dest():
    with open(os.path.join(TOOL_DIR, "schema", "example-request.json"), encoding="utf-8") as f:
        req = json.load(f)
    req["unity"]["dest"] = "Assets/a.wav"
    assert any(".png" in e for e in validate_request(req))


@pytest.mark.parametrize("category, loop, channels", [("sfx", False, 1), ("music", True, 2), ("ambience", True, 2)])
def test_category_defaults(category, loop, channels):
    req = _example()
    req["category"] = category
    for k in ("loop", "channels"):
        req["output"].pop(k)
    o = normalize_request(req)["output"]
    assert (o["loop"], o["channels"], o["format"]) == (loop, channels, "wav")


def test_audio_prompt_carries_tempo_key_and_loop():
    p = compile_prompt(normalize_request(_example()))
    assert "90 BPM" in p["positive"] and "D major" in p["positive"] and "seamless loop" in p["positive"]
    assert "vocals" in p["negative"]


# ---- 생성 · 승격 (mock) ----
@pytest.mark.parametrize("category", ["music", "sfx"])
def test_mock_audio_generates_clean_wav(project, cfg, category):
    def mutate(r):
        r["category"] = category
        for k in ("loop", "channels"):
            r["output"].pop(k)
        r["unity"]["import"] = {}
    path = _write_request(project, mutate)
    run = Store(str(project), cfg).generate(load_request(path), path)
    assert run["kind"] == "audio" and run["warnings"] == [], run["warnings"]
    o = run["outputs"][0]
    assert o["file"] == "variant_01.wav" and abs(o["durationSec"] - 1.5) < 0.01
    assert o["channels"] == (1 if category == "sfx" else 2) and o["sampleRate"] == 44100
    assert -4 < o["peakDbfs"] < -2


def test_audio_checks_warn_on_mismatch(project, cfg):
    path = _write_request(project)
    req = load_request(path)
    run = Store(str(project), cfg).generate(req, path)
    wav = project / run["outDir"] / "variant_01.wav"
    write_wav(str(wav), 48000, 1, [0] * 4800 + [30000, -30000] * 100)   # 다른 길이 · 레이트 · 채널 · 무음
    stats = analyze(str(wav))
    from artgen_lib.audioutil import check
    w = " | ".join(check(stats, req["output"]))
    for needle in ("길이", "샘플레이트", "채널", "루프 이음매"):
        assert needle in w, w


def test_audio_promote_writes_audio_import_entry(project, cfg):
    path = _write_request(project)
    req = load_request(path)
    store = Store(str(project), cfg)
    store.generate(req, path)
    store.select("ASSET-201", "v001", "variant_01.wav")
    store.promote(req)
    assert (project / "Assets" / "MyGame" / "Audio" / "Music" / "bgm_stage1_explore.wav").is_file()
    entry = json.loads((project / "production" / "artgen" / "import-map.json").read_text(encoding="utf-8"))["entries"][0]
    assert entry["kind"] == "audio" and entry["loadType"] == "Streaming" and entry["quality"] == 0.7
    assert entry["preloadAudioData"] is False          # music 기본값이 빠짐없이 채워짐
    assert "textureType" not in entry


def test_promote_rejects_extension_mismatch(project, cfg):
    path = _write_request(project)
    req = load_request(path)
    store = Store(str(project), cfg)
    store.generate(req, path)
    store.select("ASSET-201", "v001", "variant_01.wav")
    with pytest.raises(ArtgenError, match="확장자"):
        store.promote(req, dest="Assets/x.png")


def test_manual_provider_accepts_wav_delivery(project, cfg):
    path = _write_request(project)
    inbox = project / "production" / "artgen" / "_inbox" / "ASSET-201"
    inbox.mkdir(parents=True)
    write_wav(str(inbox / "loop_a.wav"), 44100, 2, [0, 0] * 10)
    run = Store(str(project), cfg).generate(load_request(path), path, provider_name="manual")
    assert [o["file"] for o in run["outputs"]] == ["loop_a.wav"]
    assert not list(inbox.glob("*.wav"))


# ---- ComfyUI 오디오 ----
def _job(req, tmp_path):
    o = req["output"]
    return Job(asset_id=req["assetId"], request=req, positive="p", negative="n", width=0, height=0,
               transparent=False, variants=1, seeds=[5], references=[], out_dir=str(tmp_path), job_file="",
               kind="audio", duration=o["durationSec"], loop=o["loop"], channels=o["channels"],
               sample_rate=o["sampleRate"])


def test_music_uses_ace_step_graph_with_structured_inputs(tmp_path):
    req = normalize_request(_example())
    g = build_audio_graph({}, _job(req, tmp_path), 5)
    enc = g["enc"]["inputs"]
    assert g["enc"]["class_type"] == "TextEncodeAceStepAudio1.5"
    assert (enc["bpm"], enc["keyscale"], enc["timesignature"], enc["lyrics"]) == (90, "D major", "4", "[Instrumental]")
    assert g["latent"]["inputs"]["seconds"] == 91.0                 # 루프: 60 × 1.5 + 여유 1초
    assert g["sample"]["inputs"]["model"] == ["shift", 0] and g["neg"]["class_type"] == "ConditioningZeroOut"
    assert g["save"]["class_type"] == "SaveAudioAdvanced" and g["save"]["inputs"]["format"] == "flac"


def test_audio_graph_non_loop_generates_only_tail_margin(tmp_path):
    # Arrange
    req = _example()
    req["output"]["loop"] = False
    req = normalize_request(req)
    # Act
    g = build_audio_graph({}, _job(req, tmp_path), 5)
    # Assert
    assert g["latent"]["inputs"]["seconds"] == 61.0                 # 한 번 재생: 60 + 여유 1초


def test_audio_check_loop_with_silent_tail_warns_gap(tmp_path):
    # Arrange — 회귀: 실기에서 ACE-Step 이 끝맺음까지 만들어 루프 끝 2초가 무음이었는데,
    # 무음끼리 이어져 이음매 점프가 0 이라 경고 없이 통과했다
    from artgen_lib.audioutil import check
    import math
    wav = tmp_path / "loop.wav"
    tone = [int(math.sin(2 * math.pi * 220 * i / 44100) * 20000) for i in range(44100 * 2)]
    write_wav(str(wav), 44100, 1, tone + [0] * (44100 * 2))
    out = {"durationSec": 4.0, "sampleRate": 44100, "channels": 1, "loop": True}
    # Act
    stats = analyze(str(wav))
    warnings = check(stats, out)
    # Assert
    assert stats["loopSeam"] < 0.1
    assert any("반복 시 공백" in w for w in warnings), warnings


def test_sfx_uses_stable_audio_graph_and_category_override(tmp_path):
    req = _example()
    req["category"] = "sfx"
    req = normalize_request(req)
    g = build_audio_graph({}, _job(req, tmp_path), 5)
    assert g["latent"]["class_type"] == "EmptyLatentAudio" and g["clip"]["inputs"]["type"] == "stable_audio"
    g2 = build_audio_graph({"audioGraphByCategory": {"sfx": "ace-step-1.5"}}, _job(req, tmp_path), 5)
    assert g2["enc"]["class_type"] == "TextEncodeAceStepAudio1.5"
    with pytest.raises(ArtgenError, match="오디오 그래프"):
        build_audio_graph({"audioGraph": "nope"}, _job(req, tmp_path), 5)


class FakeComfyAudio:
    """그래프를 받아 기록하고, 오디오 출력으로 미리 만든 WAV 를 돌려준다."""

    def __init__(self, wav_path):
        self.prompts = []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, obj):
                body = json.dumps(obj).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/system_stats":
                    return self._json({"devices": [{"name": "fake"}]})
                if self.path.startswith("/history/"):
                    pid = self.path.rsplit("/", 1)[1]
                    return self._json({pid: {"status": {"completed": True}, "outputs": {"save": {"audio": [
                        {"filename": "artgen_00001_.wav", "subfolder": "artgen", "type": "output"}]}}}})
                with open(wav_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                fake.prompts.append(json.loads(self.rfile.read(int(self.headers["Content-Length"])))["prompt"])
                return self._json({"prompt_id": "p1"})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def test_comfyui_audio_requires_post_interpreter_before_generating(project, cfg, tmp_path_factory):
    wav = tmp_path_factory.mktemp("src") / "src.wav"
    write_wav(str(wav), 44100, 2, [0, 0] * 100)
    fake = FakeComfyAudio(str(wav))
    cfg["providers"]["comfyui"] = {"url": fake.url, "checkpoint": "c"}
    cfg["audio"] = {"python": ""}
    path = _write_request(project)
    with pytest.raises(ArtgenError, match="audio.python"):
        Store(str(project), cfg).generate(load_request(path), path, provider_name="comfyui")
    assert fake.prompts == []                       # GPU 를 쓰기 전에 멈춘다
    fake.server.shutdown()


@needs_audio_py
def test_comfyui_audio_roundtrip_with_post_processing(project, cfg, tmp_path_factory):
    # 모델 원본 흉내: 48kHz 모노 · 요청보다 1초 김 · 1.5초 지점에서 끝과 처음이 맞지 않는 사인파 (정수 주기 아님)
    import math
    wav = tmp_path_factory.mktemp("src") / "src.wav"
    n = 48000 * 5 // 2
    write_wav(str(wav), 48000, 1, [int(math.sin(2 * math.pi * 333.3 * i / 48000) * 20000) for i in range(n)])
    fake = FakeComfyAudio(str(wav))
    cfg["providers"]["comfyui"] = {"url": fake.url, "checkpoint": "c"}
    cfg["audio"] = {"python": AUDIO_PY}
    path = _write_request(project)                  # music · 1.5s · 루프 · 스테레오 · 44.1kHz
    run = Store(str(project), cfg).generate(load_request(path), path, provider_name="comfyui")
    fake.server.shutdown()
    o = run["outputs"][0]
    vdir = project / run["outDir"]
    assert (vdir / "variant_01.src.wav").is_file() and o["file"] == "variant_01.wav"
    assert (o["sampleRate"], o["channels"]) == (44100, 2) and abs(o["durationSec"] - 1.5) < 0.01
    assert abs(o["peakDbfs"] + 1.0) < 0.2           # -1 dBFS 로 정규화
    assert o["post"]["crossfadeSec"] > 0 and o["loopSeam"] < 0.1
    assert run["warnings"] == [], run["warnings"]


@needs_audio_py
def test_audio_post_loop_picks_window_before_fade_out(tmp_path):
    # Arrange — 음악 모델 원본 흉내: 1초 조용한 도입 · 5초 본편 · 2초 무음 끝맺음, 루프 3초 요청
    import math
    src = tmp_path / "song.wav"
    rate = 44100
    body = [int(math.sin(2 * math.pi * 220 * i / rate) * 20000) for i in range(rate * 5)]
    intro = [int(math.sin(2 * math.pi * 220 * i / rate) * 300) for i in range(rate)]
    write_wav(str(src), rate, 1, intro + body + [0] * (rate * 2))
    out = tmp_path / "loop.wav"
    # Act
    proc = subprocess.run([AUDIO_PY, AUDIO_POST, "--in", str(src), "--out", str(out), "--rate", "44100",
                           "--channels", "1", "--duration", "3", "--loop", "1"], capture_output=True, text=True, encoding="utf-8")
    info = json.loads(proc.stdout.strip().splitlines()[-1])
    stats = analyze(str(out))
    # Assert
    assert info["ok"] and 1.0 <= info["loopStartSec"] <= 3.0      # 도입도 끝맺음도 피한 본편 구간
    assert stats["tailSilenceSec"] < 0.1 and stats["leadSilenceSec"] < 0.1 and stats["loopSeam"] < 0.1


@needs_audio_py
def test_audio_post_reports_decode_failure_as_json(tmp_path):
    bad = tmp_path / "bad.flac"
    bad.write_bytes(b"not audio")
    proc = subprocess.run([AUDIO_PY, AUDIO_POST, "--in", str(bad), "--out", str(tmp_path / "o.wav"), "--rate", "44100",
                           "--channels", "1", "--duration", "1"], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1 and json.loads(proc.stdout.strip().splitlines()[-1])["ok"] is False
