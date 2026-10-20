"""manual — 사람 아티스트의 납품물을 생성 결과처럼 받는다.

아티스트(또는 보조 세션)가 <inboxDir>/<ASSET-ID>/ 에 PNG 를 넣고 generate 를 실행하면,
파일을 새 버전 디렉터리로 **이동**한다 (받은함은 다음 라운드를 위해 비워짐).
이후 검수 · select · promote · Unity 임포트는 AI 생성물과 똑같이 처리된다.

설정 (artgen.config.json):
    "providers": { "manual": { "inboxDir": "production/artgen/_inbox" } }
"""
import glob
import os
import shutil

from .. import ArtgenError
from .base import Provider


class ManualProvider(Provider):
    name = "manual"
    description = "사람 아티스트 납품 수령 (<inboxDir>/<ASSET-ID>/*.png → 새 버전)"
    capabilities = {"transparent": True, "references": True, "seed": False}
    honors_variants = False

    def _inbox(self, job):
        rel = self.options.get("inboxDir", "production/artgen/_inbox")
        return os.path.join(job.project_root or os.getcwd(), *rel.split("/"), job.asset_id)

    def check(self):
        return True, f"받은함: {self.options.get('inboxDir', 'production/artgen/_inbox')}/<ASSET-ID>/"

    def generate(self, job):
        inbox = self._inbox(job)
        os.makedirs(inbox, exist_ok=True)
        files = sorted(glob.glob(os.path.join(inbox, "*.png")))
        if not files:
            raise ArtgenError(f"{job.asset_id}: 납품물 없음 — 아티스트가 PNG 를 넣을 위치: {inbox}")
        paths = []
        for src in files:
            dst = os.path.join(job.out_dir, os.path.basename(src))
            shutil.move(src, dst)
            paths.append(dst)
        return paths


PROVIDER_CLASS = ManualProvider
