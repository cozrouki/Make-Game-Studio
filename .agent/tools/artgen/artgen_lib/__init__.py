"""artgen 라이브러리 — 요청 검증 · 프롬프트 컴파일 · 백엔드 어댑터 · 버전 저장소 · Unity 승격."""
import os

SCHEMA_ID = "artgen-request/1"
# .agent/tools/artgen/
TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ArtgenError(Exception):
    """사용자에게 그대로 보여 줄 수 있는 오류 (CLI 가 exit 1 로 변환)."""
