#!/usr/bin/env python3
"""Download YouTube auto-captions for a lecture playlist and clean them into
plain-text transcripts in the same shape as the existing CS229/transcripts/*.txt.

Two artefacts per lecture:
  subtitles/Lxx.vtt   raw WebVTT, timestamps intact (needed to anchor 放映厅 shots)
  transcripts/Lxx.txt cleaned prose, rolling-caption duplicates collapsed
"""
import subprocess, sys, re, html, pathlib, json, argparse

def run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")

TS = re.compile(r"^(\d\d:\d\d:\d\d\.\d\d\d) --> (\d\d:\d\d:\d\d\.\d\d\d)")
TAG = re.compile(r"<[^>]+>")

def clean_vtt(path):
    """YouTube auto-captions roll: each cue repeats the previous line then adds
    a new one. Keep only text that is genuinely new, in order."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out, seen_tail = [], ""
    for ln in lines:
        if TS.match(ln) or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or not ln.strip():
            continue
        txt = html.unescape(TAG.sub("", ln)).strip()
        if not txt or txt == seen_tail:
            continue
        # the rolling window: new cue often starts with the tail of the last one
        if seen_tail and txt.startswith(seen_tail):
            txt = txt[len(seen_tail):].strip()
            if not txt:
                continue
        out.append(txt)
        seen_tail = out[-1]
    prose = " ".join(out)
    prose = re.sub(r"\s+", " ", prose)
    prose = re.sub(r"\[\s*(Music|Applause|Laughter)\s*\]", "", prose, flags=re.I)
    return prose.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--prefix", default="L")
    ap.add_argument("--index-from-title", default="", help="regex with group 1 = lecture number")
    a = ap.parse_args()

    root = pathlib.Path(a.outdir)
    subs, trans = root / "subtitles", root / "transcripts"
    subs.mkdir(parents=True, exist_ok=True); trans.mkdir(parents=True, exist_ok=True)

    listing = run(["yt-dlp", "--flat-playlist", "--print",
                   "%(playlist_index)s\t%(id)s\t%(title)s", a.playlist])
    if listing.returncode != 0:
        print(listing.stderr[-2000:]); sys.exit(1)

    items = []
    for row in listing.stdout.strip().splitlines():
        parts = row.split("\t")
        if len(parts) < 3:
            continue
        idx, vid, title = parts[0], parts[1], parts[2]
        num = idx
        if a.index_from_title:
            m = re.search(a.index_from_title, title)
            if m:
                num = m.group(1)
        items.append((f"{a.prefix}{int(num):02d}", vid, title))

    # ⚠ 标签撞车必须当场停。
    #
    # 实测代价（CS224R，2026-09-30）：播放列表第 18 个是
    # 「Tutorial Session: Review of Q-Learning」，标题里**没有** "Lecture N"，
    # 于是 --index-from-title 匹配不上，num 退回播放列表序号 18；而第 19 个
    # 「Lecture 18: Frontiers」正则匹配出 18 —— 两者都成了 L18。
    # 后写的**静默覆盖**先写的，脚本照常打印「DONE 19 lectures」，
    # 而 Frontiers 那一讲的讲稿根本不存在。
    #
    # 这和 prim_mix 扫出 0 部片却打印「全部通过」是同一类事故：
    # **失败看起来和成功一模一样。** 所以这里宁可报错退出，也不猜。
    seen = {}
    for tag, vid, title in items:
        if tag in seen:
            raise SystemExit(
                "标签撞车：%s 同时来自\n  %s\n  %s\n"
                "多半是 --index-from-title 对其中一个匹配不上、退回了播放列表序号。\n"
                "解法：把匹配不上的那个单独抓，给它自己的标签（如 LTUT）。"
                % (tag, seen[tag][:70], title[:70]))
        seen[tag] = title

    manifest = []
    for tag, vid, title in items:
        vtt = subs / f"{tag}.vtt"
        if not vtt.exists():
            print(f"[get ] {tag}  {title[:70]}", flush=True)
            r = run(["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
                     "--sub-langs", "en.*", "--sub-format", "vtt",
                     "-o", str(subs / tag), f"https://www.youtube.com/watch?v={vid}"])
            # yt-dlp appends .en.vtt -- normalise
            for cand in sorted(subs.glob(f"{tag}.*.vtt")):
                cand.rename(vtt); break
            if not vtt.exists():
                print(f"[FAIL] {tag}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'no subs'}")
                continue
        prose = clean_vtt(vtt)
        (trans / f"{tag}.txt").write_text(prose, encoding="utf-8")
        wc = len(prose.split())
        print(f"[ ok ] {tag}  {wc:>6,} words  {title[:60]}", flush=True)
        manifest.append({"tag": tag, "video_id": vid, "title": title, "words": wc})

    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDONE  {len(manifest)} lectures -> {root}")

if __name__ == "__main__":
    main()
