# -*- coding: utf-8 -*-
"""重新分布 CS234 精读自测题的答案位置。

**只改 quiz 里每道题的 `o`（选项顺序）与 `a`（正确项下标），别的一个字节不动。**
所以做法不是「解析整个 JSON 再写回去」—— 那会把 notes 也重排一遍，
diff 里全是无关改动，也就没法一眼看出「讲解没被动过」。

做法是字符级定位：在 quiz 块里逐个找到题目对象，取出它 `"o": [...]` 的
原始子串与 `"a": N` 的原始子串，只替换这两处。

自证：**恒等置换必须让文件逐字节不变**。做不到就说明定位或序列化有偏差，
那时候任何打散结果都不可信。
"""
import io
import json
import os
import random
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8")

SEED = 20261012
BOLD = re.compile(r"</?b>")


def find_block(s, i):
    """从 s[i] 处的 { 或 [ 开始，返回配对闭括号的下标（含）。字符串内的括号不算。"""
    open_ch = s[i]
    close_ch = {"{": "}", "[": "]"}[open_ch]
    depth, j, in_str, esc = 0, i, False, False
    while j < len(s):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return j
        j += 1
    raise ValueError("括号不配对，从 %d 开始" % i)


def iter_questions(s):
    """产出 quiz 块里每个题目对象的 (起, 止) 下标。止是闭括号的下标。"""
    qi = s.find('"quiz"')
    if qi < 0:
        return
    brace = s.index("{", qi)
    end = find_block(s, brace)
    blk_s, blk_e = brace, end
    # 在 quiz 块里找每个页码键后面的数组，数组里每个 { 就是一道题
    j = blk_s + 1
    while j < blk_e:
        if s[j] == "[":
            arr_end = find_block(s, j)
            k = j + 1
            while k < arr_end:
                if s[k] == "{":
                    qe = find_block(s, k)
                    yield k, qe
                    k = qe + 1
                elif s[k] == '"':          # 跳过字符串
                    k = skip_str(s, k)
                else:
                    k += 1
            j = arr_end + 1
        elif s[j] == '"':
            j = skip_str(s, j)
        else:
            j += 1


def skip_str(s, i):
    """s[i] 是开引号，返回闭引号之后的下标。"""
    j, esc = i + 1, False
    while j < len(s):
        c = s[j]
        if esc:
            esc = False
        elif c == "\\":
            esc = True
        elif c == '"':
            return j + 1
        j += 1
    raise ValueError("字符串没有闭合")


def field_span(s, a, b, name):
    """在 s[a:b] 这个题目对象里定位 "name": <值> 的值的 (起, 止)。止不含。"""
    key = '"%s"' % name
    i = s.index(key, a, b)
    j = s.index(":", i + len(key), b) + 1
    while s[j] in " \t\n":
        j += 1
    if s[j] in "[{":
        return j, find_block(s, j) + 1
    # 标量：读到逗号或对象结束
    k = j
    depth = 0
    while k < b:
        if s[k] in ",}" and depth == 0:
            break
        k += 1
    return j, k


def dump_opts(opts, sample):
    """按原样本的排版风格序列化选项数组。

    两种风格都要认 —— L02–L09 是单行，L01.a/b/c 与 L10 是多行且带缩进。
    第一版只认单行，自证当场在 L01.b 上拦下来了。
    """
    dumps = [json.dumps(o, ensure_ascii=False) for o in opts]
    if "\n" not in sample:
        sep = ", " if '", "' in sample else ","
        return "[" + sep.join(dumps) + "]"
    # 多行：从样本里量出每项的缩进与闭括号的缩进
    lines = sample.split("\n")
    item_indent = re.match(r"\s*", lines[1]).group(0)
    close_indent = re.match(r"\s*", lines[-1]).group(0)
    body = (",\n" + item_indent).join(dumps)
    return "[\n" + item_indent + body + "\n" + close_indent + "]"


def process(path, identity=False, strip_bold=True, salt=0):
    s0 = io.open(path, encoding="utf-8", newline="").read()
    spans = list(iter_questions(s0))
    out, prev, n, nbold, pos = [], 0, 0, 0, {}
    for a, b in spans:
        os_a, os_b = field_span(s0, a, b, "o")
        as_a, as_b = field_span(s0, a, b, "a")
        raw_opts = s0[os_a:os_b]
        opts = json.loads(raw_opts)
        ans = int(s0[as_a:as_b].strip())
        # ① 清掉选项里的加粗
        clean = [BOLD.sub("", o) for o in opts] if strip_bold else list(opts)
        nbold += sum(1 for x, y in zip(opts, clean) if x != y)
        # ② 打散。种子取自文件名 + 题在文件中的序号 + 盐 => 稳定可复现。
        # ⚠ 这里**不能**用 hash()：Python 的字符串 hash 每个进程都不同
        # （2026-10-07 实测：同一字符串三次独立进程得到三个值），
        # 于是「稳定可复现」只是注释里的一句话，实际每跑一次都是新的抽奖。
        # zlib.crc32 是确定的，跨进程、跨版本都一样。
        idx = list(range(len(clean)))
        if not identity:
            key = zlib.crc32(os.path.basename(path).encode("utf-8")) % 9973
            random.Random(SEED * 1000 + key * 97 + n + salt * 7919).shuffle(idx)
        new_opts = [clean[i] for i in idx]
        new_ans = idx.index(ans)          # 按下标搬运，重复文本也不会搬错
        pos[new_ans] = pos.get(new_ans, 0) + 1
        n += 1
        # 只替换这两段，其余原样
        assert os_a < as_a, "本文件里 a 在 o 之前，定位逻辑要改"
        out.append(s0[prev:os_a])
        out.append(dump_opts(new_opts, raw_opts))
        out.append(s0[os_b:as_a])
        out.append(str(new_ans))
        prev = as_b
    out.append(s0[prev:])
    return "".join(out), n, nbold, pos, s0


def ok_spread(pos, n):
    """打散的结果够不够散。判据与 build_reader.check_quiz_leak **逐条一致** ——
    两边不一致的话，这里放过去的会在那边被拦，等于白打散一次。"""
    if n >= 8:
        for k in pos:
            if pos[k] > n * 0.5:
                return False
    elif n >= 4 and len(pos) == 1:
        return False
    return True


def main():
    files = sys.argv[1:]
    if not files:
        raise SystemExit("用法：reshuffle.py <data/*.json>")

    # ── 自证：恒等置换必须逐字节不变 ──
    for f in files:
        # identity 模式必须连「清加粗」也关掉 —— 否则 L09 p33 那处真泄题
        # 会让自证失败，而那是**内容上的有意改动**，不是定位错误。
        # 两件事混在一起，自证就分不清「定位错了」和「确实该改」。
        got, _, _, _, s0 = process(f, identity=True, strip_bold=False)
        if got != s0:
            raise SystemExit("自证失败：%s 在恒等置换下发生了改变，定位逻辑不可信" % f)
    print("自证通过：%d 个文件在恒等置换下逐字节不变\n" % len(files))

    tot = {}
    for f in files:
        # ── 打散完必须自己合格，否则换盐重试 ──
        # 判据与 build_reader.check_quiz_leak 一致。不自检的后果实测过：
        # 2026-10-07 把 C13.b.json 从 3/7/6/3 打成 2/2/11/4（58% 全在 C），
        # 而构建闸门量的是**合并后**的题集，单片的集中被稀释，一路绿灯。
        # 「打散」这个动作本身不保证结果更好 —— 必须验。
        for salt in range(64):
            new, n, nbold, pos, s0 = process(f, salt=salt)
            if ok_spread(pos, n):
                break
        else:
            raise SystemExit(
                "%s：连试 64 个盐都没打散到合格（%d 题，位置 %s）。"
                "多半是题太少或选项数太少，手工调题比继续抽奖有用。"
                % (os.path.basename(f), n,
                   "/".join(str(pos.get(i, 0)) for i in range(4))))
        io.open(f, "w", encoding="utf-8", newline="").write(new)
        for k, v in pos.items():
            tot[k] = tot.get(k, 0) + v
        print("%-12s %3d 题  清掉加粗 %d 处  位置 %s%s"
              % (os.path.basename(f), n, nbold,
                 "/".join(str(pos.get(i, 0)) for i in range(4)),
                 "" if salt == 0 else "  （换了 %d 次盐才合格）" % salt))
    N = sum(tot.values())
    print("\n合计 %d 题，位置 A/B/C/D = %s（各占 %s）"
          % (N, "/".join(str(tot.get(i, 0)) for i in range(4)),
             " ".join("%.0f%%" % (tot.get(i, 0) / N * 100) for i in range(4))))


if __name__ == "__main__":
    main()
