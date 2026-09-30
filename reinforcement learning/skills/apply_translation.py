# -*- coding: utf-8 -*-
"""把并行翻译的英文段落装配回 SKILL.md / explainer-arc.md。

翻译由 5 个 agent 分段完成，每段返回 (行区间, 原文首行, 原文末行, 英文)。
这里只做装配：
  · 按行区间从后往前替换，避免行号漂移；
  · **用返回的「原文首行/末行」核对锚点** —— 对不上就整体中止，
    否则一处错位会把整份文档搅乱且很难发现；
  · 全部核对通过才写盘。

用法：
    python apply_translation.py            # 空跑
    python apply_translation.py --apply    # 写盘
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = ("C:/Users/donot/.claude/projects/G--open-course-reinforcement-learning/"
           "fd46a8a5-42d8-43fa-a757-cb496077b688/subagents/workflows/"
           "wf_5275e095-6f9/journal.jsonl")

DASH = re.compile(r"[–—-]")          # en dash / em dash / hyphen 都当区间分隔符


def load_blocks():
    """从 journal 里取出全部翻译块，按目标文件归类。"""
    out = {"SKILL.md": [], "explainer-arc.md": []}
    seen = set()
    for line in io.open(JOURNAL, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") != "result":
            continue
        r = o.get("result")
        if not isinstance(r, dict) or "blocks" not in r:
            continue
        unit = r.get("unit", "")
        target = "explainer-arc.md" if "explainer-arc" in unit else "SKILL.md"
        for b in r["blocks"]:
            key = (target, b.get("range"))
            if key in seen:
                continue
            seen.add(key)
            out[target].append(b)
    return out


def parse_range(s):
    parts = [p for p in DASH.split(str(s).strip()) if p.strip().isdigit()]
    if len(parts) == 1:
        return int(parts[0]), int(parts[0])
    return int(parts[0]), int(parts[1])


def norm(s):
    """归一化后比对锚点：去空白、去 Markdown 强调符，避免因排版差异误判。"""
    return re.sub(r"[\s*`_>#-]", "", (s or ""))[:24]


def check_and_apply(fname, blocks, dry):
    path = os.path.join(HERE, fname)
    L = io.open(path, encoding="utf-8").read().split("\n")
    n0 = len(L)
    rows = []
    for b in blocks:
        a, z = parse_range(b["range"])
        rows.append((a, z, b))
    rows.sort(key=lambda t: -t[0])          # 从后往前

    print("── %s（%d 行，%d 个翻译块）" % (fname, n0, len(rows)))
    ok = True
    for a, z, b in rows:
        if a < 1 or z > len(L):
            print("   ✗ 区间 %s 越界" % b["range"])
            ok = False
            continue
        got_first, got_last = L[a - 1], L[z - 1]
        exp_first, exp_last = b.get("first_line_zh", ""), b.get("last_line_zh", "")
        m1 = norm(got_first).startswith(norm(exp_first)[:14]) or norm(exp_first)[:14] in norm(got_first)
        m2 = norm(got_last).startswith(norm(exp_last)[:14]) or norm(exp_last)[:14] in norm(got_last)
        flag = "" if (m1 and m2) else "   ✗ 锚点对不上"
        if not (m1 and m2):
            ok = False
        print("   %-9s 行%-9s %s" % (b["range"], "", flag or "锚点 OK"))
        if not (m1 and m2):
            print("        期望首行: %s" % exp_first[:60])
            print("        实际首行: %s" % got_first[:60])
            print("        期望末行: %s" % exp_last[:60])
            print("        实际末行: %s" % got_last[:60])
    if not ok:
        print("   锚点校验失败，不写盘。")
        return False
    if dry:
        return True
    for a, z, b in rows:
        L[a - 1:z] = b["english"].rstrip("\n").split("\n")
    io.open(path, "w", encoding="utf-8").write("\n".join(L))
    print("   ✓ 已写盘：%d 行 → %d 行" % (n0, len("\n".join(L).split("\n"))))
    return True


def main():
    dry = "--apply" not in sys.argv
    groups = load_blocks()
    allok = True
    for fname, blocks in groups.items():
        if not blocks:
            print("── %s：没有翻译块" % fname)
            continue
        if not check_and_apply(fname, blocks, dry):
            allok = False
        print()
    print("（空跑。加 --apply 写盘）" if dry else ("完成。" if allok else "有失败项。"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
