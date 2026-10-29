"""사전 설치 점검 · 설치 — 자동화(스튜디오 모드 · artgen 그래픽/사운드 · Unity MCP)를 돌리기 전에 필요한 것.

    python .agent/tools/setup/prereq.py check   [--roles dev,art] [--platforms android] [--json]
    python .agent/tools/setup/prereq.py install [항목 ...] [--yes] [--dry-run] [--comfyui-home DIR] [--library-dir DIR]

check   항목마다 ok · missing · warn · decide(사용자 결정) 를 보여 준다. 필수 항목이 missing 이면 종료 코드 1.
install 자동으로 고칠 수 있는 missing 항목만 처리한다 (항목을 주지 않으면 전부). 받을 용량 · 라이선스를 먼저 보여 주고
        --yes 가 없으면 확인을 받는다. 라이선스 동의가 필요한 것(Stable Audio · gamedesign 카탈로그)은 절대 자동으로 받지 않는다.

표준 라이브러리만 쓴다. 모델은 크기와 SHA256 을 고정해 두고 받은 뒤 검증한다 (이어받기 · 재시도 포함).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ARTGEN_DIR = os.path.join(os.path.dirname(TOOL_DIR), "artgen")
sys.path.insert(0, ARTGEN_DIR)

from artgen_lib import library as soundlib  # noqa: E402
from artgen_lib.config import load_config  # noqa: E402

ROLES = ("planning", "art", "dev")
MIN_GIT = (2, 25)
MIN_COMFYUI = (0, 42)
MIN_VRAM_MB = 8000
COMFYUI_CANDIDATES = (r"D:\AI\ComfyUI_windows_portable", r"C:\AI\ComfyUI_windows_portable", r"C:\ComfyUI_windows_portable")
COMFYUI_RELEASES = "https://github.com/comfyanonymous/ComfyUI/releases (ComfyUI_windows_portable_nvidia.7z)"
UNITY_MCP_PKG = '"com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"'

# 상업 이용 가능 · 게이트 없음 확인 (2026-10-29). size · sha256 은 HF LFS 메타데이터
MODELS = {
    "sdxl-base": {"repo": "stabilityai/stable-diffusion-xl-base-1.0", "path": "sd_xl_base_1.0.safetensors",
                  "dir": "checkpoints", "file": "sd_xl_base_1.0.safetensors", "license": "CreativeML Open RAIL++-M",
                  "size": 6938078334, "sha256": "31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b"},
    "sdxl-vae": {"repo": "madebyollin/sdxl-vae-fp16-fix", "path": "sdxl.vae.safetensors",
                 "dir": "vae", "file": "sdxl_vae_fp16_fix.safetensors", "license": "MIT",
                 "size": 334641162, "sha256": "235745af8d86bf4a4c1b5b4f529868b37019a10f7c0b2e79ad0abca3a22bc6e1"},
    "birefnet": {"repo": "Comfy-Org/BiRefNet", "path": "background_removal/birefnet.safetensors",
                 "dir": "background_removal", "file": "birefnet.safetensors", "license": "MIT",
                 "size": 444473596, "sha256": "9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154"},
    "z-image-unet": {"repo": "Comfy-Org/Z-Image-Turbo", "path": "split_files/diffusion_models/z_image_turbo_bf16.safetensors",
                     "dir": "diffusion_models", "file": "z_image_turbo_bf16.safetensors", "license": "Apache-2.0",
                     "size": 12309866400, "sha256": "2407613050b809ffdff18a4ac99af83ea6b95443ecebdf80e064a79c825574a6"},
    "z-image-clip": {"repo": "Comfy-Org/Z-Image-Turbo", "path": "split_files/text_encoders/qwen_3_4b.safetensors",
                     "dir": "text_encoders", "file": "qwen_3_4b.safetensors", "license": "Apache-2.0",
                     "size": 8044982048, "sha256": "6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a"},
    "z-image-vae": {"repo": "Comfy-Org/Z-Image-Turbo", "path": "split_files/vae/ae.safetensors",
                    "dir": "vae", "file": "ae.safetensors", "license": "Apache-2.0",
                    "size": 335304388, "sha256": "afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38"},
    "ace-step-1.5": {"repo": "Comfy-Org/ACE-Step-1.5", "path": "checkpoints/ace_step_1.5_turbo_aio.safetensors",
                     "dir": "checkpoints", "file": "ace_step_1.5_turbo_aio.safetensors", "license": "Apache-2.0 (원본 MIT)",
                     "size": 10025478736, "sha256": "67b0f43aa5c51c840bd0228e6a935d8ff416ec87e5df2fc0637da17a561252bc"},
}
# Kenney 오디오 팩 — 모두 CC0 (페이지에 "CC0 licensed" 명시). 음성(voiceover)은 대사라 제외
KENNEY_PACKS = ("interface-sounds", "ui-audio", "impact-sounds", "digital-audio", "rpg-audio", "casino-audio",
                "sci-fi-sounds", "music-jingles")


# ---------------------------------------------------------------- 공통
def _ver(text):
    m = re.search(r"(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _run(argv, timeout=20):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _human(n):
    return f"{n / 1e9:.1f}GB" if n >= 1e9 else f"{n / 1e6:.0f}MB"


class Ctx:
    """점검 대상 프로젝트와 설정."""

    def __init__(self, root, roles=ROLES, comfyui_home=None, library_dir=None, platforms=None):
        self.root = os.path.abspath(root)
        self.roles = set(roles)
        self.platforms = {p.lower() for p in platforms} if platforms is not None else None  # None = 문서에서 판단
        self.local_path = os.path.join(self.root, ".agent", "tools", "artgen", "artgen.config.local.json")
        self.local = _read_json(self.local_path, {}) or {}
        self.cfg = load_config(os.path.join(self.root, ".agent", "tools", "artgen")) \
            if os.path.isdir(os.path.join(self.root, ".agent", "tools", "artgen")) else load_config()
        self.comfyui_home = comfyui_home or self.cfg.get("providers", {}).get("comfyui", {}).get("home") \
            or next((c for c in COMFYUI_CANDIDATES if os.path.isfile(os.path.join(c, "ComfyUI", "main.py"))), None)
        lib = library_dir or self.cfg.get("providers", {}).get("library", {}).get("dir", "art-source/sound-library")
        self.library_dir = os.path.normpath(lib if os.path.isabs(lib) else os.path.join(self.root, lib))
        self.library_dir_overridden = bool(library_dir)

    def comfy_python(self):
        if not self.comfyui_home:
            return None
        p = os.path.join(self.comfyui_home, "python_embeded", "python.exe" if os.name == "nt" else "python")
        return p if os.path.isfile(p) else None

    def needed_models(self):
        """현재 설정이 실제로 쓰는 모델만."""
        c = self.cfg.get("providers", {}).get("comfyui", {})
        need = []
        if c.get("graph", "sdxl") == "sdxl" and not c.get("workflow"):
            need += ["sdxl-base", "sdxl-vae"]
        if c.get("graph") == "z-image-turbo":
            need += ["z-image-unet", "z-image-clip", "z-image-vae"]
        if c.get("removeBackground"):
            need.append("birefnet")
        routed = self.cfg.get("audio", {}).get("providerByCategory", {})
        by_cat = {"sfx": "stable-audio", "music": "ace-step-1.5", "ambience": "ace-step-1.5"}
        by_cat.update(c.get("audioGraphByCategory", {}))
        if any(by_cat[cat] == "ace-step-1.5" and routed.get(cat, "comfyui") == "comfyui" for cat in ("music", "ambience")):
            need.append("ace-step-1.5")
        return need


# ---------------------------------------------------------------- 항목
class Item:
    """id · 묶음 · 대상 역할 · 점검 · 자동 설치(있으면)."""

    def __init__(self, id, group, roles, title, check, install=None, manual="", size=0, license=""):
        self.id, self.group, self.roles, self.title = id, group, roles, title
        self._check, self._install, self.manual, self.size, self.license = check, install, manual, size, license

    def applies(self, ctx):
        return not self.roles or bool(self.roles & ctx.roles)

    def check(self, ctx):
        status, detail = self._check(ctx)
        return {"id": self.id, "group": self.group, "title": self.title, "status": status, "detail": detail,
                "auto": self._install is not None and status == "missing",
                "manual": self.manual(ctx) if callable(self.manual) else self.manual,
                "size": self.size, "license": self.license}


def _winget(pkg):
    def install(ctx, dry):
        if not shutil.which("winget"):
            raise RuntimeError("winget 없음 — 안내된 명령으로 직접 설치")
        if dry:
            return f"winget install --id {pkg} -e"
        code, out = _run(["winget", "install", "--id", pkg, "-e", "--accept-package-agreements",
                          "--accept-source-agreements"], timeout=1800)
        if code != 0:
            raise RuntimeError(out[-400:])
        return f"{pkg} 설치 — 새 터미널에서 PATH 반영"
    return install


def c_git(ctx):
    if not shutil.which("git"):
        return "missing", "git 없음"
    v = _ver(_run(["git", "--version"])[1])
    if not v or v < MIN_GIT:
        return "missing", f"git {v} < {MIN_GIT}"
    crlf = _run(["git", "config", "--get", "core.autocrlf"])[1].strip()
    if os.name == "nt" and crlf not in ("input", "false"):
        return "warn", f"git {v[0]}.{v[1]} · core.autocrlf={crlf or '미설정'} — 훅 스크립트 LF 유지를 위해 input 권장"
    return "ok", f"git {v[0]}.{v[1]}"


def c_python(ctx):
    v = sys.version_info
    return ("ok" if v >= (3, 8) else "missing"), f"Python {v.major}.{v.minor} ({sys.executable})"


def c_which(name, label):
    def check(ctx):
        p = shutil.which(name)
        return ("ok", p) if p else ("missing", f"{label} 을 PATH 에서 찾지 못함")
    return check


def _project_unity_version(ctx):
    text = ""
    try:
        with open(os.path.join(ctx.root, "ProjectSettings", "ProjectVersion.txt"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None, None
    v = re.search(r"m_EditorVersion:\s*(\S+)", text)
    rev = re.search(r"m_EditorVersionWithRevision:\s*\S+\s*\((\w+)\)", text)
    return (v.group(1) if v else None), (rev.group(1) if rev else None)


def unity_editor_dirs():
    dirs = [r"C:\Program Files\Unity\Hub\Editor"]
    sec = _read_json(os.path.join(os.environ.get("APPDATA", ""), "UnityHub", "secondaryInstallPath.json"))
    if isinstance(sec, str) and sec:
        dirs.insert(0, sec)
    return [d for d in dirs if os.path.isdir(d)]


def c_unity_editor(ctx):
    ver, _rev = _project_unity_version(ctx)
    if not ver:
        return "warn", "ProjectSettings/ProjectVersion.txt 없음 — Unity 프로젝트 루트에서 실행하는지 확인"
    for d in unity_editor_dirs():
        exe = os.path.join(d, ver, "Editor", "Unity.exe")
        if os.path.isfile(exe):
            return "ok", f"Unity {ver} ({exe})"
    return "missing", f"프로젝트 버전 Unity {ver} 미설치 (찾은 위치: {', '.join(unity_editor_dirs()) or '없음'})"


def m_unity_editor(ctx):
    ver, rev = _project_unity_version(ctx)
    link = f"unityhub://{ver}/{rev}" if ver and rev else "Unity Hub > Installs"
    return f"Unity Hub 로 설치: {link}"


def c_unity_mcp_pkg(ctx):
    text = ""
    try:
        with open(os.path.join(ctx.root, "Packages", "manifest.json"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return "warn", "Packages/manifest.json 없음 (Unity 프로젝트가 아님?)"
    return ("ok", "com.coplaydev.unity-mcp 의존성 있음") if "com.coplaydev.unity-mcp" in text \
        else ("missing", "MCPForUnity 패키지 의존성 없음")


def i_unity_mcp_pkg(ctx, dry):
    path = os.path.join(ctx.root, "Packages", "manifest.json")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new = re.sub(r'"dependencies"\s*:\s*\{', '"dependencies": {\n    ' + UNITY_MCP_PKG + ",", text, count=1)
    if new == text:
        raise RuntimeError("manifest.json 에서 dependencies 를 찾지 못함")
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
    return "manifest.json 에 MCPForUnity 추가 — Unity 에 포커스하면 설치된다"


def _unity_servers(servers):
    return [k for k in (servers or {}) if "unity" in k.lower()]


def c_mcp_json(ctx):
    """프로젝트 .mcp.json · Claude Code 사용자 설정 · 프로젝트 로컬 설정(~/.claude.json projects) 어디든 있으면 된다."""
    found = _unity_servers((_read_json(os.path.join(ctx.root, ".mcp.json"), {}) or {}).get("mcpServers"))
    if found:
        return "ok", f".mcp.json {found[0]}"
    user = _read_json(os.path.join(os.path.expanduser("~"), ".claude.json"), {}) or {}
    found = _unity_servers(user.get("mcpServers"))
    if found:
        return "ok", f"Claude Code 사용자 설정 {found[0]}"
    key = ctx.root.replace("\\", "/").lower()
    for path, proj in (user.get("projects") or {}).items():
        if path.replace("\\", "/").lower() == key and _unity_servers(proj.get("mcpServers")):
            return "ok", f"Claude Code 프로젝트 로컬 설정 {_unity_servers(proj['mcpServers'])[0]}"
    return "missing", "Unity MCP 서버 등록 없음 (.mcp.json · ~/.claude.json)"


# ---------------------------------------------------------------- Android (대상 플랫폼일 때만)
def android_target(ctx):
    """--platforms 로 지정했거나, technical-preferences.md 의 Target Platforms 줄에 Android 가 있으면 대상."""
    if ctx.platforms is not None:
        return "android" in ctx.platforms
    try:
        with open(os.path.join(ctx.root, ".claude", "docs", "technical-preferences.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False
    return any("target platform" in line.lower() and "android" in line.lower() for line in text.splitlines())


def _android_player(ctx):
    ver, _rev = _project_unity_version(ctx)
    for d in unity_editor_dirs():
        p = os.path.join(d, ver or "", "Editor", "Data", "PlaybackEngines", "AndroidPlayer")
        if ver and os.path.isdir(p):
            return p
    return None


def _adb(ctx):
    found = shutil.which("adb")
    if found:
        return found
    player = _android_player(ctx)
    exe = os.path.join(player, "SDK", "platform-tools", "adb.exe" if os.name == "nt" else "adb") if player else None
    return exe if exe and os.path.isfile(exe) else None


def android_only(check):
    def wrapped(ctx):
        if not android_target(ctx):
            return "skip", "대상 플랫폼에 Android 없음 (technical-preferences.md Target Platforms · --platforms android)"
        return check(ctx)
    return wrapped


def c_android_module(ctx):
    p = _android_player(ctx)
    return ("ok", p) if p else ("missing", "프로젝트 버전 Unity 에 Android Build Support 모듈 없음")


def m_android_module(ctx):
    return f"{m_unity_editor(ctx)} → Add modules → Android Build Support (OpenJDK · Android SDK & NDK 포함)"


def c_adb(ctx):
    exe = _adb(ctx)
    return ("ok", exe) if exe else ("missing", "adb 없음 — 기기 트레이스 기록(android-profiler) · 설치 확인에 필요")


def c_adb_device(ctx):
    exe = _adb(ctx)
    if not exe:
        return "warn", "adb 없음"
    code, out = _run([exe, "devices"])
    devices = [ln.split()[0] for ln in out.splitlines()[1:] if ln.strip().endswith("device")]
    return ("ok", f"연결된 기기 {len(devices)}대") if devices else \
        ("warn", "연결된 기기 없음 — 트레이스 기록 · 실기 테스트 때만 필요 (USB 디버깅 켜기)")


def c_android_catalog(ctx):
    cat = _read_json(os.path.join(ctx.root, ".agent", "android", "catalog.json"))
    if cat and cat.get("count"):
        return "ok", f"android 카탈로그 스킬 {cat['count']}개 (/ext list android)"
    return "missing", ".agent/android 미러 없음"


def c_protobuf(ctx):
    if _run([sys.executable, "-c", "import google.protobuf"])[0] == 0:
        return "ok", "protobuf"
    return "warn", "Python protobuf 없음 — r8-analyzer(Export Project 한 Gradle 프로젝트)에만 필요"


def c_gpu(ctx):
    if not shutil.which("nvidia-smi"):
        return "missing", "nvidia-smi 없음 — NVIDIA GPU · 드라이버 필요 (로컬 생성)"
    code, out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    if code != 0 or not out.strip():
        return "missing", "nvidia-smi 실패 — 드라이버 확인"
    name, mem = [x.strip() for x in out.strip().splitlines()[0].split(",")[:2]]
    if int(float(mem)) < MIN_VRAM_MB:
        return "warn", f"{name} {mem}MB — 8GB 미만이면 큰 모델이 매우 느리다"
    return "ok", f"{name} {mem}MB"


def c_comfyui(ctx):
    if not ctx.comfyui_home:
        return "missing", "ComfyUI 포터블을 찾지 못함 (--comfyui-home 으로 지정 가능)"
    ver = None
    try:
        with open(os.path.join(ctx.comfyui_home, "ComfyUI", "comfyui_version.py"), encoding="utf-8") as f:
            ver = _ver(f.read())
    except OSError:
        pass
    if ver and ver < MIN_COMFYUI:
        return "missing", f"ComfyUI {ver} < {MIN_COMFYUI} — 오디오 · 배경 제거 코어 노드가 없다 (update/update_comfyui.bat)"
    return "ok", f"{ctx.comfyui_home} (v{ver[0]}.{ver[1]})" if ver else ctx.comfyui_home


def _model_path(ctx, key):
    m = MODELS[key]
    return os.path.join(ctx.comfyui_home, "ComfyUI", "models", m["dir"], m["file"]) if ctx.comfyui_home else None


def c_model(key):
    def check(ctx):
        if key not in ctx.needed_models():
            return "skip", "현재 설정에서 쓰지 않음"
        p = _model_path(ctx, key)
        if not p:
            return "missing", "ComfyUI 위치를 먼저 정해야 함"
        if not os.path.isfile(p):
            return "missing", f"없음: {p}"
        size = os.path.getsize(p)
        if size != MODELS[key]["size"]:
            return "missing", f"크기 불일치 {size} ≠ {MODELS[key]['size']} (받다 끊긴 파일?)"
        return "ok", p
    return check


def i_model(key):
    def install(ctx, dry):
        m = MODELS[key]
        p = _model_path(ctx, key)
        if not p:
            raise RuntimeError("ComfyUI 위치 미정 — --comfyui-home")
        url = f"https://huggingface.co/{m['repo']}/resolve/main/{m['path']}"
        if dry:
            return f"{url} → {p}"
        download(url, p, m["size"], m["sha256"])
        return f"{m['file']} 받음 · SHA256 확인"
    return install


def _has_av(python):
    return bool(python) and _run([python, "-c", "import av, numpy"], timeout=60)[0] == 0


def c_audio_python(ctx):
    exe = ctx.cfg.get("audio", {}).get("python")
    if exe and _has_av(exe):
        return "ok", exe
    if exe:
        return "missing", f"audio.python={exe} 에 PyAV · numpy 없음"
    return "missing", "audio.python 미설정 — 오디오 후처리(FLAC→WAV · 루프 · 정규화)에 필요"


def i_audio_python(ctx, dry):
    py = ctx.comfy_python()
    if not _has_av(py):
        raise RuntimeError("ComfyUI python_embeded 에 PyAV · numpy 가 없음 — PyAV · numpy 있는 Python 을 직접 지정")
    if not dry:
        _merge_local(ctx, {"audio": {"python": py.replace("\\", "/")}})
    return f"audio.python = {py}"


def c_local_config(ctx):
    if ctx.local.get("provider") == "comfyui":
        return "ok", "provider=comfyui"
    return "missing", f"artgen.config.local.json provider={ctx.local.get('provider', '(없음 → mock)')}"


def i_local_config(ctx, dry):
    patch = {"provider": "comfyui"}
    if ctx.comfyui_home:
        patch["providers"] = {"comfyui": {"home": ctx.comfyui_home.replace("\\", "/")}}
    if ctx.library_dir_overridden:
        patch.setdefault("providers", {})["library"] = {"dir": ctx.library_dir.replace("\\", "/")}
    if not dry:
        _merge_local(ctx, patch)
    return f"artgen.config.local.json ← {json.dumps(patch, ensure_ascii=False)}"


def _merge_local(ctx, patch):
    def merge(a, b):
        for k, v in b.items():
            a[k] = merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
        return a
    ctx.local = merge(ctx.local, patch)
    os.makedirs(os.path.dirname(ctx.local_path), exist_ok=True)
    with open(ctx.local_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ctx.local, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ctx.cfg = load_config(os.path.dirname(ctx.local_path))


def c_library(ctx):
    index = _read_json(os.path.join(ctx.library_dir, soundlib.INDEX_FILE))
    if not index or not index.get("entries"):
        return "missing", f"효과음 라이브러리 없음: {ctx.library_dir}"
    missing = [p for p in KENNEY_PACKS if f"kenney-{p}" not in index.get("packs", {})]
    detail = f"팩 {len(index['packs'])}개 · 소리 {len(index['entries'])}개"
    return ("ok", detail) if not missing else ("warn", f"{detail} — 기본 팩 중 없음: {', '.join(missing)}")


def i_library(ctx, dry):
    if dry:
        return f"Kenney CC0 팩 {len(KENNEY_PACKS)}개 → {ctx.library_dir}"
    tmp = os.path.join(ctx.library_dir, "_download")
    os.makedirs(tmp, exist_ok=True)
    added = []
    for pack in KENNEY_PACKS:
        name = f"kenney-{pack}"
        if os.path.isdir(os.path.join(ctx.library_dir, name)):
            continue
        link = kenney_link(pack)
        zpath = os.path.join(tmp, f"{name}.zip")
        download(link, zpath)
        soundlib.add_pack(ctx.library_dir, zpath, name, "CC0-1.0", f"https://kenney.nl/assets/{pack}")
        os.remove(zpath)
        added.append(name)
    shutil.rmtree(tmp, ignore_errors=True)
    py = ctx.cfg.get("audio", {}).get("python") or ctx.comfy_python()
    index = soundlib.build_index(ctx.library_dir, py if _has_av(py) else None)
    return f"팩 {len(added)}개 추가 · 색인 {len(index['entries'])}개"


def kenney_link(pack):
    """kenney.nl 의 '기부 없이 계속' 과 같은 경로 — 서명된 일회용 다운로드 URL 을 받는다."""
    hid = f"assets/{pack}".encode().hex()
    req = urllib.request.Request(f"https://kenney.nl/download-link/{hid}",
                                 headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://kenney.nl/assets/{pack}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        url = json.loads(r.read().decode("utf-8")).get("url")
    if not url:
        raise RuntimeError(f"Kenney 다운로드 링크를 받지 못함: {pack}")
    return url


def c_comfy_server(ctx):
    url = ctx.cfg.get("providers", {}).get("comfyui", {}).get("url", "http://127.0.0.1:8188")
    try:
        urllib.request.urlopen(url.rstrip("/") + "/system_stats", timeout=2).close()
        return "ok", f"{url} 응답"
    except OSError:
        return "warn", f"{url} 응답 없음 — 생성할 때 run_nvidia_gpu.bat 실행 (설치 단계에서는 꺼져 있어도 된다)"


def c_decide(text):
    return lambda ctx: ("decide", text)


def c_pytest(ctx):
    if _run([sys.executable, "-c", "import pytest"])[0] == 0:
        return "ok", "pytest"
    return ("ok", "uvx pytest 로 실행 가능") if shutil.which("uvx") else ("warn", "pytest 없음 — 도구 테스트에만 필요")


def c_graphify(ctx):
    exe = shutil.which("graphify")
    if not exe:
        return "missing", "graphify 없음 — 기존 C# 코드 구조 파악 · 영향 범위 질의용 (선택)"
    backend = os.environ.get("GRAPHIFY_BACKEND")
    if backend != "none":
        # 코드만 그래프로 만들 때도 문서 · 이미지가 섞이면 환경의 API 키나 claude -p 로 외부 모델을 부른다
        return "warn", f"{exe} — GRAPHIFY_BACKEND={backend or '미설정'}: 실행할 때 GRAPHIFY_BACKEND=none 으로 (외부 모델 · 사용량 방지)"
    return "ok", f"{exe} (GRAPHIFY_BACKEND=none)"


def i_graphify(ctx, dry):
    if not shutil.which("uv"):
        raise RuntimeError("uv 없음 — 먼저 uv 설치")
    if dry:
        return "uv tool install graphifyy"
    code, out = _run(["uv", "tool", "install", "graphifyy"], timeout=900)
    if code != 0:
        raise RuntimeError(out[-400:])
    return "graphify 설치 (uv tool) — Claude 상시 훅 · git 훅은 설치하지 않는다"


ITEMS = [
    Item("git", "기본", set(), "Git 2.25+ (+ core.autocrlf=input)", c_git, _winget("Git.Git"),
         "https://git-scm.com/download/win · 설치 후 git config --global core.autocrlf input"),
    Item("python", "기본", set(), "Python 3.8+", c_python, None, "https://www.python.org/downloads/"),
    Item("claude", "기본", set(), "Claude Code CLI", c_which("claude", "claude"), None,
         "PowerShell: irm https://claude.ai/install.ps1 | iex"),
    Item("uv", "기본", {"dev"}, "uv / uvx (Unity MCP 서버 실행)", c_which("uvx", "uvx"), _winget("astral-sh.uv"),
         "PowerShell: irm https://astral.sh/uv/install.ps1 | iex"),
    Item("vscode", "기본", set(), "(선택) VS Code — studio launch 의 vscode 창", c_which("code", "code"),
         _winget("Microsoft.VisualStudioCode"), "https://code.visualstudio.com/"),
    Item("pytest", "기본", set(), "(선택) pytest — 도구 테스트", c_pytest, None, "pip install pytest"),
    Item("graphify", "기본", {"dev"}, "(선택) graphify — 코드 지식 그래프 (C# 의존 · 영향 범위 질의)", c_graphify,
         i_graphify, "uv tool install graphifyy · 실행은 GRAPHIFY_BACKEND=none (코드만, 외부 모델 없음)",
         license="Apache-2.0 / MIT"),
    Item("unity-editor", "Unity", {"dev"}, "프로젝트 버전과 같은 Unity 에디터", c_unity_editor, None, m_unity_editor),
    Item("unity-mcp-pkg", "Unity", {"dev"}, "MCPForUnity 패키지 (Packages/manifest.json)", c_unity_mcp_pkg,
         i_unity_mcp_pkg, "scripts/install.ps1 를 다시 실행"),
    Item("mcp-json", "Unity", {"dev"}, ".mcp.json unity-mcp 서버", c_mcp_json, None,
         "템플릿의 scripts/install.ps1 -Target <프로젝트> (또는 claude mcp add)"),
    Item("android-module", "Android", {"dev"}, "Unity Android Build Support 모듈", android_only(c_android_module), None,
         m_android_module),
    Item("adb", "Android", {"dev"}, "adb (Android 플랫폼 도구)", android_only(c_adb), None,
         "Unity Android 모듈의 SDK/platform-tools 에 함께 설치됨 — 모듈을 먼저 설치"),
    Item("android-catalog", "Android", {"dev"}, "android 스킬 카탈로그 (/ext — 기기 프로파일링 · Play 정책 · ANR · R8)",
         android_only(c_android_catalog), None,
         "템플릿의 studio.py upgrade, 또는 python <템플릿>/scripts/sync-catalog.py android --fetch --root <프로젝트>"),
    Item("adb-device", "Android", {"dev"}, "(선택) 연결된 Android 기기", android_only(c_adb_device), None,
         "기기의 개발자 옵션 → USB 디버깅"),
    Item("protobuf", "Android", {"dev"}, "(선택) Python protobuf — r8-analyzer", android_only(c_protobuf), None,
         "pip install protobuf"),
    Item("gpu", "생성", {"art"}, "NVIDIA GPU · 드라이버 (VRAM 8GB+)", c_gpu, None, "https://www.nvidia.com/drivers"),
    Item("comfyui", "생성", {"art"}, "ComfyUI 포터블 0.42+", c_comfyui, None, COMFYUI_RELEASES),
    *[Item(f"model:{k}", "생성", {"art"}, f"모델 {MODELS[k]['file']}", c_model(k), i_model(k),
           f"https://huggingface.co/{MODELS[k]['repo']}", MODELS[k]["size"], MODELS[k]["license"]) for k in MODELS],
    Item("audio-python", "생성", {"art"}, "오디오 후처리 Python (PyAV · numpy)", c_audio_python, i_audio_python,
         "PyAV · numpy 가 있는 Python 경로를 artgen.config.local.json audio.python 에"),
    Item("sound-library", "생성", {"art"}, "효과음 라이브러리 (Kenney CC0 팩)", c_library, i_library,
         "python .agent/tools/artgen/artgen.py library add <zip> --name .. --license ..", 60_000_000, "CC0-1.0"),
    Item("local-config", "생성", {"art"}, "artgen 로컬 설정 (provider=comfyui)", c_local_config, i_local_config, ""),
    Item("comfyui-server", "생성", {"art"}, "ComfyUI 서버 실행 중", c_comfy_server, None, "run_nvidia_gpu.bat"),
    Item("stable-audio", "사용자 결정", {"art"}, "(선택) Stable Audio 효과음 생성 모델",
         c_decide("Stability AI 라이선스(매출 기준 상업 제한) — 효과음은 라이브러리로 대신함. 쓰려면 사용자가 조건 확인 후 직접 받기"),
         None, "https://huggingface.co/Comfy-Org/stable-audio-3"),
    Item("gamedesign", "사용자 결정", {"planning"}, "(선택) gamedesign 감사 카탈로그",
         c_decide("PolyForm Noncommercial — 회사 사용이면 상업 라이선스 필요. /ext 의 설치 돕기로 사용자가 조건 선택"),
         None, "python scripts/sync-catalog.py gamedesign --fetch --accept-license <noncommercial|commercial>"),
]
REQUIRED_SKIP = {"vscode", "comfyui-server", "stable-audio", "gamedesign", "pytest", "adb-device", "protobuf",
                 "graphify"}
# 선택 항목은 missing 이어도 실패로 보지 않고, install 을 항목 없이 실행할 때도 설치하지 않는다 (이름을 줘야 설치)  # missing 이어도 실패로 보지 않음


# ---------------------------------------------------------------- 다운로드
def download(url, dest, size=None, sha256=None, retries=8):
    """이어받기 · 재시도 · 크기 · SHA256 검증. 다 받기 전에는 .part 로 둔다."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part"
    for attempt in range(1, retries + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if size and have >= size:
            break
        req = urllib.request.Request(url, headers={"User-Agent": "artgen-prereq", **({"Range": f"bytes={have}-"} if have else {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if have and r.status != 206:  # 서버가 이어받기를 무시하면 처음부터
                    have = 0
                total = size or (have + int(r.headers.get("Content-Length") or 0))
                with open(part, "ab" if have else "wb") as f:
                    last = time.monotonic()
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        have += len(chunk)
                        if time.monotonic() - last > 15 and total:
                            print(f"    {os.path.basename(dest)} {have * 100 // total}% ({_human(have)}/{_human(total)})", flush=True)
                            last = time.monotonic()
            if not size or have >= size:
                break
        except (urllib.error.URLError, OSError, TimeoutError) as e:  # TLS 끊김(보안 프로그램 등)은 이어받기로 넘긴다
            print(f"    재시도 {attempt}/{retries} — {e}", flush=True)
            time.sleep(min(30, 3 * attempt))
    else:
        raise RuntimeError(f"다운로드 실패 {retries}회: {url}")
    got = os.path.getsize(part)
    if size and got != size:
        raise RuntimeError(f"크기 불일치 {got} ≠ {size}: {part} (지우고 다시)")
    if sha256:
        h = hashlib.sha256()
        with open(part, "rb") as f:
            for block in iter(lambda: f.read(1 << 22), b""):
                h.update(block)
        if h.hexdigest() != sha256:
            raise RuntimeError(f"SHA256 불일치: {part} — 손상 파일이라 쓰지 않는다 (지우고 다시)")
    os.replace(part, dest)


# ---------------------------------------------------------------- CLI
ICON = {"ok": "✔", "missing": "✖", "warn": "!", "decide": "?", "skip": "·"}


def run_checks(ctx):
    return [it.check(ctx) for it in ITEMS if it.applies(ctx)]


def cmd_check(ctx, args):
    rows = run_checks(ctx)
    fails = [r for r in rows if r["status"] == "missing" and r["id"] not in REQUIRED_SKIP]
    if args.json:
        print(json.dumps({"root": ctx.root, "roles": sorted(ctx.roles), "items": rows, "ok": not fails},
                         ensure_ascii=False, indent=1))
        return 1 if fails else 0
    group = None
    for r in rows:
        if r["group"] != group:
            group = r["group"]
            print(f"\n[{group}]")
        flag = "" if not r["auto"] else (f" (선택 — 설치: prereq.py install {r['id']})" if r["id"] in REQUIRED_SKIP
                                         else " (자동 설치 가능)")
        print(f"  {ICON[r['status']]} {r['title']}{flag}\n      {r['detail']}")
        if r["status"] in ("missing", "warn") and not r["auto"] and r["manual"]:
            print(f"      → {r['manual']}")
    autos = [r for r in rows if r["auto"] and r["id"] not in REQUIRED_SKIP]
    print(f"\n필수 누락 {len(fails)}개 · 자동 설치 가능 {len(autos)}개"
          + (f" ({_human(sum(r['size'] for r in autos))} 이상)" if any(r['size'] for r in autos) else ""))
    if autos:
        print("  → python .agent/tools/setup/prereq.py install")
    return 1 if fails else 0


def cmd_install(ctx, args):
    rows = {r["id"]: r for r in run_checks(ctx)}
    by_id = {it.id: it for it in ITEMS}
    wanted = args.items or [i for i, r in rows.items() if r["auto"] and i not in REQUIRED_SKIP]
    order = [it.id for it in ITEMS]  # 설정 → 경로가 필요한 항목 순서를 ITEMS 순서로 보장
    plan = []
    for i in sorted(wanted, key=lambda x: order.index(x) if x in order else 999):
        if i not in by_id:
            print(f"알 수 없는 항목: {i}")
            return 2
        r = rows.get(i)
        if r and r["status"] == "decide":
            print(f"  ? {i}: 사용자 결정 항목이라 자동 설치하지 않음 — {r['detail']}")
            continue
        if by_id[i]._install is None:
            print(f"  - {i}: 자동 설치 불가 — {by_id[i].manual}")
            continue
        if r and r["status"] in ("ok", "skip"):
            continue
        plan.append(by_id[i])
    if not plan:
        print("설치할 항목 없음.")
        return 0
    print("설치 계획:")
    for it in plan:
        extra = " · ".join(x for x in (_human(it.size) if it.size else "", it.license) if x)
        print(f"  - {it.id}: {it.title}" + (f" ({extra})" if extra else ""))
    if not args.yes and not args.dry_run:
        if input("진행할까요? [y/N] ").strip().lower() != "y":
            print("취소")
            return 1
    failed = 0
    for it in plan:
        try:
            print(f"  ▶ {it.id}: {it._install(ctx, args.dry_run)}", flush=True)
        except Exception as e:  # 한 항목이 실패해도 나머지는 진행 — 마지막에 요약
            failed += 1
            print(f"  ✖ {it.id}: {e}", flush=True)
    print(f"\n완료 — 실패 {failed}개. 다시 점검: python .agent/tools/setup/prereq.py check")
    return 1 if failed else 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="prereq", description="자동화 사전 설치 점검 · 설치")
    ap.add_argument("--root", default=os.getcwd(), help="Unity 프로젝트 루트 (기본: 현재 디렉터리)")
    ap.add_argument("--roles", default=",".join(ROLES), help="이 PC 에서 맡을 역할 (기본 planning,art,dev)")
    ap.add_argument("--comfyui-home", help="ComfyUI 포터블 폴더")
    ap.add_argument("--library-dir", help="효과음 라이브러리 폴더 (여러 프로젝트가 공유하려면 절대경로)")
    ap.add_argument("--platforms", help="대상 플랫폼 (예: android,ios). 생략하면 technical-preferences.md 의 Target Platforms")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("install")
    p.add_argument("items", nargs="*", help="항목 id (생략하면 자동 설치 가능한 전부)")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    bad = [r for r in roles if r not in ROLES]
    if bad:
        ap.error(f"알 수 없는 역할: {bad}")
    platforms = [x.strip() for x in args.platforms.split(",") if x.strip()] if args.platforms is not None else None
    ctx = Ctx(args.root, roles, args.comfyui_home, args.library_dir, platforms)
    return cmd_check(ctx, args) if args.cmd == "check" else cmd_install(ctx, args)


if __name__ == "__main__":
    sys.exit(main())
