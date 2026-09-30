# -*- coding: utf-8 -*-
"""画面多样性审计：一部片里到底有几种不同的画法？

用法：
    python prim_mix.py            # 看分布
    python prim_mix.py --check    # 超标就非零退出

═══ 为什么要有这条检查（事故实录）═══

CS234 放映厅做到后面，`lamps`（三个圈 + ✓/✗ + 标签）占到 L16 的 45 镜中 29 镜（64%），
全课 725 镜里占 203 镜。`lamps` 讲 MCTS 能用、讲 bandit 能用、讲 PAC 也能用 ——
**正因为哪儿都能用，它哪儿都没在教东西**。它是修辞装置，不是被讲的那个对象。

病因是机械的：只有 build_L01.py 引用过 corpus 里的 slides，其余 14 讲只看了讲稿。
手上没有课件那张具体的图，就只能退回到套什么都成立的版式。

═══ 这个指标改过三次，前两次都问错了问题 ═══

第一版：正则抓所有 `xxx(`。结果把 JS 的 `function(` 和 LaTeX 的 `V(` `Q(`
        全当成图元，报出「function 超标」「theta 22%」。
第二版：只认引擎导出的图元。这下手绘的片被低估了 —— L16 改画之后几乎全是
        片内函数（mN/mE/mT）和裸 E.gS.append，按这个算法只得 3 种，
        可它恰恰是形式最多的一部；而 mN/mE 这种「节点/边」原子还会被判超标。
第三版（现在）：数**每镜的画法签名**有多少种不同的。
        签名 = 这一镜用到的全部绘图调用的集合。45 镜只有 3 种签名 = 在套模板；
        45 镜有 30 种签名 = 每镜都在画不同的东西。
        这个度量对「库里的图元」和「手写的 SVG」一视同仁。

**注意它的边界**：它衡量「有没有在套同一张图」，不衡量「画得好不好」。
真正的判据只有一条 —— 这一镜画的是不是课件上那个对象。
"""
import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 单个「整张图」级别的图元占一部片的上限。超过就是在套版式。
CAP = 0.25
# 一部片的「不同画法数 / 有图镜数」下限。
MIN_VARIETY = 0.30

# 原子：它们是砖，不是房子。到处都在用是正常的，不参与占比判断。
# 裸 SVG 形状（svg:rect / svg:path / svg:circle …）同样是砖：
# 一部手绘的片里它们必然遍地都是，拿它们判「套版式」是误报。
ATOMS = {"note", "arrow", "boxNode", "link", "axes", "fn", "dots", "curve",
         "mN", "mE", "mT", "mStat", "mDiv", "mRoll",
         "svg:rect", "svg:path", "svg:circle", "svg:ellipse",
         "svg:line", "svg:text", "svg:g", "svg:polygon"}
# 排版通道，完全不算画图
CHROME = {"setCap", "setEq", "setBig", "setTitle", "clearScene", "flip", "T",
          "setNarr", "note", "noTitle"}

CALL = re.compile(r"(?:^|[^A-Za-z0-9_$.])([a-zA-Z][a-zA-Z0-9_]*)\s*\(")
RAW = re.compile(r'gS\.append\(\s*"([a-z]+)"')


def engine_prims():
    src = io.open(os.path.join(HERE, "build_common.py"), encoding="utf-8").read()
    return set(re.findall(r"E\.([a-zA-Z_][a-zA-Z0-9_]*)\s*=", src))


def local_helpers(lec):
    """片内自定义画法也算画法 —— 指标不能只认库里有的东西。"""
    fp = os.path.join(HERE, "film-%s.json" % lec)
    if not os.path.exists(fp):
        return set()
    pre = json.load(io.open(fp, encoding="utf-8")).get("prelude_js") or ""
    return set(re.findall(r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", pre))


def scan():
    prims = engine_prims()
    figs = collections.defaultdict(collections.Counter)
    sigs = collections.defaultdict(collections.Counter)
    shots = collections.Counter()
    for f in sorted(glob.glob(os.path.join(HERE, "episodes-L*.json"))):
        if ".bak" in f:
            continue
        lec = os.path.basename(f).split("-")[1].split(".")[0]
        vocab = prims | local_helpers(lec)
        for e in json.load(io.open(f, encoding="utf-8")):
            for sh in e.get("shots", []):
                js = sh.get("draw_js") or ""
                if not js.strip():
                    continue
                used = (set(CALL.findall(js)) & vocab) - CHROME
                used |= set("svg:" + t for t in RAW.findall(js))
                if not used:
                    continue
                shots[lec] += 1
                sigs[lec][frozenset(used)] += 1
                for p in used - ATOMS:
                    figs[lec][p] += 1
    return figs, sigs, shots


def main():
    figs, sigs, shots = scan()
    if not shots:
        print("没找到分片。")
        return 1
    over, thin = [], []
    print("%-5s %6s %6s %7s  %s"
          % ("片", "有图镜", "画法数", "多样度", "整图级图元占比"))
    for lec in sorted(shots):
        n, nv = shots[lec], len(sigs[lec])
        var = nv / float(n)
        top = figs[lec].most_common(4)
        line = "  ".join("%s %d%%" % (k, round(100.0 * v / n)) for k, v in top)
        flag = ""
        for k, v in top:
            if v > CAP * n:
                over.append((lec, k, v, n))
                flag += "  <== %s 超标" % k
        if var < MIN_VARIETY:
            thin.append((lec, nv, n, var))
            flag += "  <== 画法太少"
        print("%-5s %6d %6d %7.2f  %s%s" % (lec, n, nv, var, line, flag))

    print()
    if thin:
        print("画法太少的片（不同画法 / 有图镜数 < %.2f）：%d 部" % (MIN_VARIETY, len(thin)))
        for lec, nv, n, var in thin:
            print("   %s：%d 镜只有 %d 种画法（%.2f）" % (lec, n, nv, var))
        print()
    if over:
        print("单个整图级图元超过 %d%% 的：%d 处" % (round(CAP * 100), len(over)))
        for lec, k, v, n in over:
            print("   %s 的 %s：%d/%d 镜（%d%%）" % (lec, k, v, n, round(100.0 * v / n)))
        print()
    if thin or over:
        print("→ 去 corpus/<课程>/slides/ 把该讲的课件调出来，按课件上那个真实对象重画。")
    else:
        print("没有把同一张图当版式反复套。")
    if "--check" in sys.argv:
        return 1 if (thin or over) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
