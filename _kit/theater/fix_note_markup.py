# -*- coding: utf-8 -*-
"""把 note() 里的 **强调** 标记去掉。

事故：note() 的实现是 gN.append("text")....text(t) —— SVG 文本节点，
**不解析任何标记**，既不认 Markdown 也不认 HTML。于是我在 note 里写的
**着重号** 全部以字面星号显示在画面上。用户截图里那句
「就把动作这一维**按 π 加权求和掉**」就是它。全片共 96 处。

对照：setCap() 与 narration 走的是 innerHTML，<b> 在那里是有效的，
所以那两处不动。

处理方式不是简单删星号 —— 星号标出来的正是那一行的重点，删掉就把重点也
抹平了。画布上的层级只能靠**颜色**（引擎的字号是闭集，只有 13/14/15px，
混用会让画面每次切换都跳一下）。所以：
  · 若该行整行都被星号包住 → 去掉星号，并把颜色提升为强调色（y）
  · 若只是行内一段被包住   → 去掉星号，颜色保持原样（行内无法分色）
    这类行在后续的密度改写里会被拆成独立短行，那时再上色。

用法：
    python fix_note_markup.py            # 空跑
    python fix_note_markup.py --apply    # 写盘
"""
import io
import json
import glob
import sys

BS = chr(92)
Q = '"'
EMPH = "y"          # 强调色：黄 = 注意力/结论（与 ML 版语义一致）
# 这些类已经是语义色，不要覆盖掉（覆盖会破坏颜色语义）
KEEP = ("r", "g", "v", "b", "y")


def read_string(src, i):
    """src[i] 指向开引号，返回 (内容, 结束下标)。"""
    i += 1
    out = []
    n = len(src)
    while i < n:
        c = src[i]
        if c == BS and i + 1 < n:
            out.append(src[i])
            out.append(src[i + 1])
            i += 2
            continue
        if c == Q:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    return "".join(out), i


def split_args(src, i):
    """从左括号后开始，按顶层逗号切出实参的 (文本, 起, 止) 列表。"""
    args, depth, start, n = [], 0, i, len(src)
    while i < n:
        c = src[i]
        if c == Q:
            _, i = read_string(src, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                args.append((src[start:i], start, i))
                return args, i
            depth -= 1
        elif c == "," and depth == 0:
            args.append((src[start:i], start, i))
            start = i + 1
        i += 1
    return args, i


def strip_marks(js, fname, stats):
    """把 fname(...) 第一个字符串实参里的 ** 去掉，只去标记不改颜色。"""
    edits = []
    i, tok = 0, fname + "("
    while True:
        j = js.find(tok, i)
        if j < 0:
            break
        if j > 0 and (js[j - 1].isalnum() or js[j - 1] in "_."):
            i = j + len(tok)
            continue
        args, end = split_args(js, j + len(tok))
        i = end + 1
        if not args:
            continue
        raw = args[0][0].strip()
        if "**" not in raw or not (raw.startswith(Q) and raw.endswith(Q)):
            continue
        stats["lines"] += 1
        stats["inline"] += 1
        edits.append((args[0][1], args[0][2], " " + raw.replace("**", "")))
    for a, b, rep in sorted(edits, key=lambda e: -e[0]):
        js = js[:a] + rep + js[b:]
    return js


def fix_shot(js, stats):
    """处理一镜里的所有 note(...) 与 setEq(...)，从后往前改以免下标漂移。

    setEq 也必须处理：它把串交给 MathJax，而 \\text{...} 里的星号同样是
    字面星号（实测 L02 KP7 镜4 的 "的**精确**值函数"）。LaTeX 里没有
    「行内加粗一段中文」的省事写法，所以这里只去标记，不做替代强调。
    """
    js = strip_marks(js, "setEq", stats)
    edits = []
    i, tok = 0, "note("
    while True:
        j = js.find(tok, i)
        if j < 0:
            break
        if j > 0 and (js[j - 1].isalnum() or js[j - 1] in "_."):
            i = j + len(tok)
            continue
        args, end = split_args(js, j + len(tok))
        i = end + 1
        if not args or "**" not in args[0][0]:
            continue
        raw = args[0][0].strip()
        if not (raw.startswith(Q) and raw.endswith(Q)):
            continue
        body = raw[1:-1]
        whole = body.startswith("**") and body.endswith("**") and body.count("**") == 2
        new_body = body.replace("**", "")
        stats["lines"] += 1
        stats["whole" if whole else "inline"] += 1
        # 替换第一个实参
        a_start, a_end = args[0][1], args[0][2]
        edits.append((a_start, a_end, " " + Q + new_body + Q))
        # 整行强调 -> 把类提升为强调色（仅当原类是无色/中性时）
        if whole and len(args) >= 4:
            craw = args[3][0].strip()
            if craw.startswith(Q) and craw.endswith(Q):
                cls = craw[1:-1]
                parts = [p for p in cls.split() if p]
                if not any(p in KEEP for p in parts):
                    parts = [p for p in parts if p != "ink"]
                    parts.append(EMPH)
                    edits.append((args[3][1], args[3][2], Q + " ".join(parts) + Q))
                    stats["recolored"] += 1
    for a, b, rep in sorted(edits, key=lambda e: -e[0]):
        js = js[:a] + rep + js[b:]
    return js


def main():
    apply = "--apply" in sys.argv
    stats = {"lines": 0, "whole": 0, "inline": 0, "recolored": 0, "files": 0}
    for f in sorted(glob.glob("episodes-L0*.json")):
        if ".bak" in f:
            continue
        eps = json.loads(io.open(f, encoding="utf-8").read())
        hit = 0
        for ep in eps:
            for sh in ep["shots"]:
                if "**" not in sh["draw_js"]:
                    continue
                before = sh["draw_js"]
                sh["draw_js"] = fix_shot(before, stats)
                if sh["draw_js"] != before:
                    hit += 1
        left = sum(s["draw_js"].count("**") for e in eps for s in e["shots"])
        print("   %-24s 改了 %2d 镜，剩余字面星号 %d" % (f, hit, left))
        if hit:
            stats["files"] += 1
            if apply:
                io.open(f, "w", encoding="utf-8").write(
                    json.dumps(eps, ensure_ascii=False, indent=1))
    print()
    print("共 %d 行 note 含星号：整行强调 %d（其中 %d 行已改为强调色），行内强调 %d"
          % (stats["lines"], stats["whole"], stats["recolored"], stats["inline"]))
    print("（空跑。加 --apply 写盘）" if not apply else "已写盘。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
