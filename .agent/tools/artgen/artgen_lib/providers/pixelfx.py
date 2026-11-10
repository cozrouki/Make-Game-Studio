"""pixelfx — 코드로 그리는 픽셀아트 VFX(patch-gg/pixelfx, MIT)를 스프라이트 시트로 굽는다. GPU · 모델 없음.

이미지를 '생성' 하지 않고, 라이브러리의 효과 하나를 시드 · 팔레트로 렌더한다 (같은 시드 = 같은 바이트).
변형 = 시드만 다른 같은 효과. 결과는 변형마다 세 파일:
    variant_NN.png          투명 PNG 시트 (프레임 격자)
    variant_NN.sheet.json   Aseprite 형식 프레임 데이터 + meta.pixelfx (fps · loop · frameSize · pivot · columns · 타격 타이밍)
    variant_NN.source.json  출처 · 라이선스 — 승격하면 credits.json 에 기록된다

요청 (providerOptions.pixelfx):
    effect    효과 id "<분류>/<이름>" (필수) — `node tools/list.mjs` 또는 갤러리에서 고른다
    options   효과에 넘길 값 (선택, 예: {"light": 0.6}) — palette 를 주면 prompt.palette 보다 우선
    fps       굽는 프레임률 (선택, 1~60 · 기본은 효과 값 보통 30). 시트 메모리 = 프레임 수에 비례 — 12~15 로 줄이면
              픽셀아트 느낌은 그대로이고 텍스처는 절반 이하가 된다
    trim      모든 프레임에 공통인 빈 여백 자르기 + 한 번 재생 효과 끝의 빈 프레임 버리기 (기본 true, pivot 보정).
              효과 캔버스는 캐릭터 옆 시점 기준이라 여백이 크다. 기록: sheet.json meta.pixelfx.trim
    trimMargin 자른 뒤 남길 여백 px (기본 1 — 스프라이트 메시 가장자리 번짐 방지)

prompt.palette 는 밝기 순(어두운 → 밝은)으로 정렬해 효과의 색 램프로 넘긴다. 효과마다 고정 색(손잡이 · 돌 등)은
바뀌지 않는다. 시트 크기는 효과가 정한다 — 요청 output.width/height 와 비교하지 않는다 (sized_by_source).

설정 (artgen.config.json → providers.pixelfx):
    dir        pixelfx 폴더 (절대경로 또는 프로젝트 루트 기준, 기본 art-source/pixelfx — prereq.py install pixelfx)
    node       Node 실행 파일 (기본 "node", 18 이상)
    timeoutSec 변형 하나 렌더 시간 상한 (기본 300)
    check      생성 뒤 tools/check.mjs 로 효과 검사 (기본 true) — 결과는 run.json warnings 로
"""
import json
import os
import re
import shutil
import subprocess

from .. import ArtgenError
from ..pixelart import trim_sheet
from .base import Provider

EFFECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$")
MIN_NODE = (18, 0)
URL = "https://github.com/patch-gg/pixelfx"
LICENSE = "MIT"
ATTRIBUTION = "pixelfx — Copyright (c) 2026 Patch, MIT License"
# NOTICE.md — 효과 파일 머리에 이 이름이 있으면 그 원저작자도 함께 표기한다
UPSTREAM_NOTICES = {
    "Sprite Fusion": "Sprite Fusion pixel art VFX — Copyright (c) 2026 Hugo Duprez, MIT License",
}


def pixelfx_dir(options, project_root):
    d = options.get("dir", "art-source/pixelfx")
    return d if os.path.isabs(d) else os.path.join(project_root or os.getcwd(), d)


def palette_ramp(colors):
    """#RRGGBB 목록을 상대 휘도 오름차순(어두운 → 밝은)으로 — pixelfx 색 램프 규약."""
    def luma(c):
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    return sorted(colors, key=luma)


def _node_version(node):
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.match(r"v(\d+)\.(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _commit(root):
    """prereq 가 남긴 고정 커밋 (.pixelfx-commit) — 없으면 빈 문자열 (git 클론 등 직접 받은 경우)."""
    try:
        with open(os.path.join(root, ".pixelfx-commit"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


class PixelfxProvider(Provider):
    name = "pixelfx"
    description = "코드 픽셀아트 VFX 시트 굽기 (patch-gg/pixelfx, MIT — 결정론 · 팔레트 · GPU 불필요)"
    capabilities = {"transparent": True, "references": False, "seed": True}
    kinds = ("image",)
    sized_by_source = True

    def _root(self):
        return pixelfx_dir(self.options, self.project_root)

    def check(self):
        root = self._root()
        if not os.path.isfile(os.path.join(root, "tools", "render.mjs")):
            return False, f"pixelfx 없음: {root} — python .agent/tools/setup/prereq.py install pixelfx"
        node = self.options.get("node", "node")
        ver = _node_version(node)
        if ver is None:
            return False, f"Node 를 실행하지 못함 ({node}) — Node {MIN_NODE[0]}+ 설치 또는 providers.pixelfx.node 지정"
        if ver < MIN_NODE:
            return False, f"Node {ver[0]}.{ver[1]} — {MIN_NODE[0]} 이상 필요"
        commit = _commit(root)
        return True, f"{root} · Node {ver[0]}.{ver[1]}" + (f" · 커밋 {commit[:7]}" if commit else "")

    def _effect(self, job, root):
        effect = job.options.get("effect")
        if not isinstance(effect, str) or not EFFECT_RE.match(effect):
            raise ArtgenError("providerOptions.pixelfx.effect 필수 — '<분류>/<이름>' (예: ice/frost-nova). "
                              "목록: node <pixelfx>/tools/list.mjs")
        # render.mjs 는 없는 id 에도 exit 0 이라 여기서 막는다 (패턴 · 분류 전체 렌더도 막힌다)
        src = os.path.join(root, "src", "fx", *effect.split("/")) + ".js"
        if not os.path.isfile(src):
            raise ArtgenError(f"pixelfx 효과 없음: {effect} — node {root}/tools/list.mjs 로 id 확인")
        return effect, src

    def _opts(self, job):
        extra = job.options.get("options") or {}
        if not isinstance(extra, dict):
            raise ArtgenError("providerOptions.pixelfx.options 는 객체")
        opts = dict(extra)
        palette = job.request.get("prompt", {}).get("palette") or []
        if "palette" not in opts and palette:
            opts["palette"] = palette_ramp(palette)
        return opts

    def _run(self, argv, root):
        try:
            return subprocess.run(argv, cwd=root, capture_output=True, text=True, encoding="utf-8",
                                  timeout=self.options.get("timeoutSec", 300))
        except subprocess.TimeoutExpired:
            raise ArtgenError(f"pixelfx 시간 초과 ({self.options.get('timeoutSec', 300)}s): {' '.join(argv[1:3])}")
        except OSError as e:
            raise ArtgenError(f"Node 실행 실패: {e}")

    def generate(self, job):
        self.project_root = self.project_root or job.project_root
        root = self._root()
        ok, msg = self.check()
        if not ok:
            raise ArtgenError(msg)
        effect, src = self._effect(job, root)
        opts = self._opts(job)
        margin = job.options.get("trimMargin", 1)
        if not isinstance(margin, int) or isinstance(margin, bool) or not 0 <= margin <= 16:
            raise ArtgenError("providerOptions.pixelfx.trimMargin 은 0~16 정수")
        fps = job.options.get("fps")
        if fps is not None and (not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 60):
            raise ArtgenError("providerOptions.pixelfx.fps 는 1~60 정수")
        node = self.options.get("node", "node")
        render = os.path.join(root, "tools", "render.mjs")
        name = effect.split("/")[1]
        work = os.path.join(job.out_dir, "_pixelfx")
        source = self._source(effect, src, root, opts)

        paths = []
        for i, seed in enumerate(job.seeds):
            argv = [node, render, effect, "--sheet", "--no-actor", "--seed", str(seed), "--out", work]
            if fps:
                argv += ["--fps", str(fps)]
            if opts:
                argv += ["--opts", json.dumps(opts, ensure_ascii=False)]
            proc = self._run(argv, root)
            sheet_png = os.path.join(work, *effect.split("/"), f"{name}.png")
            sheet_json = os.path.join(work, *effect.split("/"), f"{name}.json")
            if proc.returncode != 0 or not os.path.isfile(sheet_png) or not os.path.isfile(sheet_json):
                raise ArtgenError(f"pixelfx 렌더 실패 ({effect} seed={seed}): "
                                  f"{(proc.stderr or proc.stdout).strip()[-600:] or '출력 없음'}")
            stem = os.path.join(job.out_dir, f"variant_{i + 1:02d}")
            with open(sheet_json, encoding="utf-8") as f:
                sheet = json.load(f)
            sheet.setdefault("meta", {})["image"] = os.path.basename(stem) + ".png"
            sheet["meta"].setdefault("pixelfx", {}).update(seed=seed, options=opts)
            os.replace(sheet_png, stem + ".png")
            _write_json(stem + ".sheet.json", sheet)
            if job.options.get("trim", True):
                trim_sheet(stem + ".png", stem + ".sheet.json", margin=int(job.options.get("trimMargin", 1)))
            _write_json(stem + ".source.json", source)
            shutil.rmtree(work, ignore_errors=True)  # 다음 변형이 이전 시트를 집지 않게
            paths.append(stem + ".png")

        if self.options.get("check", True):
            self.run_warnings += self._check_effect(node, root, effect)
        return paths

    def _source(self, effect, src, root, opts):
        with open(src, encoding="utf-8") as f:
            head = f.read(4000)
        attribution = [ATTRIBUTION] + [v for k, v in UPSTREAM_NOTICES.items() if k in head]
        out = {"library": "pixelfx", "file": effect, "license": LICENSE, "url": URL,
               "attribution": "; ".join(attribution)}
        commit = _commit(root)
        if commit:
            out["commit"] = commit
        return out

    def _check_effect(self, node, root, effect):
        """tools/check.mjs — 캔버스 밖 픽셀 · 루프 이음새 · 시드 없는 난수 · 느린 프레임. 결과를 경고 문자열로."""
        proc = self._run([node, os.path.join(root, "tools", "check.mjs"), effect], root)
        notes = [ln.strip() for ln in proc.stdout.splitlines() if ln.startswith("      ") and ln.strip()]
        if proc.returncode != 0:
            return [f"pixelfx check 실패 ({effect}): " + ("; ".join(notes) or proc.stderr.strip()[-300:])]
        return [f"pixelfx check: {n}" for n in notes]


def _write_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


PROVIDER_CLASS = PixelfxProvider
