"""사전 설치 점검 · 설치 — 자동화(스튜디오 모드 · artgen 그래픽/사운드 · 엔진 도구)를 돌리기 전에 필요한 것.
엔진 항목은 프로젝트 엔진(project.yaml engine.name → 표지 파일)에 맞는 것만 점검하고, 나머지는 이유를 붙여 skip 한다.

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
from artgen_lib.store import detect_engine  # noqa: E402

ROLES = ("planning", "art", "dev")
MIN_GIT = (2, 25)
MIN_COMFYUI = (0, 42)
MIN_VRAM_MB = 8000
COMFYUI_CANDIDATES = (r"D:\AI\ComfyUI_windows_portable", r"C:\AI\ComfyUI_windows_portable", r"C:\ComfyUI_windows_portable")
COMFYUI_RELEASES = "https://github.com/comfyanonymous/ComfyUI/releases (ComfyUI_windows_portable_nvidia.7z)"
# Epic Games Launcher 기본 설치 위치 — 소스 빌드 엔진은 project.yaml engine.path 로 지정
UNREAL_INSTALL_DIRS = (r"C:\Program Files\Epic Games", r"D:\Program Files\Epic Games", r"D:\Epic Games")
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
        # 외부 도구 출력 — 코드 페이지가 달라도 죽지 않게 (영어 Windows cp1252 · 한국어 cp949)
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def _is_portable(home):
    return bool(home) and os.path.isfile(os.path.join(home, "ComfyUI", "main.py"))


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
        self.engine = detect_engine(self.root)  # unity · godot · unreal · None
        self.local_path = os.path.join(self.root, ".agent", "tools", "artgen", "artgen.config.local.json")
        self.local = _read_json(self.local_path, {}) or {}
        self.cfg = load_config(os.path.join(self.root, ".agent", "tools", "artgen")) \
            if os.path.isdir(os.path.join(self.root, ".agent", "tools", "artgen")) else load_config()
        # 설정된 home 이 이 PC 에 없으면(다른 PC 에서 옮겨 온 설정) 옛 경로로 기록하고 후보 위치를 대신 쓴다
        configured = self.cfg.get("providers", {}).get("comfyui", {}).get("home")
        candidate = next((c for c in COMFYUI_CANDIDATES if _is_portable(c)), None)
        self.comfyui_stale = configured if configured and not comfyui_home and not _is_portable(configured) else None
        self.comfyui_home = comfyui_home or (configured if configured and not self.comfyui_stale else None) or candidate
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


def engine_only(engine, check):
    """그 엔진 프로젝트에서만 점검한다. 아니면 무엇 때문에 건너뛰는지 밝힌다 (조용한 skip 금지)."""
    def wrapped(ctx):
        if ctx.engine != engine:
            why = f"{ctx.engine} 프로젝트" if ctx.engine else "엔진 미설정 (project.yaml engine.name · 엔진 표지 파일 없음)"
            return "skip", f"{engine.capitalize()} 전용 — {why}"
        return check(ctx)
    return wrapped


def _engine_path(ctx):
    """project.yaml engine.path — Godot 은 실행 파일, Unreal 은 엔진 루트 (/setup-engine 이 쓴다). 없으면 None."""
    try:
        with open(os.path.join(ctx.root, "project.yaml"), encoding="utf-8") as f:
            in_engine = False
            for line in f:
                if line.startswith("engine:"):
                    in_engine = True
                    continue
                if in_engine and line.strip() and not line[:1].isspace() and not line.startswith("#"):
                    break
                s = line.strip()
                if in_engine and s.startswith("path:"):
                    v = s[5:].split(" #")[0].strip().strip("\"'")
                    return v or None
    except OSError:
        pass
    return None


def _project_godot_version(ctx):
    try:
        with open(os.path.join(ctx.root, "project.godot"), encoding="utf-8") as f:
            m = re.search(r'config/features=PackedStringArray\("(\d+\.\d+)', f.read())
    except OSError:
        return None
    return m.group(1) if m else None


def c_godot_editor(ctx):
    want = _project_godot_version(ctx)
    configured = _engine_path(ctx)
    exe = configured if configured and os.path.isfile(configured) else         next((shutil.which(n) for n in ("godot", "godot4", "Godot") if shutil.which(n)), None)
    if not exe:
        return "missing", f"Godot 실행 파일을 PATH 에서 찾지 못함 (프로젝트 {want or '버전 미상'})"
    code, out = _run([exe, "--version"])
    have = re.search(r"(\d+\.\d+)", out or "")
    if code != 0 or not have:
        return "warn", f"{exe} --version 실패: {(out or '').strip()[:120]}"
    if want and have.group(1) != want:
        return "missing", f"프로젝트는 Godot {want}, PATH 의 godot 은 {have.group(1)} ({exe})"
    return "ok", f"Godot {out.strip().split()[0]} ({exe})"


def c_gdunit4(ctx):
    p = os.path.join(ctx.root, "addons", "gdUnit4", "bin", "GdUnitCmdTool.gd")
    return ("ok", "addons/gdUnit4") if os.path.isfile(p) else         ("missing", "gdUnit4 없음 — Godot 테스트 실행(.claude/scripts/test-run.sh godot)이 돌지 않는다")


# ---------------------------------------------------------------- Godot MCP (선택 — .NET 판 프로젝트만)
# IvanMurzak/Godot-MCP (Apache-2.0). 애드온 · godot-cli 버전을 함께 고정한다 — 2026-11-04 확인 (v0.34.0, 2026-10-31).
# 요구: Godot 4.3+ .NET(mono) 판 · .NET 8 SDK. GDScript 전용 Godot 은 애드온을 컴파일하지 못한다.
# 템플릿 기본은 로컬 서버(Custom 모드) — 상류 기본값인 ai-game.dev 클라우드는 계정 로그인 · 외부 경유라 쓰지 않는다.
GODOT_MCP_VERSION = "0.34.0"
GODOT_MCP_GUIDE = ".claude/docs/mcp-godot-guide.md"


def _godot_csproj(ctx):
    """루트의 Godot .NET 프로젝트 파일 (Godot.NET.Sdk). 없으면 None — GDScript 전용 프로젝트."""
    try:
        names = sorted(n for n in os.listdir(ctx.root) if n.endswith(".csproj"))
    except OSError:
        return None
    for n in names:
        try:
            with open(os.path.join(ctx.root, n), encoding="utf-8", errors="replace") as f:
                if "Godot.NET.Sdk" in f.read():
                    return n
        except OSError:
            pass
    return None


def godot_dotnet_only(check):
    """Godot .NET 프로젝트에서만. 아니면 왜 하지 않는지 밝힌다 (조용한 skip 금지)."""
    def wrapped(ctx):
        if ctx.engine != "godot":
            why = f"{ctx.engine} 프로젝트" if ctx.engine else "엔진 미설정"
            return "skip", f"Godot 전용 — {why}"
        if not _godot_csproj(ctx):
            return "skip", "GDScript 전용 프로젝트 (Godot.NET.Sdk .csproj 없음) — Godot MCP 는 .NET(C#) 판만 지원해 하지 않음"
        return check(ctx)
    return wrapped


def c_dotnet_sdk(ctx):
    exe = shutil.which("dotnet")
    if not exe:
        return "missing", ".NET SDK 없음 — Godot MCP 애드온 빌드에 .NET 8 이상 필요"
    code, out = _run([exe, "--list-sdks"])
    majors = [int(m) for m in re.findall(r"^(\d+)\.\d+\.\d+", out or "", re.M)]
    if code != 0 or not majors:
        return "missing", f"dotnet --list-sdks 에 SDK 없음 ({(out or '').strip()[:80]})"
    if max(majors) < 8:
        return "missing", f".NET SDK {max(majors)} — 8 이상 필요"
    note = " · .NET 10 은 어셈블리 리로드 때 에디터가 멈출 수 있음(상류 안내: DOTNET_ThreadPool_ThreadsToKeepAlive=-1)" \
        if 10 in majors and 8 not in majors and 9 not in majors else ""
    return "ok", f".NET SDK {', '.join(str(m) for m in sorted(set(majors)))}{note}"


def c_godot_mcp_addon(ctx):
    addon = os.path.join(ctx.root, "addons", "godot_mcp")
    if not os.path.isdir(addon):
        return "missing", f"addons/godot_mcp 없음 — Godot MCP 애드온 미설치 (안내: {GODOT_MCP_GUIDE})"
    try:
        with open(os.path.join(ctx.root, "project.godot"), encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        text = ""
    plugins = re.search(r"\[editor_plugins\][^\[]*", text)
    if not plugins or "godot_mcp" not in plugins.group(0):
        return "warn", "addons/godot_mcp 는 있으나 project.godot [editor_plugins] 에서 꺼져 있음"
    return "ok", "addons/godot_mcp (플러그인 켜짐)"


def i_godot_mcp_addon(ctx, dry):
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("Node.js(npx) 없음 — https://nodejs.org 설치 후 다시 실행")
    # 애드온 버전은 CLI 버전을 따른다 — CLI 를 고정하면 애드온도 고정된다. `install-plugin --version x` 는 0.34.0 에서
    # 전역 --version(버전 출력)에 가로채여 설치 없이 0 으로 끝난다 (2026-11-04 실측) — 쓰지 않는다
    argv = [npx, "-y", f"godot-cli@{GODOT_MCP_VERSION}", "install-plugin", "--path", ctx.root]
    if dry:
        return " ".join(argv[1:])
    code, out = _run(argv, timeout=900)
    if code != 0:
        raise RuntimeError(out[-400:])
    return (f"Godot MCP 애드온 {GODOT_MCP_VERSION} — addons/godot_mcp · .csproj NuGet 참조 · 플러그인 켜기. "
            f"다음: 에디터 독에서 Custom 모드 + Start Server, 그 뒤 MCP 등록 ({GODOT_MCP_GUIDE})")


def _godot_mcp_servers(servers):
    """Godot MCP 로 보이는 등록 — 로컬 gamedev-mcp-server 이거나 ai-game.dev / localhost 의 /mcp 주소. (이름은 도구마다 달라 주소로 본다)"""
    found = []
    for name, s in (servers or {}).items():
        if not isinstance(s, dict) or "unity" in name.lower():
            continue
        url = str(s.get("url", ""))
        cmd = " ".join([str(s.get("command", ""))] + [str(a) for a in s.get("args", [])])
        if "ai-game.dev" in url:
            found.append((name, "cloud"))
        elif "gamedev-mcp-server" in cmd or re.match(r"https?://(localhost|127\.0\.0\.1)(:\d+)?/mcp", url):
            found.append((name, "local"))
    return found


def c_godot_mcp_json(ctx):
    sources = [(".mcp.json", (_read_json(os.path.join(ctx.root, ".mcp.json"), {}) or {}).get("mcpServers"))]
    user = _read_json(os.path.join(os.path.expanduser("~"), ".claude.json"), {}) or {}
    sources.append(("Claude Code 사용자 설정", user.get("mcpServers")))
    key = ctx.root.replace("\\", "/").lower()
    for path, proj in (user.get("projects") or {}).items():
        if path.replace("\\", "/").lower() == key:
            sources.append(("Claude Code 프로젝트 로컬 설정", proj.get("mcpServers")))
    found = [(where, name, kind) for where, servers in sources for name, kind in _godot_mcp_servers(servers)]
    local = [f for f in found if f[2] == "local"]
    if local:
        return "ok", f"{local[0][0]} {local[0][1]} (로컬)"
    if found:
        return "warn", (f"{found[0][0]} {found[0][1]} 이 ai-game.dev 클라우드로 연결됨 — 템플릿 기본은 로컬 서버. "
                        f"의도한 것이면 그대로 둔다 ({GODOT_MCP_GUIDE})")
    return "missing", "Godot MCP 서버 등록 없음 (.mcp.json · ~/.claude.json)"


def _project_unreal_version(ctx):
    for n in sorted(os.listdir(ctx.root)):
        if n.endswith(".uproject"):
            data = _read_json(os.path.join(ctx.root, n), {}) or {}
            return data.get("EngineAssociation")
    return None


def c_unreal_editor(ctx):
    ver = _project_unreal_version(ctx)
    if not ver:
        ver = "?"
    root = _engine_path(ctx)
    if root:
        exe = os.path.join(root, "Engine", "Binaries", "Win64", "UnrealEditor.exe")
        if os.path.isfile(exe):
            return "ok", f"Unreal Engine (project.yaml engine.path: {exe})"
        return "missing", f"project.yaml engine.path 에 UnrealEditor.exe 없음: {exe}"
    if ver == "?":
        return "warn", ".uproject 에 EngineAssociation 없음 — 소스 빌드면 project.yaml engine.path 로 지정"
    for d in UNREAL_INSTALL_DIRS:
        exe = os.path.join(d, f"UE_{ver}", "Engine", "Binaries", "Win64", "UnrealEditor.exe")
        if os.path.isfile(exe):
            return "ok", f"Unreal Engine {ver} ({exe})"
    return "missing", (f"Unreal Engine {ver} 를 기본 위치({', '.join(UNREAL_INSTALL_DIRS)})에서 찾지 못함 — "
                       "소스 빌드 · 다른 위치면 project.yaml engine.path")


# ---------------------------------------------------------------- Unreal MCP (선택 — UE 5.8+ 엔진 플러그인 + Epic 공식 Claude Code 플러그인)
# 엔진: ModelContextProtocol(서버) + AllToolsets(도구) — UE 5.8 에서 Experimental (docs/engine-reference/unreal/PLUGINS.md).
# Claude Code 쪽: EpicGames/unreal-engine-skills-for-claude-code-plugin (MIT) — 공식 플러그인 마켓 claude-plugins-official.
# 2026-11-04 확인. 연결은 로컬(기본 127.0.0.1:8000/mcp). 안내: .claude/docs/mcp-unreal-guide.md
UE_MCP_PLUGINS = ("ModelContextProtocol", "AllToolsets")
UE_CLAUDE_PLUGIN = "unreal-engine-skills-for-claude-code@claude-plugins-official"
UE_MCP_GUIDE = ".claude/docs/mcp-unreal-guide.md"


def _uproject(ctx):
    for n in sorted(os.listdir(ctx.root)):
        if n.endswith(".uproject"):
            return os.path.join(ctx.root, n)
    return None


def _ue_version_tuple(ctx):
    m = re.match(r"^(\d+)\.(\d+)", str(_project_unreal_version(ctx) or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None  # 소스 빌드(GUID) · 없음 → None


def ue_mcp_only(check):
    """Unreal MCP 세 항목 공통 — 5.7 이하는 엔진에 MCP 서버가 없으니 '빠짐' 이 아니라 '하지 않음' 으로 밝힌다.
    버전을 모르면(소스 빌드 GUID) 막지 않고 점검하되 직접 확인하라는 메모를 붙인다."""
    def wrapped(ctx):
        ver = _ue_version_tuple(ctx)
        if ver and ver < (5, 8):
            return "skip", f"UE {ver[0]}.{ver[1]} — Unreal MCP 는 UE 5.8 부터 (MCP Server 플러그인 Experimental). 하지 않음"
        status, detail = check(ctx)
        if not ver and status != "skip":
            detail += " (엔진 버전 미상 — 소스 빌드면 5.8+ 인지 직접 확인)"
        return status, detail
    return wrapped


def c_ue_mcp_plugins(ctx):
    path = _uproject(ctx)
    data = _read_json(path, None) if path else None
    if data is None:
        return "warn", ".uproject 를 읽지 못함"
    enabled = {p.get("Name") for p in data.get("Plugins", []) or [] if isinstance(p, dict) and p.get("Enabled")}
    missing = [p for p in UE_MCP_PLUGINS if p not in enabled]
    if missing:
        return "missing", f"{os.path.basename(path)} 에서 꺼짐: {', '.join(missing)} (안내: {UE_MCP_GUIDE})"
    return "ok", f"{os.path.basename(path)} — {' · '.join(UE_MCP_PLUGINS)} 켜짐"


def i_ue_mcp_plugins(ctx, dry):
    path = _uproject(ctx)
    data = _read_json(path, None) if path else None
    if data is None:
        raise RuntimeError(".uproject 를 읽지 못함")
    ver = _ue_version_tuple(ctx)
    if ver and ver < (5, 8):
        raise RuntimeError(f"UE {ver[0]}.{ver[1]} — MCP Server 플러그인이 없는 버전 (5.8+)")
    plugins = data.setdefault("Plugins", [])
    changed = []
    for name in UE_MCP_PLUGINS:
        entry = next((p for p in plugins if isinstance(p, dict) and p.get("Name") == name), None)
        if entry is None:
            plugins.append({"Name": name, "Enabled": True})
            changed.append(f"{name} 추가")
        elif not entry.get("Enabled"):
            entry["Enabled"] = True
            changed.append(f"{name} 켬")
    if dry:
        return f"{os.path.basename(path)}: " + (", ".join(changed) or "바꿀 것 없음")
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as f:  # 에디터가 쓰는 형식(탭 들여쓰기)
            json.dump(data, f, indent="\t", ensure_ascii=False)
            f.write("\n")
    return (f"{os.path.basename(path)}: {', '.join(changed) or '바꿀 것 없음'} — 에디터를 다시 열고 "
            f"ModelContextProtocol.StartServer, 그 뒤 ModelContextProtocol.GenerateClientConfig ClaudeCode ({UE_MCP_GUIDE})")


def _ue_mcp_servers(servers):
    out = []
    for name, s in (servers or {}).items():
        if not isinstance(s, dict):
            continue
        url = str(s.get("url", ""))
        cmd = " ".join([str(s.get("command", ""))] + [str(a) for a in s.get("args", [])])
        if "unreal" in name.lower() and (re.match(r"https?://(localhost|127\.0\.0\.1)(:\d+)?/", url) or s.get("command")) \
                or "unreal_mcp_proxy" in cmd:
            out.append(name)
    return out


def c_ue_mcp_json(ctx):
    found = _ue_mcp_servers((_read_json(os.path.join(ctx.root, ".mcp.json"), {}) or {}).get("mcpServers"))
    if found:
        return "ok", f".mcp.json {found[0]}"
    user = _read_json(os.path.join(os.path.expanduser("~"), ".claude.json"), {}) or {}
    found = _ue_mcp_servers(user.get("mcpServers"))
    if found:
        return "ok", f"Claude Code 사용자 설정 {found[0]}"
    key = ctx.root.replace("\\", "/").lower()
    for path, proj in (user.get("projects") or {}).items():
        if path.replace("\\", "/").lower() == key and _ue_mcp_servers(proj.get("mcpServers")):
            return "ok", f"Claude Code 프로젝트 로컬 설정 {_ue_mcp_servers(proj['mcpServers'])[0]}"
    return "missing", "Unreal MCP 서버 등록 없음 (.mcp.json · ~/.claude.json)"


def c_ue_claude_plugin(ctx):
    files = [os.path.join(ctx.root, ".claude", "settings.json"), os.path.join(ctx.root, ".claude", "settings.local.json"),
             os.path.join(os.path.expanduser("~"), ".claude", "settings.json")]
    for f in files:
        if ((_read_json(f, {}) or {}).get("enabledPlugins") or {}).get(UE_CLAUDE_PLUGIN):
            return "ok", f"{UE_CLAUDE_PLUGIN} 켜짐 ({os.path.basename(os.path.dirname(f))}/{os.path.basename(f)})"
    return "missing", "Epic 공식 Claude Code 플러그인 꺼짐 — MCP 는 없이도 되지만 사용 규칙(스킬)과 세션 안내가 빠진다"


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


# Microsoft.Unity.Analyzers — Unity 공식 Roslyn 분석기 (MIT). 2026-10-29 Unity 6000.3.24f1 에서 UNT 경고 출력 확인
UNITY_ANALYZERS = {"version": "1.28.0", "size": 168715,
                   "sha256": "8b5fcfc94090a5d925a84c78b0091962a8accd682ef978c4753cffbc01cefb21",
                   "dll": "analyzers/dotnet/cs/Microsoft.Unity.Analyzers.dll",
                   "dest": "Assets/Analyzers/Microsoft.Unity.Analyzers.dll",
                   "guid": "b9fbeda283c554d29f25b4ebf23983c8"}  # 고정 GUID — 프로젝트마다 같아 병합 충돌이 없다
ANALYZER_META = """fileFormatVersion: 2
guid: {guid}
labels:
- RoslynAnalyzer
PluginImporter:
  externalObjects: {{}}
  serializedVersion: 2
  iconMap: {{}}
  executionOrder: {{}}
  defineConstraints: []
  isPreloaded: 0
  isOverridable: 0
  isExplicitlyReferenced: 0
  validateReferences: 1
  platformData:
  - first:
      Any:
    second:
      enabled: 0
      settings: {{}}
  - first:
      Editor: Editor
    second:
      enabled: 0
      settings:
        DefaultValueInitialized: true
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def c_unity_analyzers(ctx):
    dll = os.path.join(ctx.root, *UNITY_ANALYZERS["dest"].split("/"))
    if not os.path.isdir(os.path.join(ctx.root, "Assets")):
        return "skip", "Unity 프로젝트가 아님"
    if not os.path.isfile(dll):
        return "missing", "Unity 공식 분석기 없음 — 컴파일 때 UNT 경고(빈 메시지 · tag 비교 · GetComponent 할당 등)를 못 본다"
    try:
        with open(dll + ".meta", encoding="utf-8") as f:
            labeled = "RoslynAnalyzer" in f.read()
    except OSError:
        labeled = False
    if not labeled:
        return "missing", f"{UNITY_ANALYZERS['dest']}.meta 에 RoslynAnalyzer 라벨 없음 — 컴파일러가 분석기로 쓰지 않는다"
    if not os.path.isfile(os.path.join(ctx.root, "Assets", "Default.ruleset")):
        return "warn", "Assets/Default.ruleset 없음 — 기본 Info 규칙은 컴파일 출력에 안 보인다"
    return "ok", f"Microsoft.Unity.Analyzers ({UNITY_ANALYZERS['dest']}) · Default.ruleset"


def i_unity_analyzers(ctx, dry):
    a = UNITY_ANALYZERS
    url = f"https://api.nuget.org/v3-flatcontainer/microsoft.unity.analyzers/{a['version']}/microsoft.unity.analyzers.{a['version']}.nupkg"
    dest = os.path.join(ctx.root, *a["dest"].split("/"))
    ruleset = os.path.join(ctx.root, "Assets", "Default.ruleset")
    if dry:
        return f"{url} → {a['dest']} (+ .meta RoslynAnalyzer" + (", Default.ruleset)" if not os.path.isfile(ruleset) else ")")
    import tempfile
    import zipfile
    tmp = tempfile.mkdtemp(prefix="unity-analyzers-")
    try:
        pkg = os.path.join(tmp, "pkg.nupkg")
        download(url, pkg, a["size"], a["sha256"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zipfile.ZipFile(pkg) as z, open(dest, "wb") as out:
            out.write(z.read(a["dll"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(dest + ".meta", "w", encoding="utf-8", newline="\n") as f:
        f.write(ANALYZER_META.format(guid=a["guid"]))
    added = ""
    if not os.path.isfile(ruleset):
        shutil.copyfile(os.path.join(os.path.dirname(TOOL_DIR), "lint", "Default.ruleset"), ruleset)
        added = " · Assets/Default.ruleset"
    return f"Microsoft.Unity.Analyzers {a['version']} → {a['dest']}{added} — Unity 가 다시 컴파일하면 UNT 경고가 나온다 (dev 영역 커밋)"


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
    if ctx.comfyui_stale:
        found = (f" — 이 PC 에서 찾은 포터블: {ctx.comfyui_home} (prereq.py install local-config 가 설정을 고친다)"
                 if ctx.comfyui_home else " — prereq.py --comfyui-home <폴더> install local-config 로 이 PC 경로를 지정")
        return "missing", f"설정된 providers.comfyui.home 이 이 PC 에 없음: {ctx.comfyui_stale} (다른 PC 의 경로?){found}"
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


# 포터블에 딸린 torch 가 이 PC 의 GPU 를 실제로 쓸 수 있는지 — 폴더를 다른 PC 로 옮겼을 때의 함정(드라이버가 동봉 CUDA 보다
# 오래됨 · torch 빌드가 지원하지 않는 GPU 세대 · VC++ 재배포 패키지 없음)을 생성 전에 잡는다. nvidia-smi 로는 알 수 없다
TORCH_PROBE = "\n".join([
    "import json, torch",
    "d = {'torch': torch.__version__, 'cudaver': torch.version.cuda, 'cuda': torch.cuda.is_available(),",
    "     'arch': torch.cuda.get_arch_list(), 'cap': None, 'name': None}",
    "if d['cuda']:",
    "    d['cap'] = list(torch.cuda.get_device_capability(0)); d['name'] = torch.cuda.get_device_name(0)",
    "print(json.dumps(d))",
])
VC_REDIST = "https://aka.ms/vc14/vc_redist.x64.exe"


def c_comfyui_torch(ctx):
    py = ctx.comfy_python()
    if not py:
        return "skip", "ComfyUI 포터블(python_embeded)이 없어 확인하지 않음 — 위 ComfyUI 항목부터"
    code, out = _run([py, "-s", "-c", TORCH_PROBE], timeout=180)
    line = next((ln for ln in reversed(out.splitlines()) if ln.strip().startswith("{")), None)
    if code != 0 or line is None:
        if "c10.dll" in out or "WinError 126" in out:
            return "missing", f"torch 를 불러오지 못함 (c10.dll) — VC++ 재배포 패키지 설치: {VC_REDIST}"
        return "missing", f"torch 실행 실패: {out.strip()[-300:] or '출력 없음'}"
    d = json.loads(line)
    ver = f"torch {d['torch']} (CUDA {d['cudaver']})"
    if not d["cuda"]:
        return "missing", (f"{ver} 가 GPU 를 쓰지 못함 — NVIDIA 드라이버가 CUDA {d['cudaver']} 보다 오래됐거나 GPU 가 없다. "
                           "드라이버를 최신으로 (https://www.nvidia.com/drivers)")
    sm = f"sm_{d['cap'][0]}{d['cap'][1]}"
    built = sorted(int(a[3:]) for a in d.get("arch") or [] if a.startswith("sm_") and a[3:].isdigit())
    if built and d["cap"][0] * 10 + d["cap"][1] < built[0]:
        return "missing", (f"{d['name']} ({sm}) 는 {ver} 빌드가 지원하지 않는 GPU 세대 (최소 sm_{built[0]}) — 더 새 GPU 가 "
                           "필요하거나 이 GPU 를 지원하는 이전 CUDA 판 ComfyUI 포터블을 쓴다")
    return "ok", f"{ver} · {d['name']} ({sm})"


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
    if exe and not os.path.isfile(exe if os.path.isabs(exe) else os.path.join(ctx.root, exe)):
        return "missing", (f"audio.python 경로 없음: {exe} (다른 PC 의 경로?) — prereq.py install audio-python 이 "
                           "이 PC 의 ComfyUI python_embeded 로 다시 지정한다")
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
    if ctx.local.get("provider") == "comfyui" and ctx.comfyui_stale:
        return "missing", f"provider=comfyui 이지만 home 이 이 PC 에 없는 경로: {ctx.comfyui_stale}"
    if ctx.local.get("provider") == "comfyui":
        return "ok", "provider=comfyui"
    return "missing", f"artgen.config.local.json provider={ctx.local.get('provider', '(없음 → mock)')}"


def i_local_config(ctx, dry):
    if ctx.comfyui_stale and not ctx.comfyui_home:
        raise RuntimeError("이 PC 에서 ComfyUI 포터블을 찾지 못함 — prereq.py --comfyui-home <폴더> install local-config")
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


# pixelfx — 코드 픽셀아트 VFX (MIT). 2026-11-10 커밋 044e12a 를 Node 22.14 로 실측: 시트 렌더 · 같은 시드 같은 바이트
PIXELFX = {"commit": "044e12a45dc9cc312cec50ee606dfc98afe5adc2", "size": 12785192,
           "sha256": "f425fc217b1c04a84a6414eba6984f6d4805451e440e1906e3cfe32cc8d61bd2",
           # 렌더 · 검사에 필요한 것만 푼다. gallery/ 의 폰트는 MIT 밖(NOTICE.md)이라 받지 않는다
           "keep": ("src", "tools", "docs", "LICENSE", "NOTICE.md", "README.md", "package.json")}
MIN_NODE = (18, 0)


def _pixelfx_dir(ctx):
    d = ctx.cfg.get("providers", {}).get("pixelfx", {}).get("dir", "art-source/pixelfx")
    return os.path.normpath(d if os.path.isabs(d) else os.path.join(ctx.root, d))


def _node_ver(ctx):
    node = ctx.cfg.get("providers", {}).get("pixelfx", {}).get("node", "node")
    code, out = _run([node, "--version"])
    m = re.match(r"v(\d+)\.(\d+)", out.strip()) if code == 0 else None
    return (int(m.group(1)), int(m.group(2))) if m else None


def c_pixelfx(ctx):
    root = _pixelfx_dir(ctx)
    if not os.path.isfile(os.path.join(root, "tools", "render.mjs")):
        return "missing", f"pixelfx 없음: {root} — 픽셀아트 VFX 시트(provider pixelfx)를 못 굽는다"
    ver = _node_ver(ctx)
    if ver is None or ver < MIN_NODE:
        have = f"Node {ver[0]}.{ver[1]}" if ver else "Node 없음"
        return "warn", f"{have} — pixelfx 는 Node {MIN_NODE[0]}+ 필요 (winget install OpenJS.NodeJS.LTS)"
    try:
        with open(os.path.join(root, ".pixelfx-commit"), encoding="utf-8") as f:
            commit = f.read().strip()
    except OSError:
        commit = ""
    if commit != PIXELFX["commit"]:
        return "warn", (f"고정 커밋 {PIXELFX['commit'][:7]} 이 아님 ({commit[:7] or '직접 받은 폴더'}) — 결과가 실측과 다를 수 "
                        f"있다. 폴더를 지우고 prereq.py install pixelfx")
    return "ok", f"{root} · 커밋 {commit[:7]} · Node {ver[0]}.{ver[1]}"


def i_pixelfx(ctx, dry):
    p = PIXELFX
    url = f"https://codeload.github.com/patch-gg/pixelfx/zip/{p['commit']}"
    dest = _pixelfx_dir(ctx)
    if dry:
        return f"{url} → {dest} ({', '.join(p['keep'])})"
    if os.path.exists(dest) and os.listdir(dest):
        raise RuntimeError(f"{dest} 가 비어 있지 않음 — 확인 후 지우고 다시")
    import tempfile
    import zipfile
    tmp = tempfile.mkdtemp(prefix="pixelfx-")
    try:
        zpath = os.path.join(tmp, "pixelfx.zip")
        download(url, zpath, p["size"], p["sha256"])
        staging = dest + ".part"
        shutil.rmtree(staging, ignore_errors=True)
        prefix = f"pixelfx-{p['commit']}/"
        with zipfile.ZipFile(zpath) as z:
            for info in z.infolist():
                rel = info.filename[len(prefix):] if info.filename.startswith(prefix) else ""
                parts = rel.split("/")
                if not rel or parts[0] not in p["keep"] or ".." in parts or rel.startswith("/") or ":" in rel:
                    continue
                target = os.path.join(staging, *[x for x in parts if x])
                if info.is_dir():
                    os.makedirs(target, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        with open(os.path.join(staging, ".pixelfx-commit"), "w", encoding="utf-8", newline="\n") as f:
            f.write(p["commit"] + "\n")
        if os.path.isdir(dest):
            os.rmdir(dest)  # 빈 폴더만 (위에서 확인)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(staging, dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    note = "" if (_node_ver(ctx) or (0, 0)) >= MIN_NODE else f" — Node {MIN_NODE[0]}+ 도 필요 (winget install OpenJS.NodeJS.LTS)"
    return f"pixelfx {p['commit'][:7]} → {dest}{note}"


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
    Item("uv", "기본", {"dev"}, "uv / uvx (Unity MCP 서버 · 도구 실행)", c_which("uvx", "uvx"), _winget("astral-sh.uv"),
         "PowerShell: irm https://astral.sh/uv/install.ps1 | iex"),
    Item("vscode", "기본", set(), "(선택) VS Code — studio launch 의 vscode 창", c_which("code", "code"),
         _winget("Microsoft.VisualStudioCode"), "https://code.visualstudio.com/"),
    Item("pytest", "기본", set(), "(선택) pytest — 도구 테스트", c_pytest, None, "pip install pytest"),
    Item("graphify", "기본", {"dev"}, "(선택) graphify — 코드 지식 그래프 (C# 의존 · 영향 범위 질의)", c_graphify,
         i_graphify, "uv tool install graphifyy · 실행은 GRAPHIFY_BACKEND=none (코드만, 외부 모델 없음)",
         license="Apache-2.0 / MIT"),
    Item("unity-editor", "Unity", {"dev"}, "프로젝트 버전과 같은 Unity 에디터", engine_only("unity", c_unity_editor),
         None, m_unity_editor),
    Item("unity-mcp-pkg", "Unity", {"dev"}, "MCPForUnity 패키지 (Packages/manifest.json)",
         engine_only("unity", c_unity_mcp_pkg), i_unity_mcp_pkg, "scripts/install.ps1 를 다시 실행"),
    Item("unity-analyzers", "Unity", {"dev"}, "Unity 공식 C# 분석기 (Microsoft.Unity.Analyzers · Default.ruleset)",
         engine_only("unity", c_unity_analyzers), i_unity_analyzers, "prereq.py install unity-analyzers",
         UNITY_ANALYZERS["size"], "MIT"),
    Item("mcp-json", "Unity", {"dev"}, ".mcp.json unity-mcp 서버", engine_only("unity", c_mcp_json), None,
         "템플릿의 scripts/install.ps1 -Target <프로젝트> (또는 claude mcp add)"),
    Item("godot-editor", "Godot", {"dev"}, "프로젝트 버전과 같은 Godot 실행 파일 (PATH)", engine_only("godot", c_godot_editor),
         None, "https://godotengine.org/download — 실행 파일을 PATH 에 두거나 project.yaml engine.path"),
    Item("gdunit4", "Godot", {"dev"}, "gdUnit4 테스트 프레임워크 (addons/gdUnit4)", engine_only("godot", c_gdunit4), None,
         "에디터 AssetLib 에서 gdUnit4 설치 후 플러그인 활성화 (/test-setup)"),
    Item("dotnet-sdk", "Godot", {"dev"}, "(선택) .NET 8+ SDK — Godot MCP (.NET 판 프로젝트만)",
         godot_dotnet_only(c_dotnet_sdk), None, "https://dotnet.microsoft.com/download (.NET 8 SDK)"),
    Item("godot-mcp-addon", "Godot", {"dev"}, f"(선택) Godot MCP 애드온 {GODOT_MCP_VERSION} (addons/godot_mcp)",
         godot_dotnet_only(c_godot_mcp_addon), i_godot_mcp_addon,
         f"npx -y godot-cli@{GODOT_MCP_VERSION} install-plugin --path <프로젝트> ({GODOT_MCP_GUIDE})",
         license="Apache-2.0"),
    Item("godot-mcp-json", "Godot", {"dev"}, "(선택) Godot MCP 서버 등록 (로컬)", godot_dotnet_only(c_godot_mcp_json), None,
         f"에디터 Godot MCP 독: Custom 모드 → Start Server, 그 뒤 npx -y godot-cli@{GODOT_MCP_VERSION} setup-mcp "
         f"claude-code <프로젝트> --url <독의 Server URL> ({GODOT_MCP_GUIDE})"),
    Item("unreal-editor", "Unreal", {"dev"}, "프로젝트 EngineAssociation 과 같은 Unreal 에디터",
         engine_only("unreal", c_unreal_editor), None, "Epic Games Launcher > Unreal Engine > 라이브러리에서 설치"),
    Item("ue-mcp-plugins", "Unreal", {"dev"}, "(선택) Unreal MCP 엔진 플러그인 (.uproject — ModelContextProtocol · AllToolsets, UE 5.8+)",
         engine_only("unreal", ue_mcp_only(c_ue_mcp_plugins)), i_ue_mcp_plugins, f"prereq.py install ue-mcp-plugins ({UE_MCP_GUIDE})",
         license="Unreal Engine EULA (엔진 플러그인)"),
    Item("ue-mcp-json", "Unreal", {"dev"}, "(선택) Unreal MCP 서버 등록 (로컬)", engine_only("unreal", ue_mcp_only(c_ue_mcp_json)), None,
         f"에디터 콘솔: ModelContextProtocol.StartServer → ModelContextProtocol.GenerateClientConfig ClaudeCode ({UE_MCP_GUIDE})"),
    Item("ue-claude-plugin", "Unreal", {"dev"}, "(선택) Epic 공식 Claude Code 플러그인 (unreal-engine-skills-for-claude-code)",
         engine_only("unreal", ue_mcp_only(c_ue_claude_plugin)), None,
         f"Claude Code 에서 /plugin install {UE_CLAUDE_PLUGIN} ({UE_MCP_GUIDE})"),
    Item("android-module", "Android", {"dev"}, "Unity Android Build Support 모듈",
         android_only(engine_only("unity", c_android_module)), None, m_android_module),
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
    Item("comfyui-torch", "생성", {"art"}, "ComfyUI torch 가 GPU 사용 가능 (드라이버 · GPU 세대 · VC++)", c_comfyui_torch, None,
         f"NVIDIA 드라이버 최신화 · VC++ 재배포 패키지 {VC_REDIST}"),
    *[Item(f"model:{k}", "생성", {"art"}, f"모델 {MODELS[k]['file']}", c_model(k), i_model(k),
           f"https://huggingface.co/{MODELS[k]['repo']}", MODELS[k]["size"], MODELS[k]["license"]) for k in MODELS],
    Item("audio-python", "생성", {"art"}, "오디오 후처리 Python (PyAV · numpy)", c_audio_python, i_audio_python,
         "PyAV · numpy 가 있는 Python 경로를 artgen.config.local.json audio.python 에"),
    Item("sound-library", "생성", {"art"}, "효과음 라이브러리 (Kenney CC0 팩)", c_library, i_library,
         "python .agent/tools/artgen/artgen.py library add <zip> --name .. --license ..", 60_000_000, "CC0-1.0"),
    Item("pixelfx", "생성", {"art"}, "(선택) pixelfx 픽셀아트 VFX (Node 18+ · provider pixelfx)", c_pixelfx, i_pixelfx,
         "python .agent/tools/setup/prereq.py install pixelfx", PIXELFX["size"], "MIT"),
    Item("local-config", "생성", {"art"}, "artgen 로컬 설정 (provider=comfyui)", c_local_config, i_local_config, ""),
    Item("comfyui-server", "생성", {"art"}, "ComfyUI 서버 실행 중", c_comfy_server, None, "run_nvidia_gpu.bat"),
    Item("stable-audio", "사용자 결정", {"art"}, "(선택) Stable Audio 효과음 생성 모델",
         c_decide("Stability AI 라이선스(매출 기준 상업 제한) — 효과음은 라이브러리로 대신함. 쓰려면 사용자가 조건 확인 후 직접 받기"),
         None, "https://huggingface.co/Comfy-Org/stable-audio-3"),
    Item("gamedesign", "사용자 결정", {"planning"}, "(선택) gamedesign 감사 카탈로그",
         c_decide("PolyForm Noncommercial — 회사 사용이면 상업 라이선스 필요. /ext 의 설치 돕기로 사용자가 조건 선택"),
         None, "python scripts/sync-catalog.py gamedesign --fetch --accept-license <noncommercial|commercial>"),
    Item("gdpractice", "사용자 결정", {"planning"}, "(선택) 게임 기획 실무 AI 활용 원고 카탈로그 (/ext gdpractice)",
         c_decide("CC BY-NC-SA 4.0 — 회사 상품 · 서비스 포함 · 상업 목적은 저자 허락 필요. 기획 방법론 스킬(ko-design-*)은 이것 없이도 돈다"),
         None, "python scripts/sync-catalog.py gdpractice --fetch --accept-license <noncommercial|commercial>"),
]
REQUIRED_SKIP = {"vscode", "comfyui-server", "stable-audio", "gamedesign", "gdpractice", "pytest", "adb-device", "protobuf",
                 "graphify", "dotnet-sdk", "godot-mcp-addon", "godot-mcp-json",
                 "ue-mcp-plugins", "ue-mcp-json", "ue-claude-plugin", "pixelfx"}
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
    ap.add_argument("--root", default=os.getcwd(), help="게임 프로젝트 루트 — Unity · Godot · Unreal (기본: 현재 디렉터리)")
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
