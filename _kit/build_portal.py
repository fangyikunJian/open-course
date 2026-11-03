# -*- coding: utf-8 -*-
"""生成 `G:\\open course\\★总入口.html` —— 所有内容的唯一入口。

    python _kit/build_portal.py

**它扫文件系统，不写死清单。** 理由很实际：CS234 那边有另一个会话在持续加讲，
今天写死的「十一讲」明天就是十三讲。每讲的几种读法（放映厅 / 速览 / 精读 /
课件）各自存在与否，都是现查的 —— 文件不在就把按钮灰掉，不会给出死链。

页面分三层，从粗到细：
  ① **课程总览** —— 一门课一张卡，带每种读法的完成度。这是「入口」的那一层，
     让人一眼看清有哪几门、各做到哪儿，而不是一上来就吞 77 行。
  ② **研究学习清单** —— plan.json 的条目，链到 ★科研学习清单.html 的锚点。
  ③ **逐讲明细** —— 每门课一节，一讲一行。搜索框过滤的就是这一层。

**加一门课只要改一处**：下面的 `COURSES` 列表加一行。总览、小节、计数、
锚点导航全都从它派生。（旧版要改三处且容易漏，`n_items` 与收尾 print 的
格式串曾经对不上。）

ARTI2001 在另一棵树上（它有自己的总入口），单独处理，不进 COURSES。

配色走 coursekit/theme.py 的 LIGHT / DARK，浅色纸感为默认。
搜索框是纯前端过滤，键入即筛，不依赖任何服务。
"""
import html as _html
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
# 复用精读那边已经在用的 canonical-PDF 解析，不另写一份
from build_reader import _remote_pdf   # noqa: E402

# ARTI2001 在另一棵树上。相对 ROOT 的路径 —— 两者同在 G: 盘，所以互链成立。
ARTI_REL = "../Adelaide COMSC/2026S2/Machine Learning"

# ── 唯一需要维护的清单 ───────────────────────────────────────────
#   dir    : 相对 ROOT 的课程目录（里面要有 course.json）
#   code   : 总览卡上的短代号
#   name   : 中文名
#   meta   : 卡片第二行（开课方 / 年份 / 讲者）
#   unit   : 计量单位（「讲」或「章」）
#   note   : 逐讲小节的说明文字，可带 HTML
COURSES = [
    {
        "dir": "reinforcement learning", "code": "CS234", "name": "强化学习",
        "meta": "斯坦福 Winter 2019 · Emma Brunskill", "unit": "讲",
        "note": "四种读法：放映厅看讲解、速览一屏滚到底、精读左课件右讲解带自测、"
                "课件是原件。",
    },
    {
        "dir": "cs224r-2025", "code": "CS224R", "name": "深度强化学习",
        "meta": "斯坦福 Spring 2025 · Chelsea Finn", "unit": "讲",
        "note": "补 CS234 2019 版没有的三块：<b>PPO</b>（L05）、"
                "<b>RLHF / DPO</b>（L09）、<b>LLM 推理</b>（L10）。",
    },
    {
        "dir": "bandits-cse541", "code": "CSE 541", "name": "交互式学习",
        "meta": "华盛顿大学 Spring 2025 · Kevin Jamieson", "unit": "讲",
        "note": "<b>学习清单条目 1 的主体</b> —— 纯探索 bandit。"
                "⚠ 讲义是手写稿，推导全在墨迹里。",
    },
    {
        "dir": "CME295", "code": "CME 295", "name": "Transformers 与大语言模型",
        "meta": "斯坦福 Autumn 2025 · Afshine &amp; Shervine Amidi", "unit": "讲",
        "note": "<b>九讲九部放映厅</b>。⚠ 这门课的中文内容以<b>讲稿时间码</b>为准"
                "（每一镜都能对回原视频），讲义页码作参照 —— 与其余几门的做法不同。",
    },
    {
        "dir": "reinforcement learning/corpus/sutton-barto",
        "code": "S&amp;B", "name": "Sutton &amp; Barto 第二版",
        "meta": "经典教材 · 2020 年印次 · 作者免费提供全文", "unit": "章",
        "note": "<b>只读 CS234 没系统讲过的那几章</b>，按节写不逐页。"
                "<b>真正的增量是第 8 章</b>：规划与学习的统一视角、Dyna、"
                "优先遍历、决策时规划、rollout 与 MCTS。",
    },
]


TAG = re.compile(r"<[^>]+>")


def plain(s):
    """剥掉标记并还原实体，只留可搜的文字。

    两步都要：知识点里本来就带 <b>（搜索时不该把标签也搜进去），而课程代号里
    写的是 `S&amp;B` —— 只剥标签的话，搜「S&B」反而搜不到，控制台也会印出
    `S&amp;B` 这种东西。
    """
    return _html.unescape(TAG.sub("", str(s)))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def url(rel):
    """站内相对路径 → 可点的 href（空格等按 URL 编码，中文保留可读）。"""
    return rel.replace("\\", "/").replace(" ", "%20").replace("#", "%23")


def anchor_of(code):
    """课程代号 → 可做 id 的小写无空格串（CSE 541 → cse541，S&B → sb）。"""
    return re.sub(r"[^a-z0-9]", "", plain(code).lower())


def course_rows(course_dir, cfg_name="course.json"):
    """扫一门课，返回 [(tag, num_cn, title, kps, [(label, href, color, ok, remote), ...])]。

    ⚠ `remote` 是**线上**该用的地址。讲义 PDF 在 `corpus/` 里，被 `.gitignore`
    挡在库外（第三方版权材料），所以本地能开的相对路径**在 GitHub Pages 上一律
    404** —— 实测过，改版前总入口的 56 条 PDF 链接线上全是 404。精读页早就有
    解法（course.json 的 `pdf_remote` + 模板按 hostname 切换），这里复用同一份
    解析，页面上用 `data-remote` 带出去，由 JS 在 github.io 下换掉 href。
    没声明 `pdf_remote` 的课（CS234）仍旧只有本地路径，行为与从前一致。
    """
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
                btns.append((v["label"], None, v.get("color"), False, ""))
                continue
            full = co.abspath(rel)
            ok = os.path.exists(full)
            href = url(course_dir + "/" + rel) if ok else None
            remote = _remote_pdf(co, L) if rel.lower().endswith(".pdf") else ""
            btns.append((v["label"], href, v.get("color"), ok, remote))
        rows.append((L["tag"], L.get("num_cn", ""), L["title"], L.get("kp") or [], btns))
    return rows


def view_stats(rows):
    """按读法统计完成度 → [(label, color, 有几讲, 共几讲)]，顺序同 course.json。"""
    if not rows:
        return []
    labels = [(lb, c) for lb, _h, c, _ok, _rm in rows[0][4]]
    out = []
    for i, (lb, color) in enumerate(labels):
        n = sum(1 for r in rows if r[4][i][3])
        out.append((lb, color or "var(--acc)", n, len(rows)))
    return out


CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.7 var(--sans);-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 96px}

/* ══ 页头 ══ */
header{padding:52px 0 26px}
.kicker{font:12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;
  color:var(--acc);margin:0 0 14px}
h1{font-size:clamp(28px,4.4vw,40px);line-height:1.18;margin:0 0 12px;
  letter-spacing:-.5px;font-weight:700}
.lede{color:var(--ink3);font-size:15px;margin:0 0 20px;max-width:62ch}
.stats{display:flex;flex-wrap:wrap;gap:0 26px;margin:0;padding:0;list-style:none}
.stats li{display:flex;align-items:baseline;gap:7px}
.stats b{font:600 23px/1.2 var(--sans);letter-spacing:-.4px;color:var(--ink2)}
.stats span{font-size:12.5px;color:var(--dim)}

/* ══ 吸顶工具条 ══ */
.tools{position:sticky;top:0;z-index:20;display:flex;gap:10px;align-items:center;
  flex-wrap:wrap;padding:12px 0;margin:0 0 30px;
  background:var(--bg);border-bottom:1px solid var(--line)}
#q{flex:1;min-width:200px;background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-radius:10px;padding:10px 14px;
  font:14px var(--sans)}
#q:focus{outline:none;border-color:var(--acc);
  box-shadow:0 0 0 3px var(--tintacc)}
.cnt{font:12px var(--mono);color:var(--dim);white-space:nowrap}
#themeBtn{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  border-radius:10px;padding:9px 13px;cursor:pointer;font-size:14px;line-height:1}
#themeBtn:hover{border-color:var(--line2)}

/* ══ ① 课程总览卡 ══ */
.grid{display:grid;gap:13px;margin:0 0 14px;
  grid-template-columns:repeat(auto-fill,minmax(268px,1fr))}
.cc{display:block;text-decoration:none;background:var(--panel);
  border:1px solid var(--line);border-radius:14px;padding:16px 17px 14px;
  transition:border-color .15s,transform .15s,box-shadow .15s}
:root:not([data-theme="dark"]) .cc{box-shadow:var(--shadow)}
.cc:hover{border-color:var(--acc);transform:translateY(-2px)}
.cc .code{font:600 15.5px/1.3 var(--sans);letter-spacing:-.2px;color:var(--ink2)}
.cc .code em{font-style:normal;color:var(--ink3);font-weight:450}
.cc .meta{font-size:12px;color:var(--dim);margin:4px 0 13px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{height:5px;border-radius:99px;background:var(--sunken);overflow:hidden;
  display:flex;margin:0 0 11px}
.bar i{display:block;height:100%}
.vs{display:flex;flex-wrap:wrap;gap:5px 11px;font-size:11.5px;color:var(--ink3)}
.vs u{text-decoration:none;display:inline-flex;align-items:center;gap:5px}
.vs .dot{width:7px;height:7px;border-radius:99px;flex:0 0 auto}
.vs b{font:600 11.5px var(--mono);color:var(--ink2)}
.vs .zero{color:var(--dim);opacity:.6}

/* ══ 小节 ══ */
section{margin:0 0 34px;scroll-margin-top:68px}
h2{font-size:18px;margin:0 0 5px;display:flex;align-items:baseline;gap:10px;
  letter-spacing:-.2px}
h2 .n{font:11.5px var(--mono);color:var(--dim);border:1px solid var(--line2);
  border-radius:99px;padding:1px 9px;font-weight:400}
.sub{color:var(--dim);font-size:13px;margin:0 0 14px;max-width:78ch}
.sub a{color:var(--blue);text-decoration:none;border-bottom:1px solid transparent}
.sub a:hover{border-bottom-color:var(--blue)}

/* ══ ③ 逐讲行 ══ */
.row{border:1px solid var(--line);border-radius:11px;padding:10px 14px;margin:7px 0;
  background:var(--panel);display:flex;gap:14px;align-items:center;flex-wrap:wrap}
:root:not([data-theme="dark"]) .row{box-shadow:var(--shadow)}
.row:hover{border-color:var(--line2)}
.row .tag{font:12px var(--mono);color:var(--dim);min-width:48px;flex:0 0 auto}
.row .mid{flex:1;min-width:220px}
.row .ttl{font-weight:600;font-size:14.5px;line-height:1.45}
/* 知识点压成一行：行高不齐是这页最刺眼的毛病，而全文仍然可搜（在 data-s 里）*/
.row .kp{color:var(--dim);font-size:12.5px;line-height:1.5;margin-top:2px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.btns{display:flex;gap:6px;flex-wrap:wrap;align-items:center;flex:0 0 auto}
.b{font-size:12.5px;text-decoration:none;border-radius:99px;padding:4px 12px;
  border:1px solid transparent;white-space:nowrap;line-height:1.5}
/* 课程视图色（#7fd1c1 等）是给**暗场**配的淡彩，所以按钮文字一律用固定深墨，
   不跟主题走 —— 用 var(--bg) 的话浅色下是「近白字 + 淡彩底」，对比度只有 1.6。
   深墨对四个淡彩底都在 8.6:1 以上，两套主题都成立。 */
.b.on{color:#12161b;font-weight:600}
.b.on:hover{filter:brightness(1.06)}
/* 缺的那几种读法：旧版用实心灰按钮，占的地方和「有」的一样大，
   于是半页都是灰占位。改成虚线空心，退到背景里去。 */
.b.off{color:var(--dim);opacity:.5;cursor:default;background:none;
  border:1px dashed var(--line2);font-weight:400}

/* ══ ② 清单条目 ══ */
.card{border:1px solid var(--line);border-left:3px solid var(--line2);
  border-radius:11px;padding:12px 15px;margin:7px 0;background:var(--panel)}
:root:not([data-theme="dark"]) .card{box-shadow:var(--shadow)}
.card.done{border-left-color:var(--acc)}
.card.doing{border-left-color:var(--acc2)}
.card .hd{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.card .big{font-size:14.5px;font-weight:620;flex:1;min-width:200px;line-height:1.45}
.card .st{font:11.5px var(--mono);color:var(--dim);flex:0 0 auto}
.card.done .st{color:var(--acc)}
.card.doing .st{color:var(--acc2)}
.card .why{color:var(--ink3);font-size:13px;margin:5px 0 0}
/* 材料链接旧版是整排深蓝实心胶囊 —— 全页最响的东西，而它们只是外链。
   改成安静的文字链。 */
.mats{display:flex;flex-wrap:wrap;gap:4px 16px;margin:8px 0 0;font-size:12.5px}
.mats a{color:var(--blue);text-decoration:none;border-bottom:1px solid transparent}
.mats a:hover{border-bottom-color:var(--blue)}

.nores{color:var(--dim);font-size:14px;padding:34px 2px 10px;text-align:center}
.nores kbd{font:11.5px var(--mono);border:1px solid var(--line2);border-radius:5px;
  padding:1px 6px;color:var(--ink3)}
.hide{display:none!important}
.empty{color:var(--dim);font-size:13.5px;padding:14px 2px}
footer{margin-top:44px;padding-top:20px;border-top:1px solid var(--line);
  font-size:12px;color:var(--dim);text-align:center;line-height:1.9}
footer code{font:11.5px var(--mono)}

@media(max-width:620px){
  .wrap{padding:0 14px 72px}
  header{padding:34px 0 20px}
  .stats{gap:0 18px}
  .stats b{font-size:19px}
  .row{gap:9px}
  .row .tag{min-width:40px}
}
"""

TPL = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>学习总入口</title>
<style>
:root{{{LIGHT}}
  --sans:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  --mono:"JetBrains Mono",Consolas,"Courier New",monospace;
}
:root[data-theme="dark"]{{{DARK}}}
html{color-scheme:light dark;scroll-behavior:smooth}
{{CSS}}
</style></head><body>
<div class="wrap">
<header>
  <p class="kicker">Open Course · 中文学习站</p>
  <h1>学习总入口</h1>
  <p class="lede">{{LEDE}}</p>
  <ul class="stats">{{STATS}}</ul>
</header>
<div class="tools">
  <input id="q" type="search" placeholder="搜讲次、标题、知识点…（例：PPO、老虎机、截断）" autocomplete="off">
  <span class="cnt" id="cnt"></span>
  <button id="themeBtn" title="切换主题">☾</button>
</div>
<p class="nores hide" id="nores">没有匹配的条目。换个词，或按 <kbd>Esc</kbd> 清空。</p>
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

  /* 线上（GitHub Pages）：讲义 PDF 在 corpus/ 里，被 .gitignore 挡在库外，
     相对路径一律 404。换成 course.json 声明的 canonical 源（data-remote）。
     没声明的课（CS234）保持原样 —— 它在本机仍然能开。 */
  var hn = location.hostname.toLowerCase();
  var ONLINE = (hn === "github.io" || hn.slice(-11) === ".github.io");
  if(ONLINE){
    [].forEach.call(document.querySelectorAll("[data-remote]"), function(a){
      a.href = a.getAttribute("data-remote");
      a.target = "_blank"; a.rel = "noopener";
      a.title = "讲义是第三方版权材料，不入库；这里打开的是原站／存档";
    });
    /* ARTI2001 在另一棵目录树上，没跟着部署 —— 三个按钮线上必 404，灰掉 */
    [].forEach.call(document.querySelectorAll(".localonly a.b.on"), function(a){
      var s=document.createElement("span");
      s.className="b off"; s.textContent=a.textContent;
      s.title="这部分只在本机，没有发布到线上";
      a.parentNode.replaceChild(s,a);
    });
    [].forEach.call(document.querySelectorAll(".localonly .kp"), function(e){
      e.textContent="⚠ 材料在另一棵目录树上，没有发布到线上 —— 在本机打开本页才能用。";
    });
  }

  /* 纯前端过滤。每一行把可搜的文字预先塞在 data-s 里（已小写）。 */
  var items=[].slice.call(document.querySelectorAll("[data-s]"));
  var secs=[].slice.call(document.querySelectorAll("section"));
  var ov=document.getElementById("overview");
  var q=document.getElementById("q"), cnt=document.getElementById("cnt");
  var nores=document.getElementById("nores");
  function run(){
    var k=q.value.trim().toLowerCase(), n=0;
    items.forEach(function(el){
      var hit = !k || el.dataset.s.indexOf(k)>=0;
      el.classList.toggle("hide", !hit);
      if(hit) n++;
    });
    secs.forEach(function(s){
      if(s===ov) return;             /* 总览不参与过滤：它是导航，不是结果 */
      var any=s.querySelector("[data-s]:not(.hide)");
      s.classList.toggle("hide", !any);
    });
    if(ov) ov.classList.toggle("hide", !!k);   /* 搜索时收起总览，让结果占满屏 */
    cnt.textContent = k ? (n + " / " + items.length + " 条") : (items.length + " 条");
    nores.classList.toggle("hide", n > 0 || !k);
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


def render_overview(cards):
    """① 课程总览。cards = [(code, name, meta, unit, n, stats, href, anchor)]"""
    out = ['<section id="overview"><h2>课程总览'
           '<span class="n">%d 门</span></h2>'
           '<p class="sub">一门课一张卡，点进去是那门课自己的入口；'
           '下面是逐讲明细，搜索框过滤的是明细。</p><div class="grid">' % len(cards)]
    for code, name, meta, unit, n, stats, href, anchor in cards:
        done = sum(k for _lb, _c, k, _t in stats)
        total = sum(t for _lb, _c, _k, t in stats) or 1
        # 进度条按读法分段，颜色与下面的按钮一致，长度是各自的完成比例
        segs = "".join(
            '<i style="background:%s;width:%.3f%%"></i>' % (c, 100.0 * k / total)
            for _lb, c, k, t in stats if k)
        vs = "".join(
            '<u%s><span class="dot" style="background:%s"></span>%s'
            '<b>%d/%d</b></u>'
            % ("" if k else ' class="zero"', c, esc(lb), k, t)
            for lb, c, k, t in stats)
        out.append(
            '<a class="cc" href="%s"><div class="code">%s <em>%s</em></div>'
            '<div class="meta">%s · %d %s</div>'
            '<div class="bar">%s</div><div class="vs">%s</div></a>'
            % (href, code, name, meta, n, unit, segs, vs))
    out.append("</div></section>")
    return "\n".join(out)


def render_course(c, rows, href):
    """③ 一门课的逐讲明细。"""
    title = "%s %s" % (c["code"], c["name"])
    anchor = anchor_of(c["code"])
    if not rows:
        return ('<section id="%s"><h2>%s</h2><p class="empty">（还没有内容）</p></section>'
                % (anchor, title))
    out = ['<section id="%s"><h2>%s<span class="n">%d %s</span></h2>'
           '<p class="sub">%s　<a href="%s">课程入口 ↗</a></p>'
           % (anchor, title, len(rows), c["unit"], c["note"], href)]
    # 代号要给两种写法：「CSE 541」和「CSE541」。实测过 —— 不加的话
    # 搜 cme295 / cse541 / S&B 全是 0 条，因为代号只出现在小节标题里。
    code = plain(c["code"])
    head = [code, code.replace(" ", ""), plain(c["name"])]
    for tag, num_cn, ttl, kps, btns in rows:
        s = plain(" ".join(head + [tag, num_cn, ttl] + list(kps))).lower()
        bs = []
        for label, link, color, ok, remote in btns:
            if ok:
                bs.append('<a class="b on" style="background:%s" href="%s"%s>%s</a>'
                          % (color or "var(--acc)", link,
                             (' data-remote="%s"' % esc(remote)) if remote else "",
                             esc(label)))
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

    # ── 先把每门课扫出来，总览与明细共用同一份数据 ──
    scanned = []
    for c in COURSES:
        rows = course_rows(c["dir"])
        href = url(c["dir"] + "/index.html")
        scanned.append((c, rows, href))

    body = []

    # ① 课程总览
    cards = [(c["code"], c["name"], c["meta"], c["unit"], len(rows),
              view_stats(rows), href, anchor_of(c["code"]))
             for c, rows, href in scanned if rows]
    body.append(render_overview(cards))

    # ② 研究学习清单
    n_done = sum(1 for it in plan["items"] if it["status"] == "done")
    tiers = len({it["tier"] for it in plan["items"]})
    body.append('<section id="plan"><h2>研究学习清单<span class="n">%d 个条目</span></h2>'
                '<p class="sub">%d 条，%d 个梯队，已完成 %d 条。'
                '每条都绑着一个能拿去和导师讨论的产出。'
                '<a href="%s">打开完整清单 ↗</a></p>'
                % (len(plan["items"]), len(plan["items"]), tiers, n_done,
                   url("★科研学习清单.html")))
    for it in plan["items"]:
        s = plain(" ".join([str(it["n"]), it["title"], it["why"],
                            it["tier"], it.get("dir", "")])).lower()
        st = {"todo": "待开工", "doing": "进行中", "done": "已完成"}.get(it["status"], "")
        # 相对路径要过 url()：plan.json 里写的是「reinforcement learning/...」，
        # 带空格，不编码的话某些地方会断。外链原样。
        mats = "".join(
            '<a href="%s">%s ↗</a>'
            % (esc(m["href"] if m["href"].startswith("http") else url(m["href"])),
               esc(m["t"]))
            for m in it.get("mats", [])[:3])
        body.append('<div class="card %s" data-s="%s">'
                    '<div class="hd"><div class="big">%d · %s</div>'
                    '<div class="st">%s</div></div>'
                    '<div class="why">%s</div>'
                    '<div class="mats">%s</div></div>'
                    % (esc(it["status"]), esc(s), it["n"], esc(it["title"]),
                       esc(st), it["why"], mats))
    body.append("</section>")

    # ③ 各门课的逐讲明细
    for c, rows, href in scanned:
        body.append(render_course(c, rows, href))

    # ④ ARTI2001（另一棵树，只做转接）
    arti = []
    for label, rel, color in [
        ("课程总入口", "★总入口.html", "#7fd1c1"),
        ("全部材料", "全部材料.html", "#8fb8ff"),
        ("复习放映厅", "复习放映厅/★放映厅-总入口.html", "#f0c674"),
    ]:
        full = os.path.join(ROOT, ARTI_REL, rel)
        arti.append((label, url(ARTI_REL + "/" + rel) if os.path.exists(full) else None, color))
    btns = "".join(
        ('<a class="b on" style="background:%s" href="%s">%s</a>' % (c, h, esc(lb)))
        if h else ('<span class="b off">%s</span>' % esc(lb))
        for lb, h, c in arti)
    # ⚠ ARTI2001 在另一棵树上，**没有**跟着部署到 Pages —— 这三条线上是 404。
    # 标出来由 JS 在 github.io 下灰掉，好过点进去撞 404。
    body.append(
        '<section id="arti"><h2>ARTI2001 机器学习<span class="n">本学期课程</span></h2>'
        '<p class="sub">Adelaide 的课，三个 Module。它有自己的一套总入口与材料清单，'
        '这里只做转接。</p>'
        '<div class="row localonly" data-s="arti2001 机器学习 课程 m1 m2 m3 考试 复习">'
        '<div class="tag">课程</div><div class="mid"><div class="ttl">'
        'ARTI2001 全部课程材料</div><div class="kp">官方 PPT · Tutorial 与 Practical · '
        '逐页精读 · 备考包 · 复习放映厅</div></div>'
        '<div class="btns">%s</div></div></section>' % btns)

    # ── 页头的统计数字：全部从扫出来的数据算，不手写 ──
    n_lec = sum(len(rows) for _c, rows, _h in scanned)
    n_kp = sum(len(r[3]) for _c, rows, _h in scanned for r in rows)
    n_items = len(plan["items"]) + n_lec + 1
    stats_html = "".join(
        "<li><b>%s</b><span>%s</span></li>" % (v, k)
        for k, v in (("门课", len(cards)), ("讲 / 章", n_lec),
                     ("个知识点", n_kp), ("清单条目", len(plan["items"]))))

    lede = ("把散在各处的材料收成一个入口：%d 门课的中文学习站、"
            "研究学习清单，以及本学期 ARTI2001 的全部材料。"
            "<b>按 / 搜索</b>，Esc 清空。" % len(cards))

    html = TPL
    for a, b in (("{{LIGHT}}", theme.LIGHT), ("{{DARK}}", theme.DARK), ("{{CSS}}", CSS),
                 ("{{LEDE}}", lede), ("{{STATS}}", stats_html),
                 ("{{BODY}}", "\n".join(body)),
                 ("{{FOOT}}", "课件版权归各校与讲者；中文部分是配合原件阅读的学习笔记。<br>"
                              "本页由 <code>_kit/build_portal.py</code> 扫描文件系统生成 —— "
                              "加了新讲之后重跑一次即可，不必手改。")):
        html = html.replace(a, b)
    left = [t for t in ("{{LIGHT}}", "{{DARK}}", "{{CSS}}", "{{LEDE}}",
                        "{{STATS}}", "{{BODY}}", "{{FOOT}}") if t in html]
    assert not left, "模板里还有没填的占位符：%s" % left

    # ⚠ 旧版这里的 :root 块多了一个游离的 `}`（开 2 闭 3）。浏览器忽略它，
    #   所以一直没人发现。顺手加一道断言，别再悄悄长回来。
    head = html[html.index(":root{"):html.index("html{color-scheme")]
    assert head.count("{") == head.count("}"), \
        "生成的 :root 块花括号不配对：开 %d 闭 %d" % (head.count("{"), head.count("}"))

    out = os.path.join(ROOT, "★总入口.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write(html)
    print("写出 %s" % os.path.basename(out))
    print("  课程 %d 门 · %d 讲/章 · %d 个知识点 · 清单 %d 条 ⇒ 可搜 %d 条"
          % (len(cards), n_lec, n_kp, len(plan["items"]), n_items))
    for c, rows, _h in scanned:
        if not rows:
            print("    ⚠ %s 扫不到内容（%s/course.json 不在？）" % (c["code"], c["dir"]))
            continue
        vs = " · ".join("%s %d/%d" % (plain(lb), k, t)
                        for lb, _c2, k, t in view_stats(rows))
        print("    %-9s %2d %s   %s" % (plain(c["code"]), len(rows), c["unit"], vs))


if __name__ == "__main__":
    main()
