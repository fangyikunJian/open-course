# -*- coding: utf-8 -*-
"""生成精读页：左边是那一页课件，右边是这一页的讲解 + 自测。

    python coursekit/build_reader.py                  # 当前课程，全部重建
    python coursekit/build_reader.py L02 L03          # 只建这几讲
    python coursekit/build_reader.py 别的课/course.json

引擎（版面、翻页、自测、错题本、复习模式）在 reader_template.html 里，
一份；讲次元数据在 course.json 里；每讲的内容在 <data>/<tag>.json 里。
改自测逻辑只动模板，不必在十几个文件里各改一遍。

数据文件的形状（只有这两个键）：

    {
      "notes": [
        {"r":[3,7],                 起止页；同一张图的几个阶段算一条
         "t":"标题",
         "star":2,                  0–3，越高越该停下来看
         "one":"一句话",
         "eq":"式子",               纯文本，不排版 LaTeX，换行用 \\n
         "pts":["要点", …],
         "say":"讲稿里补的（课件上没有）",
         "tip":{"t":"标签","v":"内容","w":1}},   w=1 用醒目底色
        …
      ],
      "quiz": { "3": [{"q":"题面","o":["选项",…],"a":1,"why":"解释"}, …], … }
    }

硬规矩（违反就不出片，详见 README）：
  · quiz 的键必须是某个 notes 条目的起始页，否则那些题永远显示不出来
  · 正确项下标 a 必须落在 o 的范围内，选项不少于 3 个，且必须给 why
  · notes 的页码区间不许重叠，也不许超出该讲的 pages
"""
import io
import json
import os
import re
import sys

# 报告里全是中文，而 Windows 默认控制台是 cp1252 —— 不重设就在第一个
# print 上抛 UnicodeEncodeError。实测：改动前的版本在默认控制台下从来跑不起来，
# 只有环境里预先带了 PYTHONIOENCODING 才行。ML 版一直有这一行，这边漏了。
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _course  # noqa: E402
import theme  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "reader_template.html")

# 目标密度。不取 ML 版的 650，因为 CS234 页面更稀（大量页是上一页的增量构建）。
# 基线：改造前 L01 是 65 词/页。
DENSITY_MIN = 400
# 课件英文原话的覆盖下限，分母是有讲解的页。
QUOTE_COVER_MIN = 0.80
# 表格：每 4 页有讲解至少 1 张。
TBL_PER_PAGES = 4
# 科研格的出处档位，三档与 research/00-BRIEFING 的原始标注一致。
# 多一档少一档都不行 —— 把【待核】写成断言是本项目明确要防的事故。
RES_TAGS = ("已核", "推断", "待核")

# 「词」在本项目里只有这一个定义：剥掉 HTML 标签后，CJK 按单字、拉丁按词、
# 数字成串。密度闸门、覆盖率、报告里的每一个数都用它，不许另写一份 ——
# 两份实现会让同一个闸门在不同期给出不可比的数。
_TAG = re.compile(r"<[^>]+>")
_WORD = re.compile(r"[一-鿿]|[A-Za-z]+|[0-9.]+")


def wordcount(obj):
    """任意嵌套结构里的词数。"""
    if isinstance(obj, str):
        return len(_WORD.findall(_TAG.sub("", obj)))
    if isinstance(obj, dict):
        return sum(wordcount(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return sum(wordcount(v) for v in obj)
    return 0


def density(notes):
    """(词数, 有讲解的页数, 词/页)。分母是**被 notes 覆盖的页**，
    不是该讲总页数 —— 未覆盖页是增量构建页，本来就允许留空。"""
    pages = set()
    for n in notes:
        r = n.get("r")
        if isinstance(r, list) and len(r) == 2:
            pages.update(range(r[0], r[1] + 1))
    w = wordcount(notes)
    return w, len(pages), (w / len(pages) if pages else 0.0)


def field_cover(notes, key):
    """有该字段的页 / 有讲解的页。分母与密度一致。"""
    tot, cov = set(), set()
    for n in notes:
        r = n.get("r")
        if not (isinstance(r, list) and len(r) == 2):
            continue
        rng = range(r[0], r[1] + 1)
        tot.update(rng)
        if n.get(key):
            cov.update(rng)
    return (len(cov) / len(tot)) if tot else 0.0


def check_tbl(notes):
    """表格的结构问题。列数对不上表头，页面上会表现为「最后一格空着」，
    而不是报错 —— 所以必须机械查。"""
    out = []
    for n in notes:
        t = n.get("tbl")
        if not t:
            continue
        head = t.get("head")
        if not (isinstance(head, list) and head):
            out.append("p%s 的表格没有表头" % (n.get("r"),))
            continue
        for i, row in enumerate(t.get("rows") or []):
            if len(row) != len(head):
                out.append("p%s 表格第 %d 行 %d 格，表头 %d 列"
                           % (n.get("r"), i + 1, len(row), len(head)))
    return out


def check_res(notes):
    """科研格的格式问题。这些一律硬拦，与分片有没有声明 `_目标` 无关 ——
    把【待核】写成断言、或不给出处，正是本项目全部规矩要防的那类事故。"""
    out = []
    for n in notes:
        r = n.get("res")
        if not r:
            continue
        if r.get("tag") not in RES_TAGS:
            out.append("p%s 的科研格标记 %r 不在 %s 里"
                       % (n.get("r"), r.get("tag"), "/".join(RES_TAGS)))
        if not r.get("ref"):
            out.append("p%s 的科研格没有给出处" % (n.get("r"),))
        if not r.get("v"):
            out.append("p%s 的科研格是空的" % (n.get("r"),))
    return out


def check_link(notes):
    """「你学过的对应」必须同时有 t 与 href。

    只有文字没有链接，在页面上是一个**点不动的假链接** —— 读者会以为自己
    漏点了，比根本不写更糟。缺 t 则是一个没有标题的空框。"""
    out = []
    for n in notes:
        k = n.get("link")
        if not k:
            continue
        if not k.get("t"):
            out.append("p%s 的 link 没有显示文字" % (n.get("r"),))
        if not k.get("href"):
            out.append("p%s 的 link 没有 href" % (n.get("r"),))
    return out


def check(co, L, d):
    """把能机械检查的都查掉。放过去的错，在页面上只表现为『那道题不见了』。

    密度与覆盖率类闸门按**分片**度量，由分片自己声明 `_目标` 来开启 ——
    没有全局豁免开关，也就没有「忘了摘掉」这回事。
    """
    bad = []
    tag, pages = L["tag"], L["pages"]
    notes = d.get("notes") or []
    if not notes:
        bad.append("notes 是空的")

    seen = {}
    for n in notes:
        r = n.get("r")
        if not (isinstance(r, list) and len(r) == 2 and 1 <= r[0] <= r[1] <= pages):
            bad.append("页码区间不合法：%r（该讲共 %s 页）" % (r, pages))
            continue
        for p in range(r[0], r[1] + 1):
            if p in seen:
                bad.append("第 %d 页被两条讲解抢：「%s」和「%s」"
                           % (p, seen[p], n.get("t")))
            seen[p] = n.get("t")
        if not n.get("t"):
            bad.append("%s 这条没有标题" % (r,))

    starts = set(n["r"][0] for n in notes if isinstance(n.get("r"), list))
    for k, qs in (d.get("quiz") or {}).items():
        if not str(k).isdigit():
            bad.append("题库键 %r 不是页码" % k)
            continue
        if int(k) not in starts:
            bad.append("题库键 %s 不是任何讲解单元的起始页 —— 这些题永远显示不出来" % k)
        for i, q in enumerate(qs):
            o = q.get("o") or []
            if len(o) < 3:
                bad.append("%s 第 %d 题只有 %d 个选项" % (k, i + 1, len(o)))
            if not isinstance(q.get("a"), int) or not (0 <= q["a"] < len(o)):
                bad.append("%s 第 %d 题的正确项下标 %r 越界" % (k, i + 1, q.get("a")))
            if not q.get("why"):
                bad.append("%s 第 %d 题没有给解释" % (k, i + 1))
            if not q.get("q"):
                bad.append("%s 第 %d 题没有题面" % (k, i + 1))

    if not os.path.exists(co.abspath("%s/%s" % (co.dirs["slides"], L["pdf"]))):
        bad.append("找不到课件 %s" % L["pdf"])

    # 空页不算错 —— 有些页确实只是上一页的增量构建，页面会明说「往前翻一页」。
    # 但必须报出来，否则漏写一页和故意留空看起来一模一样。
    gaps = [p for p in range(1, pages + 1) if p not in seen]
    if gaps:
        print("   %s 有 %d 页没有讲解：%s" % (tag, len(gaps), gaps))

    # ── 逐片度量。打印实际数字，不打印「通过」——PROJECT-SKILL §13。
    #
    # 为什么按片而不按整讲：加厚是**逐片**推进的。78 页里厚了 19 页，整讲均值
    # 仍然不及格，于是「这一片做到了」这件事在报告里看不见，而下一片做完之前
    # 什么都验不了。分片既是写作单位就该是度量单位。
    #
    # 闸门由**分片自己声明** `_目标` 来开启，没声明的只报数不拦。这样加厚一片
    # 就给它加上目标、永久生效 —— 不需要一个全局豁免开关，也就没有「忘了摘掉」
    # 这回事。（上一版用的 --soft-density 就是一张自己发给自己的假绿灯许可证。）
    shard_of = d.get("_shard_of") or [""] * len(notes)
    targets = d.get("_targets") or {}
    groups = {}
    for n, sh in zip(notes, shard_of):
        groups.setdefault(sh, []).append(n)

    for sh in (d.get("_shards") or []):
        g = groups.get(sh) or []
        if not g:
            continue
        tg = targets.get(sh)
        gw, gcov, gper = density(g)
        gqc = field_cover(g, "quote")
        gtbl = sum(1 for n in g if n.get("tbl"))
        if tg:
            dmin = tg.get("密度", DENSITY_MIN)
            qmin = tg.get("quote覆盖", QUOTE_COVER_MIN)
            tper = tg.get("表格每N页", TBL_PER_PAGES)
            need = max(1, gcov // tper)
            print("   %s  %-14s %2d页 %5d词 %4.0f词/页%s  quote %3.0f%%%s  表格 %d/%d%s  [已声明目标]"
                  % (tag, sh, gcov, gw, gper, "✓" if gper >= dmin else "✗",
                     gqc * 100, "✓" if gqc >= qmin else "✗",
                     gtbl, need, "✓" if gtbl >= need else "✗"))
            if gper < dmin:
                bad.append("%s 密度 %.0f 词/页 低于自己声明的 %d" % (sh, gper, dmin))
            if gqc < qmin:
                bad.append("%s quote 覆盖 %.0f%% 低于自己声明的 %.0f%%"
                           % (sh, gqc * 100, qmin * 100))
            if gtbl < need:
                bad.append("%s 表格 %d 张，%d 页至少要 %d 张" % (sh, gtbl, gcov, need))
        else:
            print("   %s  %-14s %2d页 %5d词 %4.0f词/页   quote %3.0f%%   表格 %d"
                  "   [未声明目标，只报数]" % (tag, sh, gcov, gw, gper, gqc * 100, gtbl))

    w, cov, per = density(notes)
    print("   %s  ── 整讲 %d 页 %d 词 %.0f 词/页 ──" % (tag, cov, w, per))

    # 表格结构错误（列数对不上表头）一律硬拦：页面上它表现为「最后一格空着」
    # 而不是报错，所以只能机械查。
    bad += check_tbl(notes)

    # 科研格：格式错误一律硬拦，与有没有声明目标无关。
    # **不设数量下限** —— 允许整讲为 0。L04/L06 预期就是 0。设了下限会逼出
    # 凑出来的连接，而凑出来的连接比没有连接更坏：它会让人以后分不清哪条是真的。
    bad += check_res(notes)
    nres = sum(1 for n in notes if n.get("res"))
    print("   %s  科研格 %d 条（%s）" % (tag, nres, " ".join(
        "%s%d" % (t, sum(1 for n in notes
                         if (n.get("res") or {}).get("tag") == t))
        for t in RES_TAGS)))

    # link 同理不设数量下限：不是每一页都该有「你学过的对应」，硬凑等于噪声。
    bad += check_link(notes)
    nlink = sum(1 for n in notes if n.get("link"))
    print("   %s  你学过的对应 %d 条" % (tag, nlink))

    if bad:
        print("!! %s" % tag)
        for b in bad:
            print("     " + b)
    return not bad


def render(co, L, d, th=None):
    s = io.open(TPL, encoding="utf-8").read()
    notes = ",\n".join(json.dumps(n, ensure_ascii=False) for n in d["notes"])
    quiz = ",\n".join(
        "%s: %s" % (k, json.dumps(v, ensure_ascii=False))
        for k, v in sorted((d.get("quiz") or {}).items(), key=lambda kv: int(kv[0])))
    # 精读页在 dirs.reader 里，课件在 dirs.slides 里，两者之间的相对路径
    rel = os.path.relpath(co.abspath(co.dirs["slides"]),
                          co.abspath(co.dirs["reader"])).replace("\\", "/")
    sub = [
        ("{{NOTES}}", "var N = [\n%s\n];" % notes),
        ("{{QUIZ}}", "var Q = {\n%s\n};" % quiz),
        # 讲级科研主线卡。没有 <tag>.thread.json 就是 null，模板里按钮保持 hidden。
        ("{{THREAD}}", "var TH = %s;" % (
            json.dumps(th, ensure_ascii=False) if th else "null")),
        ("{{COURSE}}", co.c.get("prefix") or co.c["name"]),
        ("{{NUM_CN}}", L["num_cn"]),
        ("{{TITLE}}", L["title"]),
        ("{{PAGES}}", str(L["pages"])),
        ("{{PDFPATH}}", "%s/%s" % (rel, L["pdf"])),
        ("{{PDF}}", L["pdf"]),
        ("{{TAG}}", L["tag"]),
        ("{{KEY}}", "%s-%s" % (co.c.get("id") or "course", L["tag"].lower())),
        # 早期版本用的是不带课程前缀的键；模板里有一段一次性迁移会去找它
        ("{{OLDKEY}}", L["tag"].lower()),
        ("{{READERDIR}}", os.path.basename(co.dirs["reader"].rstrip("/"))),
        # 「打不开？」那段提示里要告诉读者在哪起 http.server。原来写死成
        # cs234-2019，换课就是一句错的指令。要服务的是**同时装得下课件与精读页**
        # 的那一层，即两者的公共祖先 —— 不是 co.root：CS234 的课件在
        # corpus/cs234-2019/slides、精读在 corpus/cs234-2019/中文精读，
        # 公共祖先是 corpus/cs234-2019，而 co.root 是课程目录本身，高了两层。
        ("{{COURSEDIR}}", os.path.basename(os.path.commonpath([
            co.abspath(co.dirs["slides"]), co.abspath(co.dirs["reader"])]))),
        ("{{READERFILE}}", os.path.basename(co.reader_file(L))),
    ]
    for a, b in sub:
        s = s.replace(a, b)
    left = [a for a, _ in sub if a in s]
    assert not left, "模板里还有没填的占位符：%s" % left
    # 最后一步：把写死暗色的壳改造成「浅色纸感默认 + ☾ 切暗色」。
    # ⚠ 这个函数的形参 th 是**科研主线**（co.load_thread），不是主题 —— 别改错。
    return theme.apply_theme(s)


def main():
    args = [a for a in sys.argv[1:]]
    cpath = None
    if args and (args[0].endswith(".json") or os.path.isdir(args[0])):
        cpath = args.pop(0)
    co = _course.Course(_course.find(cpath))

    okn = tried = 0
    for L in co.lectures(args or None):
        d = co.load_data(L)
        if d is None:
            if args:
                print("!! %s 还没有内容文件：%s" % (L["tag"], co.data_file(L)))
            continue
        tried += 1
        if not check(co, L, d):
            continue
        out = co.reader_file(L)
        d_ = os.path.dirname(out)
        if not os.path.isdir(d_):
            os.makedirs(d_)
        th = co.load_thread(L)
        io.open(out, "w", encoding="utf-8", newline="\n").write(render(co, L, d, th))
        nq = sum(len(v) for v in (d.get("quiz") or {}).values())
        print("%s  %d 页 · 讲解 %d 条 · 想一想 %d 题 · 主线卡 %s  →  %s"
              % (L["tag"], L["pages"], len(d["notes"]), nq,
                 "有" if th else "无", os.path.basename(out)))
        okn += 1

    print("\n生成 %d / %d 份（课程共 %d 讲）"
          % (okn, tried, len(co.c["lectures"])))
    if okn != tried:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
