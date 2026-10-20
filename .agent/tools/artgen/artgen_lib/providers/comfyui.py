"""comfyui — 로컬 ComfyUI 서버(HTTP API)로 이미지를 생성한다. 표준 라이브러리만 사용.

흐름: 워크플로(API 형식) 제출 POST /prompt → GET /history/<id> 로 완료 대기 → GET /view 로 이미지 수령.
변형마다 시드 하나씩 따로 제출한다 (변형별 재현성).

워크플로 두 가지:
  1. 기본 그래프 (설정만으로 동작) — 체크포인트 → 프롬프트 → SDXL 해상도 생성 → 디코드
     → [배경 제거 노드] → 요청 크기로 축소 → 저장
  2. 사용자 워크플로 — ComfyUI 에서 "Export (API)" 로 저장한 JSON. 문자열 값 안의 토큰을 치환한다:
     {{positive}} {{negative}} {{seed}} {{width}} {{height}} {{gen_width}} {{gen_height}}
     값 전체가 토큰인 숫자 필드({{seed}} 등)는 숫자로 바뀐다. 결과는 모든 SaveImage 류 출력에서 수집한다.

설정 (artgen.config.json → providers.comfyui, 요청별 덮어쓰기는 request.providerOptions.comfyui):
    url              ComfyUI 주소 (기본 http://127.0.0.1:8188)
    checkpoint       models/checkpoints 안의 파일명 (기본 그래프)
    vae              models/vae 안의 파일명 — 비우면 체크포인트 내장 VAE
    steps · cfg · sampler · scheduler
    genArea          생성 해상도 면적 기준 (SDXL 1024*1024). 요청 비율에 맞춰 64 배수로 정한다
    removeBackground 투명 배경 {"model": "birefnet.safetensors"} — models/background_removal 의 BiRefNet 으로
                     코어 노드 체인 구성 (ComfyUI 0.42+). 비우면 투명 배경 미지원 (capabilities.transparent=false)
    workflow         사용자 워크플로 JSON 경로 (프로젝트 루트 기준). 지정하면 기본 그래프 대신 사용
    timeoutSec       이미지 1장 대기 한도 (기본 600)
"""
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .. import ArtgenError
from .base import Provider

TOKENS = ("positive", "negative", "seed", "width", "height", "gen_width", "gen_height")
SAVE_NODE_TYPES = ("SaveImage", "Image Save")


def gen_size(width, height, area=1024 * 1024, multiple=64):
    """요청 비율을 유지하며 면적 ≈ area 인 64 배수 해상도 (SDXL 은 1024² 근처에서 가장 안정적)."""
    ratio = width / height
    h = math.sqrt(area / ratio)
    w = h * ratio
    return max(multiple, int(round(w / multiple)) * multiple), max(multiple, int(round(h / multiple)) * multiple)


TRANSPARENT_PHRASE = "isolated on transparent background"  # request.compile_prompt 가 붙이는 백엔드 중립 문구


def adapt_prompt(positive, negative, transparent, remove_background):
    """SDXL 은 'transparent background' 를 잘 따르지 못한다 — 배경 제거를 쓸 때는 단색 배경의 단일 오브젝트를
    그리게 하고(제거가 쉬움), 장면 · 지면 · 잘림을 부정 프롬프트로 막는다."""
    if transparent and remove_background:
        positive = positive.replace(TRANSPARENT_PHRASE, "single isolated object, centered, "
                                                        "on a plain flat white background, empty background")
        extra = "scene, landscape, environment, ground, floor, rocks, cropped, cut off, frame filling, busy background"
        negative = f"{negative}, {extra}" if negative else extra
    return positive, negative


def build_default_graph(o, positive, negative, seed, width, height, transparent):
    positive, negative = adapt_prompt(positive, negative, transparent, o.get("removeBackground"))
    gw, gh = gen_size(width, height, o.get("genArea", 1024 * 1024))
    g = {
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": o["checkpoint"]}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["ckpt", 1]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["ckpt", 1]}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": gw, "height": gh, "batch_size": 1}},
        "sample": {"class_type": "KSampler", "inputs": {
            "model": ["ckpt", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": seed, "steps": o.get("steps", 28), "cfg": o.get("cfg", 6.5),
            "sampler_name": o.get("sampler", "dpmpp_2m"), "scheduler": o.get("scheduler", "karras"), "denoise": 1.0}},
    }
    vae_ref = ["ckpt", 2]
    if o.get("vae"):
        g["vae"] = {"class_type": "VAELoader", "inputs": {"vae_name": o["vae"]}}
        vae_ref = ["vae", 0]
    g["decode"] = {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": vae_ref}}
    image = ["decode", 0]
    rb = o.get("removeBackground")
    if transparent and rb:
        # 코어 BiRefNet 체인. RemoveBackground 는 전경 확률(전경=1) 마스크를 내고,
        # JoinImageWithAlpha 는 alpha = 1 - mask 로 뒤집으므로 그 사이에 InvertMask 가 필요하다.
        # 축소 전 원본 해상도에서 제거해야 가장자리가 정확하다.
        g["bg_model"] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": rb["model"]}}
        g["bg_mask"] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["bg_model", 0], "image": image}}
        mask = ["bg_mask", 0]
        if rb.get("threshold", 0.5) is not None:
            # 전경 확률이 0.996 수준이라 그대로 쓰면 내부 알파가 254 로 남는다(미세하게 비침).
            # 원본 해상도에서 이진화한 뒤 아래 lanczos 축소가 가장자리를 다시 부드럽게 만든다.
            g["bg_threshold"] = {"class_type": "ThresholdMask", "inputs": {"mask": mask, "value": rb.get("threshold", 0.5)}}
            mask = ["bg_threshold", 0]
        g["bg_invert"] = {"class_type": "InvertMask", "inputs": {"mask": mask}}
        g["bg_join"] = {"class_type": "JoinImageWithAlpha", "inputs": {"image": image, "alpha": ["bg_invert", 0]}}
        image = ["bg_join", 0]
    if (gw, gh) != (width, height):
        g["scale"] = {"class_type": "ImageScale", "inputs": {
            "image": image, "upscale_method": "lanczos", "width": width, "height": height, "crop": "disabled"}}
        image = ["scale", 0]
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": image, "filename_prefix": "artgen"}}
    return g


def fill_workflow(graph, values):
    """사용자 워크플로의 토큰 치환. 값 전체가 토큰이면 원래 타입(숫자)으로, 부분이면 문자열로."""
    def sub(v):
        if isinstance(v, str):
            for t in TOKENS:
                if v == "{{" + t + "}}":
                    return values[t]
            for t in TOKENS:
                v = v.replace("{{" + t + "}}", str(values[t]))
            return v
        if isinstance(v, list):
            return [sub(x) for x in v]
        if isinstance(v, dict):
            return {k: sub(x) for k, x in v.items()}
        return v
    return sub(json.loads(json.dumps(graph)))


class ComfyUIProvider(Provider):
    name = "comfyui"
    description = "로컬 ComfyUI 서버 (HTTP API) — 기본 SDXL 그래프 또는 사용자 워크플로"

    def __init__(self, options):
        super().__init__(options)
        self.url = self.options.get("url", "http://127.0.0.1:8188").rstrip("/")
        self.capabilities = {"transparent": bool(self.options.get("removeBackground")),
                             "references": False, "seed": True}

    # ---- HTTP ----
    def _get(self, path, timeout=10, raw=False):
        try:
            with urllib.request.urlopen(self.url + path, timeout=timeout) as r:
                data = r.read()
        except urllib.error.URLError as e:
            raise ArtgenError(f"ComfyUI 연결 실패 ({self.url}): {e.reason if hasattr(e, 'reason') else e}")
        return data if raw else json.loads(data.decode("utf-8"))

    def _post(self, path, payload, timeout=30):
        req = urllib.request.Request(self.url + path, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(body)
                detail = err.get("error", {}).get("message", "")
                nodes = "; ".join(f"{nid}: {[x.get('message') for x in ne.get('errors', [])]}"
                                  for nid, ne in err.get("node_errors", {}).items())
                body = f"{detail} {nodes}".strip()
            except ValueError:
                pass
            raise ArtgenError(f"ComfyUI 가 워크플로를 거부 (HTTP {e.code}): {body[:600]}")
        except urllib.error.URLError as e:
            raise ArtgenError(f"ComfyUI 연결 실패 ({self.url}): {e.reason}")

    # ---- 계약 ----
    def check(self):
        try:
            stats = self._get("/system_stats", timeout=3)
        except ArtgenError as e:
            return False, f"{e} — ComfyUI 를 먼저 실행 (run_nvidia_gpu.bat)"
        devices = ", ".join(d.get("name", "?") for d in stats.get("devices", []))
        if not self.options.get("workflow") and not self.options.get("checkpoint"):
            return False, "providers.comfyui.checkpoint 미설정 (기본 그래프) 또는 workflow 지정 필요"
        return True, f"{self.url} · {devices}"

    def _graph(self, job, seed):
        o = self.options
        gw, gh = gen_size(job.width, job.height, o.get("genArea", 1024 * 1024))
        if o.get("workflow"):
            path = os.path.join(job.project_root or os.getcwd(), o["workflow"])
            try:
                with open(path, encoding="utf-8") as f:
                    graph = json.load(f)
            except (OSError, ValueError) as e:
                raise ArtgenError(f"사용자 워크플로 읽기 실패: {path} — {e}")
            return fill_workflow(graph, {"positive": job.positive, "negative": job.negative, "seed": seed,
                                         "width": job.width, "height": job.height, "gen_width": gw, "gen_height": gh})
        return build_default_graph(o, job.positive, job.negative, seed, job.width, job.height, job.transparent)

    def _wait(self, prompt_id):
        timeout = self.options.get("timeoutSec", 600)
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            hist = self._get(f"/history/{prompt_id}")
            entry = hist.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    msgs = [m for m in status.get("messages", []) if m and m[0] == "execution_error"]
                    detail = msgs[-1][1].get("exception_message", "") if msgs else ""
                    raise ArtgenError(f"ComfyUI 실행 오류: {detail[:600]}")
                if status.get("completed") or entry.get("outputs"):
                    return entry.get("outputs", {})
            time.sleep(1.0)
        raise ArtgenError(f"ComfyUI 대기 시간 초과 ({timeout}s)")

    def generate(self, job):
        ok, msg = self.check()
        if not ok:
            raise ArtgenError(msg)
        client_id = uuid.uuid4().hex
        paths = []
        for i, seed in enumerate(job.seeds):
            res = self._post("/prompt", {"prompt": self._graph(job, seed), "client_id": client_id})
            outputs = self._wait(res["prompt_id"])
            images = [img for out in outputs.values() for img in out.get("images", []) if img.get("type") == "output"]
            if not images:
                raise ArtgenError("ComfyUI 출력 이미지 없음 — 워크플로에 SaveImage 노드가 있는지 확인")
            img = images[-1]  # 마지막 저장 노드 = 최종 결과 (중간 미리보기 제외)
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                        "type": img["type"]})
            data = self._get(f"/view?{q}", timeout=60, raw=True)
            path = os.path.join(job.out_dir, f"variant_{i + 1:02d}.png")
            with open(path, "wb") as f:
                f.write(data)
            paths.append(path)
        return paths


PROVIDER_CLASS = ComfyUIProvider
