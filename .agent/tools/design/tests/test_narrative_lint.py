"""narrative_lint 테스트 — cd .agent/tools/design && uv run --no-project --with pytest python -m pytest -q tests/test_narrative_lint.py"""
import json
import os
import sys

import pytest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import narrative_lint as N  # noqa: E402

MIRA = """---
id: VOICE-mira
title: 미라 보이스
type: voice
character: 미라
status: approved
owner: 기획
updated: 2026-10-30
speech_level: 해요체        # 주석
sentence_max: 40
forbidden: [젠장, 짜증]
forbidden_ok_when: [회상]
signature: [그렇죠?]
---
미라는 늘 공손하다.
"""

RULEBOOK = {
    "world_forbidden": [{"term": "총", "reason": "화약 없는 세계", "except": ["총명"]}],
    "timeline": [{"id": "T10", "order": 10, "event": "왕 즉위"}, {"id": "T12", "order": 12, "event": "전쟁"}],
    "facts": [{"after": "T12", "term": "선왕", "reason": "즉위 전에는 '선왕' 표현 불가"}],
    "factions": {"북부": {"hostile": ["남부"]}, "남부": {"hostile": ["북부"]}},
}


def make(tmp_path, dialogue, voices=None, rulebook=RULEBOOK):
    vd = tmp_path / "voices"
    vd.mkdir()
    for name, text in (voices if voices is not None else {"mira.md": MIRA}).items():
        (vd / name).write_text(text, encoding="utf-8")
    dd = tmp_path / "dialogue"
    dd.mkdir()
    (dd / "s1.md").write_text(dialogue, encoding="utf-8")
    args = ["--root", str(tmp_path), "--voices", str(vd), "--dialogue", str(dd)]
    if rulebook is not None:
        rp = tmp_path / "rulebook.json"
        rp.write_text(json.dumps(rulebook, ensure_ascii=False) if isinstance(rulebook, dict) else rulebook,
                      encoding="utf-8")
        args += ["--rulebook", str(rp)]
    return args


def run_check(args):
    ap = N.argparse.Namespace(root=args[args.index("--root") + 1], voices=None, dialogue=None, rulebook=None, json=False)
    i = 0
    while i < len(args):
        k = args[i]
        if k == "--voices":
            ap.voices = args[i + 1]
        elif k == "--rulebook":
            ap.rulebook = args[i + 1]
        elif k == "--dialogue":
            ap.dialogue = [args[i + 1]]
        i += 2
    return N.check(ap)


def rules(findings, sev=None):
    return [f["rule"] for f in findings if sev is None or f["severity"] == sev]


CLEAN = "## 장면 S01 @ T12\n미라: 안녕하세요.\n미라: 선왕께서 그러셨죠?\n"


def test_clean_input_has_no_findings(tmp_path):
    findings, not_run, summary = run_check(make(tmp_path, CLEAN))
    assert findings == []
    assert not_run == []
    assert summary["dialogueLines"] == 2


def test_nl001_forbidden_and_exception_tag(tmp_path):
    d = "## 장면 S01 @ T12\n미라: 젠장, 늦었어요.\n미라 [회상]: 젠장, 그때는 몰랐어요.\n"
    findings, _, _ = run_check(make(tmp_path, d))
    nl1 = [f for f in findings if f["rule"] == "NL001"]
    assert [(f["severity"], f["line"]) for f in nl1] == [("warn", 2), ("info", 3)]
    assert "예외 맥락" in nl1[1]["message"]
    assert nl1[0]["character"] == "미라" and nl1[0]["text"].startswith("젠장")


def test_nl002_length(tmp_path):
    d = "## 장면 S01 @ T12\n미라: " + "가" * 45 + "요.\n"
    findings, _, _ = run_check(make(tmp_path, d))
    assert rules(findings) == ["NL002"]
    assert len(findings[0]["text"]) <= N.TEXT_PREVIEW + 1


def test_nl003_speech_level_with_ratio(tmp_path):
    d = "## 장면 S01 @ T12\n미라: 좋아요.\n미라: 괜찮아요?\n미라: 그만해.\n미라: 아!\n미라: 검.\n"
    findings, _, _ = run_check(make(tmp_path, d))
    nl3 = [f for f in findings if f["rule"] == "NL003"]
    assert len(nl3) == 1 and nl3[0]["line"] == 4
    # 판정 불가(아! · 검.)는 분모에서 빠진다 — 판정 가능 3줄 중 1줄
    assert nl3[0]["judged"] == 3 and nl3[0]["offCount"] == 1


def test_mixed_profile_skips_nl003(tmp_path):
    v = {"mira.md": MIRA.replace("speech_level: 해요체", "speech_level: 혼합")}
    findings, not_run, _ = run_check(make(tmp_path, "## 장면 S01 @ T12\n미라: 그만해.\n", voices=v))
    assert "NL003" not in rules(findings)
    assert any("혼합" in n and "미라" in n for n in not_run)


@pytest.mark.parametrize("sentence, level", [
    ("고마워요.", "해요체"), ("그렇죠?", "해요체"), ("감사합니다.", "하십시오체"), ("가시겠습니까?", "하십시오체"),
    ("앉으십시오.", "하십시오체"), ("고마워.", "해체"), ("이리 와 봐.", "해체"), ("하지 마.", "해체"), ("가자!", "해체"), ("뭐야?", "해체"), ("했다.", "해체"),
    ("아!", None), ("검.", None), ("음…", None), ("OK", None), ("...", None), ("좋아요ㅋㅋ", "해요체"),
])
def test_classify_sentence(sentence, level):
    assert N.classify_sentence(sentence) == level


def test_stats_excludes_unjudgeable(tmp_path):
    args = make(tmp_path, "미라: 좋아요.\n미라: 아!\n미라: 검.\n카이: 가자.\n", rulebook=None)
    ns = N.argparse.Namespace(root=str(tmp_path), voices=args[3], dialogue=[args[5]])
    errs, _, out = N.stats(ns)
    assert errs == []
    assert out["미라"]["levels"] == {"해요체": 1, "하십시오체": 0, "해체": 0, "판정 불가": 2}
    assert out["미라"]["dominantRatio"] == 100
    assert out["카이"]["profile"] is None


def test_nl004_world_forbidden_dialogue_and_narration_with_except(tmp_path):
    d = "## 장면 S01 @ T12\n미라: 총을 버리세요.\n멀리서 총 소리가 난다.\n미라: 총명하시네요.\n"
    findings, _, summary = run_check(make(tmp_path, d))
    nl4 = [f for f in findings if f["rule"] == "NL004"]
    assert [(f["line"], f["character"]) for f in nl4] == [(2, "미라"), (3, None)]
    assert summary["otherLines"] == 1


def test_nl005_timeline(tmp_path):
    d = "## 장면 S01 @ T10\n미라: 선왕께서 오셨어요.\n## 장면 S02 @ T12\n미라: 선왕께서 오셨어요.\n"
    findings, _, _ = run_check(make(tmp_path, d))
    nl5 = [f for f in findings if f["rule"] == "NL005"]
    assert [f["line"] for f in nl5] == [2]


def test_nl005_not_run_without_scene_timeline(tmp_path):
    findings, not_run, _ = run_check(make(tmp_path, "미라: 선왕께서 오셨어요.\n"))
    assert "NL005" not in rules(findings)
    assert any(n.startswith("NL005") for n in not_run)


def test_unknown_scene_timeline_is_input_error(tmp_path):
    findings, _, _ = run_check(make(tmp_path, "## 장면 S01 @ T99\n미라: 안녕하세요.\n"))
    assert rules(findings, "error") == ["INPUT"]


def test_nl006_missing_profile(tmp_path):
    d = "## 장면 S01 @ T12\n카이: 가자.\n카이: 빨리 와.\n"
    findings, not_run, _ = run_check(make(tmp_path, d))
    nl6 = [f for f in findings if f["rule"] == "NL006"]
    assert len(nl6) == 1 and nl6[0]["severity"] == "info" and nl6[0]["character"] == "카이"
    assert any("카이" in n for n in not_run)


def test_nl007_one_sided_hostility(tmp_path):
    rb = dict(RULEBOOK, factions={"북부": {"hostile": ["남부"]}, "남부": {"hostile": []}})
    findings, _, _ = run_check(make(tmp_path, CLEAN, rulebook=rb))
    assert rules(findings) == ["NL007"]
    assert findings[0]["severity"] == "warn"


def test_no_rulebook_names_not_run(tmp_path):
    findings, not_run, _ = run_check(make(tmp_path, "미라: 총을 버리세요.\n", rulebook=None))
    assert "NL004" not in rules(findings)
    assert any("NL004" in n and "NL005" in n and "NL007" in n and "룰북 없음" in n for n in not_run)


def test_no_voices_names_not_run(tmp_path):
    findings, not_run, _ = run_check(make(tmp_path, "## 장면 S01 @ T12\n미라: 젠장.\n", voices={}))
    assert "NL001" not in rules(findings)
    assert any(n.startswith("NL001 · NL002 · NL003") for n in not_run)


def test_comments_and_other_lines_ignored(tmp_path):
    d = "# 주석\n\n## 장면 S01 @ T12\n지문 없이 이어지는 설명\n미라: 안녕하세요.\n"
    findings, _, summary = run_check(make(tmp_path, d))
    assert findings == []
    assert summary["dialogueLines"] == 1 and summary["otherLines"] == 1


@pytest.mark.parametrize("voice, rb", [
    (MIRA.replace("sentence_max: 40", "sentence_max: 많이"), RULEBOOK),
    (MIRA.replace("speech_level: 해요체", "speech_level: 존댓말"), RULEBOOK),
    (MIRA.replace("character: 미라\n", ""), RULEBOOK),
    (MIRA, "{ not json"),
    (MIRA, dict(RULEBOOK, facts=[{"after": "T99", "term": "선왕"}])),
])
def test_input_format_errors_exit_1(tmp_path, voice, rb):
    args = make(tmp_path, CLEAN, voices={"mira.md": voice}, rulebook=rb)
    assert N.main(["check"] + args) == 1


def test_cli_exit_codes_and_json(tmp_path, capsys):
    args = make(tmp_path, "## 장면 S01 @ T12\n미라: 젠장.\n")
    assert N.main(["check"] + args + ["--json"]) == 0  # 의심 후보가 있어도 0
    out = json.loads(capsys.readouterr().out)
    assert [f["rule"] for f in out["findings"]] == ["NL001"]
    assert N.main([]) == 2
    with pytest.raises(SystemExit) as e:
        N.main(["check", "--bogus"])
    assert e.value.code == 2
    assert N.main(["check", "--root", str(tmp_path), "--dialogue", str(tmp_path / "없음")]) == 1


def test_stats_cli_text(tmp_path, capsys):
    args = make(tmp_path, "미라: 좋아요.\n", rulebook=None)
    assert N.main(["stats"] + args) == 0
    assert "미라: 대사 1줄" in capsys.readouterr().out
