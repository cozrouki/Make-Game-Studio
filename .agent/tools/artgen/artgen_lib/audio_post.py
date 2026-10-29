"""오디오 후처리 — 생성 모델의 원본(FLAC · MP3 · WAV …)을 Unity 용 16bit WAV 로 만든다.

artgen 본체와 달리 PyAV + numpy 가 필요하다. 그래서 artgen 을 import 하지 않는 단독 스크립트로 두고,
그 둘이 깔린 인터프리터(예: ComfyUI 포터블의 python_embeded)로 실행한다 — 설정 audio.python.

    <python> audio_post.py --in src.flac --out variant_01.wav --rate 44100 --channels 2 --duration 30 --loop 1

처리 순서: 디코드 → 리샘플 · 채널 변환 → (효과음) 앞 무음 제거 → 길이 맞춤
          → 루프면 꼬리를 머리에 크로스페이드 / 아니면 페이드 인 · 아웃 → 피크 정규화 → 16bit WAV
결과 지표는 stdout 에 JSON 한 줄로 낸다.
"""
import argparse
import json
import sys
import wave

SILENCE_DBFS = -50.0
MAX_GAIN_DB = 20.0
LEAD_TRIM_LIMIT_SEC = 1.0


def decode(path, rate, channels):
    import av
    import numpy as np

    layout = "mono" if channels == 1 else "stereo"
    chunks = []
    with av.open(path) as container:
        stream = container.streams.audio[0]
        src = {"srcRate": stream.rate, "srcChannels": stream.channels}
        resampler = av.AudioResampler(format="fltp", layout=layout, rate=rate)
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray())
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray())
    buf = np.concatenate(chunks, axis=1).astype(np.float32) if chunks else np.zeros((channels, 0), np.float32)
    src["srcDurationSec"] = round(buf.shape[1] / rate, 3)
    return buf, src


def best_loop_start(buf, rate, length, xf, step_sec=0.25, block_sec=0.5):
    """[start, start+length+xf) 안의 가장 작은 블록 음량이 최대가 되는 start (샘플). 여유가 없으면 0."""
    import numpy as np

    room = buf.shape[1] - (length + xf)
    if room <= 0:
        return 0
    block = max(1, int(block_sec * rate))
    n_blocks = buf.shape[1] // block
    rms = np.sqrt((buf[:, :n_blocks * block].reshape(buf.shape[0], n_blocks, block) ** 2).mean(axis=(0, 2)))
    span = max(1, (length + xf) // block)
    best, best_score = 0, -1.0
    for start in range(0, room + 1, max(1, int(step_sec * rate))):
        b0 = start // block
        window = rms[b0:b0 + span]
        if window.size < span:
            break
        score = float(window.min())
        if score > best_score:  # 같은 점수면 앞쪽 (도입 직후) 을 유지
            best, best_score = start, score
    return best


def process(buf, rate, duration, loop, crossfade_ms, fade_in_ms, fade_out_ms, peak_dbfs, trim_lead, fit_max=False):
    import numpy as np

    info = {}
    length = int(round(duration * rate))
    if trim_lead and not loop and buf.shape[1]:
        threshold = 10 ** (SILENCE_DBFS / 20)
        loud = np.nonzero(np.abs(buf[:, :int(LEAD_TRIM_LIMIT_SEC * rate)]).max(axis=0) > threshold)[0]
        start = int(loud[0]) if loud.size else 0
        buf = buf[:, start:]
        info["leadTrimmedSec"] = round(start / rate, 3)
    if fit_max and not loop:
        # 기성 소리(라이브러리)는 원래 길이가 정답이다 — 요청 길이는 상한으로만 쓰고 무음으로 늘리지 않는다
        length = min(length, buf.shape[1])

    if loop:
        # 음악 모델은 생성 길이 안에 도입 · 끝맺음을 넣는다 — 그대로 자르면 루프 안에 페이드아웃 · 무음이 들어간다.
        # 그래서 더 길게 생성된 원본에서 음량이 가장 고르게 유지되는 구간을 고른다
        want_xf = int(crossfade_ms * rate / 1000)
        start = best_loop_start(buf, rate, length, want_xf)
        buf = buf[:, start:]
        info["loopStartSec"] = round(start / rate, 3)
        # 길이 L 다음의 꼬리 X 를 머리에 겹친다 — 끝(L-1) 다음 샘플이 원래의 L 과 같아져 이음매가 사라진다
        xf = min(want_xf, length // 4, max(0, buf.shape[1] - length))
        out = np.zeros((buf.shape[0], length), np.float32)
        n = min(length, buf.shape[1])
        out[:, :n] = buf[:, :n]
        if xf > 0:
            ramp = np.linspace(0.0, 1.0, xf, dtype=np.float32)
            out[:, :xf] = buf[:, :xf] * ramp + buf[:, length:length + xf] * (1.0 - ramp)
        info["crossfadeSec"] = round(xf / rate, 3)
    else:
        out = np.zeros((buf.shape[0], length), np.float32)
        n = min(length, buf.shape[1])
        out[:, :n] = buf[:, :n]
        for ms, head in ((fade_in_ms, True), (fade_out_ms, False)):
            k = min(int(ms * rate / 1000), length // 2)
            if k > 0:
                ramp = (0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, k, dtype=np.float32)))
                if head:
                    out[:, :k] *= ramp
                else:
                    out[:, length - k:] *= ramp[::-1]
    info["paddedSec"] = round(max(0, length - buf.shape[1]) / rate, 3)

    peak = float(np.abs(out).max()) if out.size else 0.0
    gain_db = 0.0
    if peak > 0:
        gain_db = min(peak_dbfs - 20 * np.log10(peak), MAX_GAIN_DB)
        out *= 10 ** (gain_db / 20)
    info["gainDb"] = round(float(gain_db), 2)
    return out, info


def write_wav16(path, out, rate):
    import numpy as np

    pcm = np.clip(np.round(out.T * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(out.shape[0])
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def probe(paths):
    """{경로: {durationSec, channels, rate}} — 라이브러리 색인용. 읽지 못한 파일은 빠진다."""
    import av

    out = {}
    for p in paths:
        try:
            with av.open(p) as c:
                s = c.streams.audio[0]
                if s.duration is not None and s.time_base is not None:
                    dur = float(s.duration * s.time_base)
                elif c.duration is not None:
                    dur = c.duration / 1_000_000
                else:
                    dur = sum(f.samples for f in c.decode(s)) / s.rate
                out[p] = {"durationSec": round(dur, 3), "channels": s.channels, "rate": s.rate}
        except Exception:  # 손상 · 미지원 파일은 색인에서 길이 없이 남긴다
            continue
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--probe":
        paths = json.loads(sys.stdin.read()) if argv[1:] == ["-"] else argv[1:]  # "-" = 표준 입력의 JSON 목록
        print(json.dumps(probe(paths), ensure_ascii=False))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rate", type=int, required=True)
    ap.add_argument("--channels", type=int, choices=(1, 2), required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--loop", type=int, default=0)
    ap.add_argument("--crossfade-ms", type=float, default=250)
    ap.add_argument("--fade-in-ms", type=float, default=5)
    ap.add_argument("--fade-out-ms", type=float, default=30)
    ap.add_argument("--peak-dbfs", type=float, default=-1.0)
    ap.add_argument("--trim-lead", type=int, default=1)
    ap.add_argument("--fit", choices=("exact", "max"), default="exact",
                    help="exact = 요청 길이에 맞춤(짧으면 무음으로 채움) · max = 요청 길이는 상한, 짧으면 그대로")
    a = ap.parse_args(argv)
    try:
        buf, info = decode(a.src, a.rate, a.channels)
        if buf.shape[1] == 0:  # PyAV 는 깨진 파일도 빈 스트림으로 열 수 있다 — 무음 WAV 를 성공으로 내지 않는다
            raise ValueError("디코드 결과가 비어 있음 (오디오 아님 또는 손상)")
        out, more = process(buf, a.rate, a.duration, bool(a.loop), a.crossfade_ms, a.fade_in_ms, a.fade_out_ms,
                            a.peak_dbfs, bool(a.trim_lead), a.fit == "max")
        write_wav16(a.out, out, a.rate)
    except Exception as e:  # 호출 측이 JSON 으로 받아 사유를 보여 준다
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    info.update(more, ok=True)
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
