# -*- coding: utf-8 -*-
"""新增闸门的自证。每条判据都要有「必须报」与「必须不报」两侧。

规矩 E（PROJECT-SKILL §10）：收窄或新增一条检查而不自证 = 把它关掉。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_reader as br

sys.stdout.reconfigure(encoding="utf-8")

TOTAL = 18


def run():
    ok = 0
    # ── wordcount：剥标签、CJK 按字、拉丁按词、数字成串 ──
    ok += br.wordcount("<b>强化学习</b>") == 4                    # 标签不计
    ok += br.wordcount("importance sampling") == 2                # 拉丁按词
    ok += br.wordcount("γ=0.7737 时") == 2                        # 数字串 1 +「时」1
    ok += br.wordcount({"pts": ["一二", "three"]}) == 3           # 递归进结构
    # ── density：分母是有讲解的页，不是总页数 ──
    notes = [{"r": [1, 2], "one": "一二三四"}, {"r": [5, 5], "one": "五六"}]
    w, p, per = br.density(notes)
    ok += (p == 3)                                                # 1,2,5 三页
    ok += (w == 6 and round(per, 1) == 2.0)

    # ── quote 覆盖率：分母与密度一致（有讲解的页）──
    notes = [{"r": [1, 2], "quote": "x"}, {"r": [3, 3]}, {"r": [4, 4], "quote": "y"}]
    ok += (round(br.field_cover(notes, "quote"), 2) == 0.75)   # 1,2,4 有 / 共 4 页
    ok += (br.field_cover([], "quote") == 0.0)                 # 空不许崩

    # ── tbl 结构：列数必须与表头一致 ──
    ok += (br.check_tbl([{"r": [1, 1], "tbl": {"head": ["a", "b"],
                                               "rows": [["1", "2"]]}}]) == [])
    ok += (len(br.check_tbl([{"r": [1, 1], "tbl": {"head": ["a", "b"],
                                                   "rows": [["1"]]}}])) == 1)

    # ── res：三档标记闭集 + ref 必填 ──
    ok += (br.check_res([{"r": [1, 1], "res": {"tag": "已核", "v": "x",
                                               "ref": "简报 §4a"}}]) == [])
    ok += (len(br.check_res([{"r": [1, 1], "res": {"tag": "大概", "v": "x",
                                                   "ref": "y"}}])) == 1)
    ok += (len(br.check_res([{"r": [1, 1], "res": {"tag": "已核", "v": "x",
                                                   "ref": ""}}])) == 1)

    # ── 防泄题：两层各两侧 ──
    # 第一层：选项里加粗
    ok += (br.check_quiz_leak({"1": [{"o": ["a", "b", "c"], "a": 0}]}) == [])
    ok += (len(br.check_quiz_leak({"1": [{"o": ["a", "<b>b</b>", "c"], "a": 1}]})) == 1)
    # 第二层：答案位置集中。n<8 不判（4 题全在 B 只是巧合），n>=8 且过半才报
    few = {"1": [{"o": ["a", "b", "c"], "a": 1} for _ in range(4)]}
    ok += (br.check_quiz_leak(few) == [])
    many = {"1": [{"o": ["a", "b", "c"], "a": 1} for _ in range(10)]}
    ok += (len(br.check_quiz_leak(many)) == 1)
    # 均匀分布的 12 题必须不报 —— 这一侧防的是「闸门收太紧把正常写法也拦了」
    even = {"1": [{"o": ["a", "b", "c", "d"], "a": i % 4} for i in range(12)]}
    ok += (br.check_quiz_leak(even) == [])

    print("selftest_gates %d/%d" % (ok, TOTAL))
    return ok == TOTAL


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
