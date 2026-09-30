# -*- coding: utf-8 -*-
"""生成课程的唯一总入口 index.html（写在 course.json 旁边）。

    python coursekit/build_hub.py                 # 当前课程
    python coursekit/build_hub.py 别的课/course.json

为什么要有它：材料散在好几个地方——成片、速览、精读、原始课件，
每次都要想「那个东西在哪个文件夹」。所以只留一个入口：**一讲一行**，
一行里列出这一讲所有能打开的东西。没有的东西就灰掉，不假装有。

哪几种「读法」由 course.json 的 views 决定，路径模板里可以用
{tag} {pdf} {film} {slides} {reader} {data}。用到了这一讲没有的键
（比如还没拍成片的 {film}），那个按钮就自动灰掉。

所有链接都是相对路径，双击 index.html 就能用，不需要起服务。
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _course  # noqa: E402


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


CSS = """
:root{
  --bg:#0a0e14; --panel:#111823; --line:#1e2938; --ink:#e6edf6; --dim:#8494a8;
  --txt:#7f8fa4;
  --cjk:"PingFang SC","Microsoft YaHei","微软雅黑",system-ui,sans-serif;
  --mono:ui-monospace,"Cascadia Mono",Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font-family:var(--cjk);
  font-size:15px;line-height:1.65;padding:0 18px 70px}
.wrap{max-width:1120px;margin:0 auto}

header{padding:44px 0 22px}
h1{margin:0 0 10px;font-size:clamp(23px,3vw,34px);font-weight:670;letter-spacing:.3px}
.lede{color:var(--dim);font-size:14.5px;max-width:64ch;margin:0 0 18px}

/* 几种读法的图例 */
.legend{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:6px}
.lg{display:flex;align-items:center;gap:7px;border:1px solid var(--line);
  border-radius:9px;padding:7px 12px;background:var(--panel);font-size:13px}
.lg i{width:9px;height:9px;border-radius:3px;font-style:normal;flex:0 0 auto}
.lg b{font-weight:600}
.lg span{color:var(--dim)}

/* 一讲一行 */
.rows{margin-top:24px;border:1px solid var(--line);border-radius:14px;
  overflow:hidden;background:var(--panel)}
details{border-bottom:1px solid var(--line)}
details:last-child{border-bottom:0}
summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:14px;
  padding:13px 16px;transition:background .13s}
summary::-webkit-details-marker{display:none}
summary:hover{background:rgba(255,255,255,.028)}
.num{font:700 12px/1 var(--mono);letter-spacing:1px;flex:0 0 34px}
.nm{flex:1;font-size:15.5px;font-weight:600;min-width:0}
.nm em{font-style:normal;color:var(--dim);font-weight:400;font-size:13px;
  display:block;margin-top:2px}
.acts{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}
.a{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);
  border-radius:8px;padding:6px 11px;text-decoration:none;font-size:13px;
  background:#0b1017;white-space:nowrap;transition:border-color .13s,color .13s}
.a i{width:8px;height:8px;border-radius:2.5px;font-style:normal;flex:0 0 auto}
.a.txt{color:var(--txt)} .a.txt:hover{border-color:var(--txt)}
.a.off{color:#3b4657;border-style:dashed;pointer-events:none}
.kps{padding:2px 16px 16px 64px;margin:0;color:var(--dim);font-size:13.5px;
  line-height:1.72}
.kps li{margin-bottom:3px}
.more{display:flex;gap:7px;flex-wrap:wrap;padding:0 16px 14px 64px}
.none{padding:2px 16px 16px 64px;color:var(--dim);font-size:13.5px}

footer{margin-top:36px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--dim);font-size:13px;line-height:1.85}
footer b{color:var(--ink)}
@media (max-width:760px){
  summary{flex-wrap:wrap} .acts{width:100%;justify-content:flex-start;padding-left:48px}
  .kps,.more,.none{padding-left:20px}
}
"""


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    co = _course.Course(_course.find(arg))
    views = co.views()
    # 讲次编号那一列的颜色。默认取暖黄，和任何一种读法的配色都不撞。
    accent = co.c.get("accent") or "#f2bd63"

    # 每种读法各自的配色，只在这里生成一次
    vcss = "\n".join(
        ".a.v%d{color:%s} .a.v%d:hover{border-color:%s}"
        % (i, v.get("color", "#8fb8ff"), i, v.get("color", "#8fb8ff"))
        for i, v in enumerate(views))

    rows, have = [], dict((v["key"], 0) for v in views)
    for L in co.c["lectures"]:
        acts = []
        for i, v in enumerate(views):
            rel = co.fill(v["href"], L)
            if rel and os.path.exists(co.abspath(rel)):
                acts.append('<a class="a v%d" href="%s"><i style="background:%s"></i>%s</a>'
                            % (i, esc(rel), esc(v.get("color", "#8fb8ff")), esc(v["label"])))
                have[v["key"]] += 1
            else:
                acts.append('<span class="a off">%s</span>' % esc(v["label"]))

        # 展开后列什么：优先用精读的单元标题（任何课程都有），退而用 course.json 里的 kp
        d = co.load_data(L)
        items = ([n.get("t", "") for n in (d.get("notes") or [])] if d
                 else (L.get("kp") or []))
        sub = ("%d 条讲解" % len(items)) if d else (
            "%d 个知识点" % len(items) if items else "%d 页课件" % L["pages"])
        body = ('<ol class="kps">%s</ol>'
                % "".join("<li>%s</li>" % esc(x) for x in items)) if items else \
               '<div class="none">还没有中文讲解。</div>'

        more = []
        for m in (L.get("more") or []):
            more.append('<a class="a txt" href="%s">%s</a>'
                        % (esc(m["href"]), esc(m["label"])))
        if L.get("video"):
            more.append('<a class="a txt" href="%s" target="_blank" rel="noopener">'
                        '原讲座 ↗</a>' % esc(L["video"]))

        rows.append("""  <details>
    <summary>
      <span class="num" style="color:%s">%s</span>
      <span class="nm">%s<em>%s</em></span>
      <span class="acts">%s</span>
    </summary>
    %s
    <div class="more">%s</div>
  </details>""" % (esc(accent), esc(L["tag"]), esc(L["title"]), esc(sub),
                   "".join(acts), body, "".join(more)))

    legend = "\n".join(
        '    <span class="lg"><i style="background:%s"></i><b>%s</b>'
        '<span>%s</span></span>' % (esc(v.get("color", "#8fb8ff")),
                                    esc(v["label"]), esc(v.get("hint", "")))
        for v in views)
    tally = " · ".join("%s <b>%d</b>" % (esc(v["label"]), have[v["key"]]) for v in views)

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<style>%s%s</style>
</head>
<body><div class="wrap">

<header>
  <h1>%s</h1>
  <p class="lede">%s</p>
  <div class="legend">
%s
  </div>
</header>

<div class="rows">
%s
</div>

<footer>
  <b>%d 讲</b>：%s。灰掉的按钮表示还没做，不是坏链接。<br>
  全部是本地文件，<b>双击本页即可</b>，不需要起服务。
  精读页的自测成绩存在<b>这台机器的浏览器里</b>，换浏览器或清了站点数据就归零。<br>
  %s
</footer>

</div></body></html>
""" % (esc(co.c["name"]), CSS, vcss,
       co.c.get("heading") or esc(co.c["name"]),
       co.c.get("lede", ""), legend, "\n".join(rows),
       len(co.c["lectures"]), tally, co.c.get("credit", ""))

    out = os.path.join(co.root, co.c.get("hub", "index.html"))
    io.open(out, "w", encoding="utf-8", newline="\n").write(html)
    print("写出 %s" % os.path.normpath(out))
    print("  %d 讲 · %s" % (len(co.c["lectures"]),
                            " · ".join("%s %d" % (v["label"], have[v["key"]])
                                       for v in views)))


if __name__ == "__main__":
    main()
