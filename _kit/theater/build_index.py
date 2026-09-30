# -*- coding: utf-8 -*-
"""生成放映厅入口页 影片/index.html。

只读 film-LNN.json 里已有的元数据（标题、文件名、知识点名、讲座视频），
不重复维护一份清单 —— 加一讲就重跑一次。

    python build_index.py
"""
import glob
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

import _paths

# 惰性求值：out_dir() 在无内容的目录里会报错退出，写成模块级常量
# 会让「import 这个模块」本身变成一个会失败的动作。


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def load():
    films = []
    for p in sorted(glob.glob(os.path.join(_paths.src_dir(), "film-L*.json"))):
        d = json.load(io.open(p, encoding="utf-8"))
        tag = os.path.basename(p)[5:-5]              # film-L02.json -> L02
        f = os.path.join(_paths.out_dir(), d["file"])
        if not os.path.exists(f):
            print("!! 缺成片，跳过：%s" % d["file"])
            continue
        kps = d.get("kp_names") or {}
        films.append({
            "tag": tag,
            "n": int(tag[1:]),
            "file": d["file"],
            "title": d.get("title", ""),
            "video": (d.get("video") or "").rstrip("&t="),
            "kps": [kps[k] for k in sorted(kps, key=lambda x: int(x))],
            "kb": os.path.getsize(f) // 1024,
        })
    return films


def split_title(t):
    """'CS234 · Lecture 2 · 已知世界模型：MP / MRP / MDP，策略迭代与值迭代'
       -> ('Lecture 2', '已知世界模型：…')"""
    parts = [x.strip() for x in t.split("·")]
    if len(parts) >= 3:
        return parts[1], "·".join(parts[2:]).strip()
    return "", t


CSS = """
:root{
  --bg:#080b11; --panel:#0e131c; --line:#1d2635; --ink:#dfe7f2; --dim:#8494ab;
  --acc:#7fd1c1; --acc2:#f0b859; --hot:#e0685f;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);
  font:16px/1.65 "Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  padding:0 16px 80px}
.wrap{max-width:1180px;margin:0 auto}
header{padding:56px 0 30px;border-bottom:1px solid var(--line);margin-bottom:34px}
h1{margin:0 0 12px;font-size:clamp(25px,3.6vw,40px);letter-spacing:.3px;font-weight:650}
h1 span{color:var(--acc)}
.lede{color:var(--dim);max-width:70ch;margin:0 0 16px;font-size:15px}
.stats{display:flex;flex-wrap:wrap;gap:8px}
.stat{border:1px solid var(--line);border-radius:999px;padding:4px 13px;
  font-size:12.5px;color:var(--dim);background:var(--panel)}
.stat b{color:var(--ink);font-weight:600}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:13px;
  padding:19px 20px 16px;display:flex;flex-direction:column;
  transition:border-color .16s,transform .16s}
.card:hover{border-color:var(--acc);transform:translateY(-2px)}
.tag{font:600 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;
  color:var(--acc2);letter-spacing:1.4px;margin-bottom:9px}
.card h2{margin:0 0 4px;font-size:17.5px;line-height:1.42;font-weight:620}
.card h2 a{color:var(--ink);text-decoration:none}
.card:hover h2 a{color:var(--acc)}
.sub{color:var(--dim);font-size:12.5px;margin:0 0 13px}
details{border-top:1px solid var(--line);padding-top:11px;margin-top:auto}
summary{cursor:pointer;color:var(--dim);font-size:12.5px;list-style:none;
  display:flex;justify-content:space-between;align-items:center}
summary::-webkit-details-marker{display:none}
summary::after{content:"▾";color:var(--acc);transition:transform .16s}
details[open] summary::after{transform:rotate(180deg)}
ol{margin:11px 0 0;padding-left:20px;color:var(--dim);font-size:13px;line-height:1.62}
ol li{margin-bottom:3px}
ol li::marker{color:var(--acc2)}
.go{display:inline-flex;align-items:center;gap:7px;margin-top:13px;
  border:1px solid var(--line);border-radius:8px;padding:7px 13px;
  color:var(--acc);text-decoration:none;font-size:13.5px;background:#0b1017}
.go:hover{border-color:var(--acc);background:#111a22}
.acts{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.go.alt{color:var(--acc2)}
.go.alt:hover{border-color:var(--acc2);background:#1a1509}
.src{color:var(--dim);font-size:12px;text-decoration:none;margin-left:12px}
.src:hover{color:var(--acc2)}
footer{margin-top:44px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--dim);font-size:13px}
kbd{border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;
  padding:1px 6px;font:12px ui-monospace,Menlo,monospace;color:var(--ink);
  background:#0b1017}
@media (max-width:560px){ .grid{grid-template-columns:1fr} header{padding-top:36px} }
"""


def main():
    films = load()
    nkp = sum(len(f["kps"]) for f in films)
    cards = []
    for f in films:
        lec, name = split_title(f["title"])
        items = "\n".join("        <li>%s</li>" % esc(re.sub(r"^\d+\s*·\s*", "", k))
                          for k in f["kps"])
        vid = ('<a class="src" href="%s" target="_blank" rel="noopener">原讲座 ↗</a>'
               % esc(f["video"])) if f["video"] else ""
        # 速览页：整部片摊平成一张长页，不用一镜一镜翻。没生成就不显示这个入口。
        ovrel = "速览/%s-速览.html" % f["tag"]
        ov = ('<a class="go alt" href="%s">全片速览 ⤢</a>' % esc(ovrel)
              if os.path.exists(os.path.join(_paths.out_dir(), ovrel)) else "")
        cards.append("""    <article class="card">
      <div class="tag">%s%s</div>
      <h2><a href="%s">%s</a></h2>
      <p class="sub">%d 个知识点 · %d KB</p>
      <details>
        <summary>知识点清单</summary>
        <ol>
%s
        </ol>
      </details>
      <div class="acts"><a class="go" href="%s">进入放映厅 →</a>%s%s</div>
    </article>""" % (esc(f["tag"]), " · " + esc(lec) if lec else "",
                     esc(f["file"]), esc(name), len(f["kps"]), f["kb"],
                     items, esc(f["file"]), ov, vid))

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CS234 放映厅 · 斯坦福强化学习</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>CS234 <span>放映厅</span></h1>
  <p class="lede">斯坦福 CS234《强化学习》Winter 2019 的中文动画讲解。
  每部一讲、九个知识点，每个知识点走同一条六拍：钩子 → 错误答案 → 铺陈 → 主体 → 反驳 → 检验
  —— 先把一个似是而非的说法摆出来，再当场把它杀掉。
  片中所有数值都由独立脚本重算核对过，不是配合结论编的。</p>
  <div class="stats">
    <span class="stat"><b>%d</b> 部</span>
    <span class="stat"><b>%d</b> 个知识点</span>
    <span class="stat"><b>%d</b> 个画面</span>
    <span class="stat">操作：<kbd>空格</kbd> 推进 · <kbd>N</kbd> 开关讲解</span>
  </div>
</header>
<main class="grid">
%s
</main>
<footer>
  点任意一部进入。片子是独立的单个 HTML，可以直接双击打开，也可以拷走单独发。
  公式用 MathJax、图形用 d3，都走 CDN，<b>首次打开需要联网</b>。
</footer>
</div>
</body>
</html>
""" % (CSS, len(films), nkp, 725, "\n".join(cards))

    out = os.path.join(_paths.out_dir(), "index.html")
    io.open(out, "w", encoding="utf-8").write(html)
    print("写出 %s" % os.path.normpath(out))
    print("  %d 部 · %d 个知识点" % (len(films), nkp))


if __name__ == "__main__":
    main()
