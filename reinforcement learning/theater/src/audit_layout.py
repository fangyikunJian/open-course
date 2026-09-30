# -*- coding: utf-8 -*-
"""版面碰撞审计。

起因：用户截图里公式与 note 直接叠在一起，另有若干图「不知所以」。
在浏览器里量了真实几何（SVG 逻辑坐标 1280×720）：

    setEq(...,"top") 单行            y  90 → 189
    setEq(...,"top") 两行 aligned    y  63 → 301
    字幕带 capWrap（短字幕+有讲解）    y 303 → 622
    字幕带 capWrap（长字幕+长讲解）    y 262 → 622   ← 最坏情况
    字幕带 capWrap（无讲解，按 N 关）  y 581 → 622

讲解默认是显示的，所以默认情况下字幕带从 y≈303 起，最坏 y≈262 起。
又从 ML 版 19 部能用的片子里量出它们的惯例：note/boxNode 的 y 中位数 240，
66% 落在 180–300，最大 474 —— 主画区就是 y≈130–300。

于是两条可执行的规则：

  R1  一镜若用了 setEq(...,"top")，画布元素不得落在 60–310 这个带里。
      两行以上的公式会占满整个主画区，此时这一镜**不应再有画布内容**。

  R2  画布元素不得落在 y > SAFE_BOTTOM（默认 300）—— 那是字幕带的地盘。
      超过 480 一定被盖住；300–480 只在字幕很短且关掉讲解时才勉强可见。

用法：
    python audit_layout.py <内容脚本或 build 脚本>
"""
import io
import re
import sys

# ── 阈值来自 1440×900 真实窗口的实测，不是估的 ────────────────────────────
# 关键教训：第一版阈值是在 652×367 的预览面板里量的，而字幕带用 vh 单位、
# 相对**视口**而非 720 画布，小窗口下它被严重放大（占到 58%），于是把安全区
# 300–470 误判成危险区，69 镜里报了 67 镜 —— 阈值本身反向错了。
#
# 【单位事故·必读】下面这组数原来是在 1440×900 的浏览器里用开发者工具量的，
# 量到的是**屏幕像素**；可本文件拿它们去比的是 draw_js 里写的 y，那是**SVG 用户坐标**。
# 两者差一个仿射变换：svg 的 viewBox 是 1280×720，实际画在 (0,45) 处的 1440×810，
#     screen_y = 45 + 1.125 * svg_y      <=>     svg_y = (screen_y - 45) / 1.125
# 于是「字幕带从 480 起」被当成「svg y 480 以下才危险」，实际 svg 只要过 405 就压到字幕。
# 整整 70 个用户坐标的误差，全落在字幕正文第一行上，12 镜因此漏检（L01 3 镜 + 另外 9 镜）。
#
# 1440×900 实测，换算回 SVG 用户坐标之后：
#     setEq(...,"top") 两行 aligned    svg y   5 → 212   （屏幕 51 → 283）
#     自由画布                          svg y 218 → 396   （屏幕 290 → 491）
#     字幕正文顶边 #cap                 svg y 405 → 449   （屏幕 501 → 550）
#        —— 注意这条线是**浮动**的：字幕越长、换行越多，顶边越往上，最高到 405。
#        所以按最坏情形 405 收，不要按某一镜量到的 449 收。
EQ_TOP_BAND = (0, 215)       # 有 top 公式时，这个带归公式所有（svg 用户坐标）
SAFE_BOTTOM = 396            # 自由画布下界：再往下，长字幕就会压上来
HARD_BOTTOM = 405            # 最坏情形下字幕正文的顶边，过线必被压

# 各原语的 y 参数怎么取
POSITIONAL = {
    "note": 2,        # note(text, x, y, cls, anchor)
    "boxNode": 1,     # boxNode(x, y, w, h, label, cls)
    "arrow": None,    # arrow(x1,y1,x2,y2,...) -> 取 y1 与 y3
    "link": None,     # link(x1,y1,x2,y2)
}
OBJECT_PRIMS = ["bars", "morphBars", "fillBars", "gridworld", "sweepGrid",
                "mdpChain", "errbar", "matrix", "backup", "tree"]


def strip_strings(js):
    """手写扫描器剥掉字符串字面量，避免把文字里的数字当坐标。

    用等长空格填充而不是 '""' —— 必须**保持字符偏移不变**，
    否则后面拿 code 里的偏移去 src 里取原文（为了读 LaTeX）会取错位置。
    """
    bs = chr(92)
    out, i, n = [], 0, len(js)
    while i < n:
        c = js[i]
        if c in ('"', "'"):
            q, start = c, i
            i += 1
            while i < n:
                if js[i] == bs:
                    i += 2
                    continue
                if js[i] == q:
                    i += 1
                    break
                i += 1
            out.append(" " * (i - start))
        else:
            out.append(c)
            i += 1
    return "".join(out)


def split_args(argstr):
    depth, cur, out = 0, [], []
    for ch in argstr:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur).strip())
    return out


def call_args(code, start):
    """从函数名后的左括号开始括号配平，返回实参串与结束位置。"""
    i = code.index("(", start)
    depth, j = 0, i
    while j < len(code):
        if code[j] in "([{":
            depth += 1
        elif code[j] in ")]}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return code[i + 1:j], j


def num(tok):
    try:
        return float(tok)
    except (TypeError, ValueError):
        return None


def ys_in_shot(code):
    """收集这一镜里所有能静态确定的 y 坐标，返回 [(原语, y)]。"""
    found = []
    for name, idx in POSITIONAL.items():
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(", code):
            try:
                argstr, _ = call_args(code, m.start())
            except ValueError:
                continue
            args = split_args(argstr)
            if name in ("arrow", "link"):
                for k in (1, 3):
                    if k < len(args):
                        v = num(args[k])
                        if v is not None:
                            found.append((name, v))
            elif idx is not None and idx < len(args):
                v = num(args[idx])
                if v is not None:
                    found.append((name, v))
    # 对象参数形态：取 y，并按各原语的实际纵向占位算出底边
    for name in OBJECT_PRIMS:
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            try:
                argstr, _ = call_args(code, m.start())
            except ValueError:
                continue
            y = re.search(r"\by\s*:\s*(-?[0-9.]+)", argstr)
            if not y:
                continue
            yv = float(y.group(1))
            found.append((name, yv))
            # bars 系列的 y 是**基线**，柱子往上长；其余的 y 是顶边，往下长
            if name in ("bars", "morphBars", "fillBars"):
                h = re.search(r"\bh\s*:\s*(-?[0-9.]+)", argstr)
                hv = float(h.group(1)) if h else 210.0
                found.append((name + "(顶)", yv - hv))
                found.append((name + "(标签)", yv + 22))
            elif name in ("gridworld", "sweepGrid"):
                cs = re.search(r"\bcs\s*:\s*(-?[0-9.]+)", argstr)
                rows = re.search(r"\brows\s*:\s*(-?[0-9]+)", argstr)
                csv = float(cs.group(1)) if cs else 88.0
                rv = int(rows.group(1)) if rows else 1
                found.append((name + "(底)", yv + csv * rv))
            elif name == "errbar":
                h = re.search(r"\bh\s*:\s*(-?[0-9.]+)", argstr)
                hv = float(h.group(1)) if h else 300.0
                found.append((name + "(底)", yv + hv + 22))
            elif name == "matrix":
                ch = re.search(r"\bch\s*:\s*(-?[0-9.]+)", argstr)
                rows = re.search(r"\brows\s*:\s*(-?[0-9]+)", argstr)
                chv = float(ch.group(1)) if ch else 42.0
                rv = int(rows.group(1)) if rows else 1
                found.append((name + "(底)", yv + chv * rv))
    return found


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    src = io.open(path, encoding="utf-8").read()
    code = strip_strings(src)

    shots = [m.start() for m in re.finditer(r"\bS\(\d", code)] + [len(code)]
    issues = 0
    print("版面审计：%s" % path)
    print("  主画区 y = 130…%d   ·   setEq(top) 占 %d…%d   ·   y > %d 必被字幕带盖住"
          % (SAFE_BOTTOM, EQ_TOP_BAND[0], EQ_TOP_BAND[1], HARD_BOTTOM))
    print()

    for a, b in zip(shots, shots[1:]):
        seg = code[a:b]
        line = code[:a].count(chr(10)) + 1
        # 公式带的下界要按**这一镜公式的实际高度**算，不能一律用最坏情况。
        # 第一版用固定 285，把单行公式（实测只到 y=189）的镜头误判成重叠，
        # 而修复器是按 195+10 放的 —— 两边阈值不一致，报了 18 镜假重叠。
        raw = src[a:b]                      # 未剥字符串的原文，才能看到 LaTeX
        eqm = re.search(r'setEq\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*"top"\s*\)', raw)
        has_top_eq = bool(eqm)
        eq_bottom = 0
        if eqm:
            latex = eqm.group(1)
            tall = any(k in latex for k in
                       ("aligned", "underbrace", "frac", "begin{", "pmatrix",
                        "bmatrix", chr(92) * 4, "sum_{", "prod_{", "int_"))
            eq_bottom = 285 if tall else 195
        ys = ys_in_shot(seg)
        if not ys:
            continue
        bad_eq, bad_low, bad_hard = [], [], []
        for name, y in ys:
            if has_top_eq and EQ_TOP_BAND[0] <= y <= eq_bottom:
                bad_eq.append((name, y))
            if y > HARD_BOTTOM:
                bad_hard.append((name, y))
            elif y > SAFE_BOTTOM:
                bad_low.append((name, y))
        if bad_eq or bad_low or bad_hard:
            issues += 1
            print("  镜 @ 行 %d%s" % (line, "   [有 top 公式]" if has_top_eq else ""))
            if bad_eq:
                print("     ✗ 与公式重叠 (%d 处): %s"
                      % (len(bad_eq), ", ".join("%s@%g" % t for t in bad_eq[:8])))
            if bad_hard:
                print("     ✗ 必被字幕带盖住 y>%d (%d 处): %s"
                      % (HARD_BOTTOM, len(bad_hard),
                         ", ".join("%s@%g" % t for t in bad_hard[:8])))
            if bad_low:
                print("     ! 有风险 y>%d (%d 处): %s"
                      % (SAFE_BOTTOM, len(bad_low),
                         ", ".join("%s@%g" % t for t in bad_low[:8])))
    print()
    print("共 %d 镜有版面问题。" % issues)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
