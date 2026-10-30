"""command — 임의의 외부 프로그램을 백엔드로 연결 (Python 어댑터 작성 없이).

ComfyUI API 호출 스크립트, 사내 생성 서버 CLI, 상용 API 래퍼 등 무엇이든 argv 로 실행한다.
셸을 거치지 않는다 (shell=False) — 인자 치환 결과가 그대로 한 인자가 된다.

설정 예 (artgen.config.local.json):
    "providers": {
      "command": {
        "argv": ["python", "tools/my_gen.py", "--job", "{job_file}", "--out", "{out_dir}"],
        "timeoutSec": 900,
        "env": {"MY_BACKEND_URL": "http://127.0.0.1:8188"},
        "capabilities": {"transparent": false, "references": true, "seed": true}
      }
    }

치환 토큰: {job_file} {out_dir} {prompt} {negative} {width} {height} {variants} {seed} {asset_id}
외부 프로그램 계약: {out_dir} 에 PNG (오디오 요청이면 16bit WAV)를 쓴다. 파일명 정렬 순서 = 변형 순서. 종료 코드 0 = 성공.
job_file 은 base.Job 의 JSON 직렬화 (seeds 배열 포함) — 변형별 시드가 필요하면 그것을 읽는다.
"""
import glob
import os
import subprocess

from .. import ArtgenError
from .base import Provider

TOKENS = ("job_file", "out_dir", "prompt", "negative", "width", "height", "variants", "seed", "asset_id", "duration")


class CommandProvider(Provider):
    name = "command"
    description = "외부 프로그램 실행 (argv 템플릿) — 스크립트/CLI 형태의 어떤 백엔드든 연결"
    kinds = ("image", "audio")

    def __init__(self, options):
        super().__init__(options)
        caps = dict(Provider.capabilities)
        caps.update(self.options.get("capabilities", {}))
        self.capabilities = caps

    def check(self):
        argv = self.options.get("argv")
        if not argv:
            return False, "providers.command.argv 미설정 — artgen.config.local.json 에 실행 명령을 지정"
        if not (isinstance(argv, list) and all(isinstance(a, str) for a in argv)):
            return False, "providers.command.argv 는 문자열 배열"
        return True, f"argv[0]={argv[0]}"

    def generate(self, job):
        ok, msg = self.check()
        if not ok:
            raise ArtgenError(msg)
        values = {
            "job_file": job.job_file, "out_dir": job.out_dir, "prompt": job.positive, "negative": job.negative,
            "width": str(job.width), "height": str(job.height), "variants": str(job.variants),
            "seed": str(job.seeds[0]), "asset_id": job.asset_id, "duration": str(job.duration),
        }
        argv = [_substitute(a, values) for a in self.options["argv"]]
        env = dict(os.environ)
        env.update({k: str(v) for k, v in self.options.get("env", {}).items()})
        timeout = self.options.get("timeoutSec", 600)
        try:
            proc = subprocess.run(argv, env=env, timeout=timeout, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")  # OS 코드 페이지와 무관하게 — 영어 Windows(cp1252)에서도 한글이 깨져 죽지 않게
        except FileNotFoundError:
            raise ArtgenError(f"실행 파일을 찾을 수 없음: {argv[0]}")
        except subprocess.TimeoutExpired:
            raise ArtgenError(f"외부 백엔드 시간 초과 ({timeout}s)")
        with open(os.path.join(job.out_dir, "command.log"), "w", encoding="utf-8") as f:
            f.write(f"$ {argv!r}\n[exit {proc.returncode}]\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip()[-800:]
            raise ArtgenError(f"외부 백엔드 실패 (exit {proc.returncode}) — command.log 참고\n{tail}")
        ext = "wav" if job.kind == "audio" else "png"
        paths = sorted(glob.glob(os.path.join(job.out_dir, f"*.{ext}")))
        if not paths:
            raise ArtgenError(f"외부 백엔드가 {ext.upper()} 를 하나도 쓰지 않음 — {{out_dir}} 계약 확인")
        return paths


def _substitute(arg, values):
    # str.format 대신 토큰 단위 치환 — 프롬프트 안의 중괄호가 깨지지 않게
    for t in TOKENS:
        arg = arg.replace("{" + t + "}", values[t])
    return arg


PROVIDER_CLASS = CommandProvider
