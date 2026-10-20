"""생성 요청(artgen-request/1) 로드 · 검증 · 정규화 · 프롬프트 컴파일.

외부 의존성(jsonschema) 없이 검증한다. 스키마 문서: schema/request.schema.json
"""
import hashlib
import json
import re

from . import SCHEMA_ID, ArtgenError

ASSET_ID_RE = re.compile(r"^ASSET-\d{3,}$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
CATEGORIES = {"sprite", "icon", "ui", "vfx", "environment", "texture", "concept"}
FORMATS = {"png"}

# Unity TextureImporter 설정 기본값 — 승격 시 import-map 에 빠짐없이 기록한다
IMPORT_DEFAULTS = {
    "textureType": "Sprite",       # Default | Sprite | NormalMap
    "spriteMode": "Single",        # Single | Multiple (Multiple 슬라이싱은 수동)
    "pixelsPerUnit": 100.0,
    "filterMode": "Bilinear",      # Point | Bilinear | Trilinear
    "maxSize": 2048,
    "compression": "Normal",       # None | LowQuality | Normal | HighQuality
    "mipmaps": False,
    "wrapMode": "Clamp",           # Repeat | Clamp | Mirror
    "alphaIsTransparency": True,
    "sRGB": True,
}
ENUMS = {
    "textureType": {"Default", "Sprite", "NormalMap"},
    "spriteMode": {"Single", "Multiple"},
    "filterMode": {"Point", "Bilinear", "Trilinear"},
    "compression": {"None", "LowQuality", "Normal", "HighQuality"},
    "wrapMode": {"Repeat", "Clamp", "Mirror"},
}
MAX_SIZES = {32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384}


def load_request(path):
    try:
        with open(path, encoding="utf-8") as f:
            req = json.load(f)
    except FileNotFoundError:
        raise ArtgenError(f"요청 파일 없음: {path}")
    except json.JSONDecodeError as e:
        raise ArtgenError(f"요청 JSON 오류: {path} — {e}")
    errors = validate_request(req)
    if errors:
        raise ArtgenError(f"요청 검증 실패: {path}\n  - " + "\n  - ".join(errors))
    return normalize_request(req)


def validate_request(req):
    """오류 메시지 목록을 돌려준다. 빈 목록이면 유효."""
    e = []
    if not isinstance(req, dict):
        return ["최상위는 객체여야 함"]
    if req.get("schema") != SCHEMA_ID:
        e.append(f"schema 는 '{SCHEMA_ID}' 여야 함 (현재: {req.get('schema')!r})")
    if not isinstance(req.get("assetId"), str) or not ASSET_ID_RE.match(req["assetId"]):
        e.append("assetId 는 'ASSET-NNN' 형식 (asset-manifest.md 의 ID)")
    if not isinstance(req.get("name"), str) or not req["name"].strip():
        e.append("name 필수")
    if req.get("category") not in CATEGORIES:
        e.append(f"category 는 {sorted(CATEGORIES)} 중 하나")

    p = req.get("prompt")
    if not isinstance(p, dict):
        e.append("prompt 객체 필수")
    else:
        if not isinstance(p.get("subject"), str) or not p["subject"].strip():
            e.append("prompt.subject 필수 (무엇을 그리는가)")
        for key in ("style", "negative", "palette"):
            if key in p and not (isinstance(p[key], list) and all(isinstance(x, str) for x in p[key])):
                e.append(f"prompt.{key} 는 문자열 배열")
        for c in p.get("palette", []) if isinstance(p.get("palette"), list) else []:
            if isinstance(c, str) and not HEX_RE.match(c):
                e.append(f"prompt.palette 색상은 #RRGGBB (현재: {c})")
        for key in ("composition", "lighting"):
            if key in p and not isinstance(p[key], str):
                e.append(f"prompt.{key} 는 문자열")

    o = req.get("output")
    if not isinstance(o, dict):
        e.append("output 객체 필수")
    else:
        for key in ("width", "height"):
            v = o.get(key)
            if not isinstance(v, int) or isinstance(v, bool) or not (16 <= v <= 8192):
                e.append(f"output.{key} 는 16~8192 정수")
        if o.get("format", "png") not in FORMATS:
            e.append(f"output.format 은 {sorted(FORMATS)} 중 하나")
        if "variants" in o and (not isinstance(o["variants"], int) or not (1 <= o["variants"] <= 16)):
            e.append("output.variants 는 1~16 정수")
        if "seed" in o and o["seed"] is not None and (not isinstance(o["seed"], int) or o["seed"] < 0):
            e.append("output.seed 는 0 이상 정수 또는 null")
        if "transparent" in o and not isinstance(o["transparent"], bool):
            e.append("output.transparent 는 bool")

    u = req.get("unity")
    if u is not None:
        if not isinstance(u, dict):
            e.append("unity 는 객체")
        else:
            dest = u.get("dest")
            if dest is not None:
                if not isinstance(dest, str) or not dest.startswith("Assets/") or ".." in dest.split("/"):
                    e.append("unity.dest 는 'Assets/' 로 시작하는 상대경로 ('..' 금지)")
                elif not dest.lower().endswith(".png"):
                    e.append("unity.dest 는 .png 로 끝나야 함")
            imp = u.get("import", {})
            if not isinstance(imp, dict):
                e.append("unity.import 는 객체")
            else:
                for k, v in imp.items():
                    if k not in IMPORT_DEFAULTS:
                        e.append(f"unity.import.{k} 는 알 수 없는 키 (허용: {sorted(IMPORT_DEFAULTS)})")
                    elif k in ENUMS and v not in ENUMS[k]:
                        e.append(f"unity.import.{k} 는 {sorted(ENUMS[k])} 중 하나")
                    elif k == "maxSize" and v not in MAX_SIZES:
                        e.append(f"unity.import.maxSize 는 {sorted(MAX_SIZES)} 중 하나")
                    elif isinstance(IMPORT_DEFAULTS[k], bool) and not isinstance(v, bool):
                        e.append(f"unity.import.{k} 는 bool")
                    elif k == "pixelsPerUnit" and (not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0):
                        e.append("unity.import.pixelsPerUnit 는 양수")

    if "references" in req and not (isinstance(req["references"], list) and all(isinstance(x, str) for x in req["references"])):
        e.append("references 는 경로 문자열 배열")
    if "providerOptions" in req and not isinstance(req["providerOptions"], dict):
        e.append("providerOptions 는 객체 (키 = 어댑터 이름)")
    if "history" in req and not isinstance(req["history"], list):
        e.append("history 는 배열")
    return e


def normalize_request(req):
    req = json.loads(json.dumps(req))  # 깊은 복사
    p = req["prompt"]
    for key in ("style", "negative", "palette"):
        p.setdefault(key, [])
    p.setdefault("composition", "")
    p.setdefault("lighting", "")
    o = req["output"]
    o.setdefault("format", "png")
    o.setdefault("transparent", False)
    o.setdefault("seed", None)
    req.setdefault("references", [])
    req.setdefault("providerOptions", {})
    req.setdefault("history", [])
    return req


def request_hash(req):
    """생성 결과에 영향을 주는 필드만 해시 — 같은 요청 재실행을 식별."""
    keyed = {k: req.get(k) for k in ("prompt", "output", "references", "providerOptions", "category")}
    blob = json.dumps(keyed, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def compile_prompt(req):
    """백엔드 중립 텍스트 프롬프트. 구조화 필드를 직접 쓰는 어댑터는 무시해도 된다."""
    p = req["prompt"]
    o = req["output"]
    parts = [p["subject"].strip()]
    if p["style"]:
        parts.append(", ".join(p["style"]))
    if p["composition"]:
        parts.append(p["composition"].strip())
    if p["lighting"]:
        parts.append(p["lighting"].strip())
    if p["palette"]:
        parts.append("color palette: " + " ".join(p["palette"]))
    if o["transparent"]:
        parts.append("isolated on transparent background")
    negative = list(p["negative"])
    return {"positive": ", ".join(parts), "negative": ", ".join(negative)}
