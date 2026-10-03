# -*- coding: utf-8 -*-
"""prim_mix 的「片内画法」判据自证。必须 6/6。

规矩 E（PROJECT-SKILL §10）：收窄一条检查而不自证 = 把它关掉。
这里收窄的是 local_helpers —— 从「prelude 里所有 function」收到「真的会画的
那些」。所以必须两侧都验：**会画的一个都不许漏，不画的一个都不许收**。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prim_mix as pm  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

TOTAL = 6

PRE = """
var PX0=360, PX1=940, PYM=258;
function wx(w){ return PX0 + (PX1-PX0)*(w/2); }           // 纯换算，不画
function vy(v){ return PYM - 64*v; }                      // 纯换算，不画
function clipw(w){ return Math.max(0.8, Math.min(1.2,w)); } // 纯计算，不画
function ptsRaw(A){ var p=[],w; for(w=0;w<=2;w+=0.05) p.push([wx(w),vy(w*A)]); return p; }
function frame(){ E.gS.append("line").attr("class","axline"); }   // 直接加元素
function panel(){ boxNode(10,10,100,40,"x",""); note("y",20,20,"sm"); }  // 调图元
"""


def run():
    ok = 0
    got = pm.drawing_fns(PRE)

    # ── 必须收：真的会画的 ──
    ok += ("frame" in got)        # 直接 E.gS.append
    ok += ("panel" in got)        # 调用引擎图元 boxNode / note

    # ── 必须不收：一笔都不画的 ──
    ok += ("wx" not in got)       # 坐标换算
    ok += ("vy" not in got)       # 坐标换算
    ok += ("clipw" not in got)    # 纯数学，连别的函数都不调

    # ⚠ ptsRaw 只调了 wx/vy（两个非图元），自己不画 —— 也不该收。
    # 这一条是本判据最容易写松的地方：若判据写成「调了任何片内函数就算画」，
    # 它会连带把 ptsRaw 收进来，而它返回的只是一个点数组。
    ok += ("ptsRaw" not in got)

    if ok != TOTAL:
        print("  收到的是：", sorted(got))
    return ok


if __name__ == "__main__":
    n = run()
    print("selftest_primmix %d/%d" % (n, TOTAL))
    sys.exit(0 if n == TOTAL else 1)
