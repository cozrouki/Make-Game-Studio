"""사운드 라이브러리 — 라이선스가 확인된 기성 효과음 팩을 등록 · 색인 · 검색한다.

AI 생성 대신 쓰는 효과음 출처다 (예: Kenney 오디오 팩, CC0). 팩마다 LIBRARY.json 에 라이선스를 적고,
승격할 때 출처가 production/artgen/credits.json 에 남는다.

<libraryDir>/
  index.json                      색인 (library index 가 만든다)
  <팩 이름>/LIBRARY.json          {"name", "license", "url", "attribution"}
  <팩 이름>/**/*.ogg|wav|mp3|flac  원본 파일 (zip 을 풀어 둔 그대로)
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import zipfile

from . import ArtgenError
from .audioutil import read_info

AUDIO_EXTS = (".wav", ".ogg", ".mp3", ".flac")
PACK_FILE = "LIBRARY.json"
INDEX_FILE = "index.json"
AUDIO_POST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_post.py")
# 검색어에서 버리는 말 — 프롬프트 문장을 그대로 검색어로 써도 되게
STOPWORDS = {"a", "an", "the", "of", "for", "and", "with", "in", "on", "to", "sound", "sfx", "effect", "short",
             "game", "single", "audio", "clip", "very", "soft", "loud", "quick", "small", "big"}


def tokenize(text):
    """파일 경로 · 문장 → 소문자 단어 목록. camelCase · 숫자 · 구분자를 나눈다."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return [t for t in re.split(r"[^a-zA-Z]+", text.lower()) if len(t) > 1]


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def add_pack(lib_dir, source, name, license_id, url="", attribution=""):
    """zip 이나 폴더를 <lib_dir>/<name>/ 으로 풀고 LIBRARY.json 을 쓴다. 라이선스는 필수다."""
    if not re.match(r"^[a-z0-9][a-z0-9._-]*$", name):
        raise ArtgenError("팩 이름은 소문자 · 숫자 · . _ - 만 (예: kenney-interface-sounds)")
    if not license_id:
        raise ArtgenError("--license 필수 (예: CC0-1.0) — 라이선스를 모르는 팩은 등록하지 않는다")
    dest = os.path.join(lib_dir, name)
    if os.path.exists(dest):
        raise ArtgenError(f"이미 있는 팩: {dest}")
    if os.path.isfile(source) and source.lower().endswith(".zip"):
        with zipfile.ZipFile(source) as z:
            for member in z.namelist():  # zip slip 방지
                target = os.path.realpath(os.path.join(dest, member))
                if not target.startswith(os.path.realpath(dest) + os.sep) and target != os.path.realpath(dest):
                    raise ArtgenError(f"zip 안에 바깥 경로가 있음: {member}")
            z.extractall(dest)
    elif os.path.isdir(source):
        shutil.copytree(source, dest)
    else:
        raise ArtgenError(f"zip 파일이나 폴더가 아님: {source}")
    meta = {"name": name, "license": license_id, "url": url, "attribution": attribution, "addedAt": _now()}
    with open(os.path.join(dest, PACK_FILE), "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return meta


def _probe(python, paths):
    """WAV 가 아닌 파일의 길이 — PyAV 인터프리터(audio.python)로 잰다. 없으면 빈 결과."""
    if not python or not paths:
        return {}
    # 경로 목록은 표준 입력으로 — 팩 하나에 수백 개라 인자로 넘기면 Windows 명령줄 한도(32K)를 넘는다
    proc = subprocess.run([python, AUDIO_POST, "--probe", "-"], input=json.dumps(paths), capture_output=True,
                          text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        raise ArtgenError(f"오디오 길이 측정 실패: {(proc.stderr or proc.stdout).strip()[-400:]}")


def build_index(lib_dir, python=None):
    """모든 팩을 훑어 index.json 을 다시 만든다."""
    if not os.path.isdir(lib_dir):
        raise ArtgenError(f"라이브러리 폴더 없음: {lib_dir} — 먼저 library add")
    entries, packs, others = [], {}, []
    for pack in sorted(os.listdir(lib_dir)):
        meta_path = os.path.join(lib_dir, pack, PACK_FILE)
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, encoding="utf-8") as f:
            packs[pack] = json.load(f)
        for base, _dirs, files in os.walk(os.path.join(lib_dir, pack)):
            for fn in sorted(files):
                if os.path.splitext(fn)[1].lower() not in AUDIO_EXTS:
                    continue
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, lib_dir).replace("\\", "/")
                entry = {"pack": pack, "file": rel, "tokens": sorted(set(tokenize(os.path.relpath(full, os.path.join(lib_dir, pack)))))}
                info = read_info(full) if fn.lower().endswith(".wav") else None
                if info:
                    entry.update(durationSec=round(info["durationSec"], 3), channels=info["channels"], rate=info["rate"])
                else:
                    others.append((entry, full))
                entries.append(entry)
    probed = _probe(python, [full for _e, full in others])
    for entry, full in others:
        entry.update(probed.get(full, {}))
    index = {"builtAt": _now(), "packs": packs, "entries": entries}
    with open(os.path.join(lib_dir, INDEX_FILE), "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return index


def load_index(lib_dir):
    path = os.path.join(lib_dir, INDEX_FILE)
    if not os.path.isfile(path):
        raise ArtgenError(f"색인 없음: {path} — artgen library index 를 먼저 실행")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def search(index, query, max_duration=None, limit=20):
    """질의 단어와 파일 경로 단어가 많이 겹칠수록 위. 접두 일치(click ↔ clicks)도 인정한다."""
    words = [w for w in tokenize(query) if w not in STOPWORDS]
    if not words:
        return []
    ranked = []
    for e in index["entries"]:
        d = e.get("durationSec")
        if max_duration and d and d > max_duration:
            continue
        score = sum(1.0 if w in e["tokens"] else 0.5 if any(t.startswith(w) or w.startswith(t) for t in e["tokens"]) else 0.0
                    for w in words)
        if score > 0:
            ranked.append((score, d or 0.0, e))
    ranked.sort(key=lambda r: (-r[0], r[1], r[2]["file"]))  # 같은 점수면 짧은 소리부터
    return [dict(r[2], score=r[0]) for r in ranked[:limit]]


def source_of(index, rel_file):
    """색인 항목 + 팩 라이선스 → 출처 기록."""
    entry = next((e for e in index["entries"] if e["file"] == rel_file), None)
    if entry is None:
        raise ArtgenError(f"라이브러리에 없는 파일: {rel_file} — library search 결과의 file 값을 쓴다")
    pack = index["packs"][entry["pack"]]
    return entry, {"library": entry["pack"], "file": rel_file, "license": pack["license"], "url": pack.get("url", ""),
                   "attribution": pack.get("attribution", "")}
