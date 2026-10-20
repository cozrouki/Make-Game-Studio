"""새 백엔드 어댑터 템플릿 — 이 파일을 providers/<이름>.py 로 복사해 채운다.

레지스트리는 `_` 로 시작하는 파일을 무시하므로 이 템플릿 자체는 등록되지 않는다.

체크리스트:
  1. name / description / capabilities 를 채운다.
  2. check() — 필수 설정·환경변수가 있는지만 본다 (네트워크 호출 X, `providers` 명령이 빠르게 끝나도록).
  3. generate() — job.variants 개 PNG 를 job.out_dir 에 쓰고 경로 목록 반환.
     - 투명 배경을 백엔드가 못 하면 capabilities["transparent"]=False 로 두면 된다.
       (검수 단계가 알파 채널 부재를 지적하고, 스킬이 배경 제거 후처리를 안내한다)
  4. 비밀값은 os.environ 에서 읽는다. 설정에는 환경변수 이름만 둔다 (apiKeyEnv).
  5. tests/test_artgen.py 에 최소 check() 테스트를 추가한다.
  6. artgen.config.local.json 에 "provider": "<이름>" 으로 전환.
"""
import os

from .. import ArtgenError
from .base import Provider


class TemplateProvider(Provider):
    name = "template"
    description = "설명 한 줄"
    capabilities = {"transparent": False, "references": False, "seed": True}

    def check(self):
        env_name = self.options.get("apiKeyEnv", "")
        if env_name and not os.environ.get(env_name):
            return False, f"환경변수 {env_name} 미설정"
        if not self.options.get("endpoint"):
            return False, "providers.template.endpoint 미설정"
        return True, self.options["endpoint"]

    def generate(self, job):
        ok, msg = self.check()
        if not ok:
            raise ArtgenError(msg)
        paths = []
        for i, seed in enumerate(job.seeds):
            # TODO: 백엔드 호출 — job.positive / job.negative / job.width / job.height / seed / job.references
            #       job.request["providerOptions"] 의 원본 값은 job.options 에 이미 병합되어 있다.
            # png_bytes = ...
            path = os.path.join(job.out_dir, f"variant_{i + 1:02d}.png")
            # with open(path, "wb") as f: f.write(png_bytes)
            paths.append(path)
        raise NotImplementedError("템플릿 — 백엔드 호출을 구현하세요")


# PROVIDER_CLASS = TemplateProvider   ← 실제 어댑터에서는 주석 해제
