#!/usr/bin/env node
/**
 * shot_probe.js —— 放映厅的几何转储器。
 *
 * 它**不是抽帧器**。这个项目没有 video（S(t,…) 的 t 是指向源讲座的时间码，不是本片时长），
 * 推进靠空格键，而在无头/隐藏环境里 requestAnimationFrame 不触发，抽帧只能抽到开场卡。
 * 正确的对应物是：把每一镜的**末态几何**转储成可 diff 的 JSON。
 *
 * 量出来的东西比截图强不是弱：精确、可 grep、可 diff、可入库当回归基线，
 * 而且另一个同样看不见画面的人也能复核。截图只有看得见的人能用。
 *
 * 零依赖：只用 Node 内置的 http / child_process / WebSocket（Node ≥ 21 内置）驱动
 * Chrome DevTools Protocol。不需要 puppeteer / playwright。
 *
 * 用法：
 *   node shot_probe.js <片子.html> [--out shots.json] [--viewport 1440x900] [--selftest]
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

// ── 实测版面常数（1440×900，frame 1440×810，标准 16:9）────────────────────
// 阈值必须带着测量条件一起活着 —— 第一版在 652×367 的预览面板里量，
// 而字幕带用 vh 相对**视口**，小窗口下被放大到 58%，把安全区误判成危险区。
const LAYOUT = {
  eqTopTall: [51, 283],   // setEq(...,"top") 两行 aligned
  eqTopShort: [90, 189],  // setEq(...,"top") 单行
  freeCanvas: [290, 470],
  captionBand: 480,       // 字幕带顶边（讲解默认显示）
  canvasW: 1280,
  canvasH: 720,
};

function arg(name, dflt) {
  const i = process.argv.indexOf(name);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
}
const has = (name) => process.argv.includes(name);

function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = "";
      res.on("data", (c) => (b += c));
      res.on("end", () => {
        try { resolve(JSON.parse(b)); } catch (e) { reject(e); }
      });
    }).on("error", reject);
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch(port, profile) {
  if (!CHROME) throw new Error("找不到 Chrome 或 Edge");
  const child = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    // setEq 的延迟写入是 setTimeout(...,150)；被节流到 ≥1000ms 就会量成「没有公式」。
    "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--allow-file-access-from-files",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    "about:blank",
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
    const r = await send("Runtime.evaluate", {
      expression: expr, returnByValue: true, awaitPromise,
    });
    if (r.exceptionDetails) {
      throw new Error("页面内异常: " +
        (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    }
    return r.result.value;
  };
  return { ws, ready, send, evaluate };
}

// ══════════════════════════════════════════════════════════════════════════
// 四个补丁。缺一不可，理由各不相同 —— 不打补丁量到的是**起始帧**，不是末态。
// ══════════════════════════════════════════════════════════════════════════
const PATCHES = String.raw`
(function(){
  if (window.__probePatched) return "already";
  window.__probePatched = true;
  window.__probeLog = [];

  // (a) d3 过渡 → 恒等。过渡靠 rAF 驱动，rAF 不跑则链上 .attr() 的目标值永不落地。
  //     换成恒等后，后续 .attr() 立刻生效，每一镜直接落在末帧。
  //     .tween 必须单独跑 t=1：morphBars 的滚动数字是靠 tween 写 textContent 的，
  //     跳过它数字会停在初值（这正是「柱子到位而数字没到位」那类假象的来源）。
  //     顺带白送一件事：过渡**开始前**的属性留在 WeakMap 里、**结束后**的在 DOM 上 ——
  //     一次遍历同时拿到运动的两个端点。这是「反超 / 收缩 / 依次点亮」这类命题
  //     唯一可机械验证的形式。
  if (window.d3 && d3.selection) {
    var P = d3.selection.prototype;
    window.__t0 = new WeakMap();
    // 只抓判定用得上的几个属性。第一版抓全部属性，结果 curve() 的 d 路径
    // 每条几百个点，87 镜累计把 JSON.stringify 撑爆（Invalid string length）。
    // 转储是给判定用的，不是给存档用的 —— 不需要的一律不抓。
    var KEEP = ["y","height","cy","r","opacity","width","x"];
    var snap = function(n){
      var o = {};
      for (var i=0;i<KEEP.length;i++){
        var v = n.getAttribute && n.getAttribute(KEEP[i]);
        if (v != null) o[KEEP[i]] = v;
      }
      var t = n.textContent || "";
      o.__text = t.length > 24 ? t.slice(0,24) : t;
      return o;
    };
    P.transition = function(){
      try { this.each(function(){ window.__t0.set(this, snap(this)); }); } catch(e){}
      return this;
    };
    // 绝不能把 remove 列进来。这些名字要中性化的是**过渡**上的方法，而
    // transition() 现在返回 selection 本身，所以覆盖的其实是
    // d3.selection.prototype.remove —— 而 clearScene() 正是靠
    // gS.selectAll("*").remove() 清场的。第一版把 remove 写了进去，
    // 结果清场失效、每镜叠加前面所有镜的节点：84 镜写出 369MB，
    // 而且不报任何错，只是几何判定全盘错乱（所有元素都「重叠」）。
    // 淡出后删除这类用法，末态本来就是「已删除」，直接 remove 反而是对的。
    ["duration","delay","ease","on","end","attrTween","styleTween"]
      .forEach(function(k){ P[k] = function(){ return this; }; });
    P.tween = function(name, f){
      this.each(function(){
        try { var g = f.call(this); if (g) g.call(this, 1); } catch(e){}
      });
      return this;
    };
  }

  // (b) 必须**两个都打**。eng.txt 里的 FAST 是**闭包变量**，核心图元
  //     （fadeIn / dots / curve / matrix / setEq）直接读它，从外面改不了；
  //     E.isFast 只是一个读该闭包的函数，覆盖它只影响 build_common 的 RL 图元那一批。
  //     补丁 (a) 负责兜住 eng.txt 那一批 —— 它们的过渡同样被换成了恒等。
  if (window.__engine) window.__engine.isFast = function(){ return true; };

  // (c) flip() 的非 FAST 分支用 Web Animations：淡入是 fill:"backwards" + delay，
  //     会把 opacity 钉在 0，量出**假的不可见**。换成空桩。
  if (window.Element && Element.prototype.animate) {
    Element.prototype.animate = function(){ return { cancel:function(){}, finish:function(){},
      play:function(){}, pause:function(){}, addEventListener:function(){} }; };
  }
  return "ok";
})()
`;

const DUMP = String.raw`
(function(){
  var frame = document.getElementById("frame");
  var fr = frame.getBoundingClientRect();
  var sx = 1280 / fr.width, sy = 720 / fr.height;
  var toCanvas = function(r){ return {
    x1: +( (r.left - fr.left) * sx ).toFixed(1),
    y1: +( (r.top  - fr.top ) * sy ).toFixed(1),
    x2: +( (r.right- fr.left) * sx ).toFixed(1),
    y2: +( (r.bottom-fr.top ) * sy ).toFixed(1) }; };

  var nodes = [];
  document.querySelectorAll("#scene *").forEach(function(el){
    if (el.tagName === "defs" || el.closest("defs")) return;
    var r = el.getBoundingClientRect();
    if (!r.width && !r.height) return;
    var cs = getComputedStyle(el);
    var t0 = window.__t0 && window.__t0.get(el);
    nodes.push({
      tag: el.tagName,
      cls: el.getAttribute("class") || "",
      text: (el.textContent || "").slice(0, 60),
      box: toCanvas(r),
      fill: cs.fill, stroke: cs.stroke, fontSize: cs.fontSize, opacity: cs.opacity,
      t0: t0 ? { y: t0.y, height: t0.height, text: (t0.__text||"").slice(0,24) } : null,
      t1: { y: el.getAttribute("y"), height: el.getAttribute("height") }
    });
  });

  var overlay = {};
  // 2026-10-30 补上 "big"：setBig 那一拍（每部片子的「错误答案」几乎都用它）
  // 原来不在这张表里，于是那些镜在转储里表现为「0 图元 + 无活跃覆盖层」，
  // 看上去像空镜，实际画面是满的 —— 整整一类镜处在探针的盲区。
  ["capWrap","eqBox","narr","sum","quiz","titleL","cap","big"].forEach(function(id){
    var el = document.getElementById(id);
    if (!el) return;
    var r = el.getBoundingClientRect();
    overlay[id] = {
      box: toCanvas(r),
      hidden: !!el.hidden,
      off: el.classList.contains("off"),
      scrollH: el.scrollHeight, clientH: el.clientHeight,
      overflow: el.scrollHeight - el.clientHeight,
      chars: (el.innerText || "").replace(/\s+/g," ").trim().length
    };
  });

  // 字幕的**行盒**：容器盒横跨整幅且顶边高于第一行文字，用它判重叠会大量误报。
  // Range.getClientRects() 给的是每一行实际占的矩形，这才是读者看到的东西。
  var capLines = [];
  ["cap","narr"].forEach(function(id){
    var el = document.getElementById(id);
    if (!el || el.hidden) return;
    var rg = document.createRange(); rg.selectNodeContents(el);
    Array.prototype.forEach.call(rg.getClientRects(), function(r){
      if (r.width > 1 && r.height > 1) capLines.push(toCanvas(r));
    });
  });

  // 公式的**字形盒**：mjx-container 是 MathJax 排好的那一块，.tok 是 flip() 的 token。
  // 拿 #eqBox 容器盒去判重叠会大量误报 —— 和字幕那条是同一个病。
  var eqLines = [];
  (function(){
    var e = document.getElementById("eqBox");
    if (!e || e.hidden || e.classList.contains("off")) return;
    Array.prototype.forEach.call(e.querySelectorAll("mjx-container, .tok"), function(g){
      var r = g.getBoundingClientRect();
      if (r.width > 1 && r.height > 1) eqLines.push(toCanvas(r));
    });
  })();

  var eq = document.getElementById("eqBox");
  return {
    eqLines: eqLines,
    capLines: capLines,
    nodeCount: nodes.length,
    nodes: nodes,
    overlay: overlay,
    eqText: eq ? (eq.innerText || "").replace(/\s+/g," ").trim().slice(0,120) : "",
    mjx: eq ? eq.querySelectorAll("mjx-container").length : 0,
    rawBackslash: eq ? (eq.innerText || "").indexOf(String.fromCharCode(92)) >= 0 : false,
    narrText: (function(){ var n=document.getElementById("narr");
      return n ? (n.innerText||"").replace(/\s+/g," ").trim() : ""; })()
  };
})()
`;

async function probe(file, outPath, vw, vh) {
  const port = 9200 + Math.floor(Date.now() % 700);
  const profile = path.join(os.tmpdir(), "shotprobe-" + Date.now());
  const { child, page } = await launch(port, profile);
  const cdp = connect(page.webSocketDebuggerUrl);
  await cdp.ready;
  try {
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: vw, height: vh, deviceScaleFactor: 1, mobile: false,
    });

    // 用 path.sep 拼，不写反斜杠字面量 —— 本项目里凡是把反斜杠写进正则/字符串的地方
    // 都出过转义事故（已经八次）。
    const url = "file:///" + path.resolve(file).split(path.sep).join("/");
    await cdp.send("Page.navigate", { url });

    // 等引擎挂载。d3 与 MathJax 来自 CDN，是异步的；无头 Chrome 首次拉取可能很慢。
    let ready = false;
    let diag = null;
    for (let i = 0; i < 160; i++) {          // 40 秒
      try {
        ready = await cdp.evaluate("!!(window.__engine && window.__go && window.d3)");
      } catch (e) { /* 导航中 */ }
      if (ready) break;
      await sleep(250);
    }
    if (!ready) {
      // 失败时必须说清**缺什么**，而不是只说「没挂载」—— 否则下一步只能靠猜
      try {
        diag = await cdp.evaluate(`({
          readyState: document.readyState,
          scripts: document.querySelectorAll("script").length,
          srcs: [].slice.call(document.querySelectorAll("script[src]")).map(function(s){return s.src.slice(0,64);}),
          d3: typeof window.d3, MathJax: typeof window.MathJax,
          engine: typeof window.__engine, go: typeof window.__go,
          bodyLen: document.body ? document.body.innerHTML.length : -1
        })`);
      } catch (e) { diag = { evalError: e.message }; }
      throw new Error("40 秒内引擎没有挂载。现场：" + JSON.stringify(diag));
    }

    // 视口断言：字幕带与公式带用 vh 相对视口，窗口一变所有阈值一起失效
    const vp = await cdp.evaluate("({w:innerWidth,h:innerHeight})");
    if (vp.w !== vw || vp.h !== vh) {
      throw new Error(`视口应为 ${vw}x${vh}，实际 ${vp.w}x${vp.h} —— 阈值会全部失效`);
    }

    const patched = await cdp.evaluate(PATCHES);
    const n = await cdp.evaluate("window.__n || 0");
    if (!n) throw new Error("window.__n 为 0，读不到镜数");

    // 逐镜流式写 JSONL：第一行是表头，之后一行一镜。
    // 第一版把 87 镜攒成一个数组再 stringify，撑爆了 V8 的字符串上限；
    // 流式写还有个好处 —— 中途崩了也留下可用的部分数据，而不是全丢。
    const ws = fs.createWriteStream(outPath, { encoding: "utf8" });
    ws.write(JSON.stringify({
      _header: true,
      file: path.basename(file),
      viewport: { w: vw, h: vh },
      mode: "末态（d3 过渡已换成恒等，isFast 已强制，animate 已打桩）",
      layout: LAYOUT, shotCount: n,
    }) + "\n");

    const shots = [];
    for (let i = 0; i < n; i++) {
      await cdp.evaluate(`window.__go(${i}, true)`);
      // 【取样窗口】setEq 的非 FAST 分支是 setTimeout(go,150)：__go 刚回来的那一瞬间
      // eqBox 必然是 off + 空。下面的 settle 判据会把这个状态读成「这镜没有公式」，
      // 所以**必须先无条件等过这个窗口**，否则量到的不是这一镜的状态 ——
      // 修掉 setEq 竞态之前，这个位置上躺的是上一镜迟到的公式（串镜），
      // 修掉之后就是空的，两次都不是真相。
      await sleep(240);
      // MathJax 再给足预算（排版是异步的）。
      for (let k = 0; k < 30; k++) {
        const done = await cdp.evaluate(
          `(function(){var e=document.getElementById("eqBox");
            return !e || e.classList.contains("off") || !e.textContent.trim()
                   || e.querySelectorAll("mjx-container").length>0;})()`);
        if (done) break;
        await sleep(100);
      }
      await sleep(60);
      const d = await cdp.evaluate(DUMP);
      d.shot = i;
      ws.write(JSON.stringify(d) + "\n");
      shots.push(d);
      if ((i + 1) % 10 === 0) process.stderr.write(`  ...${i + 1}/${n}\n`);
    }
    await new Promise((r) => ws.end(r));

    return {
      file: path.basename(file),
      viewport: { w: vw, h: vh },
      patched, layout: LAYOUT, shotCount: n, shots,
    };
  } finally {
    try { cdp.ws.close(); } catch (e) {}
    try { child.kill(); } catch (e) {}
  }
}

// ── 判定：全部是对这份 JSON 的纯函数，离线可跑、可复核 ────────────────────
function judge(dump) {
  const issues = [];
  const add = (lvl, code, shot, msg) => issues.push({ lvl, code, shot, msg });
  for (const s of dump.shots) {
    const ov = s.overlay || {};
    // 1. 覆盖层溢出（SUM / QUIZ 卡看不到后面几栏）
    for (const id of ["sum", "quiz"]) {
      const o = ov[id];
      if (o && !o.hidden && !o.off && o.overflow > 2) {
        add("BLOCK", "overlay-overflow", s.shot,
          `#${id} 溢出 ${o.overflow}px（clientH ${o.clientH} / scrollH ${o.scrollH}，${o.chars} 字）`);
      }
    }
    // 2. 公式里漏出原始反斜杠
    if (s.rawBackslash) add("BLOCK", "raw-backslash", s.shot, `公式里有原始反斜杠：${s.eqText.slice(0, 50)}`);
    // 3. 画布元素落进公式带或字幕带
    // 用公式的**字形盒**（eqLines），不用 #eqBox 容器盒 ——
    // 容器盒横跨一大片、顶边又高出真正的公式一截，判出来的重叠绝大多数是假的
    // （旧注释自己写着「实测 15 条 eq-overlap 全假」）。
    // 老转储没有 eqLines 时退回容器盒，并在文案里声明这个数会虚报。
    const eqG = s.eqLines;
    const eq = ov.eqBox;
    const eqH = eq && eq.box ? eq.box.y2 - eq.box.y1 : 0;
    const eqLive = eqG ? eqG.length > 0
                       : (eq && !eq.hidden && !eq.off && s.eqText && eqH > 4);
    for (const nd of s.nodes) {
      if (nd.tag === "svg" || nd.tag === "g") continue;
      const b = nd.box;
      if (b.y2 > dump.layout.captionBand) {
        add("BLOCK", "under-caption", s.shot,
          `${nd.tag}.${nd.cls} 底边 ${b.y2} > 字幕带 ${dump.layout.captionBand}：${nd.text.slice(0, 24)}`);
      }
      // 和公式**字形**比，而且要压掉三成面积才算 —— 擦到边角不算。
      let eqHit = 0;
      if (eqLive && eqG) {
        const area = Math.max(0, b.x2 - b.x1) * Math.max(0, b.y2 - b.y1);
        for (const g of eqG) {
          const ox = Math.min(b.x2, g.x2) - Math.max(b.x1, g.x1);
          const oy = Math.min(b.y2, g.y2) - Math.max(b.y1, g.y1);
          if (ox > 0 && oy > 0) eqHit += ox * oy;
        }
        if (area <= 0 || eqHit <= 0.30 * area) eqHit = 0;
      } else if (eqLive) {
        eqHit = (b.y1 < eq.box.y2 && b.y2 > eq.box.y1) ? 1 : 0;
      }
      if (eqHit) {
        add(eqG ? "BLOCK" : "WARN", "eq-overlap", s.shot,
          (eqG ? "" : "【老转储，只能比容器盒，会虚报】") +
          `${nd.tag}.${nd.cls} (${b.y1}–${b.y2}) 与公式带 (${eq.box.y1}–${eq.box.y2}) 重叠：${nd.text.slice(0, 24)}`);
      }
      if (b.x1 < 0 || b.x2 > dump.layout.canvasW) {
        add("BLOCK", "x-overflow", s.shot,
          `${nd.tag}.${nd.cls} 横向出界 ${b.x1}–${b.x2}：${nd.text.slice(0, 24)}`);
      }
    }
    // 4. 画布标签的字号：一镜只许有一种。
    //    旧判据写死 13/14/15px，那是 .slbl 还固定 14px 时代的产物；
    //    现在 .slbl 是 clamp(12.5px,1.15vw,16.5px)，随视口变，硬编码整数集必然误报
    //    （实测 1440 宽下是 16.5px，一次报 36 条）。
    //    真正要防的是「随手写个字号」造成的字号泛滥，那就直接查有没有泛滥：
    //    同一镜里所有 .slbl 应当同号；要强调就用颜色或位置，不要偷偷改大小。
    const lblSizes = new Set(
      s.nodes.filter(n => n.tag === "text" && /slbl/.test(n.cls || ""))
             .map(n => Math.round(parseFloat(n.fontSize) * 2) / 2)
             .filter(v => v));
    if (lblSizes.size > 1) {
      add("WARN", "font-size", s.shot,
        `同一镜出现 ${lblSizes.size} 种画布字号：${[...lblSizes].join(" / ")}px`);
    }
  }
  return issues;
}

async function main() {
  const file = process.argv[2];
  if (!file || file.startsWith("--")) {
    console.log(fs.readFileSync(__filename, "utf8").split("*/")[0]);
    process.exit(2);
  }
  const [vw, vh] = arg("--viewport", "1440x900").split("x").map(Number);
  const out = arg("--out", "shots.json");
  process.stderr.write(`探针：${path.basename(file)} @ ${vw}x${vh}\n`);
  const dump = await probe(file, out, vw, vh);
  process.stderr.write(`量测环境：${vw}×${vh} / 末态模式\n`);
  process.stderr.write(`读到 ${dump.shotCount} 个镜 -> ${out}\n\n`);

  const issues = judge(dump);
  const blocking = issues.filter((i) => i.lvl === "BLOCK");
  const seen = new Set();
  for (const i of issues) {
    const k = i.code + "|" + i.shot;
    if (seen.has(k)) continue;
    seen.add(k);
    console.log(`[${i.lvl}] 镜${i.shot} ${i.code}: ${i.msg}`);
  }
  console.log(`\n${blocking.length} blocking · ${issues.length - blocking.length} warning` +
    `（去重后显示 ${seen.size} 条）`);
  process.exit(blocking.length ? 1 : 0);
}

main().catch((e) => { console.error("探针失败：" + e.message); process.exit(3); });
