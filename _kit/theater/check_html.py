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
    n = 0
    for p in sys.argv[1:]:
        n += check(p)
    sys.exit(1 if n else 0)
