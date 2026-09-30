# -*- coding: utf-8 -*-
"""把「工具在哪」和「内容在哪」分开。

CS234 时期工具与内容同在 `theater/src/`，所以脚本一律用 `HERE`（脚本自己的目录）
找 `episodes-*.json` / `film-*.json`，也一律往 `HERE/../影片` 写片子。抽出 `_kit/`
之后这条假设不成立了：工具在 `_kit/theater/`，内容在 `<课程>/theater/src/`。

**这个错误的症状不对称，所以尤其危险：**

- `assemble.py` 会明说「找不到 episodes-L05*.json」—— 吵，但看得见。
- `prim_mix.py` 只会扫出 **0 部片**，然后打印「全部通过」并 return 0。
  这正是 PROJECT-SKILL §14 记的那条事故：**一条匹配不到任何东西的检查，
  和一条通过的检查长得一模一样。**

规矩：**工具自己的资产（`eng.txt`、`build_common.py`）用 `HERE`；
内容用 `src_dir()`；产出用 `out_dir()`。**

`src_dir()` 的决定顺序：环境变量 `FILM_SRC` → 当前工作目录（若含内容）→ `HERE`。
CS234 的用法是 `cd` 进 `theater/src` 再跑，那里 cwd 就是内容目录，**所以行为不变**。
"""
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def has_content(d):
    """这个目录里有没有片子的内容文件。"""
    return bool(glob.glob(os.path.join(d, "film-*.json"))
                or glob.glob(os.path.join(d, "episodes-*.json")))


def src_dir():
    """内容目录。找不到就报错退出 —— 绝不静默退回 HERE 扫出 0 部片。"""
    env = os.environ.get("FILM_SRC")
    if env:
        if not has_content(env):
            raise SystemExit(
                "FILM_SRC=%s 里没有 film-*.json / episodes-*.json" % env)
        return os.path.abspath(env)
    cwd = os.getcwd()
    if has_content(cwd):
        return cwd
    if has_content(HERE):
        return HERE
    raise SystemExit(
        "找不到内容目录。请 cd 进含 film-*.json / episodes-*.json 的目录再跑，"
        "或设 FILM_SRC=<那个目录>。")


def out_dir():
    """片子写到哪：内容目录的上一层的 `影片/`。不存在就建。"""
    d = os.path.normpath(os.path.join(src_dir(), "..", "影片"))
    if not os.path.isdir(d):
        os.makedirs(d)
    return d
