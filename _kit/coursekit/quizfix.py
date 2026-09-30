# -*- coding: utf-8 -*-
"""放映厅选择题的防泄题处理：① 选项里不许出现加粗 ② 正确答案位置打散。

⚠ 2026-09-28：逐页精读里犯过一次（50 题全加粗、48 题答案在 B，用户当场发现）。
放映厅的片子当时没查，结果一模一样地中招（T1 24/24 加粗、23/24 在 B；T2 22/22 全中）。
两条防线合并在这里，build_m2t*.py 的 KP() 统一调用，以后新片子照抄即可。
"""
import random, re

BOLD = re.compile(r"</?b>")
SEED = 20261012

# 位置相关的选项（「以上皆是」之类）打散会变得不通，命中就保持原序并报告
POSITIONAL = ("以上皆", "以上都", "上述都", "上述皆", "以上全部", "A 和 B", "A、B 都", "前两项")

_report = {"bold": 0, "skipped": [], "pos": {}}


def fix_quiz(q, key):
    """返回处理后的 quiz 副本；key（知识点序号）用来生成稳定的每题种子。"""
    raw = q["o"]
    opts = [BOLD.sub("", o) for o in raw]
    _report["bold"] += sum(1 for a, b in zip(raw, opts) if a != b)

    idx = list(range(len(opts)))
    if any(p in o for o in opts for p in POSITIONAL):
        _report["skipped"].append(key)          # 保持原序
    else:
        random.Random(SEED * 1000 + key).shuffle(idx)

    out = dict(q)
    out["o"] = [opts[i] for i in idx]
    out["a"] = idx.index(q["a"])                # 按下标搬运，重复文本也不会搬错
    _report["pos"][out["a"]] = _report["pos"].get(out["a"], 0) + 1
    return out


def report():
    d = _report["pos"]
    return "防泄题：清掉加粗 %d 处；答案位置 A/B/C/D = %s；未打散（位置相关选项）%s" % (
        _report["bold"],
        "/".join(str(d.get(i, 0)) for i in range(4)),
        _report["skipped"] or "无",
    )
