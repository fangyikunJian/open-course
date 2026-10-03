# -*- coding: utf-8 -*-
"""生成 `G:\\open course\\★总入口.html` —— 所有内容的唯一入口。

    python _kit/build_portal.py

**它扫文件系统，不写死清单。** 理由很实际：CS234 那边有另一个会话在持续加讲，
今天写死的「十一讲」明天就是十三讲。每讲的四种读法（放映厅 / 速览 / 精读 /
课件）各自存在与否，都是现查的 —— 文件不在就把按钮灰掉，不会给出死链。

收录四块：
  ① 研究学习清单（plan.json 的十个条目，链到 ★科研学习清单.html 的锚点）
  ② CS234 强化学习      —— reinforcement learning/course.json
  ③ CS224R 深度强化学习 —— cs224r-2025/course.json
  ④ ARTI2001 课程材料   —— G:/Adelaide COMSC/.../Machine Learning（它有自己的总入口）

配色与各页同一套变量（coursekit/theme.py 的 LIGHT / DARK），浅色为默认。
搜索框是纯前端过滤，键入即筛，不依赖任何服务。
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, os.path.join(HERE, "coursekit"))
import theme     # noqa: E402
import _course   # noqa: E402

# ARTI2001 在另一棵树上。相对 ROOT 的路径 —— 两者同在 G: 盘，所以互链成立。
ARTI_REL = "../Adelaide COMSC/2026S2/Machine Learning"


TAG = re.compile(r"<[^>]+>")


def plain(s):
    """剥掉标记，只留可搜的文字。知识点里本来就带 <b>，搜索时不该把标签也搜进去。"""
    return TAG.sub("", str(s))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def url(rel):
    """站内相对路径 → 可点的 href（空格等按 URL 编码，中文保留可读）。"""
    return rel.replace("\\", "/").replace(" ", "%20").replace("#", "%23")


def course_rows(course_dir, cfg_name="course.json"):
    """扫一门课，返回 [(tag, num_cn, title, [(label, href, color, ok), ...])]。"""
    path = os.path.join(ROOT, course_dir, cfg_name)
    if not os.path.exists(path):
        return []
    co = _course.Course(path)
    rows = []
    for L in co.lectures():
        btns = []
        for v in co.views():
            rel = co.fill(v["href"], L)
            if rel is None:
                btns.append((v["label"], None, v.get("color"), False))
                continue
            full = co.abspath(rel)
            ok = os.path.exists(full)
            href = url(course_dir + "/" + rel) if ok else None
            btns.append((v["label"], href, v.get("color"), ok))
        rows.append((L["tag"], L.get("num_cn", ""), L["title"], L.get("kp") or [], btns))
    return rows


CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.7 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:34px 20px 90px}
h1{font-size:27px;margin:0 0 8px;letter-spacing:-.3px}
.lede{color:var(--ink3);font-size:14.5px;margin:0 0 20px;max-width:74ch}
.tools{display:flex;gap:10px;align-items:center;margin:0 0 26px;flex-wrap:wrap}
#q{flex:1;min-width:220px;background:var(--sunken);color:var(--ink);
  border:1px solid var(--line);border-radius:9px;padding:9px 13px;font:14px var(--sans)}
#q:focus{outline:none;border-color:var(--acc)}
.cnt{font:12px var(--mono);color:var(--dim)}
section{margin:0 0 30px}
h2{font-size:17px;margin:0 0 4px;display:flex;align-items:baseline;gap:10px}
h2 .n{font:11.5px var(--mono);color:var(--dim);border:1px solid var(--line2);
  border-radius:99px;padding:1px 9px}
.sub{color:var(--dim);font-size:13px;margin:0 0 12px}
.row{border:1px solid var(--line);border-radius:11px;padding:11px 14px;margin:8px 0;
  background:var(--panel);display:flex;gap:13px;align-items:flex-start;flex-wrap:wrap}
:root:not([data-theme="dark"]) .row{box-shadow:var(--shadow)}
.row .tag{font:12px var(--mono);color:var(--dim);min-width:54px;padding-top:3px}
.row .mid{flex:1;min-width:230px}
.row .ttl{font-weight:600;font-size:14.5px;margin-bottom:3px}
.row .kp{color:var(--dim);font-size:12.5px;line-height:1.6}
.btns{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
.b{font-size:12.5px;text-decoration:none;border-radius:99px;padding:4px 13px;
  border:1px solid var(--line2);white-space:nowrap}
/* 课程视图色（#7fd1c1 等）是给**暗场**配的淡彩，所以按钮文字一律用固定深墨，
   不跟主题走 —— 用 var(--bg) 的话浅色下是「近白字 + 淡彩底」，对比度只有 1.6。
   深墨对四个淡彩底都在 8.6:1 以上，两套主题都成立。 */
.b.on{color:#12161b;font-weight:600}
/* 清单里的材料按钮底色走变量（浅色下是深蓝），那种才该用 --bg 当字色 */
.b.var{color:var(--bg)}
.b.off{color:var(--dim);opacity:.42;cursor:default}
.card{border:1px solid var(--line);border-radius:11px;padding:14px 16px;margin:8px 0;
  background:var(--panel);display:flex;gap:14px;align-items:center;flex-wrap:wrap}
:root:not([data-theme="dark"]) .card{box-shadow:var(--shadow)}
.card .big{font-size:15px;font-weight:620;flex:1;min-width:200px}
.card .why{color:var(--ink3);font-size:13px;width:100%;margin-top:-4px}
.hide{display:none!important}
.empty{color:var(--dim);font-size:13.5px;padding:14px 2px}
footer{margin-top:36px;font-size:12px;color:var(--dim);text-align:center;line-height:1.9}
#themeBtn{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  border-radius:9px;padding:8px 12px;cursor:pointer;font-size:14px;line-height:1}
@media(max-width:620px){.wrap{padding:22px 13px 70px}h1{font-size:22px}}
"""

TPL = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>学习总入口</title>
<style>
:root{{{LIGHT}}
  --sans:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  --mono:"JetBrains Mono",Consolas,"Courier New",monospace;
}}
:root[data-theme="dark"]{{{DARK}}}
html{color-scheme:light dark}
{{CSS}}
</style></head><body>
<div class="wrap">
<h1>学习总入口</h1>
<p class="lede">{{LEDE}}</p>
<div class="tools">
  <input id="q" type="search" placeholder="搜讲次、标题、知识点…（例：PPO、老虎机、截断）" autocomplete="off">
  <span class="cnt" id="cnt"></span>
  <button id="themeBtn" title="切换主题">☾</button>
</div>
{{BODY}}
<footer>{{FOOT}}</footer>
</div>
<script>
(function(){
  var root=document.documentElement, btn=document.getElementById("themeBtn");
  function get(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
  function set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
  function paint(){ btn.textContent = root.getAttribute("data-theme")==="dark" ? "☀" : "☾"; }
  if(get("portal-theme")==="dark") root.setAttribute("data-theme","dark");
  paint();
  btn.onclick=function(){
    var d=root.getAttribute("data-theme")==="dark";
    if(d) root.removeAttribute("data-theme"); else root.setAttribute("data-theme","dark");
    set("portal-theme", d?"light":"dark"); paint();
  };

  /* 纯前端过滤。每一行把可搜的文字预先塞在 data-s 里（已小写）。 */
  var items=[].slice.call(document.querySelectorAll("[data-s]"));
  var secs=[].slice.call(document.querySelectorAll("section"));
  var q=document.getElementById("q"), cnt=document.getElementById("cnt");
  function run(){
    var k=q.value.trim().toLowerCase(), n=0;
    items.forEach(function(el){
      var hit = !k || el.dataset.s.indexOf(k)>=0;
      el.classList.toggle("hide", !hit);
      if(hit) n++;
    });
    secs.forEach(function(s){
      var any=s.querySelector("[data-s]:not(.hide)");
      s.classList.toggle("hide", !any);
    });
    cnt.textContent = k ? (n + " / " + items.length + " 条") : (items.length + " 条");
  }
  q.addEventListener("input", run);
  run();
  /* / 聚焦搜索框，Esc 清空 */
  document.addEventListener("keydown", function(e){
    if(e.key==="/" && document.activeElement!==q){ e.preventDefault(); q.focus(); }
    if(e.key==="Escape" && document.activeElement===q){ q.value=""; run(); q.blur(); }
  });
})();
</script>
</body></html>
"""


def render_course(title, note, rows, anchor):
    if not rows:
        return ('<section id="%s"><h2>%s</h2><p class="empty">（还没有内容）</p></section>'
                % (anchor, esc(title)))
    out = ['<section id="%s"><h2>%s<span class="n">%d 讲</span></h2>'
           '<p class="sub">%s</p>' % (anchor, esc(title), len(rows), note)]
    for tag, num_cn, ttl, kps, btns in rows:
        s = plain(" ".join([tag, num_cn, ttl] + list(kps))).lower()
        bs = []
        for label, href, color, ok in btns:
            if ok:
                bs.append('<a class="b on" style="background:%s;border-color:%s" href="%s">%s</a>'
                          % (color or "var(--acc)", color or "var(--acc)", href, esc(label)))
            else:
                bs.append('<span class="b off">%s</span>' % esc(label))
        # 知识点里作者写了 <b> 等标记，这里**不转义** —— 转义了会把标签原样印在页面上。
        # 内容是自己写的，不是外来输入。可搜文字那一侧已经用 plain() 剥过标签。
        kp = ("<div class='kp'>" + " · ".join(kps[:3]) + "</div>") if kps else ""
        out.append('<div class="row" data-s="%s"><div class="tag">%s</div>'
                   '<div class="mid"><div class="ttl">%s</div>%s</div>'
                   '<div class="btns">%s</div></div>'
                   % (esc(s), esc(tag), esc(ttl), kp, "".join(bs)))
    out.append("</section>")
    return "\n".join(out)


def main():
    plan = json.load(io.open(os.path.join(ROOT, "plan.json"), encoding="utf-8"))

    body = []

    # ① 研究学习清单
    body.append('<section id="plan"><h2>研究学习清单<span class="n">%d 个条目</span></h2>'
                '<p class="sub">十条，四个梯队。每条都绑着一个能拿去和导师讨论的产出。'
                '<a href="%s">打开完整清单 ↗</a></p>'
                % (len(plan["items"]), url("★科研学习清单.html")))
    for it in plan["items"]:
        s = " ".join([str(it["n"]), it["title"], it["why"], it["tier"]]).lower()
        st = {"todo": "待开工", "doing": "进行中", "done": "已完成"}.get(it["status"], "")
        mats = "".join(
            '<a class="b on var" style="background:var(--blue);border-color:var(--blue)" '
            'href="%s">%s</a>' % (esc(m["href"]), esc(m["t"]))
            for m in it.get("mats", [])[:2])
        body.append('<div class="card" data-s="%s"><div class="big">%d · %s</div>'
                    '<div class="btns"><span class="b off">%s</span>%s</div>'
                    '<div class="why">%s</div></div>'
                    % (esc(s), it["n"], esc(it["title"]), esc(st), mats, it["why"]))
    body.append("</section>")

    # ② CS234
    cs234 = course_rows("reinforcement learning")
    body.append(render_course(
        "CS234 强化学习 · 中文学习站",
        '斯坦福 Winter 2019（Emma Brunskill）。四种读法：放映厅看讲解、速览一屏滚到底、'
        '精读左课件右讲解带自测、课件是原件。<a href="%s">课程入口 ↗</a>'
        % url("reinforcement learning/index.html"),
        cs234, "cs234"))

    # ③ CS224R
    cs224r = course_rows("cs224r-2025")
    body.append(render_course(
        "CS224R 深度强化学习 · 中文学习站",
        '斯坦福 Spring 2025（Chelsea Finn）。补 CS234 2019 版没有的三块：'
        'PPO（L05）、RLHF/DPO（L09）、LLM 推理（L10）。<a href="%s">课程入口 ↗</a>'
        % url("cs224r-2025/index.html"),
        cs224r, "cs224r"))

    # ④ ARTI2001
    arti = []
    for label, rel, color in [
        ("课程总入口", "★总入口.html", "var(--acc)"),
        ("全部材料", "全部材料.html", "var(--blue)"),
        ("复习放映厅", "复习放映厅/★放映厅-总入口.html", "var(--acc2)"),
    ]:
        full = os.path.join(ROOT, ARTI_REL, rel)
        arti.append((label, url(ARTI_REL + "/" + rel) if os.path.exists(full) else None, color))
    btns = "".join(
        ('<a class="b on var" style="background:%s;border-color:%s" href="%s">%s</a>'
         % (c, c, h, esc(lb))) if h else ('<span class="b off">%s</span>' % esc(lb))
        for lb, h, c in arti)
    body.append(
        '<section id="arti"><h2>ARTI2001 机器学习<span class="n">本学期课程</span></h2>'
        '<p class="sub">Adelaide 的课，三个 Module。它有自己的一套总入口与材料清单，'
        '这里只做转接。</p>'
        '<div class="row" data-s="arti2001 机器学习 课程 m1 m2 m3 考试 复习">'
        '<div class="tag">课程</div><div class="mid"><div class="ttl">'
        'ARTI2001 全部课程材料</div><div class="kp">官方 PPT · Tutorial 与 Practical · '
        '逐页精读 · 备考包 · 复习放映厅</div></div>'
        '<div class="btns">%s</div></div></section>' % btns)

    n_items = (len(plan["items"]) + len(cs234) + len(cs224r) + 1)
    html = TPL
    for a, b in (("{{LIGHT}}", theme.LIGHT), ("{{DARK}}", theme.DARK), ("{{CSS}}", CSS),
                 ("{{LEDE}}", "一个入口，四块内容：研究学习清单、两门强化学习课的中文学习站、"
                              "以及本学期 ARTI2001 的全部材料。<b>按 / 搜索</b>，Esc 清空。"),
                 ("{{BODY}}", "\n".join(body)),
                 ("{{FOOT}}", "课件版权归各校与讲者；中文部分是配合原件阅读的学习笔记。<br>"
                              "本页由 <code>_kit/build_portal.py</code> 扫描文件系统生成 —— "
                              "加了新讲之后重跑一次即可，不必手改。")):
        html = html.replace(a, b)
    left = [t for t in ("{{LIGHT}}", "{{DARK}}", "{{CSS}}", "{{LEDE}}", "{{BODY}}", "{{FOOT}}")
            if t in html]
    assert not left, "模板里还有没填的占位符：%s" % left

    out = os.path.join(ROOT, "★总入口.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write(html)
    print("写出 %s" % os.path.basename(out))
    print("  研究清单 %d 条 · CS234 %d 讲 · CS224R %d 讲 · ARTI2001 1 块 ⇒ 共 %d 条"
          % (len(plan["items"]), len(cs234), len(cs224r), n_items))


if __name__ == "__main__":
    main()
