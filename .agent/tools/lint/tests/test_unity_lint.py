"""unity_lint 테스트 — python -m pytest .agent/tools/lint/tests -q"""
import os
import subprocess
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import unity_lint as L  # noqa: E402


def _rules(src, path="Assets/Game/Scripts/X.cs"):
    return [(f["rule"], f["line"]) for f in L.lint_source(src, path)]


def _mb(body, header="", fields=""):
    return f"using UnityEngine;\n{header}\npublic class X : MonoBehaviour\n{{\n{fields}\n    void Update()\n    {{\n{body}\n    }}\n}}\n"


@pytest.mark.parametrize("body, rule", [
    ("        var a = list.Where(x => x > 0).ToList();", "UL001"),
    ("        var l = new List<int>();", "UL002"),
    ("        var arr = new float[16];", "UL002"),
    ("        yield return new WaitForSeconds(1f);", "UL002"),
    ("        label.text = $\"score {score}\";", "UL003"),
    ("        label.text = \"score \" + score;", "UL003"),
    ("        label.text = score.ToString();", "UL003"),
    ("        var rb = GetComponent<Rigidbody>();", "UL004"),
    ("        var cam = Camera.main;", "UL004"),
    ("        var p = FindFirstObjectByType<Player>();", "UL004"),
    ("        rb.AddForce(Vector3.up);", "UL006"),
    ("        rb.linearVelocity = Vector3.zero;", "UL006"),
    ("        Debug.Log(\"tick\");", "UL008"),
])
def test_unity_lint_hot_path_rule_detected(body, rule):
    src = _mb(body, header="using System.Linq;\nusing System.Collections.Generic;")
    assert rule in [r for r, _ in _rules(src)]


@pytest.mark.parametrize("body", [
    "        if (_animator == null) _animator = GetComponentInChildren<Animator>();",   # 지연 초기화
    "        _cam ??= Camera.main;",
    "        var d = hit.collider.GetComponentInParent<IDamageable>();",                # 충돌 결과 대상
    "        const string help = \"a\" + \"b\";",                                       # 리터럴끼리 + 는 컴파일 때 합쳐짐
    "        var v = Mathf.Max(a, b);",                                                 # Mathf.Max 는 LINQ 아님
    "        var p = new Vector3(1, 2, 3);",                                            # 구조체 생성은 할당 아님
    "        // var l = new List<int>(); GetComponent<X>(); $\"x{y}\"",                 # 주석
    "        var s = \"GetComponent<X>() new List<int>()\";",                           # 문자열 안
])
def test_unity_lint_known_false_positives_are_not_reported(body):
    src = _mb(body, header="using System.Linq;\nusing System.Collections.Generic;")
    assert _rules(src) == [], _rules(src)


def test_unity_lint_rules_apply_only_inside_hot_methods():
    src = ("using UnityEngine;\npublic class X : MonoBehaviour\n{\n    void Start()\n    {\n"
           "        var rb = GetComponent<Rigidbody>(); var l = new System.Collections.Generic.List<int>();\n    }\n}\n")
    assert _rules(src) == []


def test_unity_lint_fixedupdate_allows_rigidbody():
    src = "public class X : MonoBehaviour\n{\n    void FixedUpdate()\n    {\n        rb.AddForce(f);\n    }\n}\n"
    assert _rules(src) == []


def test_unity_lint_linq_requires_using_directive():
    src = _mb("        var a = list.Where(x => x > 0);")
    assert "UL001" not in [r for r, _ in _rules(src)]


def test_unity_lint_debug_log_counted_once_not_as_string_too():
    src = _mb("        Debug.Log($\"pos {transform.position}\" +\n            \" more\");")
    assert [r for r, _ in _rules(src)] == ["UL008"]


def test_unity_lint_animator_and_material_string_params_anywhere():
    src = ("public class X : MonoBehaviour\n{\n    void Start()\n    {\n        anim.SetBool(\"Run\", true);\n"
           "        block.SetFloat(\"_Dissolve\", 1f);\n        anim.SetBool(RunHash, true);\n    }\n}\n")
    assert _rules(src) == [("UL005", 5), ("UL005", 6)]


def test_unity_lint_public_tuning_field_in_monobehaviour_only():
    src = ("public class X : MonoBehaviour\n{\n    public float speed = 6f;\n    public const int Max = 3;\n"
           "    [SerializeField] private float _jump = 2f;\n    public static int Count;\n}\n"
           "public class Plain\n{\n}\n")
    assert _rules(src) == [("UL007", 3)]
    assert _rules("public class Plain\n{\n    public float speed = 6f;\n}\n") == []


def test_unity_lint_editor_code_skips_hot_path_rules():
    body = "        var l = new List<int>(); Debug.Log(\"x\");"
    assert _rules(_mb(body), "Assets/Game/Editor/Tool.cs") == []
    editor_class = "using UnityEditor;\npublic class W : EditorWindow\n{\n    void OnGUI()\n    {\n" + body + "\n    }\n}\n"
    assert _rules(editor_class) == []


def test_unity_lint_ignore_comment_on_same_or_previous_line():
    src = _mb("        // unity-lint: ignore UL004\n        var rb = GetComponent<Rigidbody>();\n"
              "        var c = Camera.main; // unity-lint: ignore UL004")
    assert _rules(src) == []


def test_unity_lint_blocking_rules_from_config(tmp_path):
    f = tmp_path / "Assets" / "X.cs"
    f.parent.mkdir()
    f.write_text(_mb("        var rb = GetComponent<Rigidbody>();\n        Debug.Log(\"x\");"), encoding="utf-8")
    r = L.run(["Assets"], str(tmp_path), {"blocking": ["UL004"], "disabled": [], "exclude": []})
    assert [x["rule"] for x in r["blocking"]] == ["UL004"]
    assert {x["rule"] for x in r["findings"]} == {"UL004", "UL008"}
    r = L.run(["Assets"], str(tmp_path), {"blocking": [], "disabled": ["UL008"], "exclude": ["Assets/**"]})
    assert r["files"] == 0


def test_unity_lint_cli_exit_code_follows_blocking(tmp_path):
    f = tmp_path / "Assets" / "X.cs"
    f.parent.mkdir()
    f.write_text(_mb("        var rb = GetComponent<Rigidbody>();"), encoding="utf-8")
    script = os.path.join(TOOL_DIR, "unity_lint.py")
    ok = subprocess.run([sys.executable, script, "--root", str(tmp_path), "Assets"], capture_output=True, text=True)
    strict = subprocess.run([sys.executable, script, "--root", str(tmp_path), "--strict", "Assets"],
                            capture_output=True, text=True)
    assert ok.returncode == 0 and "UL004" in ok.stdout          # 기본 설정은 경고만
    assert strict.returncode == 1
