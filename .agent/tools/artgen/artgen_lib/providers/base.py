"""백엔드 어댑터 계약.

새 백엔드 추가 = providers/<이름>.py 하나 작성 + 모듈 끝에 `PROVIDER_CLASS = <클래스>`.
`_template.py` 를 복사해서 시작한다. 레지스트리가 자동 발견한다 (이름이 `_` 로 시작하는 파일은 제외).
"""
from dataclasses import dataclass, field


@dataclass
class Job:
    """어댑터가 받는 1회 생성 작업. 경로는 모두 절대경로."""
    asset_id: str
    request: dict              # 정규화된 artgen-request/1 전체
    positive: str              # compile_prompt() 결과
    negative: str
    width: int
    height: int
    transparent: bool
    variants: int
    seeds: list                # 길이 = variants
    references: list           # 참조 이미지 절대경로
    out_dir: str               # 결과 PNG 를 쓸 디렉터리 (이미 생성됨)
    job_file: str              # 이 Job 을 JSON 으로 직렬화한 파일 (외부 프로세스 전달용)
    options: dict = field(default_factory=dict)  # config.providers[이름] ← request.providerOptions[이름]
    project_root: str = ""     # Unity 프로젝트 루트 (설정의 상대경로 해석용)


class Provider:
    """모든 백엔드 어댑터의 기반 클래스."""

    name = "base"
    description = ""
    # 백엔드가 직접 지원하는 기능 — 스킬이 요청을 만들 때 참고한다
    capabilities = {"transparent": False, "references": False, "seed": False}
    # True 면 결과가 자리표시 이미지 — 검수 단계는 시각 평가를 건너뛰고 기술 검사만 한다
    placeholder = False
    # False 면 결과 수가 요청 variants 와 달라도 경고하지 않는다 (사람 납품처럼 개수가 정해지지 않는 경우)
    honors_variants = True

    def __init__(self, options):
        self.options = options or {}

    def check(self):
        """(사용 가능 여부, 메시지). 네트워크 호출 없이 설정만 점검하는 것을 권장."""
        return True, "ok"

    def generate(self, job):
        """job.out_dir 에 PNG 를 쓰고 그 절대경로 목록을 돌려준다 (순서 = 변형 순서)."""
        raise NotImplementedError
