#!/usr/bin/env node
/**
 * check_reader.js —— 精读页的实测。
 *
 *   node coursekit/check_reader.js                   # 当前课程全部
 *   node coursekit/check_reader.js L02               # 只测这一讲
 *   node coursekit/check_reader.js 别的课/course.json L02
 *
 * 为什么不能用编辑器预览面板测：它把页面塞进 data: URL，localStorage 直接抛
 * SecurityError，自测/错题本/翻页记忆全部测不到。必须起真 file:// 源。
 *
 * 期望值全部从页面自己的 N / Q / data-key 推出来，不写死 ——
 * 所以同一份脚本能测任何课程的任何一讲。
 * 零依赖：Node 内置的 http / child_process / WebSocket 驱动 CDP。
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
  "/usr/bin/google-chrome", "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find((p) => fs.existsSync(p));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (u) => new Promise((res, rej) => {
  http.get(u, (r) => { let b = ""; r.on("data", (c) => (b += c));
    r.on("end", () => { try { res(JSON.parse(b)); } catch (e) { rej(e); } }); }).on("error", rej);
});
const fileURL = (p) => "file:///" + p.replace(/\\/g, "/").split("/")
  .map(encodeURIComponent).join("/").replace("%3A", ":");

// ── 定位 course.json（和 _course.py 的规则一致）────────────────────
function findCourse(arg) {
  if (arg) {
    let p = path.resolve(arg);
    if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, "course.json");
    if (!fs.existsSync(p)) throw new Error("找不到 " + p);
    return p;
  }
  let d = process.cwd();
  for (let i = 0; i < 4; i++) {
    const p = path.join(d, "course.json");
    if (fs.existsSync(p)) return p;
    const nd = path.dirname(d);
    if (nd === d) break;
    d = nd;
  }
  throw new Error("当前目录往上找不到 course.json");
}

let pass = 0, fail = 0;
const ok = (name, cond, got) => {
  if (cond) { pass++; console.log("  [ok]   " + name); }
  else { fail++; console.log("  [FAIL] " + name + "   实测: " + JSON.stringify(got)); }
};

const PROFILE = path.join(os.tmpdir(),
  "cdp-reader-" + process.pid + "-" + Date.now().toString(36));

function dropProfile() {
  // 本次这个多半删不掉 —— Windows 上 Chrome 刚被 kill，文件句柄还没释放。
  // 所以顺手把**上几次**留下的也扫掉（那时它们的 Chrome 早已退出）。
  try { fs.rmSync(PROFILE, { recursive: true, force: true }); } catch (e) { /* 留给下次 */ }
  try {
    const dir = os.tmpdir();
    for (const n of fs.readdirSync(dir)) {
      if (n === "cdp-reader" || (n.startsWith("cdp-reader-") && path.join(dir, n) !== PROFILE)) {
        try { fs.rmSync(path.join(dir, n), { recursive: true, force: true }); } catch (e) {}
      }
    }
  } catch (e) {}
}

async function connect(port) {
  const child = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run",
    "--no-default-browser-check", "--disable-background-timer-throttling",
    "--allow-file-access-from-files", `--remote-debugging-port=${port}`,
    // ⚠ 每次用**全新** profile。原来固定在 cdp-reader，于是结果取决于历史 ——
    //   2026-10-23 实测：同一份逐字节未变的页面，先前 27/0，后来稳定 24/3，
    //   主题那三条全反（存的是 light，量出来是深色）。删掉 profile 立刻恢复 27/0。
    //   省下的启动时间不值得让闸门变成一个看运气的东西。
    `--user-data-dir=${PROFILE}`,
    "about:blank"], { stdio: "ignore" });
  let tgt;
  for (let i = 0; i < 60 && !tgt; i++) {
    try { tgt = (await getJSON(`http://127.0.0.1:${port}/json`)).find((x) => x.type === "page"); }
    catch (e) { /* 还没起来 */ }
    if (!tgt) await sleep(250);
  }
  if (!tgt) throw new Error("Chrome 起来了但没有 page target");
  const ws = new WebSocket(tgt.webSocketDebuggerUrl);
  let id = 0; const pend = new Map();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { const p = pend.get(m.id); pend.delete(m.id);
      m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
  });
  await new Promise((r) => ws.addEventListener("open", r));
  const send = (method, params = {}) => new Promise((res, rej) => {
    const n = ++id; pend.set(n, { res, rej });
    ws.send(JSON.stringify({ id: n, method, params })); });
  const ev = async (expr) => {
    const r = await send("Runtime.evaluate",
      { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error("页面内异常: " +
      (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  };
  // Page.enable / Runtime.enable 必须在 navigate 之前，否则页面停在 loading
  await send("Page.enable"); await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride",
    { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  return { child, ws, send, ev };
}

async function run(cdp, file, tag) {
  const { send, ev } = cdp;
  const url = fileURL(file);
  const load = async () => {
    await send("Page.navigate", { url });
    for (let i = 0; i < 60; i++) {
      if (await ev("document.readyState").catch(() => null) === "complete") break;
      await sleep(200);
    }
    await sleep(400);
  };
  const GO = (p) => `document.querySelectorAll('#strip b')[${p - 1}].click()`;
  const CUR = "+document.getElementById('pnum').value";

  console.log("\n══ " + tag + " ══════════════════════════════════════");
  await load();
  // 存档键由页面自己声明（body 的 data-key），脚本不重复推导一遍
  const KEY = (await ev("document.body.dataset.key")) + "quiz";
  // 连同旧格式的键一起清干净：模板里有一段一次性迁移会去读它，
  // 不清的话上一轮的残留会被搬进来，测试就不是从零开始的。
  await ev(`localStorage.removeItem(${JSON.stringify(KEY)});` +
           `localStorage.removeItem(${JSON.stringify(tag.toLowerCase() + "quiz")})`);
  await load();

  // ── 前提 ──
  ok("真 file:// 源（不是 data:）", (await ev("location.protocol")) === "file:",
     await ev("location.protocol"));
  ok("localStorage 可用", (await ev(
    "(function(){try{localStorage.setItem('__t','1');var v=localStorage.getItem('__t');" +
    "localStorage.removeItem('__t');return v==='1'}catch(e){return 'ERR:'+e.name}})()")) === true,
     await ev("(function(){try{localStorage.setItem('__t','1');return true}" +
              "catch(e){return 'ERR:'+e.name}})()"));
  ok("存档键带课程前缀（多门课放一起不会互相覆盖）",
     /.+-.+quiz$/.test(KEY), KEY);
  // 用字符类而不是 \D：这串要穿过 JS 字符串字面量再到页面，
  // "\D" 在字面量里会退化成 "D"，于是变成删字母 D，结果是 NaN。
  const nPages = +(await ev(
    "document.getElementById('tot').textContent.replace(/[^0-9]/g,'')"));
  ok("页条格数 = 顶栏标的总页数",
     (await ev("document.querySelectorAll('#strip b').length")) === nPages,
     [await ev("document.querySelectorAll('#strip b').length"), nPages]);
  ok("左边内嵌的正是这一讲的课件", (await ev(
    "document.getElementById('pdf').src.indexOf(" +
    "document.querySelector('#miss code').textContent.split('/').pop())>=0")) === true,
     await ev("document.getElementById('pdf').src"));

  // ── 题库自洽（页面里跑的那一份，不是 JSON 文件） ──
  const badQ = await ev(
    "JSON.stringify(Object.keys(Q).filter(function(k){return Q[k].some(function(q){" +
    "return !(q.a>=0&&q.a<q.o.length)||!q.why||q.o.length<3})}))");
  ok("每题：正确项在范围内 · 有解释 · 选项≥3", badQ === "[]", badQ);
  const orphan = await ev(
    "JSON.stringify(Object.keys(Q).filter(function(k){" +
    "return !N.some(function(n){return n.r[0]==+k})}))");
  ok("没有孤儿题（都挂在真实讲解单元上）", orphan === "[]", orphan);
  ok("同一页内没有重复题面", (await ev(
    "JSON.stringify(Object.keys(Q).filter(function(k){var s={};" +
    "return Q[k].some(function(q){if(s[q.q])return true;s[q.q]=1;return false})}))")) === "[]", null);

  // ── 每一页都能渲染，而且始终只有一张卡片 ──
  const bad = await ev(
    "(function(){var out=[],c=document.querySelectorAll('#strip b');" +
    "for(var p=1;p<=c.length;p++){" +
    "document.querySelectorAll('#strip b')[p-1].click();" +
    "var h=document.querySelectorAll('#card>h2').length," +
    "    e=document.querySelectorAll('#card .empty').length;" +
    "if(h+e!==1) out.push(p+':h'+h+'e'+e);}return JSON.stringify(out)})()");
  ok("逐页翻一遍：每页恰好一张卡片（讲解卡或空页提示）", bad === "[]", bad);

  const noq = await ev(
    "(function(){var out=[];Object.keys(Q).forEach(function(k){" +
    "document.querySelectorAll('#strip b')[+k-1].click();" +
    "var n=document.querySelectorAll('.qq').length;" +
    "if(n!==Q[k].length) out.push(k+':'+n+'/'+Q[k].length);});return JSON.stringify(out)})()");
  ok("有题的页，题目全都渲染出来了", noq === "[]", noq);

  // ── 答错：判定 → 记录 → 页条标红 ──
  const first = await ev("Object.keys(Q).sort(function(a,b){return a-b})[0]");
  await ev(GO(+first)); await sleep(150);
  await ev("(function(){var a=Q[" + first + "][0].a;" +
           "document.querySelectorAll('.qq')[0].querySelectorAll('.opt')[a===0?1:0].click()})()");
  await sleep(150);
  ok("错项标红、正解同时点亮、解释显示",
     (await ev("document.querySelectorAll('.opt.no').length")) === 1 &&
     (await ev("document.querySelectorAll('.qq')[0].querySelectorAll('.opt.ok').length")) === 1 &&
     (await ev("getComputedStyle(document.querySelector('.why')).display")) === "block", null);
  ok("选项锁死，不能改答案",
     (await ev("Array.prototype.every.call(document.querySelectorAll('.qq')[0]" +
               ".querySelectorAll('.opt'),function(b){return b.disabled})")) === true, null);
  ok("答过的选项写进 localStorage（只记选了哪项，不记次数/错数/排名）",
     (await ev(`JSON.stringify(JSON.parse(localStorage.getItem(${JSON.stringify(KEY)}))['${first}#0'])`))
     === `{"a":${await ev("Q[" + first + "][0].a===0?1:0")}}`,
     await ev(`localStorage.getItem(${JSON.stringify(KEY)})`));

  // ── 备考外壳必须真的不在**渲染出来的页面**上 ──
  // grep 源码看不出这一条：模板里没有的东西，运行时也可能被别处注入。
  ok("备考外壳已移除：没有错题本按钮 / 面板、没有复习模式 chip、没有历史六格",
     (await ev("(function(){return !document.getElementById('wrongBtn') && " +
               "!document.getElementById('wrongPanel') && " +
               "!document.getElementById('revChip') && " +
               "document.querySelectorAll('.qhist').length===0;})()")) === true, null);

  // ── 刷新后答过状态还在（换页回来能看见自己上次怎么答的）──
  await load();
  await ev(GO(+first)); await sleep(200);
  ok("重新打开页面，答过的题仍是已判定态（正解亮 · 错项红 · 解释可见 · 选项锁死）",
     (await ev("(function(){var b=document.querySelector('.qq');if(!b)return 'no-qq';" +
               "var k=b.querySelector('.opt.ok'), n=b.querySelector('.opt.no'), " +
               "    w=b.querySelector('.why');" +
               "return !!(k && n && w && w.style.display!=='none' && k.disabled);})()")) === true,
     await ev(`localStorage.getItem(${JSON.stringify(KEY)})`));


  // ── 三个新字段：必须真的渲染出来，而且字号不许超过讲解正文 ──
  // 每条都先算出「第一个有该字段的页」；一个都没有就抛错。
  // 命中数为 0 必须失败，不许静默通过（PROJECT-SKILL §14 第 2 条）。
  const firstWith = async (k) => await ev(
    "(function(){for(var i=0;i<N.length;i++)if(N[i]." + k + ") return N[i].r[0]; return -1;})()");

  const pQuote = await firstWith("quote");
  if (pQuote < 0) throw new Error("没有任何一页有 quote —— 闸门在空跑");
  await ev(GO(pQuote)); await sleep(200);
  ok("quote 渲染出来了，且字号 ≤ 讲解正文",
     (await ev("(function(){var q=document.querySelector('.quote');if(!q)return 'missing';" +
               "return q.textContent.trim().length>0 && " +
               "parseFloat(getComputedStyle(q).fontSize)<=15.01;})()")) === true, null);

  const pTbl = await firstWith("tbl");
  if (pTbl < 0) throw new Error("没有任何一页有 tbl —— 闸门在空跑");
  await ev(GO(pTbl)); await sleep(200);
  ok("表格渲染出来了，表头列数 = 每行格数",
     (await ev("(function(){var t=document.querySelector('table.tbl');if(!t)return 'missing';" +
               "var h=t.querySelectorAll('thead th').length;" +
               "var rows=[].slice.call(t.querySelectorAll('tbody tr'));" +
               "return h>0 && rows.length>0 && rows.every(function(r){" +
               "  return r.querySelectorAll('td').length===h;});})()")) === true, null);
  ok("表格自己横向滚，不撑破右栏",
     (await ev("(function(){var t=document.querySelector('table.tbl')," +
               "r=document.getElementById('right');if(!t)return 'missing';" +
               "return r.scrollWidth<=r.clientWidth+1;})()")) === true,
     await ev("(function(){var r=document.getElementById('right');" +
              "return [r.scrollWidth,r.clientWidth];})()"));

  const pRes = await firstWith("res");
  if (pRes < 0) throw new Error("没有任何一页有 res —— 闸门在空跑");
  await ev(GO(pRes)); await sleep(200);
  ok("科研格渲染出来了，且出处档位在页面上真的可见",
     (await ev("(function(){var r=document.querySelector('.res');if(!r)return 'missing';" +
               "var t=r.querySelector('.tag');if(!t)return 'no-tag';" +
               "var s=t.textContent.trim();" +
               "return ['已核','推断','待核'].indexOf(s)>=0 && " +
               "       getComputedStyle(t).display!=='none' && " +
               "       !!r.querySelector('.ref') && " +
               "       parseFloat(getComputedStyle(r).fontSize)<=15.01;})()")) === true,
     await ev("(function(){var t=document.querySelector('.res .tag');" +
              "return t?t.textContent:null;})()"));

  // ── 讲级科研主线卡 ──
  ok("讲级科研主线卡：按钮可见、能打开、四段都渲染、出处档位可见",
     (await ev("(function(){var b=document.getElementById('threadBtn');" +
               "if(!b||b.hidden)return 'btn-hidden';b.click();" +
               "var p=document.getElementById('threadPanel');" +
               "if(!p.classList.contains('on'))return 'not-open';" +
               "var arc=document.getElementById('threadArc').textContent.trim();" +
               "var body=document.getElementById('threadBody');" +
               "var n=body.querySelectorAll('ol').length;" +
               "var rf=body.querySelectorAll('.rf').length;" +
               "document.getElementById('threadClose').click();" +
               "return arc.length>0 && n>=3 && rf>0 && !p.classList.contains('on');})()")) === true,
     await ev("(function(){var b=document.getElementById('threadBtn');" +
              "return b?(b.hidden?'hidden':'visible'):'absent';})()"));

  // ── 双主题：浅色默认 · 能切 · 记得住 · 浅色下对比度够 ──
  // 断言只认 data-theme 属性，不认 localStorage 的键名 —— 键名是实现细节
  // （_kit 用 theme.py 注入，CS234 原地那套用模板内建，两者键名不同）。
  // ⚠ 正则一律用字符类 [0-9]，不用 \d：这些是**字符串里的正则**，JS 字符串
  //   字面量会吃掉一层反斜杠，"\d" 退化成 "d"，匹配不到 "rgb(245, 243, 238)"。
  const lum = "(function(c){var m=c.match(/[0-9]+/g);" +
              "return m ? (+m[0]*0.299 + +m[1]*0.587 + +m[2]*0.114) : null;})";

  ok("默认是浅色（没有 data-theme=dark），且背景确实是浅的",
     (await ev("(function(){if(document.documentElement.getAttribute('data-theme')==='dark')" +
               "return 'defaults-dark';var L=" + lum + ";" +
               "var v=L(getComputedStyle(document.body).backgroundColor);" +
               "return v===null ? 'no-bg' : v>200;})()")) === true,
     await ev("getComputedStyle(document.body).backgroundColor"));

  ok("点一下切到暗色，背景真的变暗",
     (await ev("(function(){var b=document.getElementById('themeBtn');" +
               "if(!b)return 'no-btn';b.click();var L=" + lum + ";" +
               "return document.documentElement.getAttribute('data-theme')==='dark' && " +
               "L(getComputedStyle(document.body).backgroundColor)<60;})()")) === true,
     await ev("getComputedStyle(document.body).backgroundColor"));

  await load();
  ok("重新打开页面，主题选择还记得",
     (await ev("document.documentElement.getAttribute('data-theme')")) === "dark",
     await ev("document.documentElement.getAttribute('data-theme')"));

  // 切回浅色再量对比度 —— 浅色最容易翻车的就是「暗色下够亮的字，
  // 浅色下变成浅灰压在米色纸上」。这一条 grep 和肉眼都抓不到。
  await ev("document.getElementById('themeBtn').click()"); await sleep(120);
  await ev(GO(+first)); await sleep(200);
  const contrast = JSON.parse(await ev(
    "(function(){" +
    "function L(c){var m=c.match(/[0-9]+/g).slice(0,3).map(function(v){" +
    "  v=v/255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4);});" +
    "  return 0.2126*m[0]+0.7152*m[1]+0.0722*m[2];}" +
    "function R(fg,bg){var a=L(fg),b=L(bg);var hi=Math.max(a,b),lo=Math.min(a,b);" +
    "  return Math.round(((hi+0.05)/(lo+0.05))*100)/100;}" +
    "var page=getComputedStyle(document.getElementById('right')).backgroundColor;" +
    "var g=function(sel){var e=document.querySelector(sel);return e?" +
    "  R(getComputedStyle(e).color,page):null;};" +
    "return JSON.stringify({正文:g('#card ul li'),一句话:g('.one')," +
    "  讲稿:g('.say'),科研格:g('.res'),解释:g('.why'),加粗:g('#card b')});})()"));
  console.log("      浅色对比度 " + JSON.stringify(contrast));
  ok("浅色下正文类文字对比度全部 ≥ 4.5（WCAG AA）",
     Object.values(contrast).every((v) => v === null || v >= 4.5), contrast);

  // ── 引用了却没定义的 CSS 变量 ──
  // 为什么要有这一条：theme.py 的 HARDCODED 表只管「写死的颜色 → 变量名」，
  // 两套调色板里有没有这个变量，它不检查。漏一个，那条声明就静默失效 ——
  // 浏览器不报错，框还在（退回继承来的边框），只是颜色不对了。
  // 实测：`--warnline` 这样躺了一阵，26 条断言全绿，肉眼也看不出来。
  // 这是最该自动抓的一类「假绿灯」，所以在这里一次把整类扫掉。
  // 故意不用正则：`\(` 一类的转义经 heredoc 会退化（规矩 D 撞过三次），
  // 纯 indexOf + 字符集扫描没有这个风险。
  const cssvars = JSON.parse(await ev(
    "(function(){" +
    "var css=Array.prototype.map.call(document.querySelectorAll('style')," +
    "  function(s){return s.textContent;}).join('  ');" +
    "var idc='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-';" +
    "function nm(i){var j=i;while(j<css.length&&idc.indexOf(css.charAt(j))>=0)j++;" +
    "  return css.slice(i,j);}" +
    "function nxt(k){while(k<css.length&&css.charAt(k)===' ')k++;return css.charAt(k);}" +
    "var used={},def={},p=0,n,m,c;" +
    "while((p=css.indexOf('var(--',p))>=0){n=nm(p+4);" +
    "  c=nxt(p+4+n.length);" +          // 有 fallback（var(--x, red)）的不算缺
    "  if(n&&c!==',')used[n]=1; p+=6;}" +
    "p=0;" +
    "while((p=css.indexOf('--',p))>=0){m=nm(p);" +
    "  if(m&&nxt(p+m.length)===':')def[m]=1; p+=2;}" +
    "return JSON.stringify({用了:Object.keys(used).length," +
    "  定义了:Object.keys(def).length," +
    "  缺定义:Object.keys(used).filter(function(k){return !def[k];}).sort()});})()"));
  console.log("      CSS 变量 用了 " + cssvars.用了 + " 个 · 定义了 " +
              cssvars.定义了 + " 个 · 缺定义 " + cssvars.缺定义.length + " 个");
  ok("每个被 var() 引用的 CSS 变量都真的有定义（没有静默失效的声明）",
     cssvars.缺定义.length === 0, cssvars.缺定义);

  // ── 版面：题面不许比讲解正文大 ──
  await ev(GO(+first)); await sleep(200);
  const f = JSON.parse(await ev(
    "(function(){var g=function(s){var e=document.querySelector(s);" +
    "return e?parseFloat(getComputedStyle(e).fontSize):null};" +
    "return JSON.stringify({正文:g('#card>ul>li')||g('.one'),题面:g('.qq .t')," +
    "选项:g('.opt'),解释:g('.why')})})()"));
  console.log("      字号 " + JSON.stringify(f));
  ok("题面 / 选项 / 解释都不比讲解正文大",
     f["题面"] <= f["正文"] + 0.5 && f["选项"] <= f["正文"] + 0.5, f);

  ok("右栏没有横向溢出", (await ev(
    "(function(){var r=document.getElementById('right');" +
    "return r.scrollWidth<=r.clientWidth+2})()")) === true, null);

  await ev(`localStorage.removeItem(${JSON.stringify(KEY)})`);
}

(async () => {
  if (!CHROME) throw new Error("找不到 Chrome 或 Edge");
  let args = process.argv.slice(2);
  let cArg = null;
  if (args.length && (args[0].endsWith(".json") || fs.existsSync(args[0]))) cArg = args.shift();
  const cpath = findCourse(cArg);
  const root = path.dirname(cpath);
  const course = JSON.parse(fs.readFileSync(cpath, "utf8"));
  const want = args.map((s) => s.toUpperCase());

  const name = (course.reader_name || "{tag}-精读.html");
  const targets = course.lectures
    .filter((L) => !want.length || want.includes(L.tag.toUpperCase()))
    .map((L) => ({ tag: L.tag,
                   file: path.join(root, course.dirs.reader,
                                   name.replace("{tag}", L.tag)) }))
    .filter((t) => fs.existsSync(t.file));
  if (!targets.length) throw new Error("没有已生成的精读页可测");

  const cdp = await connect(9412);
  for (const t of targets) await run(cdp, t.file, t.tag);
  console.log("\n" + "═".repeat(54));
  console.log(`通过 ${pass} · 失败 ${fail}   （${targets.length} 讲）`);
  cdp.ws.close(); cdp.child.kill();
  dropProfile();
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("崩了: " + e.message); dropProfile(); process.exit(2); });
