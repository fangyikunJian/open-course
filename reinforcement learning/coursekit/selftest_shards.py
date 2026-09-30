# -*- coding: utf-8 -*-
"""分片合并的自证。必须 4/4 才算这条判据可信。

规矩 E（PROJECT-SKILL §10）：检查器在被信任之前，必须先用一个已知坏样本
和一个已知好样本验过。这里四个 case 两好两坏。
"""
import io, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _course

sys.stdout.reconfigure(encoding="utf-8")


def mk(d, name, obj):
    io.open(os.path.join(d, name), "w", encoding="utf-8").write(
        json.dumps(obj, ensure_ascii=False))


def run():
    ok = 0
    # ── case 1（好）：单文件，行为不变 ──
    d = tempfile.mkdtemp()
    mk(d, "L99.json", {"notes": [{"r": [1, 2], "t": "a"}], "quiz": {"1": []}})
    got = _course.merge_shards(d, "L99")
    ok += (len(got["notes"]) == 1 and got["_shards"] == ["L99.json"])
    # ── case 2（好）：两片合并，按页码升序 ──
    d = tempfile.mkdtemp()
    mk(d, "L99.b.json", {"notes": [{"r": [3, 4], "t": "b"}], "quiz": {"3": []}})
    mk(d, "L99.a.json", {"notes": [{"r": [1, 2], "t": "a"}], "quiz": {"1": []}})
    got = _course.merge_shards(d, "L99")
    ok += ([n["t"] for n in got["notes"]] == ["a", "b"]
           and got["_shards"] == ["L99.a.json", "L99.b.json"]
           and sorted(got["quiz"]) == ["1", "3"])
    # ── case 3（坏）：片间页码重叠，必须抛错 ──
    d = tempfile.mkdtemp()
    mk(d, "L99.a.json", {"notes": [{"r": [1, 3], "t": "a"}]})
    mk(d, "L99.b.json", {"notes": [{"r": [3, 5], "t": "b"}]})
    try:
        _course.merge_shards(d, "L99")
        ok += 0
    except SystemExit as e:
        ok += ("重叠" in str(e) and "3" in str(e))
    # ── case 4（坏）：单文件与分片同时存在，必须抛错（否则悄悄少读一半）──
    d = tempfile.mkdtemp()
    mk(d, "L99.json", {"notes": [{"r": [1, 2], "t": "x"}]})
    mk(d, "L99.a.json", {"notes": [{"r": [3, 4], "t": "y"}]})
    try:
        _course.merge_shards(d, "L99")
        ok += 0
    except SystemExit as e:
        ok += ("同时存在" in str(e))
    print("selftest_shards %d/4" % ok)
    return ok == 4


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
