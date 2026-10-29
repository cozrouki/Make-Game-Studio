"""library — 생성하지 않고 등록된 사운드 라이브러리(예: Kenney CC0 팩)에서 효과음을 고른다.

후보 고르기 두 가지:
  1. 요청의 providerOptions.library.files 에 라이브러리 상대경로를 적으면 그 파일들을 변형으로 쓴다
     (art 세션이 `artgen library search` 결과를 보고 고른 경우 — 권장)
  2. 없으면 prompt.subject + style 로 검색해 상위 variants 개를 쓴다

원본(ogg 등)은 variant_01.src.<ext> 로 복사하고, 저장소가 audio_post 로 WAV 를 만든다 (raw_audio).
요청 길이는 상한으로만 쓴다 — 기성 소리는 원래 길이가 정답이다 (duration_is_max).
변형마다 variant_NN.source.json 에 팩 · 파일 · 라이선스를 남기고, 승격하면 credits.json 에 기록된다.

설정 (artgen.config.json → providers.library):
    dir           라이브러리 폴더 (절대경로 또는 프로젝트 루트 기준, 기본 art-source/sound-library)
    maxOverRatio  검색 후보의 길이 상한 = 요청 길이 × 이 값 (기본 1.5, 넘는 부분은 후처리가 페이드아웃으로 자른다)
"""
import json
import os
import shutil

from .. import ArtgenError
from .. import library as lib
from .base import Provider


def library_dir(options, project_root):
    d = options.get("dir", "art-source/sound-library")
    return d if os.path.isabs(d) else os.path.join(project_root or os.getcwd(), d)


class LibraryProvider(Provider):
    name = "library"
    description = "등록된 사운드 라이브러리에서 고르기 (라이선스 확인된 기성 효과음 — 생성 없음)"
    capabilities = {"transparent": False, "references": False, "seed": False}
    kinds = ("audio",)
    raw_audio = True
    duration_is_max = True
    honors_variants = False  # 검색 결과가 variants 보다 적을 수 있다

    def check(self):
        return True, f"라이브러리: {self.options.get('dir', 'art-source/sound-library')}"

    def generate(self, job):
        root = library_dir(self.options, job.project_root)
        index = lib.load_index(root)
        pinned = job.request.get("providerOptions", {}).get("library", {}).get("files") or []
        if pinned:
            files = list(pinned)
        else:
            p = job.request["prompt"]
            query = " ".join([p["subject"], *p.get("style", [])])
            hits = lib.search(index, query, max_duration=job.duration * self.options.get("maxOverRatio", 1.5),
                              limit=job.variants)
            if not hits:
                raise ArtgenError(f"라이브러리 검색 결과 없음: '{query}' — artgen library search 로 단어를 바꿔 찾고 "
                                  "providerOptions.library.files 에 고른 파일을 적는다")
            files = [h["file"] for h in hits]
        paths = []
        for i, rel in enumerate(files):
            entry, source = lib.source_of(index, rel)
            src = os.path.join(root, *rel.split("/"))
            if not os.path.isfile(src):
                raise ArtgenError(f"라이브러리 파일 없음: {src} — library index 를 다시 실행")
            ext = os.path.splitext(rel)[1].lower()
            dst = os.path.join(job.out_dir, f"variant_{i + 1:02d}.src{ext}")
            shutil.copyfile(src, dst)
            with open(os.path.join(job.out_dir, f"variant_{i + 1:02d}.source.json"), "w", encoding="utf-8") as f:
                json.dump(source, f, ensure_ascii=False, indent=2)
            paths.append(dst)
        return paths


PROVIDER_CLASS = LibraryProvider
