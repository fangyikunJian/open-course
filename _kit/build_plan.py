# -*- coding: utf-8 -*-
"""plan.json → ★科研学习清单.html。十个条目各一行，带材料链接与验收勾选。

    python _kit/build_plan.py

配色与精读页同一套变量（`coursekit/theme.py` 的 LIGHT / DARK），浅色为默认。

**勾选状态存 localStorage，键一律带 `plan-` 前缀。** `file://` 下所有本地页面
共用一个 origin，不加前缀会和各课精读的自测记录撞键 —— coursekit 的 README
里已经为这件事付过一次学费。读写都包在 try/catch 里：隐私窗口或站点数据被清时，
localStorage 的访问本身就会抛。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, os.path.join(HERE, "coursekit"))
import theme  # noqa: E402


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# 条目正文里允许作者写 <b>，所以这一支不转义 —— 内容是自己写的，不是外来输入。
def raw(s):
    return str(s)


STATUS = {"todo": ("待开工", "s-todo"),
          "doing": ("进行中", "s-doing"),
          "done": ("已完成", "s-done")}

CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.75 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:38px 20px 90px}
header{margin-bottom:34px}
h1{font-size:26px;margin:0 0 10px;letter-spacing:-.2px}
.lede{color:var(--ink3);font-size:14.5px;margin:0;max-width:72ch}
.bar{display:flex;align-items:center;gap:10px;margin:22px 0 0}
.bar .prog{flex:1;height:6px;border-radius:99px;background:var(--sunken);overflow:hidden}
.bar .prog i{display:block;height:100%;background:var(--acc);width:0;transition:width .3s}
.bar .pct{font:12px var(--mono);color:var(--dim);min-width:8ch;text-align:right}
.item{border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:14px 0;
  background:var(--panel)}
:root:not([data-theme="dark"]) .item{box-shadow:var(--shadow)}
.item h2{font-size:17px;margin:0 0 8px;display:flex;align-items:baseline;gap:10px;
  letter-spacing:-.1px}
.item h2 .n{font:12px var(--mono);color:var(--dim);border:1px solid var(--line2);
  border-radius:99px;padding:1px 9px;flex:none}
.why{margin:0 0 10px;color:var(--ink2);font-size:14px}
.meta{margin:0 0 12px;font:12px var(--mono);color:var(--dim);letter-spacing:.2px}
.meta .st{border-radius:99px;padding:1px 9px;border:1px solid currentColor;margin-left:8px}
.s-todo{color:var(--dim)} .s-doing{color:var(--acc2)} .s-done{color:var(--acc)}
.note{border-left:3px solid var(--line2);background:var(--lift2);border-radius:0 8px 8px 0;
  padding:9px 13px;margin:0 0 12px;font-size:13px;line-height:1.7;color:var(--ink3)}
.mats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.mat{font-size:12.5px;text-decoration:none;color:var(--blue);border:1px solid var(--line2);
  border-radius:99px;padding:4px 12px;background:var(--tintblue)}
.mat:hover{border-color:var(--blue)}
.checks{border-top:1px dashed var(--line);padding-top:11px}
.ck{display:flex;gap:9px;align-items:flex-start;font-size:13.5px;line-height:1.7;
  padding:4px 0;cursor:pointer}
.ck input{margin:6px 0 0;flex:none;accent-color:var(--acc);width:15px;height:15px}
.ck.on span{color:var(--dim);text-decoration:line-through}
.chead{font:11.5px var(--mono);color:var(--dim);letter-spacing:.4px;margin-bottom:4px}
footer{margin-top:40px;font-size:12px;color:var(--dim);text-align:center}
#themeBtn{position:fixed;top:14px;right:16px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-radius:8px;padding:6px 11px;cursor:pointer;
  font-size:14px;line-height:1}
@media(max-width:640px){.wrap{padding:24px 14px 70px}h1{font-size:22px}}
"""

TPL = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}}</title>
<style>
:root{{{LIGHT}}
  --sans:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  --mono:"JetBrains Mono",Consolas,"Courier New",monospace;
}}
:root[data-theme="dark"]{{{DARK}}}
html{color-scheme:light dark}
{{CSS}}
</style></head><body>
<button id="themeBtn" title="切换主题">☾</button>
<div class="wrap">
<header>
  <h1>{{TITLE}}</h1>
  <p class="lede">{{LEDE}}</p>
  <div class="bar"><div class="prog"><i id="pi"></i></div><span class="pct" id="pt"></span></div>
</header>
{{ROWS}}
<footer>{{CREDIT}}</footer>
</div>
<script>
(function(){
  /* 主题。与精读页同一个开关行为，但键不同 —— 两者可以各记各的。 */
  var root=document.documentElement, btn=document.getElementById("themeBtn");
  function get(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
  function set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
  function paint(){
    var d=root.getAttribute("data-theme")==="dark";
    btn.textContent=d?"☀":"☾";
  }
  if(get("plan-theme")==="dark") root.setAttribute("data-theme","dark");
  paint();
  btn.onclick=function(){
    var d=root.getAttribute("data-theme")==="dark";
    if(d) root.removeAttribute("data-theme"); else root.setAttribute("data-theme","dark");
    set("plan-theme", d?"light":"dark"); paint();
  };

  /* 勾选。键带 plan- 前缀：file:// 下所有本地页共用一个 origin，
     不加前缀会和各课精读的自测记录撞键。 */
  var boxes=[].slice.call(document.querySelectorAll(".ck input"));
  function tally(){
    var n=boxes.filter(function(b){ return b.checked; }).length;
    document.getElementById("pi").style.width=(boxes.length?n/boxes.length*100:0)+"%";
    document.getElementById("pt").textContent=n+" / "+boxes.length;
  }
  boxes.forEach(function(b){
    if(get(b.dataset.k)==="1"){ b.checked=true; b.closest(".ck").classList.add("on"); }
    b.addEventListener("change", function(){
      set(b.dataset.k, b.checked?"1":"0");
      b.closest(".ck").classList.toggle("on", b.checked);
      tally();
    });
  });
  tally();
})();
</script>
</body></html>
"""


def build(p):
    rows = []
    for it in p["items"]:
        label, cls = STATUS.get(it["status"], STATUS["todo"])
        mats = "".join(
            '<a class="mat" href="%s" target="_blank" rel="noopener">%s</a>'
            % (esc(m["href"]), esc(m["t"])) for m in it.get("mats", []))
        checks = "".join(
            '<label class="ck"><input type="checkbox" data-k="plan-check-%d-%d">'
            '<span>%s</span></label>' % (it["n"], i, raw(c))
            for i, c in enumerate(it.get("checks", [])))
        rows.append(
            '<section class="item">'
            '<h2><span class="n">%d</span>%s</h2>'
            '<p class="why">%s</p>'
            '<p class="meta">%s · %s<span class="st %s">%s</span></p>'
            '%s<div class="mats">%s</div>'
            '<div class="checks"><div class="chead">验收标准</div>%s</div>'
            '</section>'
            % (it["n"], esc(it["title"]), raw(it["why"]),
               esc(it["tier"]), esc(it["when"]), cls, label,
               ('<p class="note">%s</p>' % raw(it["note"])) if it.get("note") else "",
               mats, checks))

    html = TPL
    for a, b in (("{{LIGHT}}", theme.LIGHT), ("{{DARK}}", theme.DARK),
                 ("{{CSS}}", CSS), ("{{TITLE}}", esc(p["title"])),
                 ("{{LEDE}}", raw(p["lede"])),
                 ("{{CREDIT}}", esc(p.get("credit", ""))),
                 ("{{ROWS}}", "\n".join(rows))):
        html = html.replace(a, b)
    left = [t for t in ("{{LIGHT}}", "{{DARK}}", "{{CSS}}", "{{TITLE}}",
                        "{{LEDE}}", "{{CREDIT}}", "{{ROWS}}") if t in html]
    assert not left, "模板里还有没填的占位符：%s" % left
    return html


def main():
    p = json.load(io.open(os.path.join(ROOT, "plan.json"), encoding="utf-8"))
    html = build(p)
    out = os.path.join(ROOT, "★科研学习清单.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write(html)
    nc = sum(len(i.get("checks", [])) for i in p["items"])
    nm = sum(len(i.get("mats", [])) for i in p["items"])
    print("写出 %s（%d 个条目，%d 条验收，%d 个材料链接）"
          % (os.path.basename(out), len(p["items"]), nc, nm))


if __name__ == "__main__":
    main()
