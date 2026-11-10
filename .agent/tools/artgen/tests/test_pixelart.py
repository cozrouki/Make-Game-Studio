"""픽셀아트 후처리 테스트 — PNG 디코드 · 시트 다듬기 · 픽셀아트화 · 저장소 연결.
python -m pytest .agent/tools/artgen/tests -q
"""
import json
import os
import struct
import sys
import zlib

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

from artgen_lib import ArtgenError  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402
from artgen_lib.pixelart import pixelate, trim_sheet  # noqa: E402
from artgen_lib.pngutil import PNG_SIG, read_rgba, write_rgba_bytes  # noqa: E402
from artgen_lib.request import load_request, validate_request  # noqa: E402
from artgen_lib.store import Store  # noqa: E402

EXAMPLE = os.path.join(TOOL_DIR, "schema", "example-request.json")


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _encode(path, w, h, pix, ct, filters, plte=None, trns=None):
    """테스트 전용 독립 인코더 — 행마다 지정 필터(0~4)로 순방향 필터링."""
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    stride = w * bpp
    raw, prev = bytearray(), bytes(stride)
    for y in range(h):
        line = pix[y * stride:(y + 1) * stride]
        f = filters[y % len(filters)]
        enc = bytearray()
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 0:
                pred = 0
            elif f == 1:
                pred = a
            elif f == 2:
                pred = b
            elif f == 3:
                pred = (a + b) >> 1
            else:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
            enc.append((line[i] - pred) & 255)
        raw += bytes([f]) + enc
        prev = line
    body = PNG_SIG + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0))
    if plte:
        body += _chunk(b"PLTE", plte)
    if trns:
        body += _chunk(b"tRNS", trns)
    with open(path, "wb") as fh:
        fh.write(body + _chunk(b"IDAT", zlib.compress(bytes(raw))) + _chunk(b"IEND", b""))


def _rgba(w, h, fn):
    out = bytearray()
    for y in range(h):
        for x in range(w):
            out += bytes(fn(x, y))
    return out


# ---- PNG 디코드 ----
@pytest.mark.parametrize("filters", [[0], [1], [2], [3], [4], [0, 1, 2, 3, 4]])
def test_read_rgba_decodes_every_filter(tmp_path, filters):
    pix = _rgba(7, 5, lambda x, y: ((x * 37 + y * 11) % 256, (x * x + y * 3) % 256, (255 - x * 20) % 256, (y * 60) % 256))
    path = str(tmp_path / "f.png")
    _encode(path, 7, 5, pix, 6, filters)
    assert read_rgba(path) == (7, 5, pix)


def test_read_rgba_converts_rgb_gray_and_palette(tmp_path):
    rgb = bytes([10, 20, 30, 40, 50, 60])
    _encode(str(tmp_path / "rgb.png"), 2, 1, rgb, 2, [4])
    assert read_rgba(str(tmp_path / "rgb.png"))[2] == bytearray([10, 20, 30, 255, 40, 50, 60, 255])
    _encode(str(tmp_path / "ga.png"), 2, 1, bytes([5, 200, 9, 0]), 4, [1])
    assert read_rgba(str(tmp_path / "ga.png"))[2] == bytearray([5, 5, 5, 200, 9, 9, 9, 0])
    _encode(str(tmp_path / "p.png"), 2, 1, bytes([1, 0]), 3, [0], plte=bytes([1, 2, 3, 4, 5, 6]), trns=bytes([0]))
    assert read_rgba(str(tmp_path / "p.png"))[2] == bytearray([4, 5, 6, 255, 1, 2, 3, 0])


def test_read_rgba_rejects_16bit(tmp_path):
    path = tmp_path / "x.png"
    path.write_bytes(PNG_SIG + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 16, 6, 0, 0, 0))
                     + _chunk(b"IDAT", zlib.compress(b"\x00" + b"\x00" * 8)) + _chunk(b"IEND", b""))
    with pytest.raises(ValueError, match="bit depth 16"):
        read_rgba(str(path))


# ---- 시트 다듬기 ----
def _sheet(tmp_path, frames, fw=10, fh=8, cols=2, loop=False, pivot=(5, 7)):
    """frames: 프레임마다 불투명 픽셀 (x, y) 목록 — 빈 목록이면 빈 프레임."""
    n = len(frames)
    rows = -(-n // cols)
    sw, sh = cols * fw, rows * fh
    pix = bytearray(sw * sh * 4)
    for i, pts in enumerate(frames):
        for x, y in pts:
            o = (((i // cols) * fh + y) * sw + (i % cols) * fw + x) * 4
            pix[o:o + 4] = bytes((200, 100, 50 + i, 255))
    png = str(tmp_path / "s.png")
    write_rgba_bytes(png, sw, sh, pix)
    data = {"frames": [{"filename": f"s {i}", "frame": {"x": (i % cols) * fw, "y": (i // cols) * fh, "w": fw, "h": fh},
                        "duration": 33} for i in range(n)],
            "meta": {"image": "s.png", "size": {"w": sw, "h": sh}, "frameTags": [{"name": "s", "from": 0, "to": n - 1}],
                     "pixelfx": {"frameSize": [fw, fh], "columns": cols, "frames": n, "pivot": list(pivot), "loop": loop}}}
    js = str(tmp_path / "s.json")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return png, js


def _frame_pixels(png, js):
    w, h, px = read_rgba(png)
    fx = json.load(open(js, encoding="utf-8"))["meta"]["pixelfx"]
    fw, fh = fx["frameSize"]
    cols = fx["columns"]
    out = []
    for i in range(fx["frames"]):
        pts = []
        for y in range(fh):
            for x in range(fw):
                o = (((i // cols) * fh + y) * w + (i % cols) * fw + x) * 4
                if px[o + 3]:
                    pts.append((x, y))
        out.append(pts)
    return out


def test_trim_sheet_crops_common_margin_and_drops_trailing_empty_frames(tmp_path):
    # Arrange — 내용은 x 3~6, y 2~5 에만. 마지막 두 프레임은 비어 있다
    png, js = _sheet(tmp_path, [[(3, 2), (4, 4)], [(6, 5)], [(5, 3)], [], []])
    # Act
    info = trim_sheet(png, js, margin=0)
    # Assert
    assert info["changed"] and info["to"] == [4, 4] and info["offset"] == [3, 2] and info["frames"] == [5, 3]
    meta = json.load(open(js, encoding="utf-8"))["meta"]
    assert meta["pixelfx"]["pivot"] == [2, 5]                       # (5,7) - (3,2)
    assert meta["pixelfx"]["frames"] == 3 and meta["frameTags"][0]["to"] == 2
    assert _frame_pixels(png, js) == [[(0, 0), (1, 2)], [(3, 3)], [(2, 1)]]  # 프레임 사이 상대 위치 유지
    assert read_rgba(png)[:2] == (meta["size"]["w"], meta["size"]["h"])


def test_trim_sheet_keeps_trailing_empty_frames_of_loops_and_margin(tmp_path):
    png, js = _sheet(tmp_path, [[(3, 2)], []], loop=True)
    info = trim_sheet(png, js, margin=1)
    assert info["frames"] == [2, 2]                    # 루프는 빈 프레임도 타이밍이다
    assert info["to"] == [3, 3] and info["offset"] == [2, 1]


def test_trim_sheet_reports_no_change(tmp_path):
    png, js = _sheet(tmp_path, [[(0, 0), (9, 7)]], cols=1)
    before = open(png, "rb").read()
    assert trim_sheet(png, js)["changed"] is False
    assert open(png, "rb").read() == before


# ---- 픽셀아트화 ----
def _blocks(tmp_path, name="b.png"):
    """8x8 — 왼쪽 위 4x4 빨강, 오른쪽 위 4x4 투명, 아래 절반 파랑(한 점만 초록 잡음)."""
    def fn(x, y):
        if y < 4:
            return (250, 10, 10, 255) if x < 4 else (0, 0, 0, 0)
        return (10, 240, 10, 255) if (x, y) == (1, 6) else (10, 10, 250, 255)
    path = str(tmp_path / name)
    write_rgba_bytes(path, 8, 8, _rgba(8, 8, fn))
    return path


def test_pixelate_mode_takes_majority_color_and_binary_alpha(tmp_path):
    out = str(tmp_path / "o.png")
    info = pixelate(_blocks(tmp_path), out, 2, 2, palette=["#FF0000", "#0000FF", "#00FF00"])
    w, h, px = read_rgba(out)
    assert (w, h) == (2, 2) and info["transparentPixels"] == 1 and info["method"] == "mode"
    assert [tuple(px[i:i + 4]) for i in range(0, 16, 4)] == [
        (255, 0, 0, 255), (0, 0, 0, 0), (0, 0, 255, 255), (0, 0, 255, 255)]  # 초록 점 하나는 다수에 묻힌다


def test_pixelate_adaptive_palette_and_scale(tmp_path):
    out = str(tmp_path / "o.png")
    info = pixelate(_blocks(tmp_path), out, 4, 4, colors=2, scale=3)
    w, h, px = read_rgba(out)
    assert (w, h) == (12, 12) and info["grid"] == [4, 4] and len(info["palette"]) <= 2
    assert set(px[3::4]) == {0, 255}


def test_pixelate_average_with_dither_is_deterministic(tmp_path):
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    for path in (a, b):
        pixelate(_blocks(tmp_path), path, 4, 4, palette=["#FF0000", "#0000FF"], method="average", dither=True)
    assert open(a, "rb").read() == open(b, "rb").read()


def test_pixelate_rejects_grid_larger_than_source(tmp_path):
    with pytest.raises(ValueError, match="격자"):
        pixelate(_blocks(tmp_path), str(tmp_path / "o.png"), 16, 16)


# ---- 요청 검증 ----
def _example():
    with open(EXAMPLE, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("px, needle", [
    ({"width": 64}, "height"),
    ({"width": 64, "height": 64, "palette": "prompt"}, None),
    ({"width": 64, "height": 64, "colors": 1}, "colors"),
    ({"width": 64, "height": 64, "dither": True}, "average"),
    ({"width": 64, "height": 64, "method": "nearest"}, "method"),
    ({"width": 9999, "height": 64}, "생성 크기"),
    ({"width": 64, "height": 64, "zoom": 2}, "알 수 없는 키"),
])
def test_pixelate_request_validation(px, needle):
    req = _example()
    req["output"]["pixelate"] = px
    errors = validate_request(req)
    assert (not errors) if needle is None else any(needle in e for e in errors)


def test_pixelate_prompt_palette_must_exist():
    req = _example()
    req["prompt"]["palette"] = []
    req["output"]["pixelate"] = {"width": 32, "height": 32, "palette": "prompt"}
    assert any("prompt.palette 가 비어" in e for e in validate_request(req))


# ---- 저장소 · 승격 ----
@pytest.fixture
def cfg():
    c = load_config()
    c["provider"] = "mock"
    return c


def test_generate_pixelates_keeps_source_and_promote_sets_point_import(tmp_path, cfg):
    # Arrange — mock 은 요청 크기(64x64) PNG 를 만든다
    (tmp_path / "Assets").mkdir()
    req = _example()
    req["output"].update(width=64, height=64, variants=1, seed=3,
                         pixelate={"width": 16, "height": 16, "palette": "prompt"})
    req["unity"]["dest"] = "Assets/Art/hero.png"
    req["unity"].pop("import", None)
    path = tmp_path / "ASSET-001.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    store = Store(str(tmp_path), cfg)
    # Act
    run = store.generate(load_request(str(path)), str(path))
    # Assert
    out = run["outputs"][0]
    vdir = tmp_path / run["outDir"]
    assert (out["width"], out["height"]) == (16, 16) and out["pixelate"]["grid"] == [16, 16]
    assert (vdir / "variant_01.src.png").is_file() and read_rgba(str(vdir / "variant_01.src.png"))[:2] == (64, 64)
    assert not [w for w in run["warnings"] if "크기" in w]
    allowed = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in req["prompt"]["palette"]}
    px = read_rgba(str(vdir / "variant_01.png"))[2]
    assert {tuple(px[i:i + 3]) for i in range(0, len(px), 4) if px[i + 3]} <= allowed
    store.select("ASSET-001", run["version"], "variant_01.png")
    store.promote(load_request(str(path)))
    entry = json.loads((tmp_path / "production/artgen/import-map.json").read_text(encoding="utf-8"))["entries"][0]
    assert (entry["filterMode"], entry["compression"], entry["mipmaps"]) == ("Point", "None", False)
    assert entry["spriteMode"] == "Single"


def test_generate_pixelate_failure_is_reported(tmp_path, cfg, monkeypatch):
    import artgen_lib.pixelart as pa

    def boom(*a, **k):
        raise ValueError("지원하지 않는 PNG")
    monkeypatch.setattr(pa, "pixelate", boom)
    req = _example()
    req["output"].update(width=32, height=32, variants=1, pixelate={"width": 8, "height": 8})
    path = tmp_path / "r.json"
    path.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(ArtgenError, match="픽셀아트 후처리 실패"):
        Store(str(tmp_path), cfg).generate(load_request(str(path)), str(path))
