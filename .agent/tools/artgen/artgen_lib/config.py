"""설정 로드 — artgen.config.json(추적) ← artgen.config.local.json(로컬, gitignore) ← 환경변수.

비밀값(API 키)은 설정 파일에 두지 않는다. 어댑터 설정에는 환경변수 *이름*만 적는다 (예: "apiKeyEnv": "MY_API_KEY").
"""
import copy
import json
import os

from . import TOOL_DIR, ArtgenError

DEFAULTS = {
    "provider": "mock",
    "storeDir": "production/artgen",
    "importMap": "production/artgen/import-map.json",
    "defaults": {"variants": 4, "maxRounds": 3, "passScore": 4.0},
    "providers": {},
}


def _deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ArtgenError(f"설정 JSON 오류: {path} — {e}")


def load_config(tool_dir=TOOL_DIR):
    cfg = copy.deepcopy(DEFAULTS)
    for name in ("artgen.config.json", "artgen.config.local.json"):
        p = os.path.join(tool_dir, name)
        if os.path.isfile(p):
            cfg = _deep_merge(cfg, _read_json(p))
    env_provider = os.environ.get("ARTGEN_PROVIDER")
    if env_provider:
        cfg["provider"] = env_provider
    return cfg
