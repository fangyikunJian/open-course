# -*- coding: utf-8 -*-
"""把审计产出的修订条款应用到 skill 文件。

条款正文全部来自 skills/audit-plan.json（四路对抗性审计的整合结果），
这里只负责**放到正确的位置**，不改写条款内容。

纪律：
  · 从文件末尾往前改，避免行号漂移；
  · 先空跑核对每个锚点都匹配，全部匹配才写盘；
  · 任一锚点对不上就整体中止 —— 半套应用比不应用更危险。

用法：
    python apply_amendments.py            # 空跑
    python apply_amendments.py --apply    # 写盘
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.loads(io.open(os.path.join(HERE, "audit-plan.json"), encoding="utf-8").read())
BY_RANK = {a["rank"]: a for a in PLAN["amendments"]}


def text(rank, span=None):
    """rank 为 None 时取 INLINE 里的内联正文；返回 None 表示整段删除。"""
    if rank is None:
        v = INLINE.get(span)
        return None if v is None else v.rstrip() + "\n"
    return BY_RANK[rank]["text"].rstrip() + "\n"


# ── SKILL.md 的编辑表 ──────────────────────────────────────────────────
# (起行, 止行, 条款编号, 说明)；起止为 1-indexed 含端点。止行 = 起行-1 表示「插入」。
SKILL_EDITS = [
    (238, 247, 9,  "Reference files 整表替换（6 行路径 6 行全错）"),
    (225, 225, 8,  "Legibility 第 2 条：字号「够不够大」→ 字号闭集（原条款会批准 19px）"),
    (224, 224, 3,  "Legibility 第 1 条：collision-free 加实测数字"),
    (212, 215, 7,  "Attention 整段替换（原句是装饰动画的上游许可）"),
    (192, 191, 11, "插入：原语契约 与 工程纪律"),
    (182, 191, 1,  "Step 5 整节替换：分级验证 L0–L3 + 披露义务"),
    (182, 181, 6,  "插入：检查器自证"),
    (39,  38,  10, "插入：Step 0 —— 引擎实测清单"),
    (31,  30,  13, "Core stance 三条不可谈判之后新增"),
]


PROJECT_EDITS = [
    (191, 190, 4,  "§6 在「认知负荷」与「动画」之间插入版面/字号/颜色/卡片体积分区"),
    (144, 177, 17, "§5 验证纪律整块替换（原文只记了两起事故，实际十二起）"),
    (132, 131, 15, "§3 插入：定格卡与测验卡的字数预算"),
    (126, 129, 18, "§3 合并两条字面互斥的颜色条款 + 灰度可分辨检查"),
    (122, 121, 14, "§3 开头插入：版面预算（含居中公式带与宽高比）"),
    (114, 117, 5,  "§2 watch 条整条替换（animated 须由代码推导）"),
    (20,  33,  12, "§0 整节替换（撤回两个效应量直接相除的算式，结论不变）"),
]

ARC_EDITS = [
    (15, 14, 16, "六拍开头插入：本介质没有「秒」，时长预算换成可测的量"),
]

# rank 19 / 20 是第二批：涉及跨节删除与多处改写，锚点比第一批复杂。
# 19 要从 rubric 摘掉四条不可证伪项并另立一节；20 把 Scope 整节换掉，
# 该条款正文自带 ### 小节（四种原型、无音轨），所以整块落在 Scope 位置即可。
SKILL_EDITS_2 = [
    (396, 407, 20, "Scope 整节替换（含 Step 4 改写、原型扩为四种、无音轨小节）"),
    (375, 374, 19, "插入：设计时自问（从 rubric 摘出的不可证伪项）"),
    (330, 330, None, "删除：「The learner is not left to infer…」—— 那是理由不是判据"),
    (299, 301, None, "rubric 讲解质量：三条不可证伪项 → 只留可机械检验的那半条"),
]

# 少数编辑只做删除/改写，没有对应的 audit-plan 条款，正文写在这里
INLINE = {
    (299, 301): "- [ ] 一集只有一个 aha。（可机械检验：规格表 THE AHA 单行非空；"
                "每个知识点标 aha 的镜数 == 1，且该镜含图元调用而非纯文字。）",
    (330, 330): None,   # None = 整行删除
}


def apply_file(path, edits, dry):
    src = io.open(path, encoding="utf-8").read()
    L = src.split("\n")
    n0 = len(L)
    print("── %s（%d 行）" % (os.path.basename(path), n0))
    ok = True
    for a, b, rank, note in edits:
        if b >= a:                       # 替换
            if a < 1 or b > len(L):
                print("   ✗ rank%-2d 行范围 %d–%d 越界" % (rank, a, b))
                ok = False
                continue
            t = text(rank, (a, b))
            tag = "rank%-2d" % rank if rank else "内联  "
            print("   %s %s 行%d–%d  %s"
                  % (tag, "删除" if t is None else "替换", a, b, note))
            print("        原文首行: %s" % L[a - 1][:76])
            if t is not None:
                print("        新条款首行: %s" % t.split("\n")[0][:76])
        else:                            # 插入（插在 a 之前）
            print("   rank%-2d 插入 行%d 前  %s" % (rank, a, note))
            print("        插入点当前行: %s" % (L[a - 1][:76] if a - 1 < len(L) else "<EOF>"))
            print("        新条款首行: %s" % text(rank, (a, b)).split("\n")[0][:76])
    if not ok:
        return None
    if dry:
        return src
    # 真正应用：edits 已按行号从大到小排列
    for a, b, rank, note in edits:
        t = text(rank, (a, b))
        if t is None:                    # 整段删除
            L[a - 1:b] = []
            continue
        block = t.rstrip("\n").split("\n")
        if b >= a:
            L[a - 1:b] = block
        else:
            L[a - 1:a - 1] = block + [""]
    out = "\n".join(L)
    io.open(path, "w", encoding="utf-8").write(out)
    print("   ✓ 已写盘：%d 行 → %d 行" % (n0, len(out.split("\n"))))
    return out


def main():
    dry = "--apply" not in sys.argv
    # 校验编辑表本身按行号降序，否则行号会漂移
    targets = [
        ("SKILL.md", SKILL_EDITS_2),
        ("SKILL.md", SKILL_EDITS),
        ("PROJECT-SKILL-放映厅.md", PROJECT_EDITS),
        ("explainer-arc.md", ARC_EDITS),
    ]
    for name, edits in targets:
        if os.environ.get("AMEND_BATCH") == "2" and edits is not SKILL_EDITS_2:
            continue
        if os.environ.get("AMEND_BATCH") != "2" and edits is SKILL_EDITS_2:
            continue
        rows = [e[0] for e in edits]
        if rows != sorted(rows, reverse=True):
            print("%s 的编辑表必须按起行降序排列，否则行号漂移" % name)
            return 1
        missing = [r for _, _, r, _ in edits if r is not None and r not in BY_RANK]
        if missing:
            print("audit-plan.json 里找不到条款：%s" % missing)
            return 1

    done = os.environ.get("AMEND_SKIP", "").split(",")
    for name, edits in targets:
        if os.environ.get("AMEND_BATCH") == "2" and edits is not SKILL_EDITS_2:
            continue
        if os.environ.get("AMEND_BATCH") != "2" and edits is SKILL_EDITS_2:
            continue
        if name in done:
            print("── %s（已应用，跳过）\n" % name)
            continue
        apply_file(os.path.join(HERE, name), edits, dry)
        print()
    print("（空跑。加 --apply 写盘）" if dry else "完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
