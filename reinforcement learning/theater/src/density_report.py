# -*- coding: utf-8 -*-
"""量一量每一镜画布上的文字密度。

用户反馈：「目前的文字在一张图里太密集了，大脑不适应接受如此多密集的信息都在一张
slide 上」。在改之前先把它量出来 —— 否则「改稀疏一点」没有验收标准。

量三件事：
  · 每镜 note 的**行数**（画布上并排出现的独立文本块）
  · 每镜画布上的**总字数**
  · **最长一行**的字数（一行太长要横扫，比多一行更累）

字幕带与讲解段落分开统计：它们在画布之外，是阅读通道，不计入画面密度。

实现说明：取字符串实参用**手写扫描器**，不用正则。本项目在
「把反斜杠写进正则」这件事上已经翻过三次船（[^"\\] 少一个反斜杠就会让
字符集不闭合，报 unterminated character set）。扫描器没有这个问题。
"""
import io
import json
import glob
import re
import sys
import statistics as st

BS = chr(92)
Q = '"'


def first_string_arg(src, i):
    """从 src[i] 开始（i 指向左括号后），取出第一个双引号字符串的内容。"""
    n = len(src)
    while i < n and src[i] in " \t":
        i += 1
    if i >= n or src[i] != Q:
        return None, i
    i += 1
    out = []
    while i < n:
        c = src[i]
        if c == BS and i + 1 < n:
            out.append(src[i + 1])
            i += 2
            continue
        if c == Q:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    return "".join(out), i


def calls(src, name):
    """找出 name( 的所有调用，返回每个调用的第一个字符串实参。"""
    out, i, tok = [], 0, name + "("
    while True:
        j = src.find(tok, i)
        if j < 0:
            return out
        # 必须是独立标识符，避免 setCap 命中 Cap 之类
        if j > 0 and (src[j - 1].isalnum() or src[j - 1] in "_."):
            i = j + len(tok)
            continue
        s, k = first_string_arg(src, j + len(tok))
        if s is not None:
            out.append(s)
        i = max(k, j + len(tok))


def strip_tags(s):
    out, depth = [], 0
    for c in s:
        if c == "<":
            depth += 1
        elif c == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(c)
    return "".join(out)



def _strings_in(seg):
    """把一段源码里所有双引号字符串literal 抠出来（不含转义的复杂情形）。"""
    out, i = [], 0
    while True:
        a = seg.find('"', i)
        if a < 0:
            return out
        b = a + 1
        while b < len(seg):
            if seg[b] == "\\":
                b += 2
                continue
            if seg[b] == '"':
                break
            b += 1
        if b >= len(seg):
            return out
        out.append(seg[a + 1:b])
        i = b + 1


def prim_labels(js):
    """图元在运行时自己画出来的标签（lamps 的 label/sub、各类 bars 的 label
    数组、backup 的 labels）。这些和 note() 落在同一个 14px 通道里。"""
    out = []
    # lamps({items:[{label:"..",sub:".."},...]})
    for m in re.finditer(r"items:\s*\[", js):
        seg = js[m.end():js.find("]}", m.end()) + 1 if js.find("]}", m.end()) > 0 else len(js)]
        for mm in re.finditer(r'(?:label|sub)\s*:\s*"', seg):
            s = _strings_in(seg[mm.end() - 1:])
            if s:
                out.append(s[0])
    # label:function(i){return ["a","b"][i];}  /  labels:["a","b"]
    for m in re.finditer(r"labels?\s*:", js):
        tail = js[m.end():m.end() + 400]
        a = tail.find("[")
        if a < 0:
            continue
        b = tail.find("]", a)
        if b < 0:
            continue
        out.extend(_strings_in(tail[a:b]))
    return out


def n_bars(js):
    """柱子数量 —— 每根柱子还会多出一个 fmt 算出来的数值标签，静态读不到。"""
    n = 0
    for key in ("vals:", "to:"):
        m = js.find(key)
        if m < 0:
            continue
        a = js.find("[", m)
        b = js.find("]", a)
        if a > 0 and b > a:
            n = max(n, len([x for x in js[a + 1:b].split(",") if x.strip()]))
    return n


def scan():
    rows = []
    # glob 原来写的是 episodes-L0*.json —— 两位数的 L10 起全部漏掉，
    # 而报告照样打印「超预算 N/455」，看上去像查过了。同一天里 lint_film
    # 也犯了形状一样的错（只检查 argv[1]、argv[2]）。假绿灯比假红灯危险。
    for f in sorted(glob.glob("episodes-L[0-9][0-9]*.json")):
        if ".bak" in f:
            continue
        lec = f.split("-")[1].split(".")[0]
        for ep in json.loads(io.open(f, encoding="utf-8").read()):
            for i, sh in enumerate(ep["shots"]):
                js = sh["draw_js"]
                own = calls(js, "note")
                texts = own + prim_labels(js)
                cap = calls(js, "setCap")
                nb = n_bars(js)
                # 视觉对象数：一排 lamps / 一张柱图各算 1（它们横向铺开，
                # 不是堆叠的行），加上每条独立的长 note。依据是实际渲染，
                # 见 scratchpad/refine_budget.py 的说明。
                objs = len([t for t in own if len(t) > LABEL_MAX])
                objs += len(re.findall(r"\blamps\(", js))
                objs += len(re.findall(r"\b(?:fillBars|morphBars|bars)\(", js))
                rows.append({
                    "f": f, "lec": lec, "kp": ep["kp"], "i": i,
                    "beat": sh.get("beat", ""),
                    "n": len(texts),
                    "long_n": len([t for t in texts if len(t) > 6]),
                    "chars": sum(len(t) for t in texts),
                    "longest": max((len(t) for t in texts), default=0),
                    "cap": len(strip_tags(cap[0])) if cap else 0,
                    "narr": len(strip_tags(sh.get("narration", ""))),
                    "stars": js.count("**"),
                    "bars": nb,
                    "objs": objs,
                })
    return rows


# ── 画布密度预算 ────────────────────────────────────────────────────────
# 依据不是手感，是引擎的字号事实（从 eng.txt 读出来的）：
#   画布 .slbl     14px 固定、等宽    ← 全片**最小最难读**的通道
#   字幕 #cap      clamp(13.5,1.56vw,22px)，宽 84ch，支持 <b>/<i>/<em>/<s> 上色
#   断言 #big      clamp(30,5.6vw,82px)
#   公式 #eqBox    clamp(16,2.5vw,36px)
# 也就是说：把散文塞进画布 = 把最多的字放进最小的字号里。这正是用户说的
# 「一张 slide 上信息太密集」。
#
# 于是分工固定下来：
#   note()   只做**图元标注** —— 锚在图形上的短标签，离开那个图形就没意义
#   setCap() 放**这一镜的结论**（一句话）
#   setBig() 放**一个大断言**（「错误答案」那一拍最适合）
#   narration 放**论证**
# 一镜塞不下就拆成两镜 —— 镜头便宜，认知不便宜。
BUDGET = {
    "lines": 3,      # **视觉对象**数：一排 lamps / 一张柱图算 1，长 note 各算 1
    "longest": 20,   # 最长一行的字数
    "chars": 80,     # 画布上全部文字（含图元标签）的总字数
}


LABEL_MAX = 6   # ≤6 字视为「标签」，不计入行数上限（但仍计入总字数）


def check(rows, verbose=True):
    bad = []
    for r in rows:
        why = []
        if r.get("objs", r.get("long_n", r["n"])) > BUDGET["lines"]:
            why.append("%d 个视觉对象 >%d" % (r.get("objs", 0), BUDGET["lines"]))
        if r["longest"] > BUDGET["longest"]:
            why.append("最长 %d 字 >%d" % (r["longest"], BUDGET["longest"]))
        if r["chars"] > BUDGET["chars"]:
            why.append("共 %d 字 >%d" % (r["chars"], BUDGET["chars"]))
        if why:
            bad.append((r, why))
    if verbose:
        for r, why in sorted(bad, key=lambda t: -t[0]["chars"])[:20]:
            print("   %s KP%-2d 镜%d %-7s  %s"
                  % (r["lec"], r["kp"], r["i"], r["beat"], " · ".join(why)))
    print()
    # 逐片计数。只打印最差 20 条时，看不出「哪几部还没修」——
    # 而那恰恰是唯一需要知道的事。
    per = {}
    for r in rows:
        d = per.setdefault(r["lec"], [0, 0])
        d[1] += 1
    for r, _why in bad:
        per[r["lec"]][0] += 1
    print("逐片：" + "  ".join(
        "%s %d/%d" % (lec, n, tot) for lec, (n, tot) in sorted(per.items())))
    print("超预算镜数：%d / %d（预算：≤%d 行 · 单行 ≤%d 字 · 共 ≤%d 字）"
          % (len(bad), len(rows), BUDGET["lines"], BUDGET["longest"], BUDGET["chars"]))
    return bad


def main():
    rows = scan()
    if "--check" in sys.argv:
        return 1 if check(rows) else 0
    for lec in ("L01", "L02", "L03"):
        R = [r for r in rows if r["lec"] == lec]
        if not R:
            continue
        print("%s  %2d 镜 | note 行数 中位 %.0f / 最多 %d | 画布字数 中位 %.0f / 最多 %d "
              "| 最长单行 中位 %.0f / 最多 %d"
              % (lec, len(R),
                 st.median([r["n"] for r in R]), max(r["n"] for r in R),
                 st.median([r["chars"] for r in R]), max(r["chars"] for r in R),
                 st.median([r["longest"] for r in R]), max(r["longest"] for r in R)))
    print()
    print("画布字数最多的 12 镜：")
    for r in sorted(rows, key=lambda r: -r["chars"])[:12]:
        print("   %s KP%-2d 镜%d %-7s %d 行 / %3d 字 / 最长 %2d  （字幕 %d · 讲解 %d）"
              % (r["lec"], r["kp"], r["i"], r["beat"], r["n"], r["chars"],
                 r["longest"], r["cap"], r["narr"]))
    print()
    tot = len(rows)
    for label, pred in [
        ("note ≥ 5 行", lambda r: r["n"] >= 5),
        ("note ≥ 6 行", lambda r: r["n"] >= 6),
        ("画布 ≥ 120 字", lambda r: r["chars"] >= 120),
        ("有 ≥ 30 字的单行", lambda r: r["longest"] >= 30),
        ("字面星号 **", lambda r: r["stars"] > 0),
    ]:
        k = len([r for r in rows if pred(r)])
        print("   %-18s %3d / %d  （%.0f%%）" % (label, k, tot, 100.0 * k / tot))


if __name__ == "__main__":
    main()
