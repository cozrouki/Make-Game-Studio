"""mock — 백엔드 미정 상태에서 파이프라인 전체(요청→생성→검수→승격→임포트)를 검증하기 위한 자리표시 이미지.

팔레트 색 + 시드 기반 도형을 그린다. 미술적 의미는 없으므로 검수 단계에서 시각 평가를 건너뛴다.
오디오 요청이면 시드 기반 사인파 WAV 를 만든다 — 효과음은 짧게 감쇠하는 처프, 루프는 이음매 없는 화음.
"""
import array
import math
import os
import random

from ..audioutil import write_wav
from ..pngutil import write_rgba
from .base import Provider

MOCK_PEAK = 0.7  # ≈ -3 dBFS


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _tone(job, seed):
    """루프면 길이 안에 정수 주기만 들어가는 주파수를 골라 끝과 처음이 이어지게 한다."""
    rng = random.Random(seed)
    rate = job.sample_rate
    n = max(1, int(round(job.duration * rate)))
    if job.loop:
        cycles = [max(1, round(job.duration * f)) for f in (rng.uniform(180, 260), rng.uniform(270, 400))]
        freqs = [c / job.duration for c in cycles]
    else:
        freqs = [rng.uniform(400, 900)]
    data = array.array("h")
    for i in range(n):
        t = i / rate
        if job.loop:
            v = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        else:
            v = math.sin(2 * math.pi * freqs[0] * t * (1 + t)) * math.exp(-6 * t / job.duration)
        s = int(v * MOCK_PEAK * 32767)
        for _ in range(job.channels):
            data.append(s)
    return data


class MockProvider(Provider):
    name = "mock"
    description = "자리표시 PNG · WAV (백엔드 미정 시 파이프라인 검증용, 외부 의존 없음)"
    capabilities = {"transparent": True, "references": False, "seed": True}
    placeholder = True
    kinds = ("image", "audio")

    def generate(self, job):
        if job.kind == "audio":
            paths = []
            for i, seed in enumerate(job.seeds):
                path = os.path.join(job.out_dir, f"variant_{i + 1:02d}.wav")
                write_wav(path, job.sample_rate, job.channels, _tone(job, seed))
                paths.append(path)
            return paths
        palette = [_hex(c) for c in job.request["prompt"]["palette"]] or [(90, 110, 140), (220, 200, 120), (40, 40, 50)]
        paths = []
        for i, seed in enumerate(job.seeds):
            rng = random.Random(seed)
            w, h = job.width, job.height
            bg = (0, 0, 0, 0) if job.transparent else palette[0] + (255,)
            fg = palette[(i + 1) % len(palette)] + (255,)
            accent = palette[(i + 2) % len(palette)] + (255,)
            cx, cy = w / 2 + rng.uniform(-w, w) * 0.08, h / 2 + rng.uniform(-h, h) * 0.08
            rx, ry = w * rng.uniform(0.25, 0.4), h * rng.uniform(0.25, 0.4)
            sides = rng.choice((0, 3, 4, 6))  # 0 = 타원
            pixels = []
            for y in range(h):
                for x in range(w):
                    dx, dy = (x - cx) / rx, (y - cy) / ry
                    if sides == 0:
                        d = dx * dx + dy * dy
                    else:
                        d = max(abs(dx), abs(dy)) if sides == 4 else (abs(dx) + abs(dy)) * (0.8 if sides == 6 else 1.0)
                        d *= d
                    if d <= 0.55:
                        pixels.append(accent)
                    elif d <= 1.0:
                        pixels.append(fg)
                    else:
                        pixels.append(bg)
            path = os.path.join(job.out_dir, f"variant_{i + 1:02d}.png")
            write_rgba(path, w, h, pixels)
            paths.append(path)
        return paths


PROVIDER_CLASS = MockProvider
