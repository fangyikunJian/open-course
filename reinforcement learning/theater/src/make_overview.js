#!/usr/bin/env node
/**
 * make_overview.js —— 把一部放映厅片子摊平成一张**可以直接看全部内容**的长页。
 *
 * 为什么要有它：放映厅是键盘推进的，想回看某一段只能反复前进后退。
 * 这个脚本把每一镜的**末态**快照下来，拼成一张纯静态 HTML：
 * 全片一屏滚到底、可搜索（Ctrl+F）、可打印成 PDF、不依赖 JS 运行。
 *
 * 做法和 shot_probe.js 同一条路：无头 Chrome 打开片子、逐镜 __go、
 * 把 #scene 的 SVG 连同公式带 / 字幕 / 讲解 / 总结卡 / 测验卡一起取下来。
 * 之所以不能在浏览器端直接把 45 镜同时画出来：引擎把 gS 捕获成了**闭包变量**，
 * 外部重新指向不了，每镜只能画进同一个舞台。
 *
 * 零依赖，只用 Node 内置模块。
 *
 * 用法：
 *   node make_overview.js <片子.html> [--out 速览.html] [--viewport 1440x900]
 */

const http = require("http");
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const CHROME = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
].find((p) => fs.existsSync(p));

const arg = (name, dflt) => {
  const i = process.argv.indexOf(name);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
};

function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = "";
      res.on("data", (c) => (b += c));
      res.on("end", () => { try { resolve(JSON.parse(b)); } catch (e) { reject(e); } });
    }).on("error", reject);
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch(port, profile) {
  if (!CHROME) throw new Error("找不到 Chrome 或 Edge");
  const child = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding", "--allow-file-access-from-files",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank",
  ], { stdio: "ignore", detached: false });
  for (let i = 0; i < 60; i++) {
    try {
      const t = await getJSON(`http://127.0.0.1:${port}/json`);
      const page = t.find((x) => x.type === "page");
      if (page && page.webSocketDebuggerUrl) return { child, page };
    } catch (e) { /* 还没起来 */ }
    await sleep(250);
  }
  throw new Error("Chrome 起来了但一直没有 page target");
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
    }
  });
  const ready = new Promise((r) => ws.addEventListener("open", r));
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const n = ++id;
      pending.set(n, { resolve, reject });
      ws.send(JSON.stringify({ id: n, method, params }));
    });
  const evaluate = async (expr, awaitPromise = true) => {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise });
    if (r.exceptionDetails) {
      throw new Error("页面内异常: " +
        (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    }
    return r.result.value;
  };
  return { ws, ready, send, evaluate };
}

/* 末态模式：把过渡换成恒等，否则取到的是起始帧（动画还没跑完）。
   和 shot_probe.js 用的是同一套理由。 */
const PATCH = String.raw`
(function(){
  if (window.__ovPatched) return "already";
  window.__ovPatched = true;
  if (window.d3 && d3.selection) {
    var P = d3.selection.prototype;
    P.transition = function(){ return this; };
    P.duration = P.delay = P.ease = function(){ return this; };
    P.tween = function(name, f){
      this.each(function(){ try { var g = f.call(this); if (g) g.call(this, 1); } catch(e){} });
      return this;
    };
  }
  if (window.__engine) window.__engine.isFast = function(){ return true; };
  if (window.Element && Element.prototype.animate) {
    Element.prototype.animate = function(){
      return { cancel(){}, finish(){}, play(){}, pause(){}, addEventListener(){} };
    };
  }
  return "ok";
})()`;

/* 逐镜取快照。240ms 是必须的：setEq 的非 FAST 分支是 setTimeout(...,150)，
   __go 刚回来那一瞬间公式带必然是空的。 */
const GRAB = String.raw`
(function(){
  var q = function(s){ var e = document.querySelector(s); return e; };
  var scene = q("#scene"), eq = q("#eqBox"), cap = q("#cap"),
      narr = q("#narr"), sum = q("#sum"), quiz = q("#quiz"), big = q("#big");
  var vis = function(e){ return e && !e.hidden && !e.classList.contains("off"); };
  return {
    svg   : scene ? scene.outerHTML : "",
    eq    : vis(eq) ? eq.innerHTML : "",
    eqCls : eq ? eq.className : "",
    big   : vis(big) ? big.innerHTML : "",
    cap   : cap ? cap.innerHTML : "",
    narr  : (narr && !narr.hidden) ? narr.innerHTML : "",
    sum   : vis(sum) ? sum.innerHTML : "",
    quiz  : vis(quiz) ? quiz.innerHTML : ""
  };
})()`;

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const OV_CSS = `
/* ── 速览页自己的版式（片子的原样式在上面，这里只加排布）────────────── */
html,body{overflow:auto !important;height:auto !important}
body{padding:0;margin:0}
#ovTop{position:sticky;top:0;z-index:50;background:rgba(8,11,17,.97);
  border-bottom:1px solid var(--edge);backdrop-filter:blur(8px);
  padding:14px 26px 12px}
#ovTop h1{margin:0 0 4px;font-size:clamp(17px,1.7vw,23px);font-weight:650;color:var(--ink);
  font-family:var(--canvas)}
#ovTop .sub{color:var(--dim);font-size:12.5px;margin:0 0 10px;font-family:var(--canvas)}
#ovNav{display:flex;flex-wrap:wrap;gap:6px}
#ovNav a{font-family:var(--canvas);font-size:12px;color:var(--dim);text-decoration:none;
  border:1px solid var(--edge);border-radius:999px;padding:3px 11px;white-space:nowrap}
#ovNav a:hover{color:var(--yellow);border-color:var(--yellow)}
#ovAll{margin-top:9px;background:#0b1017;border:1px solid var(--edge);border-radius:999px;
  color:var(--dim);font:12px var(--canvas);padding:4px 13px;cursor:pointer}
#ovAll:hover{color:var(--yellow);border-color:var(--yellow)}
#ovBody{max-width:1760px;margin:0 auto;padding:22px 26px 90px}
.kpHead{margin:34px 0 14px;padding-top:10px;border-top:1px solid var(--edge);
  font-family:var(--canvas)}
.kpHead .n{color:var(--green);font-size:12px;letter-spacing:.18em}
.kpHead h2{margin:4px 0 0;font-size:clamp(16px,1.5vw,21px);font-weight:620;color:var(--ink)}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(620px,1fr))}
.card{border:1px solid var(--edge);border-radius:12px;background:rgba(14,19,28,.6);
  overflow:hidden;display:flex;flex-direction:column}
.card .no{font-family:var(--canvas);font-size:11px;color:var(--dimmer);
  padding:7px 12px 0;letter-spacing:.1em}
.stage{position:relative;background:var(--bg);padding:4px 10px 0}
.stage .eqwrap{text-align:center;min-height:0;padding:2px 0}
.stage .eqwrap mjx-container{font-size:76% !important}
.stage svg{display:block;width:100%;height:auto}
.bigwrap{font-family:var(--canvas);font-size:clamp(20px,2.4vw,34px);color:var(--yellow);
  text-align:center;padding:26px 12px;font-weight:500}
.bigwrap small{display:block;font-size:.36em;color:var(--dim);letter-spacing:.14em;
  margin-top:8px;font-weight:400}
.capwrap{padding:8px 16px 4px;text-align:center;font-size:clamp(13px,1.05vw,16px);
  line-height:1.5;color:var(--ink)}
.capwrap b{color:var(--yellow);font-weight:600}
.capwrap em{font-style:normal;color:var(--green);font-weight:600}
.capwrap i{font-style:normal;color:var(--blue);font-weight:600}
.capwrap s{text-decoration:none;color:var(--coral);font-weight:600}
.narrwrap{padding:0 16px 13px;font-size:12.5px;line-height:1.72;color:#C7D2E0}
.narrwrap>summary{cursor:pointer;list-style:none;color:var(--dim);font-size:11.5px;
  letter-spacing:.14em;padding:7px 0 2px;border-top:1px solid var(--edge);
  display:flex;align-items:center;gap:6px;user-select:none}
.narrwrap>summary::-webkit-details-marker{display:none}
.narrwrap>summary::after{content:"展开";color:var(--yellow);font-size:11px;
  border:1px solid var(--edge);border-radius:999px;padding:1px 8px;margin-left:auto}
.narrwrap[open]>summary::after{content:"收起"}
.narrwrap>div{padding-top:8px;max-height:15em;overflow:auto}
.narrwrap b{color:#E8EEF7;font-weight:500}
.grid{align-items:start}
.cardwide{grid-column:1/-1}
.cardwide .sumbox,.cardwide .quizbox{padding:18px 22px}
@media print{
  #ovTop{position:static}
  .grid{grid-template-columns:1fr 1fr}
  .card{break-inside:avoid;border-color:#999}
  body{background:#fff}
}
`;

(async () => {
  const film = process.argv[2];
  if (!film || !fs.existsSync(film)) {
    console.error("用法：node make_overview.js <片子.html> [--out 速览.html]");
    process.exit(2);
  }
  const vp = arg("--viewport", "1440x900").split("x").map(Number);
  const out = arg("--out", film.replace(/\.html$/, "") + "-速览.html");

  const src = fs.readFileSync(film, "utf8");
  const style = (src.match(/<style>[\s\S]*?<\/style>/) || [""])[0];
  const title = (src.match(/<title>([\s\S]*?)<\/title>/) || [, "放映厅"])[1];
  const mj = (src.match(/<script[^>]*tex-svg[^>]*><\/script>/) || [""])[0];

  const port = 9500 + Math.floor(Math.random() * 400);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "ov-"));
  const { child, page } = await launch(port, profile);
  const cdp = connect(page.webSocketDebuggerUrl);
  await cdp.ready;
  try {
    // Page/Runtime 必须先 enable —— 少了它们页面会卡在 readyState:"loading"。
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride",
      { width: vp[0], height: vp[1], deviceScaleFactor: 1, mobile: false });
    await cdp.send("Page.navigate", { url: "file:///" + path.resolve(film).replace(/\\/g, "/") });

    let ok = false;
    for (let i = 0; i < 160; i++) {          // 40 秒：冷 profile 拉 CDN 很慢
      await sleep(250);
      try {
        ok = await cdp.evaluate("!!(window.__engine && window.__go && window.d3)");
        if (ok) break;
      } catch (e) { /* 还在加载 */ }
    }
    if (!ok) {
      const diag = await cdp.evaluate(`JSON.stringify({
        href: location.href, ready: document.readyState,
        scripts: document.scripts.length, bodyLen: document.body ? document.body.innerHTML.length : -1,
        d3: typeof window.d3, engine: typeof window.__engine, go: typeof window.__go
      })`).catch(e => "evaluate 也失败：" + e.message);
      throw new Error("40 秒内引擎没有挂载。现场：" + diag);
    }
    await sleep(700);                       // 等 MathJax 起来
    await cdp.evaluate(PATCH);

    const n = await cdp.evaluate("window.__n || 0");
    const kps = await cdp.evaluate("JSON.stringify(window.__kps||[])").then(JSON.parse);
    process.stderr.write(`读到 ${n} 镜 / ${kps.length} 个知识点\n`);

    const shots = [];
    for (let i = 0; i < n; i++) {
      await cdp.evaluate(`window.__go(${i}, true)`);
      await sleep(240);                     // 跨过 setEq 的延迟写入窗口
      for (let k = 0; k < 24; k++) {
        const done = await cdp.evaluate(
          `(function(){var e=document.getElementById("eqBox");
            return !e||e.classList.contains("off")||!e.textContent.trim()
                   ||e.querySelectorAll("mjx-container").length>0;})()`);
        if (done) break;
        await sleep(100);
      }
      shots.push(await cdp.evaluate(GRAB));
      if ((i + 1) % 20 === 0) process.stderr.write(`  …${i + 1}/${n}\n`);
    }

    // ── 拼页 ───────────────────────────────────────────────────────────
    const kpAt = (i) => {
      let k = -1;
      kps.forEach((x, j) => { if (i >= x.from) k = j; });
      return k;
    };
    const parts = [];
    let lastKp = -2;
    shots.forEach((s, i) => {
      const k = kpAt(i);
      if (k !== lastKp) {
        if (lastKp !== -2) parts.push("</div>");
        const nm = k >= 0 && kps[k] ? (kps[k].name || kps[k].title || `知识点 ${k + 1}`) : "开场";
        parts.push(`<div class="kpHead" id="kp${k + 1}">` +
          `<div class="n">${k >= 0 ? "知识点 " + (k + 1) : "开场"}</div>` +
          `<h2>${nm}</h2></div><div class="grid">`);
        lastKp = k;
      }
      const wide = s.sum || s.quiz;
      const inner = s.sum
        ? `<div class="sumbox" id="sum">${s.sum}</div>`
        : s.quiz
        ? `<div class="quizbox" id="quiz">${s.quiz}</div>`
        : (s.big
            ? `<div class="bigwrap">${s.big}</div>`
            : `<div class="stage"><div class="eqwrap ${esc(s.eqCls)}">${s.eq}</div>${s.svg}</div>`);
      parts.push(
        `<section class="card${wide ? " cardwide" : ""}">` +
        `<div class="no">${i + 1} / ${shots.length}</div>` +
        inner +
        (s.cap ? `<div class="capwrap">${s.cap}</div>` : "") +
        (s.narr ? `<details class="narrwrap"><summary>讲解</summary><div>${s.narr}</div></details>` : "") +
        `</section>`);
    });
    parts.push("</div>");

    const nav = kps.map((x, j) =>
      `<a href="#kp${j + 1}">${j + 1} · ${(x.name || x.title || "").slice(0, 16)}</a>`).join("");

    const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)} · 速览</title>
${mj}
${style}
<style>${OV_CSS}</style>
</head><body>
<div id="ovTop">
  <h1>${esc(title.replace(/ · 放映厅$/, ""))} · 全片速览</h1>
  <p class="sub">${shots.length} 镜一次看完 · Ctrl+F 可搜全文 · Ctrl+P 可存成 PDF · 想看动画回放映厅</p>
  <div id="ovNav">${nav}</div>
  <button id="ovAll">全部展开讲解</button>
</div>
<script>
(function(){
  var on=false, b=document.getElementById("ovAll");
  b.onclick=function(){
    on=!on;
    document.querySelectorAll("details.narrwrap").forEach(function(d){ d.open=on; });
    b.textContent = on ? "全部收起讲解" : "全部展开讲解";
  };
})();
</script>
<div id="ovBody">
${parts.join("\n")}
</div>
</body></html>`;
    fs.writeFileSync(out, html, "utf8");
    console.log(`速览页 -> ${out}（${shots.length} 镜，${(html.length / 1024).toFixed(0)} KB）`);
  } finally {
    try { cdp.ws.close(); } catch (e) {}
    try { child.kill(); } catch (e) {}
  }
})().catch((e) => { console.error("失败：" + e.message); process.exit(1); });
