# knowledge-map

把课件、讲义、录播字幕或论文画成能点着看的知识关系图。
Turn lecture slides, notes, lecture transcripts or papers into an interactive knowledge map.

[中文](#中文) · [English](#english)

---

## 中文

### 这是什么

knowledge-map 是一个给 Claude Code 和 Codex 用的 skill。把学习材料交给 AI，说“画成关系图”，它会读完材料，挑出 25 到 45 个知识点，写清楚知识点之间的关系，最后生成一个 HTML 文件。

这个 HTML 不联网也能打开：

- 知识点是图上的卡片，按分区排列。连线上写着两个知识点是什么关系，例如“败在”“改用”“组成”“证明”。
- 点一个知识点，只亮出和它相连的线，旁边弹出面板讲清楚这个知识点。解释按零基础来写，不看原文也能读懂。
- 点一条线，看这条关系的完整解释和出处。
- “关系链”把几条关系串成一条线，一步一步看，一次只亮一条线。
- 手机上有底部面板和文字版。
- 公式用 LaTeX 写，生成时转成浏览器自带的 MathML。

关系分五类，用颜色区分：

| 类型 | 颜色 | 含义 |
|---|---|---|
| good | 绿 | 一个解决、改进、擅长另一个；问题指向它的解法 |
| bad | 红虚线 | 失败、局限、导致问题 |
| part | 灰 | 组成、步骤、用到 |
| link | 橙 | 互补、对比、同类 |
| evid | 紫 | 证据支持论点、指标衡量对象、实验验证 |

原文有的内容和为了讲懂而补充的内容分开写。每个知识点和每条关系都给出处，推断出来的关系会标出来。论文图里，关键结果、计算值和作者的设想分别标成“实测”“模拟”“设想”。默认不加易错标记、考试标签和练习题。

### 安装

1. 装 Python 3.11 或更高版本，以及 Google Chrome。
2. 装依赖：

   ```bash
   python -m pip install latex2mathml playwright Pillow
   ```

   要读 PDF 材料，或者用 PDF 原文核对引文，再装 PyMuPDF：`python -m pip install pymupdf`。`check.py` 直接用本机的 Chrome，不需要运行 `playwright install`。

3. 下载 [Releases](https://github.com/Kankawa728-byte/knowledge-map-skill/releases) 里的 `knowledge-map.zip` 并解开，或者克隆这个仓库。两种方式都会得到一个 `knowledge-map` 文件夹。
4. 把 `knowledge-map` 文件夹复制到：
   - Claude Code：`~/.claude/skills/`，Windows 上是 `C:\Users\<用户名>\.claude\skills\`
   - Codex：`~/.agents/skills/`，Windows 上是 `C:\Users\<用户名>\.agents\skills\`
5. 重开 Claude Code 或 Codex。

两边都装、又只想维护一份时，可以在 Codex 的文件夹里建一个指向 Claude Code 那份的目录联接。在 Windows PowerShell 里运行，不需要管理员权限：

```powershell
New-Item -ItemType Junction -Path "$HOME\.agents\skills\knowledge-map" -Target "$HOME\.claude\skills\knowledge-map"
```

注意：取消共用时只能删联接本身，用递归删除会把 Claude Code 那份原件也删掉。删联接用：

```powershell
cmd /c rmdir "$HOME\.agents\skills\knowledge-map"
```

### 使用方法

**做一张图**

1. 准备材料：课件 PDF、讲义、录播字幕、论文都可以，几种一起给也行。
2. 在 Claude Code 里说“把这份课件画成关系图”，或者输入 `/knowledge-map`。在 Codex 里输入 `$knowledge-map`，或者直接说“画成知识关系图”。说“概念图”“知识图谱”“思维导图”也会用它，做出来的都是这种关系图，不是按章节展开的树。
3. 告诉 AI 材料在哪、图放在哪。不说放在哪时：材料属于当前项目，就放在项目存学习材料的文件夹；材料和当前项目无关，就在材料原件旁边新建一个文件夹；拿不准时 AI 会问你。

接下来 AI 会自己做完这些事：

1. 读完全部材料，图、表、公式页会看图片。
2. 选 25 到 45 个知识点，分 3 到 7 个区，写出关系和 4 到 8 条关系链。材料更多时拆成几张图。
3. 把内容写进数据文件 `<名字>.kmap.toml`。
4. 用 `build.py` 生成 `<名字>.html`，并拿原文核对每条引文。
5. 用 `check.py` 在浏览器里查版面、截图，看完截图，改到没有问题。
6. 给你 HTML 的路径，并写明哪些内容没有核实。

**看图**

用浏览器打开 HTML，不联网也能看。

- 点知识点或连线，看详细解释。页头那一排关系链按钮可以一步一步讲。
- “显示全部”取消突出，“−”“+”缩放，“适应宽度”让图铺满窗口。
- 地址后面加 `#n=节点id`，打开时直接点开那个知识点。加 `#check`，左下角显示版面检查的结果。

**改图**

图的内容都在 `.kmap.toml` 里。改完以后重新生成：

```bash
python "<skill 目录>/scripts/build.py" "<名字>.kmap.toml" --text "<原文.pdf>"
python "<skill 目录>/scripts/check.py" "<名字>.html" --png "<截图目录>"
```

`--text` 可以给多个原文，PDF 或文字文件都行；不给就不核对引文。`build.py -o <文件>` 可以指定输出的 HTML。也可以直接让 AI 改，例如“把第 3 个分区拆成两个”。数据文件的写法见 [`knowledge-map/references/format.md`](knowledge-map/references/format.md)。

### AI 用量

下面是实际做图时，从 Claude Code 的会话记录里统计的用量，模型都是 Claude Opus 5.5。

| 做的图 | 材料 | 知识点 | 模型调用 | 用时 | 输出 | 写入缓存 | 读取缓存 | 按 API 标价折算 |
|---|---|---|---|---|---|---|---|---|
| 一篇论文 | 17 页英文综述 PDF | 42 | 48 次 | 57 分钟 | 37 万 token | 38 万 token | 1,401 万 token | 约 13 美元 |
| 课程周图，共 7 张 | 每周的课件、课堂 slides、录播字幕和 Notebook | 35–45 | 52–135 次 | 46–122 分钟 | 30–75 万 token | 104–263 万 token | 1,482–6,501 万 token | 每张 15–36 美元，合计约 183 美元 |

<details>
<summary>7 张周图逐张的数字</summary>

| 周 | 知识点 | 模型调用 | 用时 | 输出 | 写入缓存 | 读取缓存 | 折算 |
|---|---|---|---|---|---|---|---|
| 1 | 41 | 55 次 | 46 分钟 | 30.2 万 | 103.7 万 | 1,792 万 | $14.81 |
| 2 | 35 | 52 次 | 77 分钟 | 50.0 万 | 141.2 万 | 1,482 万 | $20.02 |
| 3 | 39 | 97 次 | 122 分钟 | 75.4 万 | 248.2 万 | 3,374 万 | $34.24 |
| 4 | 45 | 98 次 | 78 分钟 | 50.5 万 | 241.3 万 | 4,601 万 | $31.36 |
| 5 | 43 | 74 次 | 54 分钟 | 34.9 万 | 233.3 万 | 3,084 万 | $24.82 |
| 6 | 42 | 135 次 | 102 分钟 | 50.6 万 | 262.5 万 | 6,501 万 | $36.25 |
| 7 | 38 | 87 次 | 53 分钟 | 33.5 万 | 157.1 万 | 3,268 万 | $21.09 |

第 3 周的数字包含一次失败：AI 想在一条回复里写完整个数据文件，输出超过 128,000 token 被中断，之后改成分段写。

</details>

- 用时是第一次到最后一次模型调用之间的时间。输出包含模型的思考过程。
- 折算用的是 Anthropic 官网 2026 年 10 月的 Claude Opus 5.5 API 标价，每百万 token：输入 4 美元，5 分钟缓存写入 5 美元，1 小时缓存写入 8 美元，读取缓存 0.20 美元，输出 20 美元。论文图在主会话里做，缓存写入是 1 小时的；周图由子任务做，缓存写入是 5 分钟的。
- 用订阅套餐时不按这个价格收费，而是占用套餐的用量额度。占多少要看套餐。

**换成别家模型的标价折算**

把上面同样的 token 数，按别家模型的 API 标价重新折算。价格是 2026 年 10 月 26 日在各家官方价格页上查的，单位是美元每百万 token：

| 模型 | 标价 | 论文图 | 周图每张 | 7 张周图合计 |
|---|---|---|---|---|
| Claude Opus 5.5（实际用的） | 输入 4，写入缓存 5 或 8，读取缓存 0.20，输出 20 | $13.26 | $14.81–36.25 | $182.59 |
| OpenAI `gpt-6-astra` | 输入 10，写入缓存 12.50，读取缓存 1，输出 50；单次输入超过 272K token 时依次是 20、25、2、75 | $52.92 | $75.86–223.73 | $997.92 |
| Google `gemini-4-argon` | 输入 2，读取缓存 0.10，输出 10；这是 11 月 30 日以前的价格，12 月 1 日起每项翻倍 | $5.87 | $6.88–16.81 | $84.36 |
| DeepSeek `deepseek-flash`（V4.1-Flash-1017） | 未命中缓存 0.30，命中缓存 0.006，输出 1.20；这是高峰价，非高峰减半 | $0.64 | $0.78–1.85 | $9.51 |

折算的做法：

- 写入缓存：OpenAI 有单独的写入价，按 30 分钟写入算；Gemini 和 DeepSeek 没有，按普通输入（未命中缓存）算。
- 读取缓存按各家的缓存命中价算，输出按各家的输出价算。
- OpenAI 逐次调用判断输入有没有超过 272K token，超过的那次按长上下文价算。这几张图里，一半到四分之三的调用超过了 272K。
- Gemini 4 Argon 从 12 月 1 日起各项翻倍，表里它的数也跟着翻倍。DeepSeek 在非高峰时段的价格是高峰的一半。

这只是价格表上的换算。各家分词方式不同，同样的内容 token 数也不同；换了模型，走的步数和写的长度也会变。

**在别的平台上实际做过的**

同一篇 17 页论文也在别的平台上做过，各做了一张 35 个知识点的图：

- Gemini（Argon 4）：用了 20 美元套餐一周额度的 15%。
- Codex（Astra High）：用了 200 美元套餐一周额度的不到 1%。

这两个数是在各自平台的用量页面上看到的，没有 token 明细。

影响用量的几件事：

- AI 每走一步，都要把整段对话重新交给模型。开了缓存以后，这部分按“读取缓存”计价，所以读取缓存的 token 最多，但单价只有输入的二十分之一。
- 材料越长、要看的图片页越多、改版面的来回越多，读取缓存就越多。
- 输出主要是数据文件和解释文字。课程周图的数据文件有 60 到 110 KB。

### 已知问题

- 在 Windows 上，两个脚本的中文输出可能是乱码。运行前先设环境变量 `PYTHONIOENCODING=utf-8`。
- 在数据文件里，粗体小标题的下一行直接写列表时，列表会被并成一段。列表前要空一行。
- 数据文件很大时，AI 一次写完可能超出单条回复的输出上限。可以让它分段写。
- 在 Codex 里，装库要联网，`check.py` 要开浏览器，沙箱可能拦下来，按提示批准即可。不批准的话，版面就没有检查。

### 仓库里有什么

| 路径 | 内容 |
|---|---|
| `knowledge-map/SKILL.md` | 入口：什么时候用、步骤、规矩 |
| `knowledge-map/references/` | 内容怎么写（writing.md）、数据文件格式（format.md）、怎么排位置（layout.md） |
| `knowledge-map/assets/template.html` | 页面模板 |
| `knowledge-map/scripts/build.py` | 把数据文件生成 HTML，核对引文 |
| `knowledge-map/scripts/check.py` | 在浏览器里查版面、截图 |
| `knowledge-map/examples/` | 写法范例 `demo`、公式折行测试 `wrap_case`、引文核对测试 `quote_case` |
| `knowledge-map/agents/openai.yaml` | Codex 里显示的名字和说明 |

### 示例里的引文

`examples/demo.kmap.toml` 里的几处短引文摘自 Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*（NeurIPS 2020）。`examples/quote_case.txt` 的几小段摘自 Zhang et al., *From Genotype to Phenotype: Raman Spectroscopy and Machine Learning for Label-Free Single-Cell Analysis*（ACS Nano 2024）。它们只用来测试引文核对。

---

## English

### What it is

knowledge-map is a skill for Claude Code and Codex. Give the AI your study materials and ask for a knowledge map. It reads everything, picks 25–45 key ideas, writes down how they relate, and produces a single HTML file.

The skill's instructions, the page interface and the explanations in the maps are in Chinese. English technical terms are kept as they appear in the source.

The HTML works offline:

- Each key idea is a card, grouped into zones. Each line carries a label that says how two ideas relate, such as "fails at", "switches to", "consists of" or "proves".
- Click an idea: only its own lines stay highlighted, and a side panel explains it. The explanations are written for complete beginners and make sense without the source.
- Click a line to read the full explanation of that relation and where it comes from.
- Relation chains string several relations into one story that you step through, one line at a time.
- On phones there is a bottom panel and a text version.
- Formulas are written in LaTeX and converted to the browser's built-in MathML.

Relations come in five kinds, told apart by color:

| Kind | Color | Meaning |
|---|---|---|
| good | green | one idea solves, improves on or beats another; a problem points to its fix |
| bad | red, dashed | failure, limitation, or a cause of problems |
| part | grey | consists of, step of, uses |
| link | orange | complementary, contrasting, same kind |
| evid | purple | evidence for a claim, a metric for a target, an experiment that verifies |

What the source says and what is added for explanation are kept apart. Every idea and every relation cites its source, and inferred relations are marked. In paper maps, key results, computed values and the authors' proposals are tagged as measured, simulated or proposed. By default the map has no exam features such as common-mistake markers, exam tags or quizzes.

### Install

1. Install Python 3.11 or later, and Google Chrome.
2. Install the dependencies:

   ```bash
   python -m pip install latex2mathml playwright Pillow
   ```

   To read PDF materials, or to check quotes against a PDF, also install PyMuPDF: `python -m pip install pymupdf`. `check.py` uses your installed Chrome, so you don't need to run `playwright install`.

3. Download `knowledge-map.zip` from [Releases](https://github.com/Kankawa728-byte/knowledge-map-skill/releases) and unzip it, or clone this repository. Either way you get a `knowledge-map` folder.
4. Copy the `knowledge-map` folder to:
   - Claude Code: `~/.claude/skills/` (on Windows, `C:\Users\<username>\.claude\skills\`)
   - Codex: `~/.agents/skills/` (on Windows, `C:\Users\<username>\.agents\skills\`)
5. Restart Claude Code or Codex.

To keep one copy for both on Windows, create a directory junction in the Codex folder that points to the Claude Code copy. Run this in Windows PowerShell; no administrator rights are needed:

```powershell
New-Item -ItemType Junction -Path "$HOME\.agents\skills\knowledge-map" -Target "$HOME\.claude\skills\knowledge-map"
```

Caution: to undo this, delete only the junction itself. A recursive delete also deletes the Claude Code copy. To delete the junction:

```powershell
cmd /c rmdir "$HOME\.agents\skills\knowledge-map"
```

### Usage

**Make a map**

1. Get your materials ready: slide PDFs, notes, lecture transcripts, papers, or a mix of them.
2. In Claude Code, type `/knowledge-map`. In Codex, type `$knowledge-map`. The skill's trigger words are Chinese (关系图, 概念图, 知识图谱, 思维导图), so when you write in English, typing the command is the safest way to start it.
3. Tell the AI where the materials are and where the map should go. If you don't say where: materials that belong to the current project go to the project's study-materials folder; unrelated materials get a new folder next to the original file; if it is unclear, the AI asks you.

The AI then does the rest:

1. Reads all the materials, looking at figures, tables and formula pages as images.
2. Picks 25–45 ideas in 3–7 zones, and writes the relations and 4–8 relation chains. Larger materials are split into several maps.
3. Writes everything into a data file, `<name>.kmap.toml`.
4. Builds `<name>.html` with `build.py`, checking every quote against the source.
5. Checks the layout in a browser with `check.py`, reviews the screenshots, and fixes problems until none are reported.
6. Gives you the path to the HTML and lists what it could not verify.

**View a map**

Open the HTML in a browser. No internet connection is needed.

- Click an idea or a line for the details. The row of relation-chain buttons at the top steps through a story.
- 显示全部 (Show all) clears the highlight, − and + zoom, and 适应宽度 (Fit width) fits the map to the window.
- Add `#n=<node id>` to the address to open the map with that idea selected. Add `#check` to show the layout check report in the lower left.

**Edit a map**

All of a map's content is in its `.kmap.toml` file. After editing, rebuild it:

```bash
python "<skill folder>/scripts/build.py" "<name>.kmap.toml" --text "<source.pdf>"
python "<skill folder>/scripts/check.py" "<name>.html" --png "<screenshot folder>"
```

`--text` accepts several source files, PDF or plain text; without it, quotes are not checked. `build.py -o <file>` sets the output path. You can also ask the AI to make the change, for example "split zone 3 into two". The data file format is described in [`knowledge-map/references/format.md`](knowledge-map/references/format.md) (in Chinese).

### AI usage

The figures below come from the Claude Code session logs of real runs. All runs used Claude Opus 5.5.

| Map | Materials | Ideas | Model calls | Time | Output | Cache writes | Cache reads | At API list price |
|---|---|---|---|---|---|---|---|---|
| One paper | 17-page review paper, PDF, in English | 42 | 48 | 57 min | 0.37 M tokens | 0.38 M tokens | 14.0 M tokens | about $13 |
| 7 course weeks | each week's slides, in-class slides, lecture transcript and notebooks | 35–45 | 52–135 | 46–122 min | 0.30–0.75 M tokens | 1.04–2.63 M tokens | 14.8–65.0 M tokens | $15–36 each, about $183 in total |

<details>
<summary>Per-week figures for the 7 course maps</summary>

| Week | Ideas | Model calls | Time | Output | Cache writes | Cache reads | At list price |
|---|---|---|---|---|---|---|---|
| 1 | 41 | 55 | 46 min | 0.302 M | 1.037 M | 17.9 M | $14.81 |
| 2 | 35 | 52 | 77 min | 0.500 M | 1.412 M | 14.8 M | $20.02 |
| 3 | 39 | 97 | 122 min | 0.754 M | 2.482 M | 33.7 M | $34.24 |
| 4 | 45 | 98 | 78 min | 0.505 M | 2.413 M | 46.0 M | $31.36 |
| 5 | 43 | 74 | 54 min | 0.349 M | 2.333 M | 30.8 M | $24.82 |
| 6 | 42 | 135 | 102 min | 0.506 M | 2.625 M | 65.0 M | $36.25 |
| 7 | 38 | 87 | 53 min | 0.335 M | 1.571 M | 32.7 M | $21.09 |

Week 3 includes one failure: the AI tried to write the whole data file in one reply, went over 128,000 output tokens and was cut off, then wrote the file in parts.

</details>

- Time is measured from the first to the last model call. Output includes the model's thinking.
- The conversion uses Anthropic's Claude Opus 5.5 API list prices as of October 2026, per million tokens: input $4, 5-minute cache writes $5, 1-hour cache writes $8, cache reads $0.20, output $20. The paper map was made in a main session, whose cache writes are 1-hour writes; the course maps were made by subagents, whose cache writes are 5-minute writes.
- On a subscription plan you are not charged these prices. The work uses part of the plan's usage limit instead, and how large a part depends on the plan.

**The same usage at other models' list prices**

The same token counts, converted at other models' API list prices. Prices were taken from each vendor's official pricing page on 26 October 2026, in US dollars per million tokens:

| Model | List price | Paper map | Each course map | All 7 course maps |
|---|---|---|---|---|
| Claude Opus 5.5 (actually used) | input 4, cache writes 5 or 8, cache reads 0.20, output 20 | $13.26 | $14.81–36.25 | $182.59 |
| OpenAI `gpt-6-astra` | input 10, cache writes 12.50, cache reads 1, output 50; for requests over 272K input tokens: 20, 25, 2 and 75 | $52.92 | $75.86–223.73 | $997.92 |
| Google `gemini-4-argon` | input 2, cache reads 0.10, output 10; these are the prices until 30 November, and each doubles from 1 December | $5.87 | $6.88–16.81 | $84.36 |
| DeepSeek `deepseek-flash` (V4.1-Flash-1017) | cache miss 0.30, cache hit 0.006, output 1.20; these are peak prices, and off-peak is half | $0.64 | $0.78–1.85 | $9.51 |

How the conversion works:

- Cache writes: OpenAI has its own cache-write price, taken as 30-minute writes. Gemini and DeepSeek have none, so cache writes are counted as ordinary (cache-miss) input.
- Cache reads use each vendor's cache-hit price, and output uses its output price.
- For OpenAI, each call is checked against 272K input tokens and priced at the long-context rate when it is over. In these runs, half to three quarters of the calls were over.
- From 1 December every Gemini 4 Argon price doubles, and so do its figures in the table. DeepSeek's off-peak price is half its peak price.

This is only a conversion on the price sheets. Vendors split text into tokens differently, so the same content gives different token counts, and a different model would also take a different number of steps and write different amounts.

**Runs actually made on other platforms**

The same 17-page paper was also mapped on other platforms, one 35-idea map each:

- Gemini (Argon 4): 15% of the weekly quota of a $20 plan.
- Codex (Astra High): less than 1% of the weekly quota of a $200 plan.

These two figures were read from each platform's usage page; no token breakdown is available.

What drives usage:

- At every step the AI sends the whole conversation to the model again. With caching on, that part is billed as cache reads. This is why cache reads are by far the largest count, at one twentieth of the input price.
- Longer materials, more pages read as images and more rounds of layout fixes all add cache reads.
- The output is mostly the data file and the explanations. The course-week data files are 60–110 KB.

### Known issues

- On Windows, the Chinese output of both scripts can be garbled. Set the environment variable `PYTHONIOENCODING=utf-8` before running them.
- In a data file, a list placed directly under a bold subheading line is merged into one paragraph. Leave a blank line before the list.
- With a very large data file, writing it in one reply can exceed the AI's per-reply output limit. Ask it to write the file in parts.
- In Codex, installing packages needs network access and `check.py` needs to start a browser, and the sandbox may block both. Approve when asked; if you don't, the layout is not checked.

### Repository layout

| Path | Contents |
|---|---|
| `knowledge-map/SKILL.md` | Entry point: when to use it, the steps, the rules |
| `knowledge-map/references/` | How to write the content (writing.md), the data file format (format.md), how to place cards (layout.md) |
| `knowledge-map/assets/template.html` | Page template |
| `knowledge-map/scripts/build.py` | Builds the HTML from a data file and checks quotes |
| `knowledge-map/scripts/check.py` | Checks the layout in a browser and takes screenshots |
| `knowledge-map/examples/` | Example map `demo`, formula line-wrap test `wrap_case`, quote check test `quote_case` |
| `knowledge-map/agents/openai.yaml` | Name and description shown in Codex |

### Quoted text in the examples

The short quotes in `examples/demo.kmap.toml` are from Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (NeurIPS 2020). The short passages in `examples/quote_case.txt` are from Zhang et al., *From Genotype to Phenotype: Raman Spectroscopy and Machine Learning for Label-Free Single-Cell Analysis* (ACS Nano 2024). They are used only to test quote checking.
