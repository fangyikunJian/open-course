# -*- coding: utf-8 -*-
"""CSE 541 讲义去重 —— 这门课的 16 份讲义是**累积快照**，同一份手稿会再拍一次。

    cd "G:/open course/bandits-cse541"
    python tools/页面去重.py              # 全量：222 页并成多少个互不相同的内容页
    python tools/页面去重.py --selftest   # 自证：三条已知的包含关系必须成立
    python tools/页面去重.py L08 L07 L09  # 单查：L08 的每一页在 L07/L09 里有没有对应

为什么要有这个脚本：这门课唯一能逐页看图做精读，而 222 页里有 65 页是重复的。
不先查就做，会把整讲白做一遍 —— **L08 七页全部落在 L07 ∪ L09 里**，而那两讲都已建好，
它一页都不用做；这件事是 2026-10-07 靠这个脚本查出来的，在那之前任务清单上还写着
「下一个建议：L08，只剩 1–2 页是新的，很便宜」。

三条判据，缺一不可（前两条是 2026-10-06 踩出来的，第三条是 2026-10-07）：
  ① **判据是墨迹包含，不是像素相等。** 累积快照常是同一手稿加了批注，
     加了批注像素就不同 —— 只认逐字节相同的话，L07 p2–p5 与 L09 p2–p5
     这种「同一手稿加批注」一对都查不出来。
  ② **必须加墨量护栏。** 只看包含率会出假阳性：一页墨迹特别重的纸几乎«包含»
     任何稀疏页，实测出过「L01 的 53 页全被判成 ⊆ L03 p9」。
     护栏是要求两页墨量可比（A ≥ 0.5·B）。**多对一映射就是假阳性的特征。**
  ③ ⚠ **问法必须是「这一讲是不是被别的讲包住」，不是「这一页是不是更早某页的重复」。**
     累积快照里**后出的那份通常是加了批注的超集**，于是「后 ⊆ 先」永远不成立。
     按「更早」那个问法做出来的表会说 L08 还有 5 页是新的 —— 错的正是这一步。

⚠ 排版重排会把同一页压到 0.85–0.95 这一档（整块位置挪了，全局平移修不回来）：
L08 p5 与 L09 p5 双向都只有约 0.90，但人眼看过是同一页，L09 那份多两处批注。
所以 0.85–0.95 之间的一律**单独列出来等人眼确认**，不自动判定。
"""
import os
import sys
import json
from collections import defaultdict

import numpy as np
import pymupdf

sys.stdout.reconfigure(encoding="utf-8")

DPI, THR = 72, 190          # 72 dpi 足够分辨笔画；灰度 < 190 算墨
HI, LO = 0.95, 0.85         # 确定档 / 疑似档
MASS = 0.5                  # 墨量护栏：批注只加一点墨，差一倍以上就不是同一页

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)            # 课程根目录（course.json 所在）


def course():
    return json.load(open(os.path.join(ROOT, "course.json"), encoding="utf-8"))


def load(tag):
    """渲染一讲的全部页面为「是不是墨」的布尔图。"""
    path = os.path.join(ROOT, "corpus", "slides", "lecture_%d.pdf" % int(tag[1:]))
    doc = pymupdf.open(path)
    out = []
    for p in doc:
        pix = p.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        out.append(np.frombuffer(pix.samples, dtype=np.uint8)
                     .reshape(pix.height, pix.width) < THR)
    doc.close()
    return out


def dilate(m):
    """3×3 膨胀：容忍一两个像素的渲染抖动，不至于把同一笔画判成不同。"""
    o = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


class Pages(dict):
    """(tag, 页号) -> 布尔图，另带膨胀版与墨量。"""

    def __init__(self, tags):
        super().__init__()
        self.dil, self.ink, self.keys_ = {}, {}, []
        for t in tags:
            for j, m in enumerate(load(t), 1):
                k = (t, j)
                self[k] = m
                self.dil[k] = dilate(m)
                self.ink[k] = int(m.sum())
                self.keys_.append(k)

    def contain(self, a, b):
        """a 的墨迹有多少落在 b（膨胀后）里面。形状不同或墨量不可比则返回 0。"""
        if self[a].shape != self[b].shape:
            return 0.0
        if self.ink[a] < MASS * self.ink[b] or self.ink[b] < MASS * self.ink[a]:
            return 0.0
        return float((self[a] & self.dil[b]).sum()) / max(self.ink[a], 1)


def cmd_pair(src, tgts):
    """单查：src 的每一页在 tgts 里有没有对应。"""
    pg = Pages([src] + [t for t in tgts if t != src])
    n = sum(1 for k in pg.keys_ if k[0] == src)
    for j in range(1, n + 1):
        a = (src, j)
        hits = []
        for t in tgts:
            for i in range(1, sum(1 for k in pg.keys_ if k[0] == t) + 1):
                b = (t, i)
                c = pg.contain(a, b)
                if c >= LO:
                    same = bool((pg[a] == pg[b]).all())
                    hits.append((t, i, c, same))
        if not hits:
            print("  p%-2d  —— 没有对应，**这一页是新的**" % j)
        for t, i, c, same in sorted(hits, key=lambda h: -h[2]):
            tier = "【逐像素相同】" if same else ("确定" if c >= HI else "⚠ 疑似，要人眼确认")
            print("  p%-2d  ⊆ %s p%-2d  包含率 %.3f  墨量 %d vs %d  %s"
                  % (j, t, i, c, pg.ink[a], pg.ink[(t, i)], tier))


def clusters(pg):
    """把所有页并成互不相同的内容类（并查集，双向任一方向包含即同类）。"""
    parent = {k: k for k in pg.keys_}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ks = pg.keys_
    for ai in range(len(ks)):
        for bi in range(ai + 1, len(ks)):
            a, b = ks[ai], ks[bi]
            if a[0] == b[0]:
                continue
            if pg.contain(a, b) >= LO or pg.contain(b, a) >= LO:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra
    out = defaultdict(list)
    for k in ks:
        out[find(k)].append(k)
    return list(out.values())


def cmd_all(built):
    co = course()
    tags = [L["tag"] for L in co["lectures"]]
    title = {L["tag"]: L["title"] for L in co["lectures"]}
    pg = Pages(tags)
    cls = clusters(pg)
    print("%d 页 ⇒ **%d 个互不相同的内容页**\n" % (len(pg.keys_), len(cls)))

    # 代表页：优先已建的讲（那一份已经有讲解了），其次批注最全，再次讲序靠前。
    # ⚠ 不加「优先已建」这一条，逐像素相同时就退化成「挑先出现的」，
    #    于是 L08 会被挑成代表、看着还有 4 页要做，其实一页都不用做。
    need, covered = defaultdict(list), defaultdict(list)
    for mem in cls:
        rep = sorted(mem, key=lambda k: (k[0] not in built, -pg.ink[k],
                                         tags.index(k[0])))[0]
        need[rep[0]].append(rep[1])
        for k in mem:
            if k != rep:
                covered[k[0]].append(rep)

    print("| 讲 | 总页 | 要从这一讲读 | 状态 |")
    print("|---|---|---|---|")
    todo = 0
    for t in tags:
        ps = sorted(need.get(t, []))
        tot = sum(1 for k in pg.keys_ if k[0] == t)
        if t in built:
            st = "✅ 已建"
        elif not ps:
            st = "⭐ **整讲都在别处，不必做**"
        else:
            st = "⬜ 待做"
            todo += len(ps)
        print("| %s | %d | **%d** | %s |" % (t, tot, len(ps), st))
    print("\n**还没做的讲里，真正要读的页共 %d 页。**\n" % todo)
    for t in tags:
        if t not in built and need.get(t):
            print("   %s  %2d 页  %s" % (t, len(need[t]), title[t][:46]))
    print("\n⭐ 整讲都在别处的：")
    for t in tags:
        if t not in built and not need.get(t):
            srcs = sorted({r[0] for r in covered[t]})
            done = "、".join(s for s in srcs if s in built) or "无"
            print("   %s（%d 页）→ 全在 %s；其中 %s 已建"
                  % (t, sum(1 for k in pg.keys_ if k[0] == t), " ∪ ".join(srcs), done))
    print("\n⚠ 疑似档（%.2f–%.2f），要人眼确认：" % (LO, HI))
    shown = 0
    for mem in cls:
        for ai in range(len(mem)):
            for bi in range(ai + 1, len(mem)):
                a, b = mem[ai], mem[bi]
                c = max(pg.contain(a, b), pg.contain(b, a))
                if LO <= c < HI:
                    print("   %s p%-2d ↔ %s p%-2d  %.3f" % (a[0], a[1], b[0], b[1], c))
                    shown += 1
    if not shown:
        print("   无")


def cmd_selftest():
    """自证：三条已知的整讲包含关系必须查得出来，且必须查得出 L08 p5 落在疑似档。

    不会失败的断言不算断言 —— 所以也反向验一条：L06 不许被判成任何别的讲的子集。
    """
    ok = fail = 0

    def check(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print("  [ok]   " + name)
        else:
            fail += 1
            print("  [FAIL] " + name + ("   " + detail if detail else ""))

    pg = Pages(["L06", "L07", "L08", "L09", "L11", "L12", "L17", "L18"])

    def fully_in(t, others):
        n = sum(1 for k in pg.keys_ if k[0] == t)
        for j in range(1, n + 1):
            best = max((pg.contain((t, j), (u, i))
                        for u in others
                        for i in range(1, sum(1 for k in pg.keys_ if k[0] == u) + 1)),
                       default=0.0)
            if best < LO:
                return False, j
        return True, None

    for t, others in (("L08", ["L07", "L09"]), ("L11", ["L12"]), ("L17", ["L18"])):
        good, miss = fully_in(t, others)
        check("%s 每一页都落在 %s 里" % (t, "∪".join(others)), good,
              "没被包住的是 p%s" % miss)

    # 反向：L06（逐次淘汰）是独有的，不许被判成别人的子集
    good, _ = fully_in("L06", ["L07", "L08", "L09", "L12", "L18"])
    check("L06 不被判成别的讲的子集（反向，防判据过松）", not good)

    # L08 p5 ↔ L09 p5 必须落在疑似档：排版重排把同一页压到 0.85–0.95
    c = max(pg.contain(("L08", 5), ("L09", 5)), pg.contain(("L09", 5), ("L08", 5)))
    check("L08 p5 ↔ L09 p5 落在疑似档（%.3f，排版重排的特征）" % c, LO <= c < HI)

    print("\n自证 %d/%d" % (ok, ok + fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--selftest":
        sys.exit(cmd_selftest())
    if len(args) >= 2:
        cmd_pair(args[0], args[1:])
    else:
        # 已经做了精读的讲（代表页优先从这些里挑）。加了新的精读就往这里补。
        cmd_all(built={"L05", "L06", "L07", "L09", "L12", "L16", "L18", "L20"})
