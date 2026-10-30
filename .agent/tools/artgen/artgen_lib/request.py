"""생성 요청(artgen-request/1) 로드 · 검증 · 정규화 · 프롬프트 컴파일.

외부 의존성(jsonschema) 없이 검증한다. 스키마 문서: schema/request.schema.json
category 로 종류가 갈린다 — 이미지(sprite · icon · …)와 오디오(sfx · music · ambience).
"""
import hashlib
import json
import re

from . import SCHEMA_ID, ArtgenError

ASSET_ID_RE = re.compile(r"^ASSET-\d{3,}$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
IMAGE_CATEGORIES = {"sprite", "icon", "ui", "vfx", "environment", "texture", "concept"}
AUDIO_CATEGORIES = {"sfx", "music", "ambience"}
CATEGORIES = IMAGE_CATEGORIES | AUDIO_CATEGORIES
FORMATS = {"png"}
AUDIO_FORMATS = {"wav"}
SAMPLE_RATES = {44100, 48000}
MAX_AUDIO_SEC = 600
KEY_RE = re.compile(r"^[A-G](#|b)? (major|minor)$")
TIME_SIGNATURES = {2, 3, 4, 6}
INSTRUMENTAL = "[Instrumental]"

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

# Unity AudioImporter 설정 기본값 — 카테고리마다 다르다 (짧은 효과음은 메모리에 풀어 두고, 음악은 스트리밍)
AUDIO_IMPORT_DEFAULTS = {
    "sfx": {"loadType": "DecompressOnLoad", "compressionFormat": "ADPCM", "quality": 1.0,
            "forceToMono": True, "loadInBackground": False, "preloadAudioData": True},
    "music": {"loadType": "Streaming", "compressionFormat": "Vorbis", "quality": 0.7,
              "forceToMono": False, "loadInBackground": True, "preloadAudioData": False},
    "ambience": {"loadType": "CompressedInMemory", "compressionFormat": "Vorbis", "quality": 0.6,
                 "forceToMono": False, "loadInBackground": True, "preloadAudioData": True},
}
AUDIO_ENUMS = {
    "loadType": {"DecompressOnLoad", "CompressedInMemory", "Streaming"},
    "compressionFormat": {"PCM", "Vorbis", "ADPCM"},
}
# 카테고리별 출력 기본값 — 효과음은 모노 · 한 번 재생, 음악 · 환경음은 스테레오 · 루프
AUDIO_OUTPUT_DEFAULTS = {
    "sfx": {"loop": False, "channels": 1},
    "music": {"loop": True, "channels": 2},
    "ambience": {"loop": True, "channels": 2},
}


def kind_of(req):
    """'audio' | 'image' — category 로 정한다."""
    return "audio" if req.get("category") in AUDIO_CATEGORIES else "image"


def import_defaults(req):
    """요청 종류에 맞는 Unity 임포트 기본값."""
    if kind_of(req) == "audio":
        return dict(AUDIO_IMPORT_DEFAULTS[req["category"]])
    return dict(IMPORT_DEFAULTS)


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
        if kind_of(req) == "audio":
            e += _validate_audio_prompt(p)

    o = req.get("output")
    if not isinstance(o, dict):
        e.append("output 객체 필수")
    elif kind_of(req) == "audio":
        e += _validate_audio_output(o)
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
                # 엔진별 위치 규칙(Unity 는 Assets/ 아래)은 승격 때 프로젝트 엔진을 보고 확인한다 (store.promote)
                if (not isinstance(dest, str) or not dest or dest.startswith(("/", "\\")) or ":" in dest
                        or ".." in dest.replace("\\", "/").split("/")):
                    e.append("unity.dest 는 프로젝트 루트 기준 상대경로 ('..' · 절대경로 금지)")
                elif kind_of(req) == "audio" and not dest.lower().endswith(".wav"):
                    e.append("unity.dest 는 .wav 로 끝나야 함 (오디오)")
                elif kind_of(req) == "image" and not dest.lower().endswith(".png"):
                    e.append("unity.dest 는 .png 로 끝나야 함")
            imp = u.get("import", {})
            if not isinstance(imp, dict):
                e.append("unity.import 는 객체")
            elif kind_of(req) == "audio":
                e += _validate_audio_import(imp)
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


def _validate_audio_prompt(p):
    e = []
    if p.get("palette"):
        e.append("prompt.palette 는 이미지 전용 (오디오 요청에서 빼기)")
    if "tempo" in p and (not isinstance(p["tempo"], int) or isinstance(p["tempo"], bool) or not (30 <= p["tempo"] <= 300)):
        e.append("prompt.tempo 는 30~300 정수 (BPM)")
    if "key" in p and (not isinstance(p["key"], str) or not KEY_RE.match(p["key"])):
        e.append("prompt.key 는 'E minor' · 'F# major' 형식")
    if "timeSignature" in p and p["timeSignature"] not in TIME_SIGNATURES:
        e.append(f"prompt.timeSignature 는 {sorted(TIME_SIGNATURES)} 중 하나")
    if "lyrics" in p and not isinstance(p["lyrics"], str):
        e.append(f"prompt.lyrics 는 문자열 (생략하면 {INSTRUMENTAL})")
    return e


def _validate_audio_output(o):
    e = []
    d = o.get("durationSec")
    if not isinstance(d, (int, float)) or isinstance(d, bool) or not (0.1 <= d <= MAX_AUDIO_SEC):
        e.append(f"output.durationSec 는 0.1~{MAX_AUDIO_SEC} 숫자 (오디오 필수)")
    if o.get("format", "wav") not in AUDIO_FORMATS:
        e.append(f"output.format 은 {sorted(AUDIO_FORMATS)} 중 하나 (오디오)")
    if "channels" in o and o["channels"] not in (1, 2):
        e.append("output.channels 는 1 또는 2")
    if "sampleRate" in o and o["sampleRate"] not in SAMPLE_RATES:
        e.append(f"output.sampleRate 는 {sorted(SAMPLE_RATES)} 중 하나")
    if "loop" in o and not isinstance(o["loop"], bool):
        e.append("output.loop 는 bool")
    if "variants" in o and (not isinstance(o["variants"], int) or not (1 <= o["variants"] <= 16)):
        e.append("output.variants 는 1~16 정수")
    if "seed" in o and o["seed"] is not None and (not isinstance(o["seed"], int) or o["seed"] < 0):
        e.append("output.seed 는 0 이상 정수 또는 null")
    for key in ("width", "height", "transparent"):
        if key in o:
            e.append(f"output.{key} 는 이미지 전용 (오디오 요청에서 빼기)")
    return e


def _validate_audio_import(imp):
    e = []
    known = AUDIO_IMPORT_DEFAULTS["sfx"]
    for k, v in imp.items():
        if k not in known:
            e.append(f"unity.import.{k} 는 알 수 없는 키 (오디오 허용: {sorted(known)})")
        elif k in AUDIO_ENUMS and v not in AUDIO_ENUMS[k]:
            e.append(f"unity.import.{k} 는 {sorted(AUDIO_ENUMS[k])} 중 하나")
        elif k == "quality" and (not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.01 <= v <= 1.0)):
            e.append("unity.import.quality 는 0.01~1.0")
        elif isinstance(known[k], bool) and not isinstance(v, bool):
            e.append(f"unity.import.{k} 는 bool")
    return e


def normalize_request(req):
    req = json.loads(json.dumps(req))  # 깊은 복사
    p = req["prompt"]
    for key in ("style", "negative", "palette"):
        p.setdefault(key, [])
    p.setdefault("composition", "")
    p.setdefault("lighting", "")
    o = req["output"]
    o.setdefault("seed", None)
    if kind_of(req) == "audio":
        for k, v in AUDIO_OUTPUT_DEFAULTS[req["category"]].items():
            o.setdefault(k, v)
        o.setdefault("format", "wav")
        o.setdefault("sampleRate", 44100)
        o["durationSec"] = float(o["durationSec"])
        p.setdefault("lyrics", INSTRUMENTAL)
    else:
        o.setdefault("format", "png")
        o.setdefault("transparent", False)
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
    if kind_of(req) == "audio":
        return _compile_audio_prompt(req)
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


def _compile_audio_prompt(req):
    """오디오 — 묘사 · 스타일 태그 · 템포/조성 · 루프 여부를 한 줄로. 모델별 구조화 입력(BPM · 조성 · 가사)은
    어댑터가 request.prompt 에서 직접 읽는다."""
    p = req["prompt"]
    o = req["output"]
    parts = [p["subject"].strip()]
    if p["style"]:
        parts.append(", ".join(p["style"]))
    if p.get("tempo"):
        parts.append(f"{p['tempo']} BPM")
    if p.get("key"):
        parts.append(p["key"])
    if p["composition"]:
        parts.append(p["composition"].strip())
    if o["loop"]:
        parts.append("seamless loop")
    return {"positive": ", ".join(parts), "negative": ", ".join(p["negative"])}
