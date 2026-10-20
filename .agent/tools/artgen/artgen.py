#!/usr/bin/env python3
"""artgen — 백엔드 중립 게임 그래픽 생성 파이프라인 CLI.

Unity 프로젝트 루트에서 실행한다:
    python .agent/tools/artgen/artgen.py providers
    python .agent/tools/artgen/artgen.py generate design/assets/requests/ASSET-001.json

상세: .agent/tools/artgen/README.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artgen_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
