# -*- coding: utf-8 -*-
"""course.json 的读取与路径解析。build_reader / build_hub 共用。

一条规矩：**course.json 所在的目录就是课程根目录**，里面所有路径都相对它。
脚本本身放在哪儿无所谓 —— 整个 coursekit/ 可以复制到任何地方，也可以放在
所有课程的上一层共用。
"""
import glob
import io
import json
import os

CN = "零一二三四五六七八九十"


def num_cn(n):
    """1 → 第一讲，13 → 第十三讲。course.json 里写了 num_cn 就以它为准。"""
    if n < 10:
        s = CN[n]
    elif n < 20:
        s = "十" + (CN[n - 10] if n > 10 else "")
    else:
        s = CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")
    return "第%s讲" % s


def find(arg=None):
    """定位 course.json：命令行给了就用给的，否则往上找三层。"""
    if arg:
        p = os.path.abspath(arg)
        if os.path.isdir(p):
            p = os.path.join(p, "course.json")
        if not os.path.exists(p):
            raise SystemExit("找不到 %s" % p)
        return p
    d = os.getcwd()
    for _ in range(4):
        p = os.path.join(d, "course.json")
        if os.path.exists(p):
            return p
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    raise SystemExit("当前目录往上找不到 course.json；"
                     "请显式给出路径：build_reader.py <course.json>")


def merge_shards(data_dir, tag):
    """读一讲的内容：单文件 <tag>.json，或分片 <tag>.a.json/.b.json/…

    分片是为了让一讲的内容可以分几次写出来，而不必一次性持有整份文件 ——
    加厚后单讲预计 200 KB 以上，改一处就要整体重写，风险和成本都不对。
    （放映厅那边在 150 KB 单文件上撞过这面墙，解法相同。）

    片间页码重叠直接报错：静默覆盖会丢掉一整段讲解。
    """
    one = os.path.join(data_dir, tag + ".json")
    parts = sorted(glob.glob(os.path.join(data_dir, tag + ".[a-z].json")))
    if os.path.exists(one) and parts:
        raise SystemExit(
            "%s：单文件与分片同时存在（%s 与 %s）。留一种，否则会少读一半。"
            % (tag, os.path.basename(one),
               " ".join(os.path.basename(p) for p in parts)))
    files = [one] if os.path.exists(one) else parts
    if not files:
        return None

    notes, quiz, shards, owner = [], {}, [], {}
    # 分片是**写作**的单位，所以也必须是**度量**的单位：加厚是逐片推进的，
    # 拿整讲平均去量，一片加厚了也看不出来（78 页里厚了 19 页 → 均值仍不及格）。
    # shard_of 与 notes 等长，记每条来自哪一片；targets 记每片自己声明的目标。
    # 不把片名写进 note 里，因为 wordcount 会把它当拉丁词算进去，污染密度数。
    shard_of, targets = [], {}
    for p in files:
        d = json.load(io.open(p, encoding="utf-8"))
        name = os.path.basename(p)
        shards.append(name)
        targets[name] = d.get("_目标")
        for n in d.get("notes") or []:
            shard_of.append(name)
            r = n.get("r")
            if isinstance(r, list) and len(r) == 2:
                for pg in range(r[0], r[1] + 1):
                    if pg in owner:
                        raise SystemExit(
                            "%s：第 %d 页在 %s 与 %s 里重叠 —— "
                            "静默覆盖会丢掉一整段讲解。"
                            % (tag, pg, owner[pg], name))
                    owner[pg] = name
            notes.append(n)
        for k, v in (d.get("quiz") or {}).items():
            if k in quiz:
                raise SystemExit("%s：题库键 %s 在多个分片里重复" % (tag, k))
            quiz[k] = v
    # 必须**成对**排序：notes 单独 sort 会让 shard_of 对不上号，
    # 于是每条讲解被算进错误的分片，密度报告全错而且不会报警。
    pairs = sorted(zip(notes, shard_of), key=lambda t: (t[0].get("r") or [10 ** 9])[0])
    notes = [n for n, _ in pairs]
    shard_of = [s for _, s in pairs]
    return {"notes": notes, "quiz": quiz, "_shards": shards,
            "_shard_of": shard_of, "_targets": targets}


class Course(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.root = os.path.dirname(self.path)
        self.c = json.load(io.open(self.path, encoding="utf-8"))
        for k in ("name", "dirs", "lectures"):
            if k not in self.c:
                raise SystemExit("course.json 缺字段：%s" % k)
        self.dirs = self.c["dirs"]
        for k in ("slides", "reader", "data"):
            if k not in self.dirs:
                raise SystemExit("course.json 的 dirs 缺字段：%s" % k)
        seen = set()
        for i, L in enumerate(self.c["lectures"]):
            for k in ("tag", "title", "pdf", "pages"):
                if k not in L:
                    raise SystemExit("第 %d 讲缺字段 %s" % (i + 1, k))
            if L["tag"] in seen:
                raise SystemExit("讲次 tag 重复：%s" % L["tag"])
            seen.add(L["tag"])
            L.setdefault("num_cn", num_cn(int("".join(
                ch for ch in L["tag"] if ch.isdigit()) or (i + 1))))

    # ── 路径 ──────────────────────────────────────────────────────
    def abspath(self, rel):
        """课程内相对路径 → 绝对路径。"""
        return os.path.join(self.root, *str(rel).replace("\\", "/").split("/"))

    def fill(self, tpl, L):
        """把 {tag} {pdf} {film} {slides} {reader} {data} 填进路径模板。
        模板里用到了这一讲没有的键（比如没拍成片的 {film}），返回 None。"""
        out = str(tpl)
        for k in ("slides", "reader", "data"):
            out = out.replace("{%s}" % k, self.dirs[k])
        for k in ("tag", "pdf", "film", "num_cn"):
            token = "{%s}" % k
            if token in out:
                if not L.get(k):
                    return None
                out = out.replace(token, str(L[k]))
        return out

    def views(self):
        return self.c.get("views") or []

    def lectures(self, want=None):
        ls = self.c["lectures"]
        if want:
            want = [w.upper() for w in want]
            ls = [L for L in ls if L["tag"].upper() in want]
            if not ls:
                raise SystemExit("没有匹配的讲次：%s" % " ".join(want))
        return ls

    def data_file(self, L):
        return self.abspath("%s/%s.json" % (self.dirs["data"], L["tag"]))

    def reader_file(self, L):
        name = self.c.get("reader_name", "{tag}-精读.html").replace("{tag}", L["tag"])
        return self.abspath("%s/%s" % (self.dirs["reader"], name))

    def load_data(self, L):
        """读这一讲的 notes + quiz；没有就返回 None。支持分片。"""
        d = merge_shards(self.abspath(self.dirs["data"]), L["tag"])
        if d is None:
            return None
        # 老格式在数据文件里也存了一份元数据，忽略即可，但对不上就报错
        for k in ("pdf", "pages"):
            if k in d and d[k] != L[k]:
                raise SystemExit("%s：数据文件里的 %s 与 course.json 不一致"
                                 % (L["tag"], k))
        return d

    def load_thread(self, L):
        """讲级科研主线卡；没有就返回 None。"""
        p = self.abspath("%s/%s.thread.json" % (self.dirs["data"], L["tag"]))
        if not os.path.exists(p):
            return None
        return json.load(io.open(p, encoding="utf-8"))
