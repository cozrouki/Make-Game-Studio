#!/usr/bin/env python3
"""
크로스툴 미러 생성기 — 단일 소스 두 곳에서 도구별 파일을 파생한다.

  [룰]  .claude/rules/*.md  (SOURCE OF TRUTH)
      ├─→ .agent/rules/*.md                        Antigravity        (verbatim)
      ├─→ .cursor/rules/*.mdc                      Cursor             (description/globs/alwaysApply)
      ├─→ .github/instructions/*.instructions.md   GitHub Copilot     (applyTo)
      ├─→ .windsurf/rules/*.md                     Windsurf           (trigger: glob | model_decision)
      └─→ AGENTS.md "파일별 규칙 색인" 블록         Codex · OpenCode · Gemini 등 glob 룰이 없는 도구

  [워크플로]  .agent/workflows/*.md  (SOURCE OF TRUTH — 도구 중립 절차)
      ├─→ .cursor/commands/*.md                    Cursor             (/이름)
      ├─→ .gemini/commands/*.toml                  Gemini CLI         (/이름, {{args}})
      ├─→ .opencode/commands/*.md                  OpenCode           (/이름, $ARGUMENTS)
      ├─→ .github/prompts/*.prompt.md              Copilot (VS Code)  (/이름)
      ├─→ .github/skills/*/SKILL.md                Copilot CLI · 코딩 에이전트 (Agent Skills 표준)
      ├─→ .agents/skills/*/SKILL.md                Codex CLI          (Agent Skills 표준)
      └─→ .windsurf/workflows/*.md                 Windsurf           (/이름)

  [포인터]  .github/copilot-instructions.md → AGENTS.md

도구별 파일은 생성물이므로 직접 편집 금지. 룰은 .claude/rules/, 절차는 .agent/workflows/ 만 고치고 다시 실행한다.
워크플로 미러는 정본 절차 파일을 가리키는 얇은 포인터라 절차가 바뀌어도 다시 생성할 필요는 없다
(추가 · 삭제 · description 변경 시에만).

    python scripts/gen-rule-mirrors.py
"""
import glob
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_SRC = os.path.join(ROOT, ".claude", "rules")
WF_SRC = os.path.join(ROOT, ".agent", "workflows")
AGENTS_MD = os.path.join(ROOT, "AGENTS.md")
GEN_NOTE = "생성물: scripts/gen-rule-mirrors.py — 직접 편집 금지"
INDEX_BEGIN = "<!-- BEGIN GENERATED: rules-index (scripts/gen-rule-mirrors.py) -->"
INDEX_END = "<!-- END GENERATED: rules-index -->"


def write(rel, text):
    path = os.path.join(ROOT, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def parse_rule(path):
    """frontmatter 의 globs:/paths: (inline 또는 block list) 와 첫 H1 을 추출."""
    text = open(path, encoding="utf-8").read()
    body, globs = text, []
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if m:
        fmtext, body = m.group(1), m.group(2)
        inline = re.search(r'^(?:globs|paths)\s*:\s*\[(.*?)\]', fmtext, re.M)
        if inline:
            globs = [x.strip().strip('"\'') for x in inline.group(1).split(",") if x.strip()]
        else:
            key = re.search(r'^(globs|paths)\s*:\s*$', fmtext, re.M)
            if key:
                for line in fmtext[key.end():].splitlines():
                    lm = re.match(r'\s*-\s*"?([^"\n]+?)"?\s*$', line)
                    if lm:
                        globs.append(lm.group(1).strip())
                    elif line.strip() and not line.startswith((' ', '\t', '-')):
                        break
    h1 = re.search(r'^#\s+(.+)$', body, re.M)
    desc = h1.group(1).strip() if h1 else os.path.basename(path)[:-3]
    return desc, globs, body.lstrip("\n")


def parse_workflow(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    desc = ""
    if m:
        dm = re.search(r"^description\s*:\s*(.+)$", m.group(1), re.M)
        desc = dm.group(1).strip() if dm else ""
    return desc or os.path.basename(path)[:-3]


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- 룰
def gen_rules():
    rows, count = [], 0
    for src in sorted(glob.glob(os.path.join(RULES_SRC, "*.md"))):
        name = os.path.basename(src)[:-3]
        desc, globs, body = parse_rule(src)

        shutil.copyfile(src, os.path.join(ROOT, ".agent", "rules", name + ".md"))

        fm = ["---", f"description: {desc}"]
        if globs:
            fm.append("globs: " + ", ".join(globs))
        fm += ["alwaysApply: false", "---"]
        write(f".cursor/rules/{name}.mdc", "\n".join(fm) + "\n" + body)

        apply_to = ",".join(globs) if globs else "**"
        write(f".github/instructions/{name}.instructions.md",
              f"---\napplyTo: {yaml_str(apply_to)}\ndescription: {yaml_str(desc)}\n---\n<!-- {GEN_NOTE} · 정본: .claude/rules/{name}.md -->\n\n{body}")

        if globs:
            wfm = f"---\ntrigger: glob\nglobs: {', '.join(globs)}\ndescription: {desc}\n---\n"
        else:
            wfm = f"---\ntrigger: model_decision\ndescription: {desc}\n---\n"
        write(f".windsurf/rules/{name}.md", wfm + f"<!-- {GEN_NOTE} · 정본: .claude/rules/{name}.md -->\n\n{body}")

        rows.append((name, desc, globs))
        count += 1
    return rows, count


def gen_agents_index(rows):
    lines = [INDEX_BEGIN,
             "",
             "> 파일별 자동 적용 룰이 없는 도구(Codex · OpenCode · Gemini CLI 등)는 **아래 경로의 파일을 만들거나 고치기 전에 해당 룰 파일을 읽는다.**",
             "> Claude Code · Cursor · Copilot · Windsurf · Antigravity 는 각자의 룰 미러로 자동 적용된다.",
             "",
             "| 룰 | 적용 경로 | 파일 |",
             "|---|---|---|"]
    for name, desc, globs in rows:
        where = " · ".join(f"`{g}`" for g in globs) if globs else "(경로 무관 — 해당 작업 시)"
        lines.append(f"| {desc} | {where} | `.agent/rules/{name}.md` |")
    lines += ["", INDEX_END]
    block = "\n".join(lines)

    text = open(AGENTS_MD, encoding="utf-8").read()
    if INDEX_BEGIN in text:
        text = re.sub(re.escape(INDEX_BEGIN) + r".*?" + re.escape(INDEX_END), lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n---\n\n## §8. 파일별 규칙 색인\n\n" + block + "\n"
    with open(AGENTS_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------------------------------------------------------------- 워크플로 → 명령 · 스킬
def pointer_body(name, desc, args_line):
    return (f"# /{name}\n\n{desc}\n\n"
            f"**정본 절차: `.agent/workflows/{name}.md` — 이 파일을 먼저 읽고 그 절차를 그대로 따른다.**\n"
            f"절차가 `.claude/skills/<이름>/SKILL.md` 를 가리키면 그 파일도 읽고 따른다 (이 도구에서 슬래시로 호출할 수 없는 스킬).\n"
            f"페르소나 · 표준은 `AGENTS.md` 를 따른다.\n\n{args_line}\n")


def gen_workflows():
    count = 0
    for src in sorted(glob.glob(os.path.join(WF_SRC, "*.md"))):
        name = os.path.basename(src)[:-3]
        desc = parse_workflow(src)
        note = f"<!-- {GEN_NOTE} · 정본: .agent/workflows/{name}.md -->\n\n"

        write(f".cursor/commands/{name}.md", note + pointer_body(name, desc, "인수: 명령 뒤에 입력한 텍스트."))

        prompt = pointer_body(name, desc, "인수: {{args}}")
        write(f".gemini/commands/{name}.toml",
              f"# {GEN_NOTE} · 정본: .agent/workflows/{name}.md\ndescription = {toml_str(desc)}\nprompt = \"\"\"\n{prompt}\"\"\"\n")

        write(f".opencode/commands/{name}.md",
              f"---\ndescription: {yaml_str(desc)}\n---\n" + note + pointer_body(name, desc, "인수: $ARGUMENTS"))

        write(f".github/prompts/{name}.prompt.md",
              f"---\ndescription: {yaml_str(desc)}\nmode: agent\n---\n" + note
              + pointer_body(name, desc, "인수: ${input:args:인수 (없으면 비움)}"))

        skill = (f"---\nname: {name}\ndescription: {yaml_str(desc)}\n---\n" + note
                 + pointer_body(name, desc, "인수: 사용자가 요청과 함께 준 값."))
        write(f".github/skills/{name}/SKILL.md", skill)
        write(f".agents/skills/{name}/SKILL.md", skill)

        write(f".windsurf/workflows/{name}.md",
              f"---\ndescription: {desc}\n---\n" + note + pointer_body(name, desc, "인수: 워크플로 호출과 함께 입력한 텍스트."))
        count += 1
    return count


def gen_pointers():
    write(".github/copilot-instructions.md",
          f"<!-- {GEN_NOTE} -->\n"
          "# 저장소 지침\n\n"
          "정본은 [AGENTS.md](../AGENTS.md) 다 — 페르소나 · 아키텍처 표준 · 문서 규칙을 그대로 따른다.\n"
          "항상 한국어로 설명하고 문서도 한국어로 쓴다.\n"
          "경로별 룰은 `.github/instructions/` 에 자동 적용된다. 슬래시 절차는 `.github/prompts/`(VS Code) · `.github/skills/`(CLI).\n")


def main():
    rows, n_rules = gen_rules()
    gen_agents_index(rows)
    n_wf = gen_workflows()
    gen_pointers()
    print(f"룰 {n_rules}개 → .agent/rules · .cursor/rules · .github/instructions · .windsurf/rules + AGENTS.md 색인")
    print(f"워크플로 {n_wf}개 → .cursor/commands · .gemini/commands · .opencode/commands · .github/prompts · "
          f".github/skills · .agents/skills · .windsurf/workflows")


if __name__ == "__main__":
    main()
