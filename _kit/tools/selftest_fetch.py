# -*- coding: utf-8 -*-
"""抓字幕的自证。必须 4/4。

规矩 E（PROJECT-SKILL §10）：新增一条检查必须两侧都验 —— 已知坏样本必须报，
已知好样本必须不报。

坏样本用的是**真实撞车数据**：CS224R 播放列表第 18、19 个的真实标题。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL = 4

# 与 fetch_subs.main() 里同一套标签推导逻辑。抽出来单测，是因为 main()
# 从头到尾要跑 yt-dlp，没法在自证里调。
# ⚠ 两边改一处就要改另一处 —— 下面第 4 条判据就是防这个的。
def tags(rows, prefix="L", pat=r"Lecture[ ]+([0-9]+)"):
    out, seen = [], {}
    for idx, title in rows:
        num = idx
        m = re.search(pat, title)
        if m:
            num = m.group(1)
        tag = "%s%02d" % (prefix, int(num))
        if tag in seen:
            raise ValueError("标签撞车：%s 同时来自 %r 和 %r" % (tag, seen[tag], title))
        seen[tag] = title
        out.append(tag)
    return out


def run():
    ok = 0

    # ── 必须报：CS224R 的真实撞车 ──
    bad_rows = [
        (18, "Stanford CS224R Deep Reinforcement Learning | Spring 2025 | "
             "Tutorial Session: Review of Q-Learning"),
        (19, "Stanford CS224R Deep Reinforcement Learning | Spring 2025 | "
             "Lecture 18: Frontiers"),
    ]
    try:
        tags(bad_rows)
        ok += 0          # 没报 = 这条判据是废的
        print("  ✗ 真实撞车没有被拦下")
    except ValueError:
        ok += 1

    # ── 必须不报：正常的播放列表 ──
    good_rows = [(i, "… | Lecture %d: X" % i) for i in range(1, 19)]
    try:
        t = tags(good_rows)
        ok += (t[0] == "L01" and t[-1] == "L18" and len(set(t)) == 18)
    except ValueError:
        print("  ✗ 正常播放列表被误报")

    # ── 必须不报：撞车的那个给了自己的标签就没事 ──
    try:
        t1 = tags([bad_rows[1]])                      # Lecture 18 → L18
        t2 = tags([(99, bad_rows[0][1])], prefix="LTUT_")  # 教程另给标签
        ok += (t1 == ["L18"] and len(t2) == 1)
    except ValueError:
        print("  ✗ 分开抓仍然被误报")

    # ── 守卫真的在 fetch_subs.py 里，不只是在这个自证里 ──
    src = io.open(os.path.join(HERE, "fetch_subs.py"), encoding="utf-8").read()
    ok += ("标签撞车" in src and "seen[tag] = title" in src)

    return ok


if __name__ == "__main__":
    n = run()
    print("selftest_fetch %d/%d" % (n, TOTAL))
    sys.exit(0 if n == TOTAL else 1)
