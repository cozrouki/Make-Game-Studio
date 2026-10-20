"""mock — 백엔드 미정 상태에서 파이프라인 전체(요청→생성→검수→승격→임포트)를 검증하기 위한 자리표시 이미지.

팔레트 색 + 시드 기반 도형을 그린다. 미술적 의미는 없으므로 검수 단계에서 시각 평가를 건너뛴다.
"""
import os
import random

from ..pngutil import write_rgba
from .base import Provider


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


class MockProvider(Provider):
    name = "mock"
    description = "자리표시 PNG (백엔드 미정 시 파이프라인 검증용, 외부 의존 없음)"
    capabilities = {"transparent": True, "references": False, "seed": True}
    placeholder = True

    def generate(self, job):
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
