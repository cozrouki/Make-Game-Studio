"""어댑터 레지스트리 — providers/*.py 중 PROVIDER_CLASS 를 가진 모듈을 자동 발견."""
import importlib
import os
import pkgutil

from .. import ArtgenError


def discover():
    """{이름: 클래스}"""
    found = {}
    pkg_dir = os.path.dirname(__file__)
    for mod in pkgutil.iter_modules([pkg_dir]):
        if mod.name.startswith("_") or mod.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        cls = getattr(module, "PROVIDER_CLASS", None)
        if cls is not None:
            found[cls.name] = cls
    return found


def create(name, config, request=None):
    classes = discover()
    if name not in classes:
        raise ArtgenError(f"알 수 없는 provider '{name}' (사용 가능: {', '.join(sorted(classes))})")
    options = dict(config.get("providers", {}).get(name, {}))
    if request:
        options.update(request.get("providerOptions", {}).get(name, {}))
    return classes[name](options)
