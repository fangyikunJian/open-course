# open course · 公开课中文学习站

一套自用的公开课学习站。**全部中文内容都是原创笔记**，课件 PDF、字幕、讲稿**不在本仓库内**（原因见下）。

线上：<https://fangyikunjian.github.io/open-course/> ·
入口是 [`★总入口.html`](★总入口.html)。

> ⚠ 原来这份 README 的标题是「强化学习课程中文精读」。站点早已不止强化学习
> （还有 Transformers / 大语言模型、约束编程），课程表也漏了两门 ——
> 2026-11-18 按实测数据重写。

## 两种读法

一门课可能有其中一种，也可能两种都有。

| | 长什么样 | 适合 |
|---|---|---|
| **精读** | 左边挂原始课件 PDF，右边逐页写中文讲解，配自测题。每个讲解单元标明它覆盖的页范围。 | 要把一讲读透、要能回查原文 |
| **放映厅** | 动画讲解，空格推进。每个知识点走**六拍**：钩子 → 错误答案 → 铺陈 → 主体 → 反驳 → 检验（总结卡 + 必答测验）。 | 要先建立直觉、或原课没有可内嵌的讲义 |

精读页里还有几种特殊格：`quote`（幻灯英文原文，逐字抄不转述）、`say`（课堂讲稿原话 ——
CS224R 很多关键细节**只在讲稿里，幻灯上完全没有**）、`eq`（公式重排成能一眼看完的纯文本块）、
**科研格**（把这一讲接回作者自己的课题，标注 `已核` / `推断` / `待核` 三档证据）。

## 收了哪几门

数字是 2026-11-18 由 `_kit/build_portal.py` 扫文件系统实测的，不是手写的。

| 课程 | 内容 | 规模 | 进度 |
|---|---|---|---|
| **Stanford CS234**（2019 冬） | 强化学习 | 15 讲 · 135 个知识点 | 放映厅 15/15 · 速览 15/15 · 精读 15/15 · 课件 15/15 ✅ |
| **Stanford CS224R**（2025 春） | 深度强化学习 | 19 讲 · 91 个知识点 | 精读 12/19 · 课件 19/19 · 放映厅 1/19 |
| **UW CSE 541**（2025 春） | 交互式学习（老虎机 / 在线学习 / 实验设计） | 16 讲 · 27 个知识点 | 精读 13/16 · 讲义 16/16（16 份讲义已全部结清）|
| **Stanford CME 295**（2025 秋） | Transformers 与大语言模型 | 9 讲 · 73 个知识点 | 放映厅 9/9 ✅（**只做放映厅**，见下）|
| **Coursera MiniZinc 三部曲** | 离散优化建模与求解（Stuckey & Jimmy Lee） | 13 模块 · 38 个知识点 | 放映厅 2/13（**只做放映厅**）|
| **Sutton & Barto 第二版** | 强化学习导论 | 6 章 · 36 个知识点 | 精读 3/6 · 原书 6/6（只做 CS234 没系统讲过的章节）|

合计 **78 讲/章 · 400 个知识点**。

⚠ **两门课只做放映厅、不做精读**，原因各不相同，别套用：
- **CME 295** —— 讲义是公开的，但响应头带 `X-Frame-Options: SAMEORIGIN`，
  浏览器拒绝把它放进 `github.io` 的 iframe，左栏做不出来。
- **MiniZinc 三部曲** —— 这是 MOOC，载体是视频，**根本没有公开讲义 PDF**。

## 目录怎么摆

六门课，**同一个形状**；目录名就是课程代号加年份，不带空格、不带大写。

```
open course/
├─ ★总入口.html          ← 真入口（_kit/build_portal.py 扫文件系统生成）
├─ ★科研学习清单.html      ← plan.json + _kit/build_plan.py 生成
├─ index.html            ← 根路径跳转页，供静态服务器用
├─ plan.json             ← 研究学习清单的数据源
├─ 任务清单.md            ← 工作日志：每次做了什么、踩了什么坑
├─ _kit/                 ← **唯一一份工具**
│   ├─ coursekit/        ← 精读页生成器 + 闸门
│   ├─ theater/          ← 放映厅引擎 + 闸门
│   ├─ tools/            ← 字幕与讲稿抓取
│   └─ build_portal.py · build_plan.py
├─ skills/               ← **全项目**的做片手册（不属于任何一门课）
│   ├─ PROJECT-SKILL-放映厅.md · SKILL.md · evidence.md · explainer-arc.md
│   ├─ corpus/3b1b/      ← 手法样本语料（21 份 .vtt），**不入库**
│   └─ tools/fetch_3b1b.sh
├─ docs/superpowers/     ← 设计与计划文档（**历史存档**，见下方说明）
├─ cs234-2019/           ← 斯坦福 CS234
├─ cs224r-2025/          ← 斯坦福 CS224R
├─ bandits-cse541/       ← 华盛顿大学 CSE 541
├─ cme295-2025/          ← 斯坦福 CME 295
├─ minizinc-coursera/    ← Coursera MiniZinc 三部曲
└─ sutton-barto/         ← Sutton & Barto 第二版
```

每门课里面都是同一套：

```
<课程目录>/
├─ course.json       ← **讲次元数据的唯一真源**（标题、页数、知识点、有哪几种读法）
├─ index.html        ← 课程门户（_kit/coursekit/build_hub.py 生成）
├─ 来源.md           ← 材料从哪来、怎么切的、踩过什么坑
├─ corpus/           ← 原始材料（slides / subtitles / transcripts），**不入库**
├─ theater/src/      ← 放映厅内容 JSON（film-*.json + episodes-*.json）
├─ theater/影片/      ← 生成的片子
└─ 精读/              ← 精读页 + data/ 数据 JSON
```

⚠ **2026-11-18 之前不是这样**，旧路径到处都还能搜到，别照着写：

| 现在 | 2026-11-18 之前 |
|---|---|
| `cs234-2019/` | `reinforcement learning/`（带空格的通名） |
| `cs234-2019/corpus/slides/`、`cs234-2019/精读/` | `.../corpus/cs234-2019/slides/`、`.../corpus/cs234-2019/中文精读/`（深两层，精读目录还另有其名） |
| `sutton-barto/` | `reinforcement learning/corpus/sutton-barto/`（**一门课住在另一门课的 corpus 里**） |
| `cme295-2025/` | `CME295/` |
| `skills/corpus/3b1b/` | `reinforcement learning/corpus/3b1b/` |

⚠ `docs/superpowers/` 下的计划与设计文档**保留当时的写法**，没有跟着改名 ——
它们记的是「某年某月做了什么」，不是「现在在哪」。要找现在的路径看本文件。

⚠ **`来源.md` 目前只有 4 门有**（CS224R / CME295 / MiniZinc / S&B）；
CS234 与 CSE 541 还没补，别以为每门都有。

⚠ **工具只有 `_kit/` 一份。** 2026-09-30 抽出 `_kit` 时，课程目录里留了副本
「原地保留兼容」，结果它停在 9 月并与 `_kit` 分叉 —— 在那个目录里直接
`python assemble.py` 会**静默用到旧引擎**。11-18 已删除全部副本
（放映厅 16 个 + 一份旧 `coursekit/` 9 个 + `tools/fetch_subs.py`）。
最后这个尤其阴：它比 `_kit` 那份少了 9-30 补的**标签撞车守卫**，
撞了会静默覆盖、照常打印「DONE 19 lectures」，而丢掉的那一讲讲稿根本不存在。
**不要再往课程目录里放工具。**

## 为什么没有课件 PDF 与字幕

`.gitignore` 挡着 `*/corpus/**/` 下的 `*.pdf` `*.vtt` `*.txt` `*.srt` `*.sbv`：

1. **体积** —— 全部材料 400 MB 以上，而本仓库跟踪的内容约 20 MB。
2. **版权** —— 课件与字幕的著作权属于各课作者与学校，本仓库不转载。

各课的 `来源.md` 写明了出处与获取方式。**要让左栏的 PDF 显示出来，需要自己按
`来源.md` 把材料下载到对应的 `corpus/` 目录**；不下载也能读右栏的讲解。

线上（GitHub Pages）另有一套办法：`course.json` 可声明 `pdf_remote`，
页面按 hostname 切换到 canonical 源（CSE 541 用学校原站，CS224R / S&B 用 Wayback 快照）。
⚠ CS234 2019 的 15 份讲义**找不到可用的公开源**（Wayback 只存到其中 2 份，且未校验），
那几份线上只有右栏。

## 工具链 `_kit/`

**精读** `_kit/coursekit/`
- `build_reader.py` —— 从 `course.json` + 每讲数据 JSON 生成精读页。带一组**硬闸门**：
  讲解密度、`quote` 覆盖率、表格密度、页范围重叠，以及防泄题检查（答案位置是否过度集中、
  某一项是否从没当过正解、选项里有没有残留加粗）。**闸门不过就改内容，不许改目标值让它通过。**
- `check_reader.js` —— 真实无头 Chrome 跑 **27 条断言**（主题切换、对比度、自测持久化、
  表格渲染、CSS 变量有没有被引用却没定义……）。
- `reshuffle_quiz.py` —— 打散答案位置，**打散完自己验，不合格就换盐重试**。
  ⚠ 用稳定哈希（crc32），**不用 Python 的 `hash()`** —— 它逐进程随机化，在这上面出过事。

**放映厅** `_kit/theater/`
- `assemble.py` —— 把 `film-LNN.json` + `episodes-LNN*.json` 组装成片子。
- `lint_film.py` —— 9 项机械检查，**每一条都对应一次真实事故**（转义层数、公式里的裸 `<`、
  动画承诺了却不动、柱子矮到看不见、总结卡超长……）。
- `shot_probe.js` —— 无头 Chrome 逐镜导出 DOM 几何为 JSON，**产出可 diff 的数值而不是截图**。
  ⚠ `lint` 看源码、`probe` 看渲染，**两道都得跑** —— 有过 lint 放行而 probe 抓到的事故。
- `audit_layout.py` · `prim_mix.py`（画面多样性）· `build_index.py`（放映厅索引）。

**抓取** `_kit/tools/`
- `fetch_subs.py` —— 按播放列表抓字幕与讲稿。⚠ 带**标签撞车守卫**：
  两个视频推导出同一个讲次号时**报错退出，绝不猜**。没有它的时候，
  后写的会静默覆盖先写的、而脚本照常打印「DONE 19 lectures」。

**站点** `_kit/build_portal.py`（总入口，扫文件系统，加一门课只改 `COURSES` 一处）、
`_kit/build_plan.py`（研究清单）。

重建全站：
```bash
cd "G:/open course"
python _kit/coursekit/build_hub.py <课程>/course.json   # 每门课一次
python _kit/build_plan.py
python _kit/build_portal.py
```

## 许可

中文讲解与工具链代码：作者保留权利，仅供学习参考。
所引用的课件原文、公式、图表，版权归各自作者所有，本仓库仅作学习注解之用。
