"""버전 저장소 — production/artgen/<ASSET-ID>/v###/ 에 생성 결과를 쌓고, 선택·승격·임포트 맵을 관리.

생성물은 Assets/ 밖에 둔다. Unity 는 검수·승격된 파일만 임포트한다.

<storeDir>/
  import-map.json                    Unity 임포트 설정 (ArtGenImportPostprocessor 가 읽음)
  ASSET-001/
    state.json                       status: generated | selected | promoted | rejected
    review.md                        검수 기록 (스킬이 작성)
    v001/ job.json run.json variant_01.png ...
                                     오디오: variant_01.wav (원본 오디오 어댑터면 variant_01.src.flac 도 남김)
"""
import datetime
import hashlib
import json
import os
import random
import shutil
import subprocess

from . import ArtgenError, audioutil
from . import providers as registry
from .pngutil import read_info
from .providers.base import Job
from .request import compile_prompt, import_defaults, kind_of, request_hash

AUDIO_POST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_post.py")
AUDIO_DEFAULTS = {"python": "", "peakDbfs": -1.0, "loopCrossfadeMs": 250, "fadeInMs": 5, "fadeOutMs": 30,
                  "trimLeadingSilence": True, "timeoutSec": 300}


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _rel(root, path):
    return os.path.relpath(path, root).replace("\\", "/")


class Store:
    def __init__(self, root, config):
        self.root = os.path.abspath(root)
        self.config = config
        self.dir = os.path.join(self.root, config["storeDir"])
        self.import_map_path = os.path.join(self.root, config["importMap"])

    # ---- 경로 · 상태 ----
    def asset_dir(self, asset_id):
        return os.path.join(self.dir, asset_id)

    def load_state(self, asset_id):
        return _read_json(os.path.join(self.asset_dir(asset_id), "state.json"))

    def _save_state(self, asset_id, state):
        state["updatedAt"] = _now()
        _write_json(os.path.join(self.asset_dir(asset_id), "state.json"), state)

    def _require_state(self, asset_id):
        state = self.load_state(asset_id)
        if not state:
            raise ArtgenError(f"{asset_id}: 생성 기록 없음 — 먼저 generate")
        return state

    def _next_version(self, asset_id):
        d = self.asset_dir(asset_id)
        nums = [int(n[1:]) for n in os.listdir(d) if n.startswith("v") and n[1:].isdigit()] if os.path.isdir(d) else []
        return f"v{(max(nums) + 1 if nums else 1):03d}"

    # ---- 생성 ----
    def generate(self, request, request_path, provider_name=None, variants=None, seed=None, dry_run=False):
        kind = kind_of(request)
        if not provider_name and kind == "audio":
            # 카테고리별 출처 (예: 효과음은 생성하지 않고 라이브러리에서) — --provider 가 우선한다
            provider_name = self._audio_settings().get("providerByCategory", {}).get(request["category"])
        provider_name = provider_name or self.config["provider"]
        provider = registry.create(provider_name, self.config, request)
        if kind not in provider.kinds:
            raise ArtgenError(f"provider '{provider_name}' 는 {kind} 요청을 지원하지 않음 (지원: {', '.join(provider.kinds)})")
        ok, msg = provider.check()
        if not ok:
            raise ArtgenError(f"provider '{provider_name}' 사용 불가 — {msg}")
        if kind == "audio" and provider.raw_audio:
            self._audio_python()  # 생성 전에 후처리 준비를 확인 — GPU 시간을 쓴 뒤 실패하지 않게

        out = request["output"]
        n = variants or out.get("variants") or self.config["defaults"]["variants"]
        base_seed = seed if seed is not None else out["seed"]
        if base_seed is None:
            base_seed = random.SystemRandom().randrange(0, 2 ** 31)
        seeds = [base_seed + i for i in range(n)]
        prompt = compile_prompt(request)

        asset_id = request["assetId"]
        version = self._next_version(asset_id)
        vdir = os.path.join(self.asset_dir(asset_id), version)
        refs = [os.path.join(self.root, r) for r in request["references"]]
        missing = [r for r, a in zip(request["references"], refs) if not os.path.isfile(a)]
        if missing:
            raise ArtgenError(f"참조 이미지 없음: {', '.join(missing)}")

        audio = kind == "audio"
        job = Job(asset_id=asset_id, request=request, positive=prompt["positive"], negative=prompt["negative"],
                  width=0 if audio else out["width"], height=0 if audio else out["height"],
                  transparent=False if audio else out["transparent"], variants=n,
                  seeds=seeds, references=refs, out_dir=vdir, job_file=os.path.join(vdir, "job.json"),
                  options=provider.options, project_root=self.root, kind=kind,
                  duration=out["durationSec"] if audio else 0.0, loop=out["loop"] if audio else False,
                  channels=out["channels"] if audio else 0, sample_rate=out["sampleRate"] if audio else 0)
        plan = {"assetId": asset_id, "version": version, "provider": provider_name, "kind": kind, "variants": n,
                "seeds": seeds, "prompt": prompt, "outDir": _rel(self.root, vdir)}
        if dry_run:
            return dict(plan, dryRun=True)

        os.makedirs(vdir)
        job_doc = {k: v for k, v in job.__dict__.items()}
        _write_json(job.job_file, job_doc)
        started = _now()
        try:
            paths = provider.generate(job)
        except Exception as e:
            _write_json(os.path.join(vdir, "run.json"), dict(plan, startedAt=started, failedAt=_now(), error=str(e)))
            if isinstance(e, ArtgenError):
                raise
            raise ArtgenError(f"provider '{provider_name}' 예외: {e!r}")

        if audio:
            outputs, warnings = self._audio_outputs(paths, out, seeds, provider, vdir)
        else:
            outputs, warnings = self._image_outputs(paths, out, seeds)
        if provider.honors_variants and len(outputs) != n:
            warnings.append(f"변형 수 {len(outputs)} ≠ 요청 {n}")

        run = dict(plan, requestFile=_rel(self.root, os.path.abspath(request_path)),
                   requestHash=request_hash(request), placeholder=getattr(provider, "placeholder", False),
                   capabilities=provider.capabilities, startedAt=started, finishedAt=_now(),
                   outputs=outputs, warnings=warnings)
        _write_json(os.path.join(vdir, "run.json"), run)

        state = self.load_state(asset_id) or {"assetId": asset_id, "name": request["name"], "versions": []}
        state.update(status="generated", name=request["name"], kind=kind, requestFile=run["requestFile"],
                     unityDest=request.get("unity", {}).get("dest"))
        state["versions"].append({"version": version, "provider": provider_name, "files": [o["file"] for o in outputs],
                                  "createdAt": run["finishedAt"]})
        self._save_state(asset_id, state)
        return run

    def _image_outputs(self, paths, out, seeds):
        outputs, warnings = [], []
        for i, p in enumerate(paths):
            p = os.path.abspath(p)
            info = read_info(p) if os.path.isfile(p) else None
            if info is None:
                warnings.append(f"{os.path.basename(p)}: PNG 아님 또는 파일 없음")
                continue
            w, h, alpha = info
            if (w, h) != (out["width"], out["height"]):
                warnings.append(f"{os.path.basename(p)}: 크기 {w}x{h} ≠ 요청 {out['width']}x{out['height']}")
            if out["transparent"] and not alpha:
                warnings.append(f"{os.path.basename(p)}: 투명 배경 요청했으나 알파 채널 없음")
            outputs.append({"file": os.path.basename(p), "width": w, "height": h, "alpha": alpha,
                            "seed": seeds[i] if i < len(seeds) else None, "sha256": _sha256(p)})
        return outputs, warnings

    # ---- 오디오 ----
    def _audio_settings(self):
        return dict(AUDIO_DEFAULTS, **self.config.get("audio", {}))

    def _audio_python(self):
        exe = self._audio_settings()["python"]
        if not exe:
            raise ArtgenError("오디오 후처리 인터프리터 미설정 — artgen.config.local.json 의 audio.python 에 PyAV + numpy 가 "
                              "있는 Python 경로를 지정 (예: ComfyUI 포터블의 python_embeded/python.exe)")
        path = exe if os.path.isabs(exe) else os.path.join(self.root, exe)
        if not os.path.isfile(path):
            raise ArtgenError(f"audio.python 경로 없음: {exe}")
        return path

    def _post_audio(self, src, dst, out, fit_max=False):
        a = self._audio_settings()
        argv = [self._audio_python(), AUDIO_POST, "--in", src, "--out", dst, "--rate", str(out["sampleRate"]),
                "--channels", str(out["channels"]), "--duration", str(out["durationSec"]),
                "--loop", str(int(out["loop"])), "--crossfade-ms", str(a["loopCrossfadeMs"]),
                "--fade-in-ms", str(a["fadeInMs"]), "--fade-out-ms", str(a["fadeOutMs"]),
                "--peak-dbfs", str(a["peakDbfs"]), "--trim-lead", str(int(a["trimLeadingSilence"])),
                "--fit", "max" if fit_max else "exact"]
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", timeout=a["timeoutSec"])
        except subprocess.TimeoutExpired:
            raise ArtgenError(f"오디오 후처리 시간 초과 ({a['timeoutSec']}s): {os.path.basename(src)}")
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        try:
            info = json.loads(lines[-1])
        except (IndexError, ValueError):
            info = {"ok": False, "error": (proc.stderr or proc.stdout).strip()[-600:]}
        if proc.returncode != 0 or not info.get("ok"):
            raise ArtgenError(f"오디오 후처리 실패 ({os.path.basename(src)}): {info.get('error')}")
        info.pop("ok", None)
        return info

    def _audio_outputs(self, paths, out, seeds, provider, vdir):
        outputs, warnings = [], []
        fit_max = getattr(provider, "duration_is_max", False)
        for i, p in enumerate(paths):
            p = os.path.abspath(p)
            post = None
            if provider.raw_audio:
                # 원본은 variant_01.src.flac 로 남기고 WAV 를 새로 만든다 (재처리 · 추적용)
                ext = os.path.splitext(p)[1].lower() or ".bin"
                src = os.path.join(vdir, f"variant_{i + 1:02d}.src{ext}")
                if p != src:
                    os.replace(p, src)
                p = os.path.join(vdir, f"variant_{i + 1:02d}.wav")
                post = self._post_audio(src, p, out, fit_max)
            stats = audioutil.analyze(p) if os.path.isfile(p) else None
            if stats is None:
                warnings.append(f"{os.path.basename(p)}: WAV 아님 또는 파일 없음")
                continue
            warnings += [f"{os.path.basename(p)}: {w}" for w in audioutil.check(stats, out, duration_is_max=fit_max)]
            entry = {"file": os.path.basename(p), "durationSec": round(stats["durationSec"], 3),
                     "sampleRate": stats["rate"], "channels": stats["channels"],
                     "seed": seeds[i] if i < len(seeds) else None, "sha256": _sha256(p)}
            for k in ("peakDbfs", "clippedRatio", "leadSilenceSec", "tailSilenceSec", "loopSeam"):
                if k in stats:
                    entry[k] = stats[k]
            if post:
                entry["post"] = post
            source = _read_json(os.path.join(vdir, f"variant_{i + 1:02d}.source.json"))
            if source:  # 기성 소리 출처 · 라이선스 — 승격 때 credits.json 으로 옮긴다
                entry["source"] = source
            outputs.append(entry)
        return outputs, warnings

    # ---- 선택 · 반려 ----
    def select(self, asset_id, version, file):
        state = self._require_state(asset_id)
        path = os.path.join(self.asset_dir(asset_id), version, file)
        if not os.path.isfile(path):
            raise ArtgenError(f"파일 없음: {_rel(self.root, path)}")
        state.update(status="selected", selected={"version": version, "file": file, "sha256": _sha256(path)})
        state.pop("rejectReason", None)
        self._save_state(asset_id, state)
        return state

    def reject(self, asset_id, reason):
        state = self._require_state(asset_id)
        state.update(status="rejected", rejectReason=reason)
        self._save_state(asset_id, state)
        return state

    # ---- Unity 승격 ----
    def promote(self, request, dest=None, force=False):
        asset_id = request["assetId"]
        state = self._require_state(asset_id)
        sel = state.get("selected")
        if state["status"] not in ("selected", "promoted") or not sel:
            raise ArtgenError(f"{asset_id}: 선택된 변형 없음 — 먼저 select")
        dest = dest or request.get("unity", {}).get("dest")
        if not dest:
            raise ArtgenError(f"{asset_id}: unity.dest 없음 — 요청에 지정하거나 --dest 사용")
        if not dest.startswith("Assets/") or ".." in dest.split("/"):
            raise ArtgenError("dest 는 'Assets/' 로 시작하는 상대경로")
        if not os.path.isdir(os.path.join(self.root, "Assets")):
            raise ArtgenError(f"Unity 프로젝트 루트가 아님 (Assets/ 없음): {self.root}")

        src = os.path.join(self.asset_dir(asset_id), sel["version"], sel["file"])
        dst = os.path.join(self.root, *dest.split("/"))
        backup = None
        if os.path.isfile(dst):
            if not force:
                raise ArtgenError(f"이미 존재: {dest} — 교체하려면 --force (기존 파일은 저장소에 백업)")
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            bdir = os.path.join(self.asset_dir(asset_id), "replaced")
            os.makedirs(bdir, exist_ok=True)
            backup = os.path.join(bdir, f"{stamp}-{os.path.basename(dst)}")
            shutil.copy2(dst, backup)
        ext = os.path.splitext(sel["file"])[1].lower()
        if os.path.splitext(dest)[1].lower() != ext:
            raise ArtgenError(f"dest 확장자가 선택 파일({ext})과 다름: {dest}")
        # 임포트 맵을 먼저 써야 Unity 가 파일을 처음 볼 때 설정이 적용된다
        settings = import_defaults(request)
        settings.update(request.get("unity", {}).get("import", {}))
        self._upsert_import_entry(dict(settings, path=dest, assetId=asset_id, kind=kind_of(request),
                                       sourceSha256=sel["sha256"]))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        self._record_credit(asset_id, sel, dest)

        state.update(status="promoted", promoted={"dest": dest, "at": _now(), "version": sel["version"],
                                                  "file": sel["file"], "backup": _rel(self.root, backup) if backup else None})
        self._save_state(asset_id, state)
        return state

    def _record_credit(self, asset_id, sel, dest):
        """기성 소스(라이브러리)에서 온 파일이면 credits.json 에 출처 · 라이선스를 남긴다 — 출시 전 라이선스 점검 근거.
        같은 경로를 생성물로 다시 승격하면 이전 기록을 지운다."""
        run = _read_json(os.path.join(self.asset_dir(asset_id), sel["version"], "run.json"), {})
        source = next((o.get("source") for o in run.get("outputs", []) if o.get("file") == sel["file"]), None)
        path = os.path.join(self.dir, "credits.json")
        data = _read_json(path, {"version": 1, "entries": []})
        entries = [e for e in data["entries"] if e.get("path") != dest]
        if source:
            entries.append(dict(source, path=dest, assetId=asset_id))
        elif len(entries) == len(data["entries"]):
            return  # 기록할 것도 지울 것도 없음 — 파일을 만들지 않는다
        data["entries"] = sorted(entries, key=lambda e: e["path"])
        os.makedirs(self.dir, exist_ok=True)
        _write_json(path, data)

    def _upsert_import_entry(self, entry):
        data = _read_json(self.import_map_path, {"version": 1, "entries": []})
        entries = [e for e in data["entries"] if e.get("path") != entry["path"]]
        entries.append(entry)
        entries.sort(key=lambda e: e["path"])
        data["entries"] = entries
        os.makedirs(os.path.dirname(self.import_map_path), exist_ok=True)
        _write_json(self.import_map_path, data)

    # ---- 조회 ----
    def list_states(self):
        if not os.path.isdir(self.dir):
            return []
        out = []
        for name in sorted(os.listdir(self.dir)):
            s = self.load_state(name) if os.path.isdir(os.path.join(self.dir, name)) else None
            if s:
                out.append(s)
        return out
