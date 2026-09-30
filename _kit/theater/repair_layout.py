# -*- coding: utf-8 -*-
"""版面修复：把落进「顶部公式带」和「字幕带」的画布内容移进自由区。

阈值来自 1440×900 真实窗口实测（frame 1440×810，标准 16:9）：

    setEq(...,"top") 两行 aligned    y  51 → 283
    自由画布                          y 290 → 470
    字幕带 capWrap                    y 480 → 676

策略：对每一镜整体平移 y 坐标（保持内部相对关系不变），使其落入
  · 有 top 公式：[295, 465]，可用高度 170
  · 无 top 公式：[130, 465]，可用高度 335
装不下的镜头不硬塞，单独报出来 —— 那是内容太多，需要拆镜或去掉公式，
不是坐标问题。

用法：
    python repair_layout.py            # 空跑，只报告
    python repair_layout.py --apply    # 写回 episodes-L01.json
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

EQ_BOTTOM = 285
FREE_TOP_WITH_EQ = 295
FREE_TOP_PLAIN = 130
FREE_BOTTOM = 465

# 位置实参里 y 的下标；arrow/link 取 y1 与 y2
POSITIONAL = {"note": [2], "boxNode": [1], "arrow": [1, 3], "link": [1, 3]}
OBJ_PRIMS = ["bars", "morphBars", "fillBars", "gridworld", "sweepGrid",
             "mdpChain", "errbar", "matrix", "backup", "tree"]


def strip_strings(js):
    """把字符串字面量替换成同长度的占位，保持字符偏移不变（后面要按偏移改写）。"""
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


def call_span(code, name_start):
    i = code.index("(", name_start)
    depth, j = 0, i
    while j < len(code):
        if code[j] in "([{":
            depth += 1
        elif code[j] in ")]}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return i, j


def arg_spans(code, lo, hi):
    """返回 [(起, 止)] —— 顶层逗号切分出的实参区间。"""
    spans, depth, start = [], 0, lo + 1
    for k in range(lo + 1, hi):
        ch = code[k]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            spans.append((start, k))
            start = k + 1
    spans.append((start, hi))
    return spans


NUM = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")


def collect_y(draw_js):
    """返回 [(起, 止, 值)] —— 所有能静态确定的 y 数字字面量的位置。"""
    code = strip_strings(draw_js)
    hits = []
    for name, idxs in POSITIONAL.items():
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(", code):
            try:
                lo, hi = call_span(code, m.start())
            except ValueError:
                continue
            spans = arg_spans(code, lo, hi)
            for idx in idxs:
                if idx < len(spans):
                    a, b = spans[idx]
                    mm = NUM.match(code[a:b])
                    if mm:
                        off = code.index(mm.group(1), a, b)
                        hits.append((off, off + len(mm.group(1)), float(mm.group(1))))
    for name in OBJ_PRIMS:
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            try:
                lo, hi = call_span(code, m.start())
            except ValueError:
                continue
            for mm in re.finditer(r"\by\s*:\s*(-?\d+(?:\.\d+)?)", code[lo:hi]):
                off = lo + mm.start(1)
                hits.append((off, off + len(mm.group(1)), float(mm.group(1))))
    # 去重（同一个字面量可能被两条规则命中）
    seen, uniq = set(), []
    for a, b, v in sorted(hits):
        if a in seen:
            continue
        seen.add(a)
        uniq.append((a, b, v))
    return uniq


def extent(draw_js, hits):
    """内容的纵向包围盒。bars 系列的 y 是基线、柱子往上长，要额外算顶边。"""
    if not hits:
        return None
    code = strip_strings(draw_js)
    tops = [v for _, _, v in hits]
    bots = [v for _, _, v in hits]
    for name in ("bars", "morphBars", "fillBars"):
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            lo, hi = call_span(code, m.start())
            seg = code[lo:hi]
            y = re.search(r"\by\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            h = re.search(r"\bh\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            if y:
                yv = float(y.group(1))
                hv = float(h.group(1)) if h else 210.0
                tops.append(yv - hv)
                bots.append(yv + 22)
    for name in ("gridworld", "sweepGrid"):
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            lo, hi = call_span(code, m.start())
            seg = code[lo:hi]
            y = re.search(r"\by\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            cs = re.search(r"\bcs\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            rows = re.search(r"\brows\s*:\s*(-?\d+)", seg)
            if y:
                bots.append(float(y.group(1))
                            + (float(cs.group(1)) if cs else 88.0)
                            * (int(rows.group(1)) if rows else 1))
    for name in ("matrix",):
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            lo, hi = call_span(code, m.start())
            seg = code[lo:hi]
            y = re.search(r"\by\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            ch = re.search(r"\bch\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            rows = re.search(r"\brows\s*:\s*(-?\d+)", seg)
            if y:
                bots.append(float(y.group(1))
                            + (float(ch.group(1)) if ch else 42.0)
                            * (int(rows.group(1)) if rows else 1))
    for name in ("errbar",):
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            lo, hi = call_span(code, m.start())
            seg = code[lo:hi]
            y = re.search(r"\by\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            h = re.search(r"\bh\s*:\s*(-?\d+(?:\.\d+)?)", seg)
            if y:
                bots.append(float(y.group(1))
                            + (float(h.group(1)) if h else 300.0) + 22)
    return min(tops), max(bots)


# 公式带的下界按公式**实际高度**分级，而不是一律用最坏情况。
# 实测（1440×900，frame 1440×810）：
#     单行简单公式        y  90 → 189
#     两行 aligned 公式   y  51 → 283
# 一律按 283 算会把单行公式的镜头误判成装不下 —— 那批本来有 265px 可用。
# 注意：JS 源码里每个 LaTeX 命令都写成双反斜杠（\\max、\\gamma），
# 所以「两个反斜杠」会匹配到每一个公式 —— 真正的 LaTeX 换行在 JS 源码里是**四个**。
# 第一版把它写成两个，导致所有公式都被误判成高公式，可用带白丢了 90px。
TALL_MARKERS = ["aligned", "underbrace", "frac", "begin{", "pmatrix", "bmatrix",
                chr(92) * 4, "sum_{", "prod_{", "int_"]


def top_eq_bottom(draw_js):
    """这一镜的顶部公式占到哪里；没有 top 公式返回 None。"""
    m = re.search(r'setEq\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*"top"\s*\)', draw_js)
    if not m:
        return None
    latex = m.group(1)
    tall = any(k in latex for k in TALL_MARKERS)
    return 285 if tall else 195


# 压缩下限：14px 字至少要 ~20px 行距。原本 34px 行距 ×0.62 = 21px，还能读；
# 再压就挤在一起了，那种镜头是内容太多，不该靠压版面解决。
MIN_SCALE = 0.62

# 需要跟着一起缩放的尺寸参数（只缩 y 不缩尺寸会让图形变形、甚至向上溢出）
SIZE_KEYS = {
    "bars": ["h"], "morphBars": ["h"], "fillBars": ["h"],
    "gridworld": ["cs"], "sweepGrid": ["cs"],
    "matrix": ["ch"], "errbar": ["h"], "backup": ["dy"], "tree": ["r"],
}


def fmt(v):
    return ("%d" % round(v)) if abs(v - round(v)) < 1e-9 else ("%.1f" % v)


def shift_js(draw_js, hits, dy):
    """按字符偏移从后往前改写 y 字面量。"""
    out = draw_js
    for a, b, v in sorted(hits, reverse=True):
        out = out[:a] + fmt(v + dy) + out[b:]
    return out


def size_spans(draw_js):
    """返回 [(起, 止, 值)] —— 需要一起缩放的尺寸字面量位置。"""
    code = strip_strings(draw_js)
    hits = []
    for name, keys in SIZE_KEYS.items():
        for m in re.finditer(r"(?<![\w.])" + name + r"\s*\(\s*\{", code):
            try:
                lo, hi = call_span(code, m.start())
            except ValueError:
                continue
            for key in keys:
                for mm in re.finditer(r"\b" + key + r"\s*:\s*(-?\d+(?:\.\d+)?)",
                                      code[lo:hi]):
                    off = lo + mm.start(1)
                    hits.append((off, off + len(mm.group(1)), float(mm.group(1))))
    return hits


def scale_js(draw_js, hits, top, k, free_top):
    """把这一镜的纵向构图整体等比缩到 k 倍，并平移到 free_top 起。

    y' = free_top + (y - top) * k ；尺寸参数同乘 k。
    两类字面量的字符区间互不相交（y 在位置实参或 y: 键上，尺寸在 h/cs/ch 键上），
    所以可以合并后统一从后往前改写。
    """
    edits = [(a, b, free_top + (v - top) * k) for a, b, v in hits]
    edits += [(a, b, v * k) for a, b, v in size_spans(draw_js)]
    out = draw_js
    for a, b, nv in sorted(edits, key=lambda t: t[0], reverse=True):
        out = out[:a] + fmt(nv) + out[b:]
    return out


# 画布上超过这个长度的 note 视为「句子」而非「标签」，搬进讲解段落。
LABEL_MAX = 16
TAGS = re.compile(r"<[^>]+>")


def thin_canvas_text(draw_js):
    """把画布上的长句 note 删掉，文本返回给调用方并入讲解。

    判据只有长度：短的是标签（贴着图元，必须在画布上），
    长的是解释（属于阅读通道）。返回 (删除条数, 新 js, [被移走的文本])。
    """
    code = strip_strings(draw_js)   # 与原串等长，可用同一套偏移
    spans, texts = [], []
    for m in re.finditer(r"(?<![\w.])note\s*\(", code):
        try:
            lo, hi = call_span(code, m.start())
        except ValueError:
            continue
        args = arg_spans(code, lo, hi)
        if not args:
            continue
        a, b = args[0]
        raw = draw_js[a:b].strip()
        if len(raw) < 2 or raw[0] not in ('"', "'"):
            continue
        text = TAGS.sub("", raw[1:-1])
        if len(text) <= LABEL_MAX:
            continue
        end = hi + 1
        while end < len(draw_js) and draw_js[end] in ";\r\n\t ":
            end += 1
        spans.append((m.start(), end))
        texts.append(text)
    if not spans:
        return 0, draw_js, []
    out = draw_js
    for a, b in sorted(spans, reverse=True):
        out = out[:a] + out[b:]
    return len(spans), out, texts


def main():
    apply = "--apply" in sys.argv
    path = os.path.join(HERE, "episodes-L01.json")
    eps = json.loads(io.open(path, encoding="utf-8").read())

    moved, rescaled, thinned, manual, clean = 0, 0, 0, [], 0
    for ep in eps:
        for si, sh in enumerate(ep["shots"]):
            js = sh["draw_js"]
            hits = collect_y(js)
            if not hits:
                clean += 1
                continue
            ext = extent(js, hits)
            if not ext:
                clean += 1
                continue
            top, bot = ext
            eq_bottom = top_eq_bottom(js)
            eq = eq_bottom is not None
            free_top = (eq_bottom + 10) if eq else FREE_TOP_PLAIN
            span = bot - top
            budget = FREE_BOTTOM - free_top
            if top >= free_top and bot <= FREE_BOTTOM:
                clean += 1
                continue
            if span > budget:
                # 装不下就等比压缩行距。下限 0.62：14px 字至少要 ~20px 行距，
                # 原本 34px 的行距压到 21px 还能读，再压就挤在一起了。
                k = budget / span
                if k < MIN_SCALE:
                    # 压不下去就说明画布上有本该在讲解里的东西。
                    # 规则（来自 skills：不要把讲解稿重复成屏幕文字）：
                    #   短的是标签，留在画布；长句子搬进讲解段落。
                    n_drop, js2, moved_text = thin_canvas_text(js)
                    if n_drop:
                        hits2 = collect_y(js2)
                        ext2 = extent(js2, hits2)
                        if ext2:
                            top2, bot2 = ext2
                            span2 = bot2 - top2
                            k2 = budget / span2 if span2 > budget else 1.0
                            if k2 >= MIN_SCALE:
                                sh["draw_js"] = (scale_js(js2, hits2, top2, k2, free_top)
                                                 if k2 < 1.0 else
                                                 shift_js(js2, hits2, free_top - top2))
                                sh["narration"] = sh["narration"] + "　" + "　".join(moved_text)
                                thinned += 1
                                print("  KP%-2d 镜%d [%-6s] 长句 %d 条移入讲解，跨度 %d -> %d"
                                      % (ep["kp"], si, sh["beat"], n_drop,
                                         round(span), round(span2 * k2)))
                                continue
                    manual.append((ep["kp"], si, sh["beat"], round(top), round(bot),
                                   round(span), round(budget), eq, round(k, 2)))
                    continue
                sh["draw_js"] = scale_js(js, hits, top, k, free_top)
                rescaled += 1
                print("  KP%-2d 镜%d [%-6s] %s 跨度 %d -> %d  压缩 ×%.2f  ->  %d…%d"
                      % (ep["kp"], si, sh["beat"], "有公式" if eq else "无公式",
                         round(span), round(span * k), k,
                         round(free_top), round(free_top + span * k)))
                continue
            # 平移到自由区：优先贴着上界，若下界超了再往上收
            dy = free_top - top
            if bot + dy > FREE_BOTTOM:
                dy = FREE_BOTTOM - bot
            if abs(dy) < 1:
                clean += 1
                continue
            sh["draw_js"] = shift_js(js, hits, dy)
            moved += 1
            print("  KP%-2d 镜%d [%-6s] %s 内容 %d…%d  平移 %+d  ->  %d…%d"
                  % (ep["kp"], si, sh["beat"], "有公式" if eq else "无公式",
                     round(top), round(bot), round(dy), round(top + dy), round(bot + dy)))

    print()
    print("平移 %d 镜 · 等比压缩 %d 镜 · 长句移入讲解 %d 镜 · 本来就合规 %d 镜 · 需人工 %d 镜"
          % (moved, rescaled, thinned, clean, len(manual)))
    if manual:
        print("\n连压到 ×%.2f 都装不下（内容太多，要拆镜或去掉公式）：" % MIN_SCALE)
        for kp, si, beat, top, bot, span, budget, eq, k in manual:
            print("  KP%-2d 镜%d [%-6s] %s 跨度 %dpx > 可用 %dpx，需压到 ×%.2f  (%d…%d)"
                  % (kp, si, beat, "有公式" if eq else "无公式",
                     span, budget, k, top, bot))
    if apply:
        io.open(path, "w", encoding="utf-8").write(
            json.dumps(eps, indent=2, ensure_ascii=False))
        print("\n已写回 episodes-L01.json")
    else:
        print("\n（空跑。加 --apply 才写回）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
