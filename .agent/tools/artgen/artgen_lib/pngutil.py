"""표준 라이브러리만으로 PNG 쓰기 · 헤더 읽기 (Pillow 의존 없음)."""
import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_rgba(path, width, height, pixels, alpha=True):
    """pixels: 길이 width*height 의 (r,g,b,a) 시퀀스, 행 우선. alpha=False 면 RGB 로 저장 (a 무시)."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # 필터 없음
        row = pixels[y * width:(y + 1) * width]
        for r, g, b, a in row:
            raw += bytes((r, g, b, a) if alpha else (r, g, b))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)  # 8bit RGBA / RGB
    with open(path, "wb") as f:
        f.write(PNG_SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b""))


def read_info(path):
    """(width, height, has_alpha) — PNG 가 아니면 None."""
    with open(path, "rb") as f:
        head = f.read(33)
    if len(head) < 33 or head[:8] != PNG_SIG or head[12:16] != b"IHDR":
        return None
    width, height, _depth, color_type = struct.unpack(">IIBB", head[16:26])
    # color_type 4 = gray+alpha, 6 = RGBA. 3(팔레트)은 tRNS 로 알파 가능 — 보수적으로 False
    return width, height, color_type in (4, 6)


def write_rgba_bytes(path, width, height, rgba):
    """rgba: 길이 width*height*4 의 bytes/bytearray (행 우선 RGBA8). 큰 이미지용 — 행마다 필터 없음."""
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(PNG_SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b""))


def read_rgba(path):
    """(width, height, bytearray RGBA8) — 8bit · 비인터레이스 PNG (그레이 · 그레이+알파 · RGB · RGBA · 팔레트+tRNS).
    다른 형식이면 ValueError. 표준 라이브러리만 쓴다 (Sub 필터 행은 채널별 누적합으로 빠르게)."""
    from itertools import accumulate
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != PNG_SIG:
        raise ValueError(f"PNG 아님: {path}")
    pos, idat, plte, trns, hdr = 8, [], None, None, None
    while pos + 8 <= len(data):
        n, = struct.unpack(">I", data[pos:pos + 4])
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat.append(body)
        elif tag == b"PLTE":
            plte = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IEND":
            break
    if hdr is None:
        raise ValueError(f"IHDR 없음: {path}")
    w, h, depth, ct, _c, _f, interlace = hdr
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ct)
    if depth != 8 or interlace != 0 or channels is None:
        raise ValueError(f"지원하지 않는 PNG (bit depth {depth} · color type {ct} · interlace {interlace}): {path}")
    raw = zlib.decompress(b"".join(idat))
    bpp, stride = channels, w * channels
    prev = bytearray(stride)
    pix = bytearray(stride * h)
    for y in range(h):
        o = y * (stride + 1)
        ft, line = raw[o], bytearray(raw[o + 1:o + 1 + stride])
        if ft == 1:
            for c in range(bpp):
                line[c::bpp] = bytes(v & 255 for v in accumulate(line[c::bpp]))
        elif ft == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif ft == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif ft != 0:
            raise ValueError(f"PNG 필터 {ft} 손상: {path}")
        pix[y * stride:(y + 1) * stride] = line
        prev = line
    if ct == 6:
        return w, h, pix
    out = bytearray(w * h * 4)
    if ct == 2:
        out[0::4], out[1::4], out[2::4] = pix[0::3], pix[1::3], pix[2::3]
        out[3::4] = b"\xff" * (w * h)
    elif ct == 0:
        out[0::4] = out[1::4] = out[2::4] = pix
        out[3::4] = b"\xff" * (w * h)
    elif ct == 4:
        out[0::4] = out[1::4] = out[2::4] = pix[0::2]
        out[3::4] = pix[1::2]
    else:  # 3 팔레트
        if plte is None:
            raise ValueError(f"PLTE 없음: {path}")
        alpha = (trns or b"") + b"\xff" * 256
        for i, k in enumerate(pix):
            out[i * 4:i * 4 + 4] = bytes((plte[k * 3], plte[k * 3 + 1], plte[k * 3 + 2], alpha[k]))
    return w, h, out
