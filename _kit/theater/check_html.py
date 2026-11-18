# -*- coding: utf-8 -*-
"""把 HTML 里的每个 <script> 抽出来交给 node --check，模仿 ML 版 patch_fixes 的验证方式。"""
import io, os, re, subprocess, sys, tempfile

def check(path):
    s = io.open(path, encoding="utf-8").read()
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)   # 先剥 HTML 注释：eng.txt 头部注释里出现过 <script> 字样
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", s, re.S)
    print("%s : %d 个内联 script" % (os.path.basename(path), len(blocks)))
    bad = 0
    for i, b in enumerate(blocks):
        fd, tmp = tempfile.mkstemp(suffix=".js"); os.close(fd)
        io.open(tmp, "w", encoding="utf-8").write(b)
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        os.unlink(tmp)
        if r.returncode:
            bad += 1
            print("  script #%d 语法错误:" % i)
            print("   ", (r.stderr or "").strip().splitlines()[:6])
        else:
            print("  script #%d ok (%d 字符)" % (i, len(b)))
    # charset 与 visibility 修复必须在
    print("  meta charset :", "<meta charset" in s[:400])
    print("  visibility fix:", "visibility:hidden" in s)
    return bad

if __name__ == "__main__":
    # ⚠ 2026-11-18：不给参数时这里原来是「循环 0 次 → return 0」——
    #   一条**假绿灯**：报告什么都没打印，退出码却是 0，看起来像通过了。
    #   手册 §14 写明「文件数为 0 必须非零退出」，但这一份没落实。实测复现：
    #   `python check_html.py` 静默退出 0。现在要么给路径，要么报错。
    paths = sys.argv[1:]
    if not paths:
        sys.exit("用法：python check_html.py <片子.html> [更多.html]\n"
                 "  不给路径就什么都没查 —— 不许静默返回 0。")
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.exit("这些文件不存在，查不了：%s" % "，".join(missing))
    n = 0
    for p in paths:
        n += check(p)
    print("共查 %d 个文件，语法有问题的 %d 个。" % (len(paths), n))
    sys.exit(1 if n else 0)
