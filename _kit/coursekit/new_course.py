# -*- coding: utf-8 -*-
"""给一门新课搭架子：扫一遍课件目录，生成 course.json 和空的内容目录。

    python coursekit/new_course.py "G:/open course/cs231n" --name "CS231n 计算机视觉" --prefix CS231n

    可选参数：
      --slides <子目录>   课件在哪（默认 slides）
      --reader <子目录>   精读页放哪（默认 中文精读）
      --id <标识>         存档键前缀，默认取目录名
      --force             已有 course.json 也覆盖

它只负责把骨架搭起来：讲次、课件文件名、页数都填好，**讲题是从 PDF 首页猜的，
基本都要手改**。之后按 README 写 <data>/<tag>.json，再跑 build_reader。
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _course  # noqa: E402


def page_count_and_title(p):
    """返回 (页数, 猜的讲题)。装了 pymupdf 就顺便猜个标题。"""
    try:
        import pymupdf
        d = pymupdf.open(p)
        n = len(d)
        title = ""
        if n:
            for line in d[0].get_text().split("\n"):
                line = line.strip()
                # 跳过太短的、纯数字的、以及作者/学期这类页脚
                if len(line) < 5 or line.isdigit():
                    continue
                if re.search(r"(Winter|Spring|Fall|Autumn|\d{4}|University|\d+\s*/\s*\d+)$", line):
                    continue
                title = line
                break
        return n, title
    except Exception:
        pass
    try:
        import pypdf
        return len(pypdf.PdfReader(p).pages), ""
    except Exception:
        return 0, ""


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        raise SystemExit(__doc__)
    root = os.path.abspath(args.pop(0))
    opt = {"slides": "slides", "reader": "中文精读", "name": None,
           "prefix": None, "id": None, "force": False}
    while args:
        a = args.pop(0)
        if a == "--force":
            opt["force"] = True
        elif a.startswith("--") and a[2:] in opt and args:
            opt[a[2:]] = args.pop(0)
        else:
            raise SystemExit("不认识的参数：%s" % a)

    if not os.path.isdir(root):
        raise SystemExit("目录不存在：%s" % root)
    sdir = os.path.join(root, opt["slides"])
    if not os.path.isdir(sdir):
        raise SystemExit("找不到课件目录：%s\n（用 --slides 指定别的子目录）" % sdir)

    out = os.path.join(root, "course.json")
    if os.path.exists(out) and not opt["force"]:
        raise SystemExit("已经有 %s 了。要覆盖请加 --force" % out)

    pdfs = sorted(f for f in os.listdir(sdir) if f.lower().endswith(".pdf"))
    if not pdfs:
        raise SystemExit("%s 里没有 PDF" % sdir)

    # 文件名里带编号就用它当讲次，否则按文件名顺序排
    lectures, used = [], set()
    for i, f in enumerate(pdfs, 1):
        m = re.search(r"(\d+)", f)
        n = int(m.group(1)) if m else i
        while n in used:            # 编号撞了就顺延，别让两讲同号
            n += 1
        used.add(n)
        pages, guess = page_count_and_title(os.path.join(sdir, f))
        lectures.append({
            "tag": "L%02d" % n,
            "num_cn": _course.num_cn(n),
            "title": guess or "（待填：这一讲讲什么）",
            "pdf": f,
            "pages": pages,
        })
    lectures.sort(key=lambda L: L["tag"])

    cid = opt["id"] or re.sub(r"[^a-z0-9]+", "-", os.path.basename(root).lower()).strip("-")
    name = opt["name"] or os.path.basename(root)
    prefix = opt["prefix"] or name.split()[0]
    reader = opt["reader"]

    course = {
        "id": cid,
        "name": name,
        "prefix": prefix,
        "heading": "%s · 中文学习站" % name,
        "lede": "<b>一讲一行</b>，点开看讲解清单。几种读法按你当下想花多少力气挑：",
        "credit": "（待填：原课件版权归谁）",
        "accent": "#f2bd63",
        "dirs": {
            "slides": opt["slides"],
            "reader": reader,
            "data": "%s/data" % reader,
        },
        "views": [
            {"key": "reader", "label": "精读", "color": "#8fb8ff",
             "hint": "左课件右讲解，一次一页，带自测与错题本",
             "href": "{reader}/{tag}-精读.html"},
            {"key": "slides", "label": "课件", "color": "#c79bf0",
             "hint": "原始课件", "href": "{slides}/{pdf}"},
        ],
        "lectures": lectures,
    }

    ddir = os.path.join(root, *course["dirs"]["data"].split("/"))
    if not os.path.isdir(ddir):
        os.makedirs(ddir)
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(course, ensure_ascii=False, indent=2) + "\n")

    # 给第一讲放一个能跑通的样例，照着改比对着文档写快
    first = lectures[0]
    sample = os.path.join(ddir, "%s.json" % first["tag"])
    if not os.path.exists(sample):
        io.open(sample, "w", encoding="utf-8", newline="\n").write(
            json.dumps({
                "notes": [
                    {"r": [1, 1], "t": "（样例）这一页讲什么",
                     "one": "一句话把这页的结论说完。",
                     "pts": ["要点一。", "要点二，可以用 <b>粗体</b> 和 <code>代码</code>。"],
                     "say": "讲稿里说了而课件上没有的话放这里。",
                     "tip": {"t": "提醒", "v": "需要单独拎出来的一条。"}},
                ],
                "quiz": {
                    "1": [{"q": "（样例）这一页的结论是？",
                           "o": ["错的选项", "对的选项", "另一个错的"],
                           "a": 1,
                           "why": "为什么是它，顺带补一句别处呼应的内容。"}]
                },
            }, ensure_ascii=False, indent=2) + "\n")

    print("写出 %s" % out)
    print("  %d 讲 · 课件目录 %s" % (len(lectures), opt["slides"]))
    print("  样例内容 %s" % os.path.relpath(sample, root))
    print("\n接下来：")
    print("  1. 打开 course.json，把 title / credit 改对（标题是从 PDF 首页猜的）")
    print("  2. 照样例写 %s/<tag>.json" % course["dirs"]["data"])
    print("  3. python %s %s" % (os.path.relpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_reader.py")), out))
    print("  4. node   %s %s" % (os.path.relpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_reader.js")), out))
    print("  5. python %s %s" % (os.path.relpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_hub.py")), out))


if __name__ == "__main__":
    main()
