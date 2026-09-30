# -*- coding: utf-8 -*-
"""把一讲的内容 JSON 组装成放映厅片子。

    python assemble.py 02

读两类文件（都在本目录）：
    film-LNN.json        片级元数据：标题、时间码基准、知识点名、开场与结尾
    episodes-LNN*.json   内容分片，每片是一个 episode 数组

分片是为了让一讲的内容可以分几次写出来而不必一次性持有整份文件 ——
L01 那份单文件有 150 KB，改一处就要整体重写，风险和成本都不对。
分片之间按 kp 号合并，重号直接报错（静默覆盖会丢掉一整集）。

这里只做机械组装，不改写内容。内容问题在 JSON 层修，改完重跑。

L01 的旧入口 assemble_L01.py 保留不动，它已经产出过正式版；
新讲一律走这个脚本。
"""
import io
import glob
import json
import os
import re
import sys

import build_common as bc

HERE = os.path.dirname(os.path.abspath(__file__))

BEAT_LABEL = {
    "hook": "钩子",
    "wrong": "错误答案",
    "setup": "铺陈",
    "body": "主体",
    "refute": "反驳",
}
BEATS = ("hook", "wrong", "setup", "body", "refute")


def js_str(text):
    """把一段文本变成合法的 JS 双引号字符串字面量。

    只需要转义反斜杠与双引号；换行统一为空格（讲解段落里不该有硬换行）。
    这里显式用 chr(92) 构造反斜杠，避免多层转义写错 —— 这个坑踩过。
    """
    bs = chr(92)
    t = text.replace(bs, bs + bs).replace('"', bs + '"')
    t = t.replace("\r", " ").replace("\n", " ")
    return '"' + t + '"'


def indent(block, pad="      "):
    lines = [l for l in block.replace("\r", "").split("\n")]
    return ("\n" + pad).join(l.strip() for l in lines if l.strip())


def _strip_strings(js):
    """手写扫描器剥掉字符串字面量，保持字符偏移不变。

    不用正则：本项目里凡是把反斜杠写进正则的地方都出过转义事故。
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


ANIM_PRIMS = ["trace", "morphBars", "fillBars", "sweepGrid", "reveal"]
# 返回坐标变换的原语。它们的返回值必须被用来定位，不许手算 —— 手算会漏掉内部的
# ymin/padding 等换算。实例：L01 KP2 镜4 把参考线写成 170+280-v/1.25*280，忽略了
# errbar 的 ymin=-0.1，参考线整体偏低 22.4px，于是画面说「A 明显偏离真值」而
# 字幕说「A 已收敛到 0.50」—— 图文互相矛盾，且两个检查器都没抓到。
TRANSFORM_PRIMS = ["errbar", "bars", "morphBars", "fillBars", "gridworld",
                   "sweepGrid", "mdpChain"]


def check_shot(kp, i, sh):
    """组装前的内容自检。发现不一致就直接失败，不要产出一部带已知缺陷的片子。"""
    js = sh["draw_js"]
    used = [a for a in ANIM_PRIMS if re.search(r"\b" + a + r"\(", js)]
    flag = bool(sh.get("animated"))
    if flag and not used:
        raise SystemExit(
            "KP%d 镜%d：animated=true 但 draw_js 里没有任何动画原语。\n"
            "  watch 会承诺一个不会发生的运动。\n"
            "  要么补上动画原语，要么把 animated 改为 false 并删掉 watch。" % (kp, i))
    if used and not flag:
        raise SystemExit(
            "KP%d 镜%d：用了动画原语 %s 但 animated=false —— 这一镜不会被要求写 watch。"
            % (kp, i, used))
    if flag and not sh.get("watch", "").strip():
        raise SystemExit(
            "KP%d 镜%d：animated=true 但没有 watch。动画必须事先告知「看什么」，"
            "否则观众会盯着错的地方。" % (kp, i))
    # 坐标手算检查：该镜若调用了会返回变换的原语，位置实参里就不该出现数字算式
    if any(re.search(r"\b" + p + r"\(", js) for p in TRANSFORM_PRIMS):
        # 必须先剥字符串字面量再找算式 —— 否则 note("总和 = 10+9+…+1 = 55") 里
        # 文字内部的算式会被当成手算坐标。这个假阳性形态已经出现过三次。
        code = _strip_strings(js)
        for m in re.finditer(
                r"\b(?:arrow|note|boxNode|link)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", code):
            if re.search(r"\d+\s*[+\-]\s*\d+\s*[+\-*/]", m.group(1)):
                print("  ! KP%d 镜%d 警告：坐标像是手算的（%s…）。"
                      "该镜调用了会返回坐标变换的原语，应当用它的返回值定位。"
                      % (kp, i, m.group(0)[:52]))


def build_episode(ep, meta):
    """一集 -> 一段 KP(...) 源码。"""
    kp = ep["kp"]
    name = meta["kp_names"][str(kp)]
    base = meta["kp_base"][str(kp)]
    out = ['KP(%s,function(){' % js_str(name)]

    for i, sh in enumerate(ep["shots"]):
        check_shot(kp, i, sh)
        t = base + i * 12          # 同一集内各镜时间码递增，便于跳转定位
        beat = BEAT_LABEL.get(sh["beat"], sh["beat"])
        out.append("  /* %s */" % beat)
        out.append("  S(%d,function(){" % t)
        out.append("      " + indent(sh["draw_js"]))
        # 动画镜的「看什么」放在讲解段落**开头**，不画在画布上。
        # 画布上 y=626 在字幕带里面（实测字幕带从 y≈480 起），会被整条盖住。
        # 讲解段落就在画布正下方、是阅读通道，放这里既满足「事先告知」又零版面风险。
        narr = sh["narration"]
        if sh.get("animated") and sh.get("watch", "").strip():
            narr = "<b>看什么：</b>" + sh["watch"].strip() + "　—— " + narr
        out.append("    },%s);" % js_str(narr))

    s = ep["sum"]
    fields = []
    for k in ("h", "k", "m", "w", "e"):
        if s.get(k):
            fields.append("%s:%s" % (k, js_str(s[k])))
    out.append("  SUM(%d,%d,{%s});" % (base, kp, ",\n    ".join(fields)))

    q = ep["quiz"]
    opts = ",".join(js_str(o) for o in q["o"])
    out.append("  QUIZ(%d,%d,{t:%s,\n    o:[%s],\n    a:%d,\n    w:%s});"
               % (base, kp, js_str(q["t"]), opts, int(q["a"]), js_str(q["w"])))
    out.append("});")
    return "\n".join(out)


def load_episodes(tag):
    """合并所有分片。重号报错 —— 静默覆盖会整集丢失且没有任何症状。"""
    pat = os.path.join(HERE, "episodes-%s*.json" % tag)
    files = sorted(f for f in glob.glob(pat) if not f.endswith(".bak"))
    if not files:
        raise SystemExit("找不到 %s" % pat)
    eps, where = {}, {}
    for f in files:
        part = json.loads(io.open(f, encoding="utf-8").read())
        if isinstance(part, dict):
            part = part.get("episodes", [])
        for e in part:
            k = e["kp"]
            if k in eps:
                raise SystemExit("KP%d 在 %s 和 %s 里各有一份，先去重"
                                 % (k, os.path.basename(where[k]), os.path.basename(f)))
            eps[k] = e
            where[k] = f
    print("读入 %d 个分片：%s" % (len(files), ", ".join(os.path.basename(f) for f in files)))
    return [eps[k] for k in sorted(eps)]


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：python assemble.py 02")
    tag = "L%02d" % int(sys.argv[1].lstrip("Ll"))

    meta = json.loads(io.open(os.path.join(HERE, "film-%s.json" % tag),
                              encoding="utf-8").read())
    eps = load_episodes(tag)

    have = [e["kp"] for e in eps]
    want = [int(k) for k in meta["kp_names"]]
    missing = [k for k in sorted(want) if k not in have]
    if missing:
        print("警告：缺少 KP %s —— 先补齐再出正式版" % missing)

    C = []
    C.append('var CFG={\n  title:%s,\n  subtitle:%s,\n  video:%s\n};\n'
             % (js_str(meta["title"]),
                js_str(meta["subtitle"] % len(eps) if "%d" in meta["subtitle"]
                       else meta["subtitle"]),
                js_str(meta["video"])))
    if meta.get("prelude_js"):
        C.append(meta["prelude_js"])

    op = meta["opening"]
    C.append('KP("开场",function(){\n  S(0,function(){\n      %s\n    },%s);\n});'
             % (indent(op["draw_js"]), js_str(op["narration"])))

    for ep in eps:
        C.append(build_episode(ep, meta))

    cl = meta["closing"]
    C.append('KP("完",function(){\n  S(%d,function(){\n      %s\n    },%s);\n});'
             % (cl.get("t", 3600), indent(cl["draw_js"]), js_str(cl["narration"])))

    bc.write(meta["file"], meta["html_title"], "\n\n".join(C))

    print()
    for ep in eps:
        beats = [s["beat"] for s in ep["shots"]]
        anim = sum(1 for s in ep["shots"] if s.get("animated"))
        lack = [b for b in BEATS if b not in beats]
        print("  KP%-2d %d镜 动画%d镜  %s%s"
              % (ep["kp"], len(ep["shots"]), anim, beats,
                 ("  缺拍:" + str(lack)) if lack else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
