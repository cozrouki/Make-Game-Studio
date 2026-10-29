"""사운드 라이브러리 테스트 — 등록 · 색인 · 검색 · library 백엔드 · 출처 기록(credits.json)."""
import json
import math
import os
import sys
import zipfile

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artgen_lib import ArtgenError  # noqa: E402
from artgen_lib import library as lib  # noqa: E402
from artgen_lib.audioutil import write_wav  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402
from artgen_lib.request import load_request  # noqa: E402
from artgen_lib.store import Store  # noqa: E402
from test_audio import AUDIO_PY, needs_audio_py  # noqa: E402


def _tone(seconds, freq=440, rate=44100):
    return [int(math.sin(2 * math.pi * freq * i / rate) * 20000) for i in range(int(seconds * rate))]


@pytest.fixture
def pack_dir(tmp_path):
    """Kenney 팩 흉내 — 이름이 설명적인 WAV 몇 개."""
    d = tmp_path / "kenney_interface"
    (d / "Audio").mkdir(parents=True)
    write_wav(str(d / "Audio" / "confirmation_001.wav"), 44100, 1, _tone(0.4))
    write_wav(str(d / "Audio" / "coinPickup_002.wav"), 44100, 1, _tone(0.3, 880))
    write_wav(str(d / "Audio" / "error_003.wav"), 44100, 1, _tone(2.5, 200))
    (d / "License.txt").write_text("CC0", encoding="utf-8")
    return d


@pytest.fixture
def project(tmp_path, pack_dir):
    root = tmp_path / "proj"
    (root / "Assets").mkdir(parents=True)
    lib_dir = root / "art-source" / "sound-library"
    lib.add_pack(str(lib_dir), str(pack_dir), "kenney-interface", "CC0-1.0", "https://kenney.nl/assets/interface-sounds")
    lib.build_index(str(lib_dir))
    return root


@pytest.fixture
def cfg():
    c = load_config()
    c["provider"] = "mock"
    c["audio"]["python"] = AUDIO_PY or ""
    return c


def _sfx_request(root, files=None):
    req = {"schema": "artgen-request/1", "assetId": "ASSET-101", "name": "coin", "category": "sfx",
           "prompt": {"subject": "coin pickup chime"}, "output": {"durationSec": 1.0, "variants": 2},
           "unity": {"dest": "Assets/MyGame/Audio/Sfx/sfx_coin.wav"}}
    if files:
        req["providerOptions"] = {"library": {"files": files}}
    path = root / "ASSET-101.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    return str(path)


# ---- 등록 · 색인 · 검색 ----
def test_library_tokenize_splits_camel_case_and_numbers():
    assert lib.tokenize("Audio/coinPickup_002.ogg") == ["audio", "coin", "pickup", "ogg"]


def test_library_add_requires_license_and_safe_name(tmp_path, pack_dir):
    with pytest.raises(ArtgenError, match="license"):
        lib.add_pack(str(tmp_path / "lib"), str(pack_dir), "pack", "")
    with pytest.raises(ArtgenError, match="팩 이름"):
        lib.add_pack(str(tmp_path / "lib"), str(pack_dir), "Bad Name", "CC0-1.0")


def test_library_add_rejects_zip_slip(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("../outside.wav", b"x")
    with pytest.raises(ArtgenError, match="바깥 경로"):
        lib.add_pack(str(tmp_path / "lib"), str(z), "evil", "CC0-1.0")
    assert not (tmp_path / "outside.wav").exists()


def test_library_index_measures_wav_without_audio_python(project):
    index = lib.load_index(str(project / "art-source" / "sound-library"))
    by_file = {e["file"]: e for e in index["entries"]}
    assert by_file["kenney-interface/Audio/coinPickup_002.wav"]["durationSec"] == 0.3
    assert index["packs"]["kenney-interface"]["license"] == "CC0-1.0"


def test_library_search_ranks_by_token_overlap_and_filters_duration(project):
    index = lib.load_index(str(project / "art-source" / "sound-library"))
    hits = lib.search(index, "a short coin pickup sound")          # 불용어(a · short · sound)는 버린다
    assert hits[0]["file"].endswith("coinPickup_002.wav") and hits[0]["score"] == 2.0
    assert lib.search(index, "error", max_duration=1.0) == []        # 2.5초짜리는 상한에 걸림
    assert lib.search(index, "confirm")[0]["file"].endswith("confirmation_001.wav")   # 접두 일치


@needs_audio_py
def test_library_probe_many_long_paths_beyond_command_line_limit(tmp_path):
    # 회귀: Kenney 팩 8개(611개) 색인 때 경로를 인자로 넘겨 WinError 206 (명령줄 32K 초과)
    d = tmp_path / ("very_long_folder_name_" * 4)
    d.mkdir()
    paths = []
    for i in range(400):
        p = d / f"interface_click_variation_{i:04d}_with_a_long_descriptive_name.wav"
        write_wav(str(p), 44100, 1, [0] * 441)
        paths.append(str(p))
    assert sum(len(p) + 1 for p in paths) > 32768
    probed = lib._probe(AUDIO_PY, paths)
    assert len(probed) == 400 and probed[paths[0]]["durationSec"] == 0.01


# ---- library 백엔드 ----
def test_library_sfx_routes_to_library_and_needs_post_interpreter(project, cfg):
    cfg["audio"]["python"] = ""
    path = _sfx_request(project)
    with pytest.raises(ArtgenError, match="audio.python"):           # mock 이 아니라 library(raw_audio)로 갔다
        Store(str(project), cfg).generate(load_request(path), path)


@needs_audio_py
def test_library_generate_pinned_file_keeps_natural_length_and_records_credit(project, cfg):
    # Arrange — art 세션이 search 결과에서 고른 파일을 고정
    path = _sfx_request(project, files=["kenney-interface/Audio/coinPickup_002.wav"])
    store = Store(str(project), cfg)
    req = load_request(path)
    # Act
    run = store.generate(req, path)
    store.select("ASSET-101", "v001", "variant_01.wav")
    store.promote(req)
    # Assert
    o = run["outputs"][0]
    assert run["provider"] == "library" and run["warnings"] == [], run["warnings"]
    assert o["durationSec"] < 0.35                                   # 요청 1초는 상한 — 무음으로 늘리지 않음
    assert o["source"]["license"] == "CC0-1.0"
    credits = json.loads((project / "production" / "artgen" / "credits.json").read_text(encoding="utf-8"))
    assert credits["entries"][0]["path"] == "Assets/MyGame/Audio/Sfx/sfx_coin.wav"
    assert credits["entries"][0]["library"] == "kenney-interface"


@needs_audio_py
def test_library_generate_search_fallback_uses_prompt(project, cfg):
    path = _sfx_request(project)
    run = Store(str(project), cfg).generate(load_request(path), path)
    assert run["outputs"][0]["source"]["file"].endswith("coinPickup_002.wav")


def test_library_unknown_pinned_file_is_rejected(project, cfg):
    if not AUDIO_PY:
        pytest.skip("PyAV + numpy 인터프리터 없음")
    path = _sfx_request(project, files=["kenney-interface/Audio/nope.wav"])
    with pytest.raises(ArtgenError, match="라이브러리에 없는 파일"):
        Store(str(project), cfg).generate(load_request(path), path)
