# -*- coding: utf-8 -*-
"""把密度改写的结果验收后写回 episodes-*.json。

不直接相信 agent 的输出。每一集先过五道机械验收，全过才落盘；任何一条不过就
**整集退回**，保留原样并打印原因 —— 半套应用比不应用更危险（这条纪律在本项目
的 apply_amendments.py 里已经写过一次，同样适用）。

五道验收：
  1. 密度预算：自写 note ≤3 行 / 单行 ≤20 字 / 合计 ≤50 字
  2. 六拍齐全：hook / wrong / setup / body / refute 各至少一镜
  3. 标记残留：note 与 setEq 的文本里不许有 ** 或 HTML 标签（它们会原样显示）
  4. 动画一致：用了动画原语 <=> animated 为真 <=> 有 watch
  5. **数字保真**（最重要的一条）：旧版这一集里出现过的每一个数字，
     在新版这一集的「画布 + 字幕 + 讲解」里必须仍然出现。
     这一条专门抓「把画布上的论证删了、却没挪进 narration」这个失败形态，
     而它恰恰是机械可查的 —— 不需要再派一个 agent 去读。

用法：
    python apply_density.py <workflow-output.json>            # 空跑
    python apply_density.py <workflow-output.json> --apply    # 写盘
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)
Q = '"'

ANIM_PRIMS = ["trace", "morphBars", "fillBars", "sweepGrid", "reveal"]
BEATS = ("hook", "wrong", "setup", "body", "refute")
BUDGET = {"lines": 3, "longest": 20, "chars": 50}

# 数字：整数、小数、带负号；至少两位有效字符，避免把 s1/KP2 这类编号当数字
NUM = re.compile(r"[-−]?[0-9]+(?:[.][0-9]+)?")


def first_string_arg(src, i):
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
    out, i, tok = [], 0, name + "("
    while True:
        j = src.find(tok, i)
        if j < 0:
            return out
        if j > 0 and (src[j - 1].isalnum() or src[j - 1] in "_."):
            i = j + len(tok)
            continue
        s, k = first_string_arg(src, j + len(tok))
        if s is not None:
            out.append(s)
        i = max(k, j + len(tok))


def all_text(ep):
    """一集里全部人读得到的文字：画布 + 字幕 + 讲解 + watch。"""
    buf = []
    for sh in ep["shots"]:
        js = sh.get("draw_js", "")
        buf += calls(js, "note") + calls(js, "setCap") + calls(js, "setEq")
        buf += calls(js, "setBig")
        buf.append(sh.get("narration", ""))
        buf.append(sh.get("watch", ""))
    return "\n".join(buf)


def nums(text):
    """取出文本里的数字，归一化负号，丢掉纯编号那一类（长度 1 的整数）。"""
    out = set()
    for m in NUM.finditer(text.replace("−", "-")):
        s = m.group(0)
        if len(s.lstrip("-")) <= 1:      # 0–9 单个数字：多是 s1/第 2 步之类的编号
            continue
        out.add(s.lstrip("+"))
    return out


def check_unit(old_ep, shots):
    """返回 problems 列表；空列表 = 通过。"""
    p = []
    fake = {"kp": old_ep["kp"], "shots": shots}

    # 1. 密度
    for i, sh in enumerate(shots):
        t = calls(sh.get("draw_js", ""), "note")
        n, tot = len(t), sum(len(x) for x in t)
        lg = max((len(x) for x in t), default=0)
        if n > BUDGET["lines"] or lg > BUDGET["longest"] or tot > BUDGET["chars"]:
            p.append("镜%d 超预算：%d 行 / 最长 %d / 合计 %d" % (i, n, lg, tot))

    # 2. 六拍
    have = {sh.get("beat") for sh in shots}
    miss = [b for b in BEATS if b not in have]
    if miss:
        p.append("缺拍：%s" % miss)

    # 3. 标记残留
    for i, sh in enumerate(shots):
        js = sh.get("draw_js", "")
        for fn in ("note", "setEq", "setBig"):
            for s in calls(js, fn):
                if "**" in s:
                    p.append("镜%d %s 里有字面星号：%s" % (i, fn, s[:24]))
                if re.search(r"<[a-zA-Z/][^>]*>", s):
                    p.append("镜%d %s 里有 HTML 标签（会原样显示）：%s" % (i, fn, s[:24]))

    # 4. 动画一致
    for i, sh in enumerate(shots):
        js = sh.get("draw_js", "")
        used = [a for a in ANIM_PRIMS if re.search(r"\b" + a + r"\(", js)]
        flag = bool(sh.get("animated"))
        w = (sh.get("watch") or "").strip()
        if used and not flag:
            p.append("镜%d 用了 %s 但 animated 不为真" % (i, used))
        if flag and not used:
            p.append("镜%d animated 为真但没有动画原语" % i)
        if flag and not w:
            p.append("镜%d animated 为真但没写 watch" % i)
        if not flag and w:
            p.append("镜%d 不是动画镜却写了 watch" % i)

    # 5. 数字保真
    lost = sorted(nums(all_text(old_ep)) - nums(all_text(fake)))
    if lost:
        p.append("丢了 %d 个数字：%s" % (len(lost), ", ".join(lost[:12])))

    return p


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：python apply_density.py <workflow-output.json> [--apply]")
    apply = "--apply" in sys.argv
    payload = json.loads(io.open(sys.argv[1], encoding="utf-8").read())
    units = payload["units"] if isinstance(payload, dict) else payload
    if not units:
        print("没有可应用的单元。")
        return 1

    by_file = {}
    for u in units:
        by_file.setdefault(u["file"], []).append(u)

    okc = badc = 0
    for fname, us in sorted(by_file.items()):
        path = os.path.join(HERE, fname)
        eps = json.loads(io.open(path, encoding="utf-8").read())
        idx = {e["kp"]: e for e in eps}
        changed = False
        print("── %s" % fname)
        for u in sorted(us, key=lambda x: x["kp"]):
            kp = u["kp"]
            if kp not in idx:
                print("   KP%-2d ✗ 文件里没有这一集" % kp)
                badc += 1
                continue
            probs = check_unit(idx[kp], u["shots"])
            n_old = len(idx[kp]["shots"])
            n_new = len(u["shots"])
            if probs:
                badc += 1
                print("   KP%-2d ✗ 退回（%d→%d 镜）" % (kp, n_old, n_new))
                for x in probs[:6]:
                    print("          · %s" % x)
                continue
            okc += 1
            print("   KP%-2d ✓ %d→%d 镜   %s" % (kp, n_old, n_new, (u.get("moved") or "")[:46]))
            if apply:
                idx[kp]["shots"] = u["shots"]
                changed = True
        if apply and changed:
            io.open(path, "w", encoding="utf-8").write(
                json.dumps(eps, ensure_ascii=False, indent=1))
    print()
    print("通过 %d 集 · 退回 %d 集" % (okc, badc))
    print("（空跑。加 --apply 写盘）" if not apply else "已写盘。")
    return 0 if okc else 1


if __name__ == "__main__":
    sys.exit(main())
