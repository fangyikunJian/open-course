# -*- coding: utf-8 -*-
"""内容目录解析的自证。必须 8/8。

规矩 E（PROJECT-SKILL §10）：检查器在被信任之前，必须先用一个已知坏样本
和一个已知好样本验过。这里每条判据都有「必须报」与「必须不报」两侧。

最后两条不测 _paths 本身，测的是**调用方真的改用了它** —— 光有正确的模块
而调用方还在用 HERE，等于没改。
"""
import io
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

TOTAL = 8


def run():
    ok = 0
    here = os.path.dirname(os.path.abspath(__file__))
    cwd0 = os.getcwd()

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "theater", "src")
        os.makedirs(src)
        io.open(os.path.join(src, "film-L05.json"), "w",
                encoding="utf-8").write("{}")

        # ── has_content：两侧 ──
        ok += _paths.has_content(src) is True          # 有 film-*.json
        ok += _paths.has_content(tmp) is False         # 空目录不算

        # ── src_dir：cwd 里有内容就用 cwd，而不是 HERE ──
        try:
            os.chdir(src)
            ok += os.path.normcase(_paths.src_dir()) == os.path.normcase(src)
            # ── out_dir：内容目录的上一层的 影片/，且会自己建出来 ──
            want = os.path.normcase(
                os.path.normpath(os.path.join(src, "..", "影片")))
            got = os.path.normcase(_paths.out_dir())
            ok += (got == want and os.path.isdir(got))
        finally:
            os.chdir(cwd0)

        # ── FILM_SRC 优先于 cwd ──
        try:
            os.environ["FILM_SRC"] = src
            os.chdir(tmp)                              # cwd 里没有内容
            ok += os.path.normcase(_paths.src_dir()) == os.path.normcase(src)
            # ── 必须报：FILM_SRC 指向没有内容的目录 ──
            os.environ["FILM_SRC"] = tmp
            try:
                _paths.src_dir()
                ok += 0                                # 没报 = 这条判据是废的
            except SystemExit:
                ok += 1
        finally:
            os.environ.pop("FILM_SRC", None)
            os.chdir(cwd0)

    # ── 调用方真的改用了 _paths，而不是留着 HERE 找内容 ──
    # 判据只看「用 HERE 拼内容文件名」这一种写法，不禁止 HERE 本身
    # （eng.txt / build_common.py 本来就该走 HERE）。
    bad = []
    for f in ("assemble.py", "prim_mix.py", "build_index.py", "build_common.py"):
        s = io.open(os.path.join(here, f), encoding="utf-8").read()
        s = re.sub(r"#.*", "", s)                      # 注释里提到属正常
        for m in re.finditer(r"join\(\s*HERE\s*,\s*[^)]*", s):
            frag = m.group(0)
            if ("episodes-" in frag or "film-" in frag or "影片" in frag):
                bad.append("%s: %s" % (f, frag[:60]))
    ok += (len(bad) == 0)
    if bad:
        print("  仍在用 HERE 找内容 / 写产出：")
        for b in bad:
            print("   ", b)

    # ── eng.txt 必须仍然走 HERE（它是工具资产，不是内容）──
    s = io.open(os.path.join(here, "build_common.py"), encoding="utf-8").read()
    ok += bool(re.search(r"join\(\s*HERE\s*,\s*[\"']eng\.txt[\"']", s))

    return ok


if __name__ == "__main__":
    n = run()
    print("selftest_paths %d/%d" % (n, TOTAL))
    sys.exit(0 if n == TOTAL else 1)
