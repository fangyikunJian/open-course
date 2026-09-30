# -*- coding: utf-8 -*-
"""放映厅出片前的机械检查。

每一条都对应一个**真实发生过的缺陷**，不是假想的风险。靠纪律记不住这些，靠脚本才行。

用法：
    python lint_film.py episodes-L01.json "../影片/L01-强化学习导论.html"

退出码非 0 表示有 blocking 级问题。
"""
import io
import json
import os
import re
import sys

BLOCK, WARN = "BLOCK", "WARN"
BS = chr(92)          # 显式构造反斜杠：本项目里凡是把反斜杠写进正则/字符串的地方都出过转义事故
issues = []


def add(level, code, msg):
    issues.append((level, code, msg))


def line_of(src, pos):
    return src[:pos].count(chr(10)) + 1


# ── 1. setEq 里的单反斜杠 ────────────────────────────────────────────────
# 事故实录：build_L01.py 里写 setEq("$$\gamma:\;0.5\;\rightarrow\;0.9$$")，
# 单反斜杠进了 JS 字符串字面量，被引擎吃掉转义：\g→g、\;→;、而 \r→**回车符**。
# 结果全片最关键的 γ 标签全坏，而 node --check 一路绿灯（这不是语法错误）。
def lint_setEq_escapes(src, path):
    for m in re.finditer(r'setEq\(\s*"((?:[^"\\]|\\.)*)"', src):
        body = m.group(1)
        line = src[:m.start()].count("\n") + 1
        # 找出前面反斜杠个数为奇数、且后接字母或 ; 的位置 —— 那就是会被 JS 吃掉的转义
        for mm in re.finditer(r'\\+', body):
            run = len(mm.group(0))
            nxt = body[mm.end():mm.end() + 1]
            if run % 2 == 1 and (nxt.isalpha() or nxt == ";"):
                add(BLOCK, "setEq-escape",
                    f"{path}:{line} setEq 里有单反斜杠 '\\{nxt}' —— JS 会吃掉它"
                    f"（\\r 更会变成回车符）。LaTeX 在这里必须写双反斜杠。")
                break


# ── 2. flip 里出现 LaTeX ────────────────────────────────────────────────
# 事故实录：假设 flip() 会排版 LaTeX，从未验证。真相是 setEq() 调
# MathJax.typesetPromise，而 flip() 只做 innerHTML=h，于是屏幕上出现原始反斜杠。
# flip 也不能改成走 MathJax —— 它靠 [data-id] 节点量位置做动画，MathJax 会重建 DOM。
def lint_flip_latex(src, path):
    for m in re.finditer(r'flip\(', src):
        # 取到该语句结尾（以 ')); ' 或 '); ' 收尾）
        seg = src[m.start():m.start() + 1600]
        end = seg.find("));")
        seg = seg[:end + 3] if end > 0 else seg.split(";")[0]
        if "\\" in seg:
            line = src[:m.start()].count("\n") + 1
            add(BLOCK, "flip-latex",
                f"{path}:{line} flip(...) 里出现反斜杠。flip **不跑 MathJax**，"
                f"只能用 HTML 的 <sub>/<sup> 与 unicode（≤ ∑ γ π ∞ →）。")


# ── 3. 原语实参个数与声明不符 ────────────────────────────────────────────
# 事故实录：arrow 声明 6 个形参，10 处调用传了 7 个（把 flow 正则替换成 arrow 时留下的
# 多余 true），第 7 个被静默丢弃 —— 作者以为请求了某个效果，其实从未渲染过。

def _strip_js_strings(js):
    """手写扫描器剥掉字符串字面量。arity 检查必须先剥，否则
    note("d = ( 0.50 , 0.25 , 0 )",640,266,"sm") 里字符串内的逗号
    会被当成实参分隔符 —— 这个假阳性真发生过。"""
    bs = chr(92)
    out = []
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        if c == '"' or c == "'":
            q = c
            i += 1
            while i < n:
                if js[i] == bs:
                    i += 2
                    continue
                if js[i] == q:
                    i += 1
                    break
                i += 1
            out.append('""')
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def lint_arity(src, path, engine_src):
    src = _strip_js_strings(src)
    sigs = {}
    for m in re.finditer(r'function\s+(\w+)\s*\(([^)]*)\)', engine_src):
        params = [p.strip() for p in m.group(2).split(",") if p.strip()]
        sigs[m.group(1)] = len(params)
    for name, nmax in sorted(sigs.items()):
        if name in ("fn",):        # fn 是数学函数生成器，调用形态特殊
            continue
        for m in re.finditer(r'\b' + name + r'\(', src):
            # 从左括号开始做括号配平，取出实参串
            i = m.end() - 1
            depth, j = 0, i
            while j < len(src):
                if src[j] in "([{":
                    depth += 1
                elif src[j] in ")]}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            argstr = src[i + 1:j]
            if "{" in argstr:      # 对象参数形态（如 mdpChain({...})），不查个数
                continue
            depth, n = 0, (1 if argstr.strip() else 0)
            for ch in argstr:
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                elif ch == "," and depth == 0:
                    n += 1
            if n > nmax:
                line = src[:m.start()].count("\n") + 1
                add(BLOCK, "arity",
                    f"{path}:{line} {name}(...) 传了 {n} 个实参，但只声明了 {nmax} 个 —— "
                    f"多余的会被静默丢弃。")


# ── 4. 无限动画 ─────────────────────────────────────────────────────────
# 3b1b 十五部片子里没有任何一个动画是不终止的。脉冲环、呼吸圆、行进虚线、
# 来回踱步的点，全部属于「首帧=末帧」，没有结论，因而不可能论证任何东西。
def _strip_comments(text):
    """剥掉 /* */ 与 // 注释再查关键字 —— 否则「这里没有 infinite 动画」这句
    自我说明的注释本身会被误判成违规（真发生过）。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    text = re.sub(r"(?m)^\s*#.*$", "", text)
    return text


def lint_infinite(html, path):
    html = _strip_comments(html)
    for pat, why in [
        # 原来这里是裸的 \binfinite\b，扫全文件。L10 的旁白引了讲座原话
        # 「might be continuous and infinite」，于是报了一处假 BLOCK。
        # "infinite" 在 RL 讲稿里是常用词（infinite horizon…），放着不管等于
        # 训练自己无视这个检查器。改成要求它落在 animation 声明里 ——
        # `animation: x 1s infinite` 和 `style.animationIterationCount="infinite"`
        # 都还在网里，纯散文不在。
        (r'animation[^;}]*\binfinite\b', "animation 声明里的 infinite"),
        # \s* 必须写在前视里面。原来是 `:\s*(?!1\b)`，\s* 会回溯到零宽，
        # 让前视落在 `1` 前面那个空格上而通过 —— 于是合法的
        # `animation-iteration-count: 1` 也被判成循环。自测里抓到的。
        (r'animation-iteration-count\s*:(?!\s*1\s*[;}\'"])',
         "iteration-count 不为 1"),
        (r'animation[^;}]*\balternate\b', "alternate（往复 = 首帧等于末帧）"),
        (r'setInterval\s*\(', "setInterval"),
    ]:
        n = len(re.findall(pat, html))
        if n:
            add(BLOCK, "infinite-anim", f"{path}: 发现 {n} 处 {why} —— 不允许循环动画。")


# ── 5. 已删除的装饰原语 ─────────────────────────────────────────────────
# 这些函数已从引擎移除，调用它们是运行时 ReferenceError，而 node --check 查不出来。
DELETED = ["ping", "breathe", "bob", "glow", "walker", "sweepMark", "loopArrows", "flow"]


def lint_deleted(src, path):
    for name in DELETED:
        for m in re.finditer(r'(?<![\w.])' + name + r'\s*\(', src):
            line = src[:m.start()].count("\n") + 1
            add(BLOCK, "deleted-primitive",
                f"{path}:{line} 调用了已删除的装饰原语 {name}() —— 运行时会抛 ReferenceError。")


# ── 6. 柱状图两端可见性 ─────────────────────────────────────────────────
# 事故实录：morphBars(rover(0.5)→rover(0.9), max=100) 的起始帧里，
# V(s₁)=1.36 只有 2.9px 高、V(s₂)=0.08 只有 0.2px，而讲解偏偏说
# 「盯住最左边那根，它被第二根追上并超过」—— 论证的前提在画面上不可见。
# 一个 morph 断言两个状态之间的对应关系；任一端不可读，就等于跟空白做对应。
MIN_PX = 6.0


def lint_bar_visibility(src, path):
    """两端可见性 + 削顶检查。

    动画的运动过程在无头/隐藏环境里无法验证（rAF 不触发，实测确认过），
    所以把能静态算的部分全部算出来：两个端点的柱高、以及有没有顶格削平。

    事故实录一：morphBars(rover(0.5)→rover(0.9), max=100) 起始帧里
    V(s₁)=1.36 只有 2.9px、V(s₂)=0.08 只有 0.2px，而讲解说「盯住最左边那根，
    它被第二根追上并超过」—— 论证的前提在画面上不可见。
    事故实录二：同一组数据在 max=10 下，s₅/s₆/s₇（11.3/20.1/35.7）全部顶格
    削平在同一高度，看上去像三者相等 —— 这是误导，不只是难看。
    """
    # 窗口原来是固定的 900 字符，会<b>溢到下一个图元调用里</b>：L12 KP6 的
    # morphBars 没有 vals 字段，于是 vals 正则读到了下一镜 fillBars 的
    # vals:[2.73,4.08,6.91,11.14]，拿它去比 morphBars 的 max=0.78，
    # 报了「4 根柱子顶格」的假警。改成在<b>本次调用结束处</b>截断。
    starts = [m.start() for m in re.finditer(r'(morphBars|fillBars|bars)\(\{', src)]
    for i, m in enumerate(re.finditer(r'(morphBars|fillBars|bars)\(\{', src)):
        hard = starts[i + 1] if i + 1 < len(starts) else len(src)
        close = src.find("});", m.start())
        end = min(m.start() + 900, hard, close + 3 if close >= 0 else len(src))
        seg = src[m.start():end]
        line = src[:m.start()].count(chr(10)) + 1
        kind = m.group(1)
        mx = re.search(r'max:\s*([0-9.]+)', seg)
        h = re.search(r'h:\s*([0-9.]+)', seg)
        if not mx:
            add(WARN, "bar-nomax",
                f"{path}:{line} {kind} 没写 max —— 各镜自动缩放会让跨镜比较失去意义。")
            continue
        mxv = float(mx.group(1))
        hv = float(h.group(1)) if h else 210.0
        # from / to / vals 三个数组都要查（morph 的两个端点都必须可读）
        for field in ("from", "to", "vals"):
            arr = re.search(field + r':\s*\[([-0-9.,\s]+)\]', seg)
            if not arr:
                continue
            try:
                vals = [abs(float(x)) for x in arr.group(1).split(",") if x.strip()]
            except ValueError:
                continue
            tiny = [v for v in vals if 0 < v / mxv * hv < MIN_PX]
            if tiny:
                add(WARN, "bar-invisible",
                    f"{path}:{line} {kind} 的 {field} 端有 {len(tiny)} 根柱高 < {MIN_PX}px "
                    f"(max={mxv}, h={hv}) —— 若讲解要读者比较它们，前提不可见。")
            clipped = [v for v in vals if v > mxv]
            if len(clipped) >= 2:
                add(WARN, "bar-clipped",
                    f"{path}:{line} {kind} 的 {field} 端有 {len(clipped)} 根柱子超过 max={mxv}，"
                    f"会一起顶格削平成同一高度 —— 读者会以为它们相等。"
                    f"要么提高 max，要么只画论证涉及的那几根。")


# ── 7. 动画镜必须声明 watch ─────────────────────────────────────────────
# 每个动画镜要能填满「驱动量 A→B，看读出量，因此某命题成立」。填不满就说明
# 这个动画没有论证载荷，应当渲染成静态。
ANIM = ["trace", "morphBars", "fillBars", "sweepGrid", "reveal"]


def lint_watch(src, path):
    shots = [m.start() for m in re.finditer(r'\bS\(\d', src)] + [len(src)]
    for a, b in zip(shots, shots[1:]):
        seg = src[a:b]
        used = [f for f in ANIM if re.search(r'\b' + f + r'\(', seg)]
        if not used:
            continue
        # 该镜是否明确告诉读者「看什么」。两种认可方式：
        #   (a) 结构标记：组装器把 watch 放在**讲解段落开头**，标记是 <b>看什么：</b>
        #   (b) 关键词：手写镜头里的「盯住 / 注意看 / 看…是否」等
        #
        # 这个检查的目标改过两次，两次都是因为它自己假报：
        #   一、只用关键词表 —— 有三条 watch 以单字「看」开头，表里没有；
        #   二、找画布上 y=626 的 note —— 那个位置在字幕带里，10 个动画镜全被盖住，
        #       watch 已改为写进讲解段落，于是这条结构标记也跟着换。
        has_watch = (re.search(r'<b>看什么：</b>', seg)
                     or re.search(r'(盯住|注意看|看着|观察|留意|watch)', seg)
                     or re.search(r'"看[^"]{8,}"', seg))
        if not has_watch:
            line = src[:a].count("\n") + 1
            add(WARN, "no-watch",
                f"{path}:{line} 这一镜用了动画 {used} 但没有一句「看什么」的提示 —— "
                f"填不满「驱动量 A→B，看读出量」就该改成静态。")


# ── 8. SUM 定格卡的文字预算 ─────────────────────────────────────────────
# 事故实录：KP1 的 SUM 卡实测 clientHeight 53px / scrollHeight 13112px —— 溢出
# 13059px；用户截图里 KP4 同样被截断，看不到最后一栏。根因不是字号，是文字太多
# （渲染后 708 字）。skills 对最终定格的要求是「能独立存在」= 一眼读完的一帧图。
SUM_BUDGET = 380
SUM_FIELD_MAX = 110
_TAGS = re.compile(r"<[^>]+>")


def lint_sum_length(src, path):
    pos = 0
    while True:
        k = src.find("SUM(", pos)
        if k < 0:
            break
        pos = k + 4
        i = src.find("{", k)
        if i < 0:
            continue
        depth, j = 1, i + 1
        while j < len(src) and depth > 0:
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
            j += 1
        blk = src[i:j]
        # 手工扫出双引号字符串，避免带反斜杠的正则（那类正则在本项目里出过多次事故）
        texts, a, n = [], 0, len(blk)
        while a < n:
            if blk[a] == '"':
                a += 1
                buf = []
                while a < n:
                    if blk[a] == BS:
                        a += 2
                        continue
                    if blk[a] == '"':
                        a += 1
                        break
                    buf.append(blk[a])
                    a += 1
                texts.append("".join(buf))
            else:
                a += 1
        plain = [len(_TAGS.sub("", t)) for t in texts]
        total = sum(plain)
        line = line_of(src, k)
        if total > SUM_BUDGET:
            add(WARN, "sum-too-long",
                "%s:%d SUM 卡合计 %d 字 > 预算 %d —— 卡片会溢出、看不到后面几栏。"
                "定格要能独立存在，一眼读完。" % (path, line, total, SUM_BUDGET))
        over = [v for v in plain if v > SUM_FIELD_MAX]
        if over:
            add(WARN, "sum-field-too-long",
                "%s:%d SUM 卡有 %d 栏超过 %d 字（最长 %d）—— 单栏太长会挤掉其余栏。"
                % (path, line, len(over), SUM_FIELD_MAX, max(over)))


# ── 9. LaTeX 反斜杠在**成片**里的转义层级 ────────────────────────────────
# 这一条的来历与其它八条不同：它来自一次**误判**，而不是一次缺陷。
# 当时用 shell grep 数成片里的反斜杠，把 BRE 的 \\ 当成了「两个反斜杠」，
# 于是得出「出货的 L01 有 120 处公式渲染错误」的结论，并据此写了一个
# 折半脚本，真的把好数据改坏了。用 Python 精确量一次就翻了案。
#
# 留下这条检查，是为了把**当时没有先问清楚的那个前提**钉死在代码里：
#   装配器对 draw_js 是**原样插入**的（build_episode 只做缩进），
#   只有 narration / SUM / QUIZ 这些**字符串字面量**才过 js_str 加倍。
#   所以内容 JSON 里的 draw_js 存的就是 **JS 源码层**。
#
# 判据（量的是成片 HTML，也就是 JS 源码层）：
#   \\pi  （2 个）→ JS 解析后 \pi  → MathJax ✓      这是唯一正确的层级
#   \pi   （1 个）→ JS 吃掉转义     → MathJax 收到 pi        ✗（第 1 条已覆盖源码侧）
#   \\\\pi（4 个）→ JS 解析后 \\pi → MathJax 读成换行+直立字母 ✗
#
# 不用 grep 数反斜杠。BRE / ERE / shell 引号三层各有一套反斜杠规则，
# 叠在一起没人算得对 —— 本项目在这上面已经翻过两次船。
LATEX_CMDS = ("pi", "gamma", "sum", "mid", "theta", "frac", "text", "left",
              "right", "max", "mathbb", "mathcal", "quad", "nabla", "big",
              "varepsilon", "to", "times", "le", "ge", "approx", "begin", "end")


def lint_latex_depth(html, path):
    def runs_before_letters(n):
        pat = ("(?<!" + re.escape(BS) + ")" + re.escape(BS * n)
               + "(?!" + re.escape(BS) + ")([A-Za-z]+)")
        return re.findall(pat, html)

    good = runs_before_letters(2)
    quad = runs_before_letters(4)
    solo = [w for w in runs_before_letters(1)
            if any(w.startswith(c) for c in LATEX_CMDS)]

    print("  latex-depth：正确层级 %d 处 · 单反斜杠(被JS吃掉) %d 处 · 四连(换行+直立) %d 处"
          % (len(good), len(solo), len(quad)))

    if quad:
        k = sorted(set(quad))
        add(BLOCK, "latex-depth-4",
            f"{path} 有 {len(quad)} 处四连反斜杠紧跟字母（{', '.join(k[:8])}）。"
            f"MathJax 会读成「换行 + 直立字母」。draw_js 存 JS 源码层，一条命令两个反斜杠。")
    if solo:
        k = sorted(set(solo))
        add(BLOCK, "latex-depth-1",
            f"{path} 有 {len(solo)} 处单反斜杠紧跟 LaTeX 命令名（{', '.join(k[:8])}）。"
            f"JS 字符串会吃掉这个转义，MathJax 只会收到命令名本身。")
    # 反向自证：一份含公式的片子必须读到若干正确层级的命令，否则说明这条检查
    # 根本没读到公式（指错文件 / 正则写错），此时「0 blocking」是假绿灯。
    if not good:
        add(WARN, "latex-depth-selfcheck",
            f"{path} 里一条 LaTeX 命令都没读到 —— 要么这片子真的没有公式，"
            f"要么这条检查指错了文件。人工确认之前不要相信它的绿灯。")


# ── 读内容源 ──────────────────────────────────────────────────────────────
# 事故实录：内容搬进 JSON 后，检查器仍按纯文本读文件，于是 flip-latex 把
# **JSON 自己的转义**（\" 与 \n）当成了 draw_js 里的反斜杠，对三处完全正确的
# flip(...)（它们用的是 <sub>/<sup> 与 unicode）报了 blocking。
# 同一个错误在别处是反向的：读错层会漏报。所以这里统一先解码，再把各镜的
# draw_js 拼成一份**合成源码**，每镜前加一行定位注释，行号仍然可用。
def load_source(path):
    raw = io.open(path, encoding="utf-8").read()
    if not path.endswith(".json"):
        return raw
    eps = json.loads(raw)
    if isinstance(eps, dict):
        eps = eps.get("episodes", [])
    out = []
    for ep in sorted(eps, key=lambda e: e["kp"]):
        for i, sh in enumerate(ep["shots"]):
            out.append("/* KP%d 镜%d */" % (ep["kp"], i))
            out.append(sh["draw_js"])
    print("  读入 %s：%d 集 %d 镜，合成源码 %d 行"
          % (os.path.basename(path), len(eps),
             sum(len(e["shots"]) for e in eps), len("\n".join(out).split("\n"))))
    if not out:
        raise SystemExit("%s 里一个镜头都没读到 —— 检查器指错了文件。" % path)
    return "\n".join(out)


def main():
    # 事故实录：本函数原来只认 argv[1]、argv[2]。一部片子拆成 a/b/c 三个分片之后，
    # 命令行是「三个 json + 一个 html」，于是 argv[2]（分片 b）被当成了 html：
    # 分片 b 的**原始 JSON 字节**被 latex-depth 按 HTML 扫，四连反斜杠（JSON 自己
    # 的转义层）报了 27 处假 BLOCK；与此同时分片 c 和真正的 HTML **一次都没被检查**。
    # 假红灯还只是浪费时间，假绿灯会放走真错误 —— 所以这里按扩展名分派，不按位置。
    args = sys.argv[1:]
    build_paths = [a for a in args if a.endswith(".json")]
    html_paths = [a for a in args if not a.endswith(".json")]
    if not build_paths or len(html_paths) != 1:
        print(__doc__)
        return 2
    html_path = html_paths[0]
    here = os.path.dirname(os.path.abspath(__file__))
    html = io.open(html_path, encoding="utf-8").read()
    engine_src = io.open(os.path.join(here, "build_common.py"), encoding="utf-8").read()
    engine_src += io.open(os.path.join(here, "eng.txt"), encoding="utf-8").read()

    for build_path in build_paths:
        src = load_source(build_path)
        lint_setEq_escapes(src, build_path)
        lint_flip_latex(src, build_path)
        lint_arity(src, build_path, engine_src)
        lint_deleted(src, build_path)
        lint_bar_visibility(src, build_path)
        lint_watch(src, build_path)
        lint_sum_length(src, build_path)

    lint_infinite(html, html_path)
    lint_latex_depth(html, html_path)

    blocking = [i for i in issues if i[0] == BLOCK]
    warns = [i for i in issues if i[0] == WARN]
    for level, code, msg in blocking + warns:
        print(f"[{level}] {code}: {msg}")
    print(f"\n{len(blocking)} blocking · {len(warns)} warning")
    if not issues:
        print("全部通过。")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
