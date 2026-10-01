# -*- coding: utf-8 -*-
"""新增闸门的自证。每条判据都要有「必须报」与「必须不报」两侧。

规矩 E（PROJECT-SKILL §10）：收窄或新增一条检查而不自证 = 把它关掉。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_reader as br

sys.stdout.reconfigure(encoding="utf-8")

TOTAL = 31


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

    # ── theme：浅色主题注入。两侧自证 ──
    import theme
    raw = ('<style>:root{--mono:x; --bg:#0b0f15; --ink:#e7eef7}\n'
           'b{font-weight:650;color:#fff}\n'
           '.tbl td b{color:#fff}\n'
           '.res{border:1px solid #3b2f4f;background:rgba(185,143,230,.06)}\n'
           '.res .t{color:#b98fe6}\n</style>'
           '<button class="btn" id="help">?</button>'
           '<script>var x=1;</script>')
    lit = theme.apply_theme(raw)
    # 必须报：.res 的三个值都换成变量，纸底上不再是深紫。
    # ⚠ 判据只看**规则里**换没换，不能写成「全文不含 #3b2f4f」——
    #   暗色调色板里 --violetline 的值本来就是它，那种写法会永远失败。
    ok += ("border:1px solid var(--violetline)" in lit)
    ok += ("color:var(--violet)" in lit and "#b98fe6" not in lit)
    ok += ("background:var(--tintviolet)" in lit
           and "rgba(185,143,230,.06)" not in lit)
    # 必须报：两处纯白加粗都修掉（浅色下对比度 1.11，等于隐形）。
    # ⚠ 同理不能写成「全文不含 color:#fff」—— .pg 是彩底白字，那处必须留白。
    ok += ("b{font-weight:650;color:var(--ink2)}" in lit
           and ".tbl td b{color:var(--ink2)}" in lit)
    # 必须不报：幂等 —— 第二次调用不许再插一个按钮
    ok += (theme.apply_theme(lit).count('id="themeBtn"') == 1)
    # 必须不报：本壳原生已有的 quote / tbl 分支不许被注入成两份
    shell = ('<style>:root{--bg:#0b0f15}</style>'
             '<button class="btn" id="help">?</button><script>'
             "if(n.quote) h+='<div class=\"quote\">'+n.quote+'</div>';"
             "if(n.tbl && n.tbl.head) h+='x';"
             "if(n.tip) h+='<div class=\"tip'+(n.tip.w?\" w2\":\"\")+'\">'"
             "+n.tip.t+'</span>'+n.tip.v+'</div>';</script>")
    th2 = theme.apply_theme(shell)
    ok += (th2.count("if(n.quote)") == 1 and th2.count("if(n.tbl") == 1)
    # 必须不报：ng / exam 是 ML 课特有的，本项目不注入、也不留死 CSS
    ok += (".ng{" not in th2 and ".exam{" not in th2)

    # ── 讲级科研主线卡的两个颜色也要换掉。两侧自证 ──
    # 必须报：.arc 的正文色写死成了暗色的 --ink，浅色下对比度 1.17 等于隐形。
    # ⚠ 这张卡默认收起，肉眼扫页面发现不了 —— 只有对比度审计能抓到，所以必须有这条。
    th3 = theme.apply_theme(
        '<style>:root{--bg:#0b0f15}\n'
        '#threadBox .arc{color:#e7eef7}\n'
        '#threadBox h3 .tag{background:rgba(185,143,230,.07)}\n</style>'
        '<button class="btn" id="help">?</button><script>var x=1;</script>')
    ok += ("color:var(--ink)" in th3)
    ok += ("background:var(--tintviolet)" in th3)

    # ── link「你学过的对应」：两侧自证 ──
    # 必须报：只有文字没有链接 = 一个点不动的假链接，比不写更糟
    ok += (len(br.check_link([{"r": [1, 1], "link": {"t": "只有文字"}}])) == 1)
    ok += (len(br.check_link([{"r": [1, 1], "link": {"href": "x.html"}}])) == 1)
    # 必须不报：齐全的 link 不该被拦；没有 link 的条目也不该被拦
    ok += (len(br.check_link([{"r": [1, 1], "link": {
        "t": "CS234 L08 策略梯度",
        "href": "../../reinforcement learning/theater/影片/L08-策略梯度.html"}}])) == 0)
    ok += (len(br.check_link([{"r": [1, 1], "one": "没有 link"}])) == 0)

    # ── 防泄题：两侧自证。两层泄题都要拦 ──
    # 必须报：选项里有加粗（写题时把答案加粗好自己核对，结果印在页面上）
    ok += (len(br.check_quiz_leak(
        {"3": [{"q": "问", "o": ["<b>对的</b>", "错一", "错二"],
                "a": 0, "why": "因为"}]})) >= 1)
    # 必须报：答案位置集中（ML 那边 50 题有 48 题在 B，闭眼选 B 就满分）
    ok += (len(br.check_quiz_leak(
        {str(i): [{"q": "问", "o": ["错", "对", "错"], "a": 1, "why": "因为"}]
         for i in range(1, 9)})) >= 1)
    # 必须不报：无加粗、位置分散
    ok += (len(br.check_quiz_leak(
        {str(i): [{"q": "问", "o": ["甲", "乙", "丙"], "a": i % 3, "why": "因为"}]
         for i in range(1, 9)})) == 0)
    # 必须不报：题太少时不判位置（4 题全在 B 只是巧合，不是泄题）
    ok += (len(br.check_quiz_leak(
        {str(i): [{"q": "问", "o": ["甲", "乙", "丙"], "a": 1, "why": "因为"}]
         for i in range(1, 5)})) == 0)
    # 必须不报：题干与解析里的加粗是正常的，只有选项里不许有
    ok += (len(br.check_quiz_leak(
        {"3": [{"q": "<b>问</b>", "o": ["甲", "乙", "丙"],
                "a": 2, "why": "<b>因为</b>"}]})) == 0)

    print("selftest_gates %d/%d" % (ok, TOTAL))
    return ok == TOTAL


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
