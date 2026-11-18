# -*- coding: utf-8 -*-
"""
CME 295 (Autumn 2025, Afshine & Shervine Amidi) 全部公开课字幕：下载 + 转成两种文本。

    python fetch_transcripts.py            # 下载缺的讲次并生成文本（已存在且一致的不动）
    python fetch_transcripts.py --check    # 回归测试：用现有 vtt 重新生成，逐字节对比现有 txt
    python fetch_transcripts.py --convert  # 只从 _vtt/ 里已有的字幕重新生成文本，不联网

产物（都在 transcripts/ 下）：
    L{n}.txt        标题头 + 视频链接，正文按句拼好、一句一行
    L{n}_timed.txt  每隔 ≥30 秒取一条 cue 的定位索引，形如 [mm:ss] 原文（分钟不进位到小时）
    _vtt/{id}.*.vtt YouTube 原始字幕（只取人工字幕；没有人工字幕才退回自动字幕）

时间码查法：在 L{n}_timed.txt 里找到那句话 → 取 [mm:ss] → 链接加 &t={秒}s。
依赖：yt-dlp（pip install yt-dlp）。本脚本不依赖项目外的任何文件。
"""
import argparse, glob, html, io, os, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
# 2026-10-30 目录对齐到项目约定（以 cs224r-2025 为模板）：
#   工具在 tools/，内容在 corpus/{transcripts,subtitles}/。
#   ⚠ 这两行若不跟着改，脚本会在 tools/ 下重新建一套空的 transcripts/，
#     而且**不会报错** —— 它只会把 9 讲重新下载一遍。
ROOT = os.path.dirname(HERE)
TDIR = os.path.join(ROOT, "corpus", "transcripts")
VDIR = os.path.join(ROOT, "corpus", "subtitles")
PLAYLIST = "PLoROMvodv4rOCXd21gf0CF4xr35yINeOy"   # Stanford CME295 Autumn 2025，9 个视频

# 键 → (视频 ID, 标题头)。这门课 9 讲，播放列表序号与讲次一一对应。
LECTURES = [
    ("L1", "Ub3GoFaUcds", "Lecture 1 - Transformer"),
    ("L2", "yT84Y5zCnaA", "Lecture 2 - Transformer-Based Models & Tricks"),
    ("L3", "Q5baLehv5So", "Lecture 3 - Transformers & Large Language Models"),
    ("L4", "VlA_jt_3Qc4", "Lecture 4 - LLM Training"),
    ("L5", "PmW_TMQ3l0I", "Lecture 5 - LLM Tuning"),
    ("L6", "k5Fh-UgTuCo", "Lecture 6 - LLM Reasoning"),
    ("L7", "h-7S6HNq0Vg", "Lecture 7 - Agentic LLMs"),
    ("L8", "8fNP4N46RRo", "Lecture 8 - LLM Evaluation"),
    ("L9", "Q86qzJ1K1Ss", "Lecture 9 - Recap & Current Trends"),
]

TS = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d+)\s+-->\s+(\d+):(\d\d):(\d\d)\.(\d+)")
TAG = re.compile(r"<[^>]*>")


def secs(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 10 ** len(ms)


def parse_vtt(path):
    """返回 [(起始秒, 文本), ...]。多行 cue 用空格拼；去掉 <c> 等内联标签；解码 &amp; 这类实体。"""
    with io.open(path, encoding="utf-8") as f:
        blocks = re.split(r"\n\s*\n", f.read().replace("\r\n", "\n"))
    cues = []
    for b in blocks:
        lines = b.strip("\n").split("\n")
        for i, ln in enumerate(lines):
            m = TS.search(ln)
            if m:
                text = " ".join(TAG.sub("", t).strip() for t in lines[i + 1:])
                text = re.sub(r"\s+", " ", html.unescape(text)).strip()
                if text:
                    cues.append((secs(*m.groups()[:4]), text))
                break
    return cues


def drop_repeats(cues):
    """人工字幕偶尔把同一句连放两个 cue（如 L15 的两个 "OK."），只留第一个。"""
    out = []
    for t, text in cues:
        if not out or out[-1][1] != text:
            out.append((t, text))
    return out


def dedupe_rolling(cues):
    """自动字幕是滚动两行：每个 cue 先重复上一行、再给新的一行。只保留新出现的行。"""
    out, prev = [], ""
    for t, text in cues:
        if text.startswith(prev) and prev:
            text = text[len(prev):].strip()
        if text:
            out.append((t, text))
            prev = text
    return out


SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z])")


def sentences(cues):
    """全部 cue 拼成一串，在「句末标点 + 空格 + 大写字母」处断句，一句一行。
    所以同一 cue 里的两句会被拆开，而 "[LAUGHTER]." 这种以 [ 开头的会粘在前一句后面。"""
    return [s for s in SPLIT.split(" ".join(t for _, t in cues)) if s]


def timed(cues, gap=30):
    """每条 cue 的时间先截断成整秒；下一条要满足 起始 ≥ 上一条的整秒 + gap。分钟不进位到小时。"""
    out, last = [], None
    for t, text in cues:
        if last is None or t >= last + gap:
            last = int(t)
            out.append("[%02d:%02d] %s" % (last // 60, last % 60, text))
    return out


def pick_vtt(vid):
    """优先人工字幕 en → en-US → en-GB → 其它 en-*；都没有才用自动稿 en-orig（需去滚动重复）。"""
    for suf in ("en", "en-US", "en-GB"):
        p = os.path.join(VDIR, "%s.%s.vtt" % (vid, suf))
        if os.path.exists(p):
            return p, False
    for p in sorted(glob.glob(os.path.join(VDIR, vid + ".en-*.vtt"))):
        if not p.endswith((".en-orig.vtt", ".en-en.vtt")):
            return p, False
    p = os.path.join(VDIR, vid + ".en-orig.vtt")
    return (p, True) if os.path.exists(p) else (None, False)


def render(key, vid, title):
    path, auto = pick_vtt(vid)
    if not path:
        return None
    cues = parse_vtt(path)
    if auto:
        cues = dedupe_rolling(cues)
    cues = drop_repeats(cues)
    txt = "# %s\n# https://www.youtube.com/watch?v=%s\n\n" % (title, vid) + "\n".join(sentences(cues)) + "\n"
    tim = "# %s\n\n" % title + "\n".join(timed(cues)) + "\n"
    # 与现有文件保持一致：Windows 换行（CRLF）
    return txt.replace("\n", "\r\n"), tim.replace("\n", "\r\n"), os.path.basename(path), auto, len(cues)


def download(vids, auto=False):
    cmd = ["yt-dlp", "--skip-download", "--sub-format", "vtt", "--sleep-subtitles", "2",
           "-o", os.path.join(VDIR, "%(id)s.%(ext)s")]
    cmd += ["--write-auto-subs", "--sub-langs", "en-orig"] if auto else \
           ["--write-subs", "--sub-langs", "en,en-US,en-GB"]
    cmd += ["https://www.youtube.com/watch?v=" + v for v in vids]
    subprocess.run(cmd, check=False)


def read(p):
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="") as f:   # s 里已经是 CRLF，原样写
        f.write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="回归测试，不写文件")
    ap.add_argument("--convert", action="store_true", help="不联网，只从已有 vtt 生成")
    a = ap.parse_args()
    os.makedirs(VDIR, exist_ok=True)

    if not a.check and not a.convert:
        need = [v for k, v, _ in LECTURES if not pick_vtt(v)[0]]
        if need:
            print("下载人工字幕：%d 个" % len(need))
            download(need)
            still = [v for v in need if not pick_vtt(v)[0]]
            if still:
                print("以下没有人工字幕，退回自动字幕：", still)
                download(still, auto=True)

    bad = 0
    for key, vid, title in LECTURES:
        r = render(key, vid, title)
        if r is None:
            print("  ✗ %-18s 没有可用字幕" % key); bad += 1; continue
        txt, tim, src, auto, n = r
        pt, pm = os.path.join(TDIR, key + ".txt"), os.path.join(TDIR, key + "_timed.txt")
        ot, om = read(pt), read(pm)
        tag = "自动稿" if auto else "人工"
        if a.check:
            if ot is None:
                continue
            st = "一致" if ot == txt else ("旧版单行，不可比" if ot.count("\n") == 0 else "✗ 不一致")
            sm = "一致" if om == tim else ("无" if om is None else "✗ 不一致")
            print("  %-18s txt %-8s timed %-6s（%s, %d cues）" % (key, st, sm, src, n))
            bad += ("✗" in st) + ("✗" in sm)
            continue
        changed = []
        if ot != txt:
            write(pt, txt); changed.append("txt")
        if om != tim:
            write(pm, tim); changed.append("timed")
        print("  %s %-18s %-5s %4d 句 %4d 条定位  %s" % ("✎" if changed else "·", key, tag,
              txt.count("\n") - 3, tim.count("\n") - 2, "更新 " + "+".join(changed) if changed else "未变"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
