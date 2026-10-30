"""업그레이드 — 프레임워크 자산(상류 GS 스킬 · 에이전트 · scripts · 엔진 레퍼런스 · 훅 등록) · 엔진 필터 · 씨앗 · 정리 테스트."""
import json
import os
import shutil
import subprocess
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import studio as S  # noqa: E402
import studio_maint as M  # noqa: E402


def _touch(root, rel, text="x"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _read(root, rel):
    with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as f:
        return f.read()


def _git(root, *args):
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True)


def _init(root):
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                 ["config", "core.autocrlf", "false"]):
        _git(root, *args)


TEMPLATE_CLAUDE = """# persona

## Technology Stack

- **Engine**: [CHOOSE]

## Engine Version Reference

<!-- ENGINE-REFERENCE-IMPORT -->
@docs/engine-reference/unity/VERSION.md

## 상류 GS 기준 문서 (필요할 때 읽는다)

- 조정 규칙: `.claude/docs/coordination-rules.md`

---

## §7. 세션 시작
"""

TEMPLATE_SETTINGS = {
    "permissions": {"deny": ["Bash(rm -rf *)", "Edit(**/*.uasset)"]},
    "hooks": {
        "PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": "bash .claude/hooks/validate-read.sh",
                                                      "timeout": 10}]}],
        "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "bash .claude/hooks/studio-pause-notice.sh"}]}],
    },
}


@pytest.fixture
def template(tmp_path):
    root = str(tmp_path / "template")
    os.makedirs(root)
    _init(root)
    shutil.copytree(TOOL_DIR, os.path.join(root, ".agent", "tools", "studio"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests", "*.local.json"))
    files = {
        ".agent/VERSION": "1.1.0\n",
        ".claude/skills/design-review/SKILL.md": "---\nname: design-review\n---\n",
        ".claude/skills/sf-add/SKILL.md": "---\nname: sf-add\n---\n",
        ".claude/agents/godot-specialist.md": "godot\n",
        ".claude/scripts/test-run.sh": "#!/bin/bash\n",
        ".claude/docs/coordination-rules.md": "rules\n",
        ".claude/docs/technical-preferences.md": "- **Engine**: [TO BE CONFIGURED]\n",
        ".claude/rules/gameplay-code.md": "# 공통 + 엔진 절\n",
        ".claude/hooks/validate-read.sh": "#!/bin/bash\n",
        ".claude/hooks/studio-pause-notice.sh": "#!/bin/bash\n",
        "docs/engine-reference/README.md": "refs\n",
        "docs/engine-reference/godot/VERSION.md": "Godot 4.7\n",
        "docs/engine-reference/unity/VERSION.md": "Unity 6.3\n",
        "project.yaml": "schema_version: 1\n",
        "design/registry/entities.yaml": "entities: []\n",
        "src/CLAUDE.md": "godot src\n",
        "CLAUDE.md": TEMPLATE_CLAUDE,
        ".claude/settings.json": json.dumps(TEMPLATE_SETTINGS),
    }
    for rel, text in files.items():
        _touch(root, rel, text)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "template")
    _touch(root, ".claude/skills/junk-untracked.txt", "local junk")   # git 추적 밖 — 가져오면 안 된다
    return root


def _project(tmp_path, name, marker):
    root = str(tmp_path / name)
    os.makedirs(root)
    _init(root)
    shutil.copytree(TOOL_DIR, os.path.join(root, ".agent", "tools", "studio"),
                    ignore=shutil.ignore_patterns("__pycache__", "tests"))
    _touch(root, *marker)
    _touch(root, "CLAUDE.md", "# persona\n\n## Technology Stack\n\n- **Engine**: Godot 4.7\n\n---\n\n## §7. 세션 시작\n")
    _touch(root, ".claude/docs/technical-preferences.md", "- **Engine**: Godot 4.7  # 프로젝트 값\n")
    _touch(root, ".claude/rules/gameplay-code.md", "# 예전 Unity 전용 규칙 — MyGame.Gameplay\n")
    _touch(root, ".claude/docs/gs-coding-standards.md", "old\n")
    _touch(root, ".claude/hooks/post-compact.sh", "#!/bin/bash\n")
    _touch(root, ".claude/settings.json", json.dumps({
        "permissions": {"deny": ["Bash(rm -rf *)"]},
        "hooks": {"PostCompact": [{"matcher": "", "hooks": [{"type": "command", "command": "bash .claude/hooks/post-compact.sh"}]}],
                  "PostToolUse": [{"matcher": "", "hooks": [{"type": "command",
                                                             "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/studio-pause-notice.sh\""}]}]}}))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "proj")
    return S.Studio(root, S.load_config(os.path.join(root, ".agent", "tools", "studio")))


def test_godot_project_gets_framework_assets_filtered_by_engine(tmp_path, template):
    st = _project(tmp_path, "godot", ("project.godot", "config_version=5\n"))
    plan = M.upgrade(st, template)
    added = set(plan["add"])
    for rel in (".claude/skills/design-review/SKILL.md", ".claude/agents/godot-specialist.md", ".claude/scripts/test-run.sh",
                ".claude/docs/coordination-rules.md", ".claude/hooks/validate-read.sh", "docs/engine-reference/godot/VERSION.md",
                "docs/engine-reference/README.md", "src/CLAUDE.md", ".agent/VERSION"):
        assert rel in added, rel
    for rel in (".claude/skills/sf-add/SKILL.md", "docs/engine-reference/unity/VERSION.md", ".claude/skills/junk-untracked.txt"):
        assert rel not in added and not os.path.exists(os.path.join(st.root, rel)), rel
    assert plan["engine"] == "godot" and plan["templateVersion"] == "1.1.0"
    assert any("sf-add" in s for s in plan["skippedByEngine"])


def test_project_data_is_seeded_or_kept_and_forks_are_listed(tmp_path, template):
    st = _project(tmp_path, "godot", ("project.godot", "config_version=5\n"))
    _touch(st.root, "design/registry/entities.yaml", "entities: [mine]\n")
    plan = M.upgrade(st, template)
    assert "project.yaml" in plan["seed"] and _read(st.root, "project.yaml") == "schema_version: 1\n"
    assert "design/registry/entities.yaml" not in plan["seed"]
    assert _read(st.root, "design/registry/entities.yaml") == "entities: [mine]\n"       # 프로젝트 데이터 보존
    assert "프로젝트 값" in _read(st.root, ".claude/docs/technical-preferences.md")          # 덮어쓰지 않음
    assert ".claude/rules/gameplay-code.md" in plan["manual"]                              # 템플릿과 달라 직접 병합 안내
    assert "예전 Unity" in _read(st.root, ".claude/rules/gameplay-code.md")


def test_hooks_permissions_obsolete_and_claude_sections(tmp_path, template):
    st = _project(tmp_path, "godot", ("project.godot", "config_version=5\n"))
    plan = M.upgrade(st, template)
    settings = json.loads(_read(st.root, ".claude/settings.json"))
    cmds = [h["command"] for es in settings["hooks"].values() for e in es for h in e["hooks"]]
    assert "bash .claude/hooks/validate-read.sh" in cmds
    assert sum("studio-pause-notice.sh" in c for c in cmds) == 1          # 다른 표기로 이미 있으면 더하지 않는다
    assert not any("post-compact.sh" in c for c in cmds)                  # 사라진 훅의 등록은 지운다
    assert "Edit(**/*.uasset)" in settings["permissions"]["deny"]
    assert not os.path.exists(os.path.join(st.root, ".claude", "docs", "gs-coding-standards.md"))
    assert not os.path.exists(os.path.join(st.root, ".claude", "hooks", "post-compact.sh"))
    assert set(plan["obsolete"]) == {".claude/docs/gs-coding-standards.md", ".claude/hooks/post-compact.sh"}
    claude = _read(st.root, "CLAUDE.md")
    assert claude.index("## Engine Version Reference") < claude.index("## 상류 GS 기준 문서") < claude.index("## §7.")
    assert "@docs/engine-reference/godot/VERSION.md" in claude and "unity/VERSION.md" not in claude
    assert "- **Engine**: Godot 4.7" in claude                            # 프로젝트 절은 그대로


def test_second_upgrade_has_nothing_to_do(tmp_path, template):
    st = _project(tmp_path, "godot", ("project.godot", "config_version=5\n"))
    M.upgrade(st, template)
    again = M.upgrade(st, template, dry_run=True)
    assert again["add"] == [] and again["replace"] == [] and again["seed"] == [] and again["obsolete"] == []
    assert not [m for m in again["merge"] if m["file"] in (".claude/settings.json", "CLAUDE.md")]


def test_unity_project_keeps_unity_layers(tmp_path, template):
    st = _project(tmp_path, "unity", ("ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 6000.3.1f1\n"))
    plan = M.upgrade(st, template)
    assert ".claude/skills/sf-add/SKILL.md" in plan["add"]
    assert "docs/engine-reference/unity/VERSION.md" in plan["add"]
    assert "src/CLAUDE.md" not in plan["add"]
    assert "@docs/engine-reference/unity/VERSION.md" in _read(st.root, "CLAUDE.md")
