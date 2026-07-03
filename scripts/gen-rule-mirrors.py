#!/usr/bin/env python3
"""
룰 미러 생성기 — 단일 소스(.claude/rules/*.md)에서 크로스툴 룰을 파생한다.

  .claude/rules/*.md   (SOURCE OF TRUTH)
      ├─→ .agent/rules/*.md    (Antigravity — verbatim 복사, plain markdown)
      └─→ .cursor/rules/*.mdc  (Cursor — frontmatter 변환: description/globs/alwaysApply)

룰을 수정할 때는 반드시 .claude/rules/ 를 고치고 이 스크립트를 다시 실행한다.
.agent/rules/ 와 .cursor/rules/ 는 생성물이므로 직접 편집 금지.

    python scripts/gen-rule-mirrors.py
"""
import os, re, glob, shutil

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, ".claude", "rules")
AG_DIR  = os.path.join(ROOT, ".agent", "rules")
CU_DIR  = os.path.join(ROOT, ".cursor", "rules")
os.makedirs(AG_DIR, exist_ok=True)
os.makedirs(CU_DIR, exist_ok=True)


def parse(path):
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
    return desc, globs, body


def main():
    count = 0
    for src in sorted(glob.glob(os.path.join(SRC_DIR, "*.md"))):
        name = os.path.basename(src)[:-3]
        desc, globs, body = parse(src)

        # Antigravity: verbatim
        shutil.copyfile(src, os.path.join(AG_DIR, name + ".md"))

        # Cursor: .mdc with converted frontmatter
        fm = ["---", f"description: {desc}"]
        if globs:
            fm.append("globs: " + ", ".join(globs))
        fm.append("alwaysApply: false")
        fm.append("---")
        mdc = "\n".join(fm) + "\n" + body.lstrip("\n")
        with open(os.path.join(CU_DIR, name + ".mdc"), "w", encoding="utf-8", newline="\n") as f:
            f.write(mdc)
        count += 1

    print(f"Generated {count} rules -> .agent/rules/ (md) + .cursor/rules/ (mdc)")


if __name__ == "__main__":
    main()
