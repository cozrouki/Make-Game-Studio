"""표준 라이브러리만으로 WAV 쓰기 · 헤더 읽기 · 기술 검사 (numpy 의존 없음).

검사는 16bit PCM 만 정밀하게 한다. 다른 비트 깊이는 길이 · 채널 · 샘플레이트만 본다.
"""
import array
import math
import sys
import wave

FULL_SCALE = 32768.0
SILENCE_DBFS = -50.0       # 이보다 작으면 무음으로 본다
SCAN_LIMIT_SEC = 5.0       # 앞 · 뒤 무음 측정은 각 끝에서 이 길이까지만 본다 (긴 음악도 빠르게)


def write_wav(path, rate, channels, samples):
    """samples: 인터리브된 16bit 정수 시퀀스 (array('h') 권장)."""
    data = samples if isinstance(samples, array.array) else array.array("h", samples)
    if sys.byteorder == "big":
        data = array.array("h", data)
        data.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def read_info(path):
    """{rate, channels, sampwidth, frames, durationSec} — WAV 가 아니면 None."""
    try:
        with wave.open(path, "rb") as w:
            rate, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
    except (wave.Error, EOFError, OSError):
        return None
    return {"rate": rate, "channels": ch, "sampwidth": sw, "frames": n, "durationSec": n / rate if rate else 0.0}


def _dbfs(x):
    return round(20 * math.log10(x), 2) if x > 0 else -120.0


def _edge_silence(data, channels, rate, threshold, from_end):
    """한쪽 끝에서 처음으로 무음 기준을 넘는 지점까지의 길이(초)."""
    frames = len(data) // channels
    limit = min(frames, int(SCAN_LIMIT_SEC * rate))
    for i in range(limit):
        f = frames - 1 - i if from_end else i
        base = f * channels
        for c in range(channels):
            if abs(data[base + c]) > threshold:
                return i / rate
    return limit / rate


def analyze(path):
    """기술 검사 지표. 16bit 가 아니면 info 만 돌려준다."""
    info = read_info(path)
    if info is None:
        return None
    out = dict(info)
    if info["sampwidth"] != 2 or info["frames"] == 0:
        out["analyzed"] = False
        return out
    with wave.open(path, "rb") as w:
        data = array.array("h", w.readframes(info["frames"]))
    if sys.byteorder == "big":
        data.byteswap()
    ch, rate = info["channels"], info["rate"]
    peak = max(max(data), -min(data)) / FULL_SCALE
    threshold = FULL_SCALE * 10 ** (SILENCE_DBFS / 20)
    clipped = data.count(32767) + data.count(-32768)
    first, last = data[:ch], data[len(data) - ch:]
    out.update(
        analyzed=True,
        peakDbfs=_dbfs(peak),
        clippedRatio=round(clipped / len(data), 6),
        leadSilenceSec=round(_edge_silence(data, ch, rate, threshold, False), 3),
        tailSilenceSec=round(_edge_silence(data, ch, rate, threshold, True), 3),
        # 루프 이음매: 마지막 프레임 → 첫 프레임으로 넘어갈 때의 순간 점프 (0 = 매끄러움, 1 = 풀스케일 점프)
        loopSeam=round(max(abs(a - b) for a, b in zip(first, last)) / FULL_SCALE, 4),
    )
    return out


def check(stats, out, duration_is_max=False):
    """요청(output) 대비 경고 목록. 차단하지 않고 검수에 넘긴다.
    duration_is_max 면 요청 길이는 상한이다 (기성 소리 — 더 짧아도 정상)."""
    w = []
    want = out["durationSec"]
    got = stats["durationSec"]
    if duration_is_max:
        if got > want + 0.05:
            w.append(f"길이 {got:.2f}s > 상한 {want:.2f}s")
    elif abs(got - want) > max(0.05, want * 0.05):
        w.append(f"길이 {got:.2f}s ≠ 요청 {want:.2f}s")
    if stats["rate"] != out["sampleRate"]:
        w.append(f"샘플레이트 {stats['rate']} ≠ 요청 {out['sampleRate']}")
    if stats["channels"] != out["channels"]:
        w.append(f"채널 {stats['channels']} ≠ 요청 {out['channels']}")
    if not stats.get("analyzed"):
        w.append(f"{stats['sampwidth'] * 8}bit — 음량 · 무음 · 루프 검사 생략 (16bit PCM 만 검사)")
        return w
    if stats["clippedRatio"] > 0.001:
        w.append(f"클리핑 {stats['clippedRatio'] * 100:.2f}%")
    if stats["peakDbfs"] < -20:
        w.append(f"너무 작음 (피크 {stats['peakDbfs']} dBFS)")
    if stats["leadSilenceSec"] > 0.2 and not out["loop"]:
        w.append(f"앞 무음 {stats['leadSilenceSec']}s (효과음은 즉시 시작해야 함)")
    if out["loop"] and stats["loopSeam"] > 0.1:
        w.append(f"루프 이음매 점프 {stats['loopSeam']} (클릭 소리 가능)")
    if out["loop"] and max(stats["tailSilenceSec"], stats["leadSilenceSec"]) > 0.5:
        # 무음끼리 이어지면 이음매 점프는 0 이라 위 검사로는 못 잡는다 — 반복 재생 때 공백이 된다
        w.append(f"루프 끝 · 처음 무음 (앞 {stats['leadSilenceSec']}s · 뒤 {stats['tailSilenceSec']}s) — 반복 시 공백")
    if stats["leadSilenceSec"] >= min(SCAN_LIMIT_SEC, stats["durationSec"]) - 0.01:
        w.append("앞부분이 모두 무음 — 생성 실패 의심")
    return w
