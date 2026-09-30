# -*- coding: utf-8 -*-
"""把 episodes-L01.json 组装成放映厅片子。

内容由九个 agent 按六拍结构分别起草，这里只做机械组装：
  每集 = hook / wrong / setup / body×N / refute 五种拍 + SUM（能独立存在的定格）
         + QUIZ（生成式提示）

不在这里做内容改写 —— 内容问题应该在 JSON 层修，改完重跑这个脚本。
"""
import io
import json
import os
import re
import sys

import build_common as bc

HERE = os.path.dirname(os.path.abspath(__file__))

KP_NAMES = {
    1: "1 · 三个承重词：序贯 · 好 · 学",
    2: "2 · 四要素坐标系",
    3: "3 · 用四盏灯划清边界",
    4: "4 · 交互回路、历史、智能体状态",
    5: "5 · Markov 条件 = 充分统计量",
    6: "6 · MDP / POMDP / 赌博机",
    7: "7 · 三大部件与折扣和的收敛性",
    8: "8 · Mars rover：γ 是问题定义的一部分",
    9: "9 · 三组分野与有限时域的非平稳性",
}

# 各知识点在讲座视频里的起始秒数（时间码用来点击跳转，取自逐讲索引）
KP_BASE = {1: 101, 2: 472, 3: 666, 4: 1445, 5: 1560, 6: 1780, 7: 2360, 8: 2760, 9: 3300}

BEAT_LABEL = {
    "hook": "钩子",
    "wrong": "错误答案",
    "setup": "铺陈",
    "body": "主体",
    "refute": "反驳",
}


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
# ymin/padding 等换算。实例：KP2 镜4 把参考线写成 170+280-v/1.25*280，忽略了
# errbar 的 ymin=-0.1，参考线整体偏低 22.4px，于是画面说「A 明显偏离真值」而
# 字幕说「A 已收敛到 0.50」—— 图文互相矛盾，且两个检查器都没抓到。
TRANSFORM_PRIMS = ["errbar", "bars", "morphBars", "fillBars", "gridworld", "sweepGrid", "mdpChain"]


def check_shot(kp, i, sh):
    """组装前的内容自检。发现不一致就直接失败，不要产出一部带已知缺陷的片子。"""
    js = sh["draw_js"]
    used = [a for a in ANIM_PRIMS if re.search(r"\b" + a + r"\(", js)]
    flag = bool(sh.get("animated"))
    if flag and not used:
        raise SystemExit(
            "KP%d 镜%d：animated=true 但 draw_js 里没有任何动画原语。\n"
            "  watch 会承诺一个不会发生的运动（实例：KP2 镜4 的「A 那根从贯穿全图收缩」）。\n"
            "  要么补上动画原语，要么把 animated 改为 false 并改写 watch。" % (kp, i))
    if used and not flag:
        raise SystemExit(
            "KP%d 镜%d：用了动画原语 %s 但 animated=false —— 这一镜不会被要求写 watch。"
            % (kp, i, used))
    # 坐标手算检查：该镜若调用了会返回变换的原语，位置实参里就不该出现数字算式
    if any(re.search(r"\b" + p + r"\(", js) for p in TRANSFORM_PRIMS):
        # 必须先剥字符串字面量再找算式 —— 否则 note("总和 = 10+9+…+1 = 55") 里
        # 文字内部的算式会被当成手算坐标。这个假阳性形态在本项目里已经出现过三次。
        code = _strip_strings(js)
        for m in re.finditer(r"\b(?:arrow|note|boxNode|link)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", code):
            if re.search(r"\d+\s*[+\-]\s*\d+\s*[+\-*/]", m.group(1)):
                print("  ! KP%d 镜%d 警告：坐标像是手算的（%s…）。"
                      "该镜调用了会返回坐标变换的原语，应当用它的返回值定位。"
                      % (kp, i, m.group(0)[:52]))


def build_episode(ep):
    """一集 -> 一段 KP(...) 源码。"""
    kp = ep["kp"]
    name = KP_NAMES.get(kp, str(kp))
    base = KP_BASE.get(kp, 0)
    out = ['KP(%s,function(){' % js_str(name)]

    for i, sh in enumerate(ep["shots"]):
        check_shot(kp, i, sh)
        t = base + i * 12          # 同一集内各镜时间码递增，便于跳转定位
        beat = BEAT_LABEL.get(sh["beat"], sh["beat"])
        out.append("  /* %s */" % beat)
        out.append("  S(%d,function(){" % t)
        out.append("      " + indent(sh["draw_js"]))
        # 动画镜的「看什么」放在讲解段落**开头**，不画在画布上。
        # 原来画在 y=626 —— 那在字幕带里面（实测字幕带从 y≈480 起），10 个动画镜
        # 全被盖住。讲解段落就在画布正下方、是阅读通道，放这里既满足「事先告知」
        # 又零版面风险。
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


def main():
    path = os.path.join(HERE, "episodes-L01.json")
    eps = json.loads(io.open(path, encoding="utf-8").read())
    eps.sort(key=lambda e: e["kp"])
    have = [e["kp"] for e in eps]
    missing = [k for k in range(1, 10) if k not in have]
    if missing:
        print("警告：缺少 KP %s —— 先补齐再出正式版" % missing)

    C = []
    C.append('''
var CFG={
  title:"CS234 · Lecture 1 · 强化学习导论",
  subtitle:"%d 个知识点 · 每集六拍：钩子 → 错误答案 → 铺陈 → 主体 → 反驳 → 检验 · 空格推进 · N 开关讲解",
  video:"https://www.youtube.com/watch?v=FgzM3zpZ55o&t="
};

// Mars rover 值函数：V(s7)=10/(1-g)，V(si)=(r_i+0.5g V(si+1))/(1-0.5g)
function rover(g){var v=[];v[6]=10/(1-g);
  for(var i=5;i>=0;i--)v[i]=((i===0?1:0)+0.5*g*v[i+1])/(1-0.5*g);return v;}

KP("开场",function(){
  S(0,function(){clearScene();setEq(null);setBig(null);setCap(null);
    setTitle("CS234 · Lecture 1","强化学习导论",
      "Emma Brunskill · Winter 2019 · 每个知识点都先说出你可能持有的错误模型，再回去杀掉它");},
    "这一讲本身不证明任何东西 —— 它建立词汇表。但本片的结构不是照搬讲座：每个知识点都按六拍走，其中第二拍会<b>同情地说出一个貌似合理的错误模型</b>，第五拍再回去指名杀掉它。这么做有实证依据：在教学研究里，正面撞击学习者的错误模型带来的效应（d≈0.79–0.83）大约是「用动画而非静态图」（d≈0.37）的两倍。干净的讲解会让人觉得更清楚、更省力，而这恰恰是问题 —— 没有碰撞，新解释会被归档在旧模型旁边，而不是替换掉它。");
});
''' % len(eps))

    for ep in eps:
        C.append(build_episode(ep))

    C.append('''
KP("完",function(){
  S(3600,function(){clearScene();setBig(null);setCap(null);setEq(null);
    setTitle("CS234 · Lecture 1 · 完","词汇表已经建好，下一讲开始有定理",
      "L2 · Given a Model of the World：Bellman 算子的 γ-压缩性 / 值迭代收敛速率 / 策略改进定理");},
    "回头看这九集，每一集都是同一个形状：先抛出一个具体问题，再说出一个你很可能真的持有过的错误模型，然后用一个带真实数字的实例把它撞碎，最后指名回去宣告它错在哪里。<b>如果你读完只记住一件事，记住那九个错误模型</b> —— 它们比九条正确结论更难得，因为正确结论到处都能查到，而「你原本以为的那样为什么不成立」通常没人写出来。L2 开始就有真正要证的定理了。");
});
''')

    body = "\n\n".join(C)
    bc.write("L01-强化学习导论.html", "CS234 L1 · 强化学习导论 · 放映厅", body)

    # 顺手报告一下结构，便于核对六拍是否齐全
    print()
    for ep in eps:
        beats = [s["beat"] for s in ep["shots"]]
        anim = sum(1 for s in ep["shots"] if s["animated"])
        lack = [b for b in ("hook", "wrong", "setup", "body", "refute") if b not in beats]
        print("  KP%-2d %d镜 动画%d镜  %s%s"
              % (ep["kp"], len(ep["shots"]), anim, beats,
                 ("  缺拍:" + str(lack)) if lack else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
