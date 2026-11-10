"""픽셀아트 후처리 — 표준 라이브러리만.

trim_sheet   스프라이트 시트(Aseprite 형식 JSON + meta.pixelfx)에서 모든 프레임에 공통인 빈 여백을 잘라내고
             (pivot 보정), 한 번 재생 효과 끝의 빈 프레임을 버린다. 프레임 정렬은 유지한다 (모든 프레임 같은 크기).
             픽셀아트는 축소하면 깨지므로 크기 조정은 하지 않는다 — 게임 속 크기는 엔진의 PPU 로 맞춘다.
pixelate     생성 이미지(SDXL 등)를 격자 크기 픽셀아트로 — 팔레트(지정 또는 적응 N색)로 양자화하고 칸마다 최빈색
             (mode, 기본) 또는 면적 평균 후 양자화(average, 순서 디더 선택), 알파 이진화. 결과는 격자 크기 그대로
             (선택: 정수 배 확대).
"""
import json

from .pngutil import read_rgba, write_rgba_bytes

# ---------------------------------------------------------------- 시트 다듬기


def trim_sheet(png_path, json_path, margin=1, drop_trailing=True):
    """시트를 제자리에서 다듬는다. 반환: {"from": [w,h], "to": [w,h], "offset": [x,y], "frames": [n0, n1], "bytes": [b0, b1]}
    — 바뀐 것이 없으면 changed False. 모든 프레임이 비어 있으면 그대로 둔다."""
    with open(json_path, encoding="utf-8") as f:
        sheet = json.load(f)
    fx = sheet["meta"]["pixelfx"]
    fw, fh = (int(v) for v in fx["frameSize"])
    cols, n = int(fx["columns"]), int(fx["frames"])
    sw, sh, px = read_rgba(png_path)

    def alpha_box(i):
        """프레임 i 의 불투명 영역 (x0, y0, x1, y1) — 비었으면 None."""
        ox, oy = (i % cols) * fw, (i // cols) * fh
        x0 = y0 = None
        x1 = y1 = -1
        for y in range(fh):
            row = (oy + y) * sw * 4
            a = px[row + ox * 4 + 3:row + (ox + fw) * 4:4]
            if not any(a):
                continue
            left = next(k for k, v in enumerate(a) if v)
            right = fw - 1 - next(k for k, v in enumerate(reversed(a)) if v)
            y0 = y if y0 is None else y0
            y1 = y
            x0 = left if x0 is None else min(x0, left)
            x1 = max(x1, right)
        return None if x0 is None else (x0, y0, x1, y1)

    boxes = [alpha_box(i) for i in range(n)]
    keep = n
    if drop_trailing and not fx.get("loop"):
        while keep > 1 and boxes[keep - 1] is None:
            keep -= 1
    filled = [b for b in boxes[:keep] if b]
    if not filled:
        return {"changed": False, "reason": "모든 프레임이 비어 있음"}
    x0 = max(0, min(b[0] for b in filled) - margin)
    y0 = max(0, min(b[1] for b in filled) - margin)
    x1 = min(fw - 1, max(b[2] for b in filled) + margin)
    y1 = min(fh - 1, max(b[3] for b in filled) + margin)
    nw, nh = x1 - x0 + 1, y1 - y0 + 1
    if (nw, nh, keep) == (fw, fh, n):
        return {"changed": False, "reason": "여백 · 빈 프레임 없음"}

    ncols = _cols(keep, nw, nh)
    nrows = -(-keep // ncols)
    out = bytearray(ncols * nw * nrows * nh * 4)
    ow = ncols * nw
    for i in range(keep):
        sx, sy = (i % cols) * fw + x0, (i // cols) * fh + y0
        dx, dy = (i % ncols) * nw, (i // ncols) * nh
        for y in range(nh):
            s = ((sy + y) * sw + sx) * 4
            d = ((dy + y) * ow + dx) * 4
            out[d:d + nw * 4] = px[s:s + nw * 4]
    write_rgba_bytes(png_path, ow, nrows * nh, out)

    frames = sheet["frames"][:keep]
    for i, fr in enumerate(frames):
        fr["frame"] = {"x": (i % ncols) * nw, "y": (i // ncols) * nh, "w": nw, "h": nh}
        fr["spriteSourceSize"] = {"x": 0, "y": 0, "w": nw, "h": nh}
        fr["sourceSize"] = {"w": nw, "h": nh}
    sheet["frames"] = frames
    meta = sheet["meta"]
    meta["size"] = {"w": ow, "h": nrows * nh}
    for tag in meta.get("frameTags", []):
        tag["to"] = min(tag.get("to", keep - 1), keep - 1)
    pivot = fx.get("pivot") or [fw / 2, fh / 2]
    info = {"changed": True, "from": [fw, fh], "to": [nw, nh], "offset": [x0, y0], "frames": [n, keep],
            "bytes": [sw * sh * 4, ow * nrows * nh * 4]}
    fx.update(frameSize=[nw, nh], columns=ncols, frames=keep, pivot=[pivot[0] - x0, pivot[1] - y0], trim=info)
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return info


def _cols(n, w, h):
    """pixelfx tools/lib/fxlib.mjs spriteSheet 와 같은 규칙 — ceil(sqrt(n*h/w)), 시트가 정사각형에 가깝게."""
    import math
    return min(n, max(1, math.ceil(math.sqrt((n * h) / w))))


# ---------------------------------------------------------------- 픽셀아트화

BAYER4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]


def _hex(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _dist(a, b):
    """redmean 근사 — 사람 눈 기준 RGB 거리 (Lab 변환 없이)."""
    rm = (a[0] + b[0]) >> 1
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return (((512 + rm) * dr * dr) >> 8) + 4 * dg * dg + (((767 - rm) * db * db) >> 8)


def median_cut(colors, n):
    """(r,g,b) 목록 → 대표색 n 개 이하 (상자 분할, 결정론)."""
    boxes = [sorted(colors)]
    while len(boxes) < n:
        idx, axis, spread = None, 0, -1
        for i, b in enumerate(boxes):
            if len(b) < 2:
                continue
            for ax in range(3):
                vals = [c[ax] for c in b]
                s = max(vals) - min(vals)
                if s > spread:
                    idx, axis, spread = i, ax, s
        if idx is None or spread <= 0:
            break
        b = sorted(boxes.pop(idx), key=lambda c: (c[axis], c))
        mid = len(b) // 2
        boxes += [b[:mid], b[mid:]]
    return [tuple(sum(c[k] for c in b) // len(b) for k in range(3)) for b in boxes if b]


def _nearest(pal, cache):
    def find(key):
        k = cache.get(key)
        if k is None:
            k = min(range(len(pal)), key=lambda j: _dist(key, pal[j]))
            cache[key] = k
        return k
    return find


def _cells(sw, sh, width, height):
    for ty in range(height):
        y0, y1 = ty * sh // height, max(ty * sh // height + 1, (ty + 1) * sh // height)
        for tx in range(width):
            x0, x1 = tx * sw // width, max(tx * sw // width + 1, (tx + 1) * sw // width)
            yield y0, y1, x0, x1


def pixelate(src, dst, width, height, palette=None, colors=16, dither=False, alpha_threshold=128, scale=1,
             method="mode"):
    """src PNG → dst PNG (width x height · scale 배). palette: '#RRGGBB' 목록이면 그 색만, 없으면 적응 colors 색.
    method: "mode"(기본) = 원본 해상도에서 팔레트로 양자화한 뒤 칸마다 최빈색 — 윤곽이 또렷하고 중간색이 생기지 않는다.
            "average" = 칸마다 면적 평균 후 양자화 — 부드러운 그러데이션 · 순서 디더(dither)는 이 방식에서만.
    반환: {"size": [w,h], "grid": [w,h], "method": m, "palette": [...], "colorsUsed": k, "transparentPixels": t}"""
    if method not in ("mode", "average"):
        raise ValueError(f"method 는 mode · average (현재 {method})")
    sw, sh, px = read_rgba(src)
    if width > sw or height > sh:
        raise ValueError(f"격자 {width}x{height} 가 원본 {sw}x{sh} 보다 크다")
    n = sw * sh
    # 팔레트 — 지정이 없으면 원본 불투명 픽셀 표본으로 적응 팔레트 (표본은 최대 약 65536개, 결정론)
    if palette:
        pal = [_hex(c) for c in palette]
    else:
        step = max(1, n // 65536)
        sample = [(px[i * 4], px[i * 4 + 1], px[i * 4 + 2]) for i in range(0, n, step) if px[i * 4 + 3] >= alpha_threshold]
        pal = median_cut(sample, colors) if sample else [(0, 0, 0)]
    find = _nearest(pal, {})
    out = bytearray(width * height * 4)
    used, transparent = set(), 0

    if method == "mode":
        idx = bytearray(n)  # 0 = 투명, k+1 = 팔레트 k
        for i in range(n):
            o = i * 4
            if px[o + 3] >= alpha_threshold:
                idx[i] = find((px[o] & 0xFC, px[o + 1] & 0xFC, px[o + 2] & 0xFC)) + 1
        for c, (y0, y1, x0, x1) in enumerate(_cells(sw, sh, width, height)):
            counts = {}
            for y in range(y0, y1):
                row = y * sw
                for v in idx[row + x0:row + x1]:
                    counts[v] = counts.get(v, 0) + 1
            total = (y1 - y0) * (x1 - x0)
            if counts.get(0, 0) * 2 >= total:  # 칸의 절반 이상이 투명이면 투명
                transparent += 1
                continue
            counts.pop(0, None)
            k = max(sorted(counts), key=lambda v: counts[v]) - 1
            used.add(k)
            out[c * 4:c * 4 + 4] = bytes((*pal[k], 255))
        return _finish(dst, out, width, height, scale, "mode", pal, used, transparent)

    # average — 면적 평균 축소 (알파 가중 색)
    small = []
    for y0, y1, x0, x1 in _cells(sw, sh, width, height):
        r = g = b = a = 0
        for y in range(y0, y1):
            row = y * sw * 4
            for x in range(x0, x1):
                o = row + x * 4
                al = px[o + 3]
                r += px[o] * al
                g += px[o + 1] * al
                b += px[o + 2] * al
                a += al
        cnt = (y1 - y0) * (x1 - x0)
        small.append((r // a, g // a, b // a, a // cnt) if a else (0, 0, 0, 0))
    # 양자화 (+ 순서 디더) · 알파 이진화
    spread = 48 if dither else 0
    for i, (r, g, b, a) in enumerate(small):
        if a < alpha_threshold:
            transparent += 1
            continue
        if spread:
            t = (BAYER4[(i // width % 4) * 4 + (i % width) % 4] - 7.5) / 16 * spread
            r, g, b = (min(255, max(0, int(v + t))) for v in (r, g, b))
        k = find((r, g, b))
        used.add(k)
        out[i * 4:i * 4 + 4] = bytes((*pal[k], 255))
    return _finish(dst, out, width, height, scale, "average", pal, used, transparent)


def _finish(dst, out, width, height, scale, method, pal, used, transparent):
    """정수 배 확대(최근접) 후 저장."""
    if scale > 1:
        bw = width * scale
        big = bytearray(bw * height * scale * 4)
        for y in range(height * scale):
            src_row = (y // scale) * width
            d = y * bw * 4
            for x in range(width):
                big[d + x * scale * 4:d + (x + 1) * scale * 4] = out[(src_row + x) * 4:(src_row + x) * 4 + 4] * scale
        write_rgba_bytes(dst, bw, height * scale, big)
    else:
        write_rgba_bytes(dst, width, height, out)
    return {"size": [width * scale, height * scale], "grid": [width, height], "method": method,
            "palette": ["#%02X%02X%02X" % c for c in pal], "colorsUsed": len(used), "transparentPixels": transparent}
