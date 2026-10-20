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
