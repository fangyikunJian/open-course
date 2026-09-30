# -*- coding: utf-8 -*-
"""阅读页统一主题：浅色纸感为默认，暗色可一键切换。

用途：被 build_reader.py 调用，把写死暗色的 HTML 壳改造成双主题。
放映厅的片子不用这套（它们保持暗场）。

**与 ML 版（`Machine Learning/精读/theme.py`）的分工不同，这一点很要紧。**

ML 版还兼着往壳里**注入渲染分支**（quote / tbl / ng / exam），因为它的壳是一个
**已构建的成品**（`_shell.html`），改不动，只能往里打补丁。这里的壳是真模板
（`reader_template.html`），能直接编辑，所以边界回到它该在的地方：

    壳负责渲染（有哪些字段、怎么排），theme.py 只负责颜色。

于是移除了 ML 版的「第 0a 步」注入。两条实测理由，不是洁癖：

1. **会重复渲染。** 本壳原生已有 `if(n.quote)` 与 `if(n.tbl && n.tbl.head)`
   两个分支，注入会各加一份，同一段原话与同一张表在页上出现两次。
2. **`tbl` 的形状两边不兼容。** 本壳与 `check_tbl()` 与既有 10 讲数据一致用
   **单对象** `{head, rows}`；ML 版用**数组** `[{cap, head, rows}]`。
   本项目沿用单对象（三方已经一致，改形状要动既有数据）。

`ng`（Andrew Ng 补基础）与 `exam`（与考试的联系）是 ML 课特有的，本项目不用：
前者的对位是壳里原生的 `link`（你学过的对应），后者没有对应物（这里没有考试）。
相应的 `.ng` / `.exam` / `.tw` / `.tc` CSS 也一并移除 —— 留着会是四段永不匹配的死规则。
"""

# ── 写死的颜色 → 变量名 ────────────────────────────────────────────
HARDCODED = {
    "#0a0e14": "--sunken",     # 按钮 / 输入框 / 代码底
    "#0d141c": "--hover",      # 选项 hover 底
    "#070a0f": "--stage",      # 左栏舞台底（PDF 四周）
    "#26303f": "--dot",        # 答题历史小方块（空）
    "#18212e": "--dot",        # strip 空页
    "#2c3c52": "--dot2",       # strip 有讲解
    "#7a3a3a": "--errdot",     # strip 错题
    "#2a3b4f": "--line2",      # .say 边框
    "#4a2b2e": "--warnline",   # .tip.w2 边框
    "#f4f8fd": "--ink2",       # .one 亮字
    "#c3d2e3": "--ink3",       # .why 次正文
    "#cfe3f5": "--codeink",    # 行内代码字
    "#dbe8f7": "--eqink",      # 公式块字
    "#d8fff4": "--okink",      # 答对选项字
    "#ffdede": "--noink",      # 答错选项字
    # 下面三个是 CS234 在 ML 版之后新增的 .res 科研格用的，ML 的映射表里没有。
    # 漏掉就会在纸底上留一个深紫框 + 深紫标题字。
    "#3b2f4f": "--violetline",  # .res 边框
    "#b98fe6": "--violet",      # .res 标题字 / 科研主线卡的 tag
}

# 半透明填充 → 变量名（浅色下原值太淡或反了，必须换）
RGBA = {
    "rgba(111,211,187,.13)": "--okfill",
    "rgba(255,143,143,.12)": "--nofill",
    "rgba(10,14,20,.97)": "--missbg",       # 「打不开？」遮罩，暗色下是近黑
    "rgba(111,211,187,.09)": "--tintacc",   # .one 左条底
    "rgba(111,211,187,.07)": "--tintacc2",  # .why 左条底
    "rgba(127,184,255,.055)": "--tintblue", # .say 底
    "rgba(255,120,120,.055)": "--tintwarn", # .tip.w2 底
    "rgba(255,143,143,.08)": "--tintwarn2", # 复习模式 chip
    "rgba(255,255,255,.022)": "--lift",     # .qq 底（暗色下靠提亮，浅色下要反过来）
    "rgba(255,255,255,.025)": "--lift2",    # .tip 底
    "rgba(185,143,230,.06)": "--tintviolet",  # .res 底（同上，ML 表里没有）
    "rgba(6,9,13,.82)": "--scrim",          # 错题本遮罩
    "0 10px 34px rgba(0,0,0,.55)": "--shadow",  # #stage 投影
}

# ── 两套调色板 ────────────────────────────────────────────────────
LIGHT = """
  --bg:#F5F3EE; --panel:#FFFFFF; --panel2:#FAF8F4; --sunken:#EDEAE3;
  --stage:#E9E6DF; --hover:#F0EDE6;
  --line:#E3DFD6; --line2:#D2CCC0;
  --dot:#DDD8CE; --dot2:#B9B1A2; --errdot:#D08A8A;
  --ink:#23272C; --ink2:#111417; --ink3:#4A525C; --dim:#616973;
  --acc:#0E7355; --acc2:#845808; --warn:#B23540; --blue:#1C6AA6;
  --mark:#FFF6DC; --codeink:#17506E; --eqink:#1E2833;
  --okink:#0B5B43; --noink:#8F2A33; --violet:#6A4BA3; --tintviolet:rgba(106,75,163,.07);
  --violetline:#D9CEEA;
  --okfill:rgba(14,115,85,.10); --nofill:rgba(178,53,64,.09);
  --missbg:rgba(245,243,238,.97);
  --tintacc:rgba(14,115,85,.07); --tintacc2:rgba(14,115,85,.05);
  --tintblue:rgba(28,106,166,.06); --tintwarn:rgba(178,53,64,.05);
  --tintwarn2:rgba(178,53,64,.06);
  --lift:rgba(60,54,44,.022); --lift2:rgba(60,54,44,.028);
  --scrim:rgba(58,52,42,.40);
  --shadow:0 1px 2px rgba(40,34,20,.05), 0 6px 18px rgba(40,34,20,.05);
"""

DARK = """
  --bg:#0b0f15; --panel:#121823; --panel2:#0d141c; --sunken:#0a0e14;
  --stage:#070a0f; --hover:#0d141c;
  --line:#212c3c; --line2:#2a3b4f;
  --dot:#18212e; --dot2:#2c3c52; --errdot:#7a3a3a;
  --ink:#e7eef7; --ink2:#f4f8fd; --ink3:#c3d2e3; --dim:#8b9ab0;
  --acc:#6fd3bb; --acc2:#f2bd63; --warn:#ff8f8f; --blue:#7fb8ff;
  --mark:#16202e; --codeink:#cfe3f5; --eqink:#dbe8f7;
  --okink:#d8fff4; --noink:#ffdede; --violet:#B48BF5; --tintviolet:rgba(180,139,245,.08);
  --violetline:#3b2f4f;
  --okfill:rgba(111,211,187,.13); --nofill:rgba(255,143,143,.12);
  --missbg:rgba(10,14,20,.97);
  --tintacc:rgba(111,211,187,.09); --tintacc2:rgba(111,211,187,.07);
  --tintblue:rgba(127,184,255,.055); --tintwarn:rgba(255,120,120,.055);
  --tintwarn2:rgba(255,143,143,.08);
  --lift:rgba(255,255,255,.022); --lift2:rgba(255,255,255,.025);
  --scrim:rgba(6,9,13,.82);
  --shadow:0 10px 34px rgba(0,0,0,.55);
"""

# 浅色下需要补的细节：卡片投影、字重微调、面板去掉过重的边框
EXTRA_CSS = """
/* ══ 双主题补丁：浅色下的可读性与质感 ══ */
html{color-scheme:light dark}
:root:not([data-theme="dark"]) #right{background:var(--bg)}
:root:not([data-theme="dark"]) .quiz,
:root:not([data-theme="dark"]) details,
:root:not([data-theme="dark"]) .opt{box-shadow:var(--shadow)}
:root:not([data-theme="dark"]) body{-webkit-font-smoothing:antialiased}
:root:not([data-theme="dark"]) h2{letter-spacing:-.1px}
:root:not([data-theme="dark"]) .one{font-weight:520}
:root:not([data-theme="dark"]) .pg{color:#fff}
:root:not([data-theme="dark"]) #strip b.on{background:var(--acc2)}
/* 主题切换按钮 */
#themeBtn{min-width:34px;text-align:center;font-size:14px;line-height:1}
"""

TOGGLE_JS = """
/* ══ 主题切换：浅色默认，记住选择 ══ */
(function(){
  var KEY = "mlreader-theme";
  var root = document.documentElement, btn = document.getElementById("themeBtn");
  function apply(t){
    root.setAttribute("data-theme", t);
    if (btn) btn.textContent = (t === "dark" ? "☀" : "☾");
    if (btn) btn.title = (t === "dark" ? "切到浅色" : "切到暗色");
  }
  var saved;
  try { saved = localStorage.getItem(KEY); } catch(e){}
  apply(saved === "dark" ? "dark" : "light");
  if (btn) btn.addEventListener("click", function(){
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    apply(next);
    try { localStorage.setItem(KEY, next); } catch(e){}
  });
})();
"""


def apply_theme(html, btn_anchor='<button class="btn" id="help">'):
    """把写死暗色的 HTML 壳改造成「浅色默认 + 暗色可切换」。"""
    import re

    # 幂等守卫：已经上过主题的文件重复调用会重复插按钮与脚本
    if 'id="themeBtn"' in html:
        return html

    # 0. ⚠ 加粗字被写死成纯白（暗色下是最亮层，浅色下对比度只有 1.11 等于隐形）。
    #    只能定点替换：#fff 还被 #stage（PDF 底）和 .pg（彩底上的白字）用着，不能一刀切。
    html = html.replace("b{font-weight:650;color:#fff}",
                        "b{font-weight:650;color:var(--ink2)}")

    #    同一个病还有第二处：表格里的加粗。ML 版没有这一行，是因为它的表格走
    #    另一套 CSS（table.nt）；本壳的 .tbl 是自己的一套。漏掉它，浅色下
    #    表格里所有加粗字都是白底白字。
    html = html.replace(".tbl td b{color:#fff}", ".tbl td b{color:var(--ink2)}")

    # 1. 写死的颜色 → 变量
    for hexv, var in HARDCODED.items():
        html = re.sub(re.escape(hexv), "var(%s)" % var, html, flags=re.I)
    for rg, var in RGBA.items():
        html = html.replace(rg, "var(%s)" % var)

    # 2. 替换 :root 里的调色板（保留字体与尺寸变量）
    m = re.search(r":root\{(.*?)\}", html, re.S)
    keep = [ln.strip() for ln in m.group(1).split("\n")
            if ln.strip() and ln.strip().startswith("--")
            and not re.match(r"--(bg|panel|line|ink|dim|acc|acc2|warn|blue|mark)\s*:", ln.strip())]
    html = (html[:m.start()]
            + ":root{" + LIGHT + "\n  " + "\n  ".join(keep) + "\n}\n"
            + ':root[data-theme="dark"]{' + DARK + "}\n"
            + html[m.end():])

    # 2b. 补丁 CSS 必须放在 <style> 末尾 —— 否则同级选择器被后面的原规则盖掉
    html = html.replace("</style>", EXTRA_CSS + "\n</style>", 1)

    # 3. 插入切换按钮
    html = html.replace(btn_anchor,
                        '<button class="btn" id="themeBtn" title="切换主题">☾</button>\n  ' + btn_anchor, 1)

    # 4. 插入切换脚本（放在第一个 <script> 之后最稳）
    i = html.index("<script>") + len("<script>")
    html = html[:i] + "\n" + TOGGLE_JS + html[i:]
    return html
