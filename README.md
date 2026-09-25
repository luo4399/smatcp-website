# SMaTCP — Somatic Mosaicism Across Normal Tissues of Chinese Population

SMaTCP 整合中国个体的正常组织高深度 WGS（300x）、PacBio HiFi（40x）、RNA-seq
等多组学数据，构建东亚人群跨组织体细胞嵌合（somatic mosaicism）图谱。
首页英雄区文案为：*GTOP generates high-quality ultra-deep sequencing data across normal
tissues to build the landscape of body-wide somatic mosaicism in Chinese individuals.*

**访问地址:** `http://10.6.109.183:5501`

## 项目结构

```
.
├── src/                            # 页面（部署时被拷到发布根）
│   ├── index.html                  # 首页：搜索 + 结果表 + 三列筛选 + 覆盖度图弹窗
│   ├── somatic-data.html           # 数据下载门户（筛选侧栏 + Data Matrix）
│   ├── donors.html                 # 供体信息
│   ├── tissue.html                 # 组织浏览
│   └── somacard.html               # SomaCard 突变注释（调 server/ 的后端 API；需登录）
├── assets/                         # 静态资源（CSS / 图片 / 图标 / 字体）
│   ├── site.css                    # 全站共享设计系统
│   ├── col-resize.js               # 表头列宽拖拽（首页搜索表 + Data Portal 共用）
│   ├── somatic-auth.js             # SomaCard 页的登录门（2026-09-25 从 10.6.109.183 取回，逐字节一致）
│   ├── hero-bg.jpg                 # 首页英雄区背景图
│   ├── cells-bg.jpg                # 浅色区块底纹（被 site.css 引用）
│   ├── donors-banner.svg           # 供体页侧脸剪影横幅（由脚本生成）
│   ├── fontawesome/                # 本地图标字体（不依赖 CDN）
│   ├── tissue/                     # 33 个组织图标 PNG
│   └── plots/                      # 覆盖度图示例 PDF（8 张；完整图集在服务器，见下文）
├── data/                           # 前端数据（全部自动生成，勿手改）
│   ├── variants_data.js            # 变异数据（8.3 MB，21 列全量，字典编码）
│   ├── genome_data.js              # Data Portal 文件清单（0.6 MB，字典编码）
│   └── plots_index.js              # 覆盖度图索引
├── scripts/                        # 构建脚本
│   ├── build_variants_data.py      # → data/variants_data.js
│   ├── build_genome_data.py        # → data/genome_data.js
│   ├── build_plots_index.py        # → data/plots_index.js
│   ├── build_donors_banner.py      # → assets/donors-banner.svg
│   └── build_publish.sh            # → publish/ 发布快照
├── server/                         # SomaCard 后端
│   ├── mutation_annotation.py      # 突变注释 + 打分引擎
│   ├── server.py                   # Web API（Flask，端口 5502）
│   └── examples/                   # 示例输入输出
│       ├── test_mutation.txt       # 示例突变 TXT（5 条）
│       ├── test_mutation.vcf       # 示例突变 VCF（2 条）
│       └── annotation.tsv          # 示例输出结果
├── data_source/                    # 源表（不进 publish/）—— 全站只有这两张源表
│   ├── variants_website.csv        # 变异源表（16 MB，21 列，107,852 行）—— 首页搜索的唯一数据源
│   └── tissue_genome_data.csv      # Data Portal 源数据（7,249 行，8 列，带 UTF-8 BOM）
├── design/                         # Figma 导出设计稿的投放目录（PNG 不入库）
├── publish/                        # 发布快照（生成物，不入库）
├── Procfile                        # 后端部署配置（gunicorn server.server:app）
├── requirements.txt                # 后端依赖
└── .vscode/settings.json           # Live Server 端口/忽略规则
```

**关于路径**：页面在 `src/`，静态资源在 `assets/` 和 `data/`，所以页面里一律写成
`../assets/…`、`../data/…`（`data/plots_index.js` 的 `PLOT_BASE` 同理）。
本地预览请访问 `http://127.0.0.1:5501/src/index.html`，不要直接双击 HTML（`file://` 会拦截 PDF 跳转）。

> 2026-09-24 目录重构：页面从根目录移入 `src/`，`tissue/`+`plots/` 并入 `assets/`，
> 三个数据 js 移入 `data/`，四个构建脚本移入 `scripts/`，`somacard/` 改名 `server/`。
> 同时清理了早期单页版遗留的 `somatic_fil.csv`、`data_process.R`、`SMaTCP overview.png`
> 及若干 `.DS_Store`（已进废纸篓，可还原）。

## 数据概况

### 首页英雄区统计条

英雄区下方的统计条（`index.html` 的 `.stats-card`）展示的是**项目级**口径：

| 指标 | 数值 | 说明 |
|------|------|------|
| Individuals | 68 | 2026-09-24 由 160 改为 68，见下方口径说明 |
| Tissues | 33 | 与 Data Portal 的 33 组织一致 |
| Short-read WGS | 300x | |
| PacBio HiFi WGS | 40x | 原标签是 `Long-read`，2026-09-24 改为 `WGS` |
| Somatic variants | 107,852 | 由 `data/variants_data.js` 的实际行数注入（`#statVariants`） |

> ⚠️ **Individuals 为什么是 68（2026-09-24 luo 明确）**
>
> 首页搜索用的变异数据（`data/variants_data.js`）覆盖 **68 供体 / 30 组织 / 107,852 条**，
> 而 Data Portal 的文件清单是 **160 个测序样本编号 / 33 组织 / 7,249 个文件** —— 两者不是同一批
> （前者是「有体细胞变异检出」的样本，后者是全部测序样本）。
>
> 统计条原先写 160，与**同一页正文**里的 “30 normal tissues from 68 post-mortem donors”
> 以及流水线图上的 “68 Individuals” 自相矛盾。现统一按首页数据的口径显示 **68**。
>
> 另：搜索数据以 `…/2026.07.15_website/variants_website.csv` 这一张表为准（本地副本与其逐字节相同），
> 不再从其它表拼接字段。所以 68/30 是**预期值**，不是待修的 bug。

### 变异数据（data/variants_data.js）

**数据源只有一张表**：`data_source/variants_website.csv`
（服务器原路径 `/media/london_A/kewei/2025.04.16_somatic/Project_SNV/2026.07.15_website/variants_website.csv`，
本地副本 md5 `7a48bd670b39536a91aa3df3e8b3b605` 与服务器**逐字节一致**）。

CSV 的 **21 列全部保留、全部展示**，不再拼接任何来自其它文件的信息
（以前表里还有 `Age` / `Sex` 两列，来自 `select_sample.xlsx`；2026-09-24 已移除 —— 混两个来源会误导读者）。

| 指标 | 数值 |
|------|------|
| 供体数 | 68 |
| 组织数 | 30 |
| 样本数 | 354 |
| 变异记录 | 107,852 |
| SNV | 106,639 |
| INDEL | 1,213 |
| 基因 | 22,044 |
| 区域（region 去重） | 262 |
| 源表 | `data_source/variants_website.csv`（16 MB，21 列） |
| 生成物 | `data/variants_data.js`（8.3 MB，自动生成，勿手改） |

**21 列**（顺序即页面从左到右）：
`contig`(Chr) · `pos` · `ref` · `alt` · `depth` · `vaf` · `mutation_type`(Type) ·
`TiTv` · `trinucleotide` · `gene_symbol`(Gene) · `region` · `sample` · `donor` · `tissue` ·
`ref_origin` · `tissue_shared` · `infiltration_pp` · `infiltration` · `cosmic_signature` ·
`CADD_PHRED` · `regulatory_score`

**突变分布最高的 5 个组织:**
Adrenal_Gland（21,099）、Whole_Blood（19,272）、Skin（15,413）、Liver（9,209）、Gallbladder（4,627）

**突变类型分布:** 基因间区（40,596）、内含子（29,785）、ncRNA内含子（4,628）、未知（2,062）、外显子（1,442）

## 服务部署

两个服务以 systemd user service 运行，开机自启、异常自动重启：

| 服务 | 端口 | systemd unit | 说明 |
|------|------|-------------|------|
| 前端 | 5501 | `somacard-www` | Python http.server 托管静态文件 |
| API | 5502 | `somacard-api` | Flask，调用 mutation_annotation.py |

```bash
systemctl --user status somacard-api somacard-www   # 查看状态
journalctl --user -u somacard-api -f                 # 查看日志
systemctl --user restart somacard-api                 # 重启 API
```

### Flask 应用同时托管静态站点时的路径规则

`server/server.py` 除了 `/api/*`，还兜底提供整个站点（`Procfile` 里的
`gunicorn server.server:app` 就是这种「一个端口既跑 API 又发页面」的部署方式，
Render 的 demo 部署用的是这个）。它的静态目录有两个：

- **项目根** `PROJECT_DIR` —— 放 `assets/`、`data/`
- **页面目录** `SRC_DIR = PROJECT_DIR/src` —— 放 5 个 `.html`

`serve_static()` 会**先查项目根、再查 `src/`**，两处都没有才回落到 `src/index.html`。

> ⚠️ **重构时必须同步改这里。** 2026-09-24 把页面从仓库根挪进 `src/` 之后，
> 这个函数一度只查项目根，于是 `/somatic-data.html` 之类的地址找不到文件、直接回落首页
> —— 表现是「导航点哪个链接都只回到首页」，而且 HTTP 状态码仍是 200，光看状态码发现不了。
> 验证方式：`curl -s <host>/somatic-data.html | grep -o '<title>[^<]*'`，
> 标题必须是 `Somatic Mosaicism Data Portal — GTOP` 而不是首页标题。

## 发布为公开链接

站点可以发布成一个公开链接（用「发布为应用」）。发布对象是 **`publish/` 这个纯净快照目录**，
**不是项目根目录**。

**为什么不能直接发根目录**：根目录里这些文件会被原样上传并可被公开访问——

| 文件 | 问题 |
|------|------|
| `.workbuddy-ai/` | 内部工作笔记，含服务器清单与内网 IP、部署细节 |
| `README.md` | 内部数据路径（`/media/iceland/...`）、服务器地址 |
| `server/` | 后端源码 |
| `data_source/` | 原始数据表（16 MB） |

### 重建 publish/

```bash
cd /Users/luo/Desktop/smatcp-website
bash scripts/build_publish.sh
```

脚本做三件事：① 把 `assets/`、`data/` 原样拷到 `publish/`；② 把 `src/*.html` 拷到 `publish/` 根，
并抹掉路径里的 `../` 前缀；③ 把 `data/plots_index.js` 的 `PLOT_BASE` 同步改成 `assets/plots/`。
最后自检产物里不再有 `../`，有就报错退出。

`publish/` 只含站点公开文件（约 9 MB）：五个 HTML、`assets/`（site.css + 图片 + fontawesome +
`tissue/` 33 张图标 + `plots/` 8 张示例 PDF）、`data/`（三个数据 js）。
它在 `.gitignore` 里，是生成物，不入库。

**为什么线上是扁平结构**：仓库里页面在 `src/`，页面用 `../assets/…` 引用资源；但线上要求首页就是
`/index.html`（不能变成 `/src/index.html`），所以构建时把页面提到根并去掉 `../`。
`publish/` 与仓库布局**不一致是正常的**，它是构建产物。

**改完站点要重新发布时，先跑 `bash scripts/build_publish.sh`，再对 `publish/` 执行发布。**
重新发布同一个目录会复用同一个分享链接，线上现有内容会被覆盖。

### 怎么发布（操作步骤）

**第 1 步 · 重建快照**（改了站点就必须重跑，否则线上还是旧内容）

```bash
cd /Users/luo/Desktop/smatcp-website
bash scripts/build_publish.sh
```

看到 `✅ publish/ 重建完成（自检通过）` 才算成功。自检不过会报错退出，产物不会留下半成品。

**第 2 步 · 发布 `publish/` 目录**

用 **「发布为应用」** 能力，把**项目目录指向 `publish/`**（⚠️ 不是项目根目录）。
按站点类型选 `language: static` —— 纯静态，不需要启动进程。

**第 3 步 · 拿到分享链接**

发布完成后会返回一个形如 `https://<hash>.sg.agentos-app.run` 的公开地址，任何人可直接打开。

> 当前线上链接：`https://c363dab05b6e47579d5a7ac5b0b836c1.sg.agentos-app.run`

**第 4 步 · 更新线上内容**

改完站点 → 重跑第 1 步 → 对**同一个 `publish/` 目录**再发布一次。链接不变，线上内容被覆盖。

**第 5 步 · 下线**

用「取消发布」对同一个 `publish/` 目录操作，分享链接立即失效。

**发布前自查清单**

- [ ] `bash scripts/build_publish.sh` 自检通过
- [ ] `ls publish/` 里**不含** `README.md`、`.workbuddy-ai/`、`server/`、`data_source/`、`design/`
- [ ] 发布后抽查 `https://<链接>/README.md`、`/server/server.py`、`/data_source/variants_website.csv`
      三个地址都返回 **404**（返回 200 说明发错目录了，立即下线重发）

### 已知限制

- `somacard.html` 的 **Load example** 和 **Annotate** 按钮依赖 `server/server.py` 提供的
  `/api/example/*` 与 `/api/annotate`。纯静态发布没有这个后端，这两个按钮会报 HTTP 404；
  页面本身能正常打开。其余四页（首页搜索 / Data Portal / Donors / Tissue）功能完整。
- 首页首次加载要下载 8.3 MB 的 `data/variants_data.js`（21 列全量），首屏表格约 3 秒后才出现。

## 页面功能

### 导航栏
Home / Expression / QTL（Small Variant, Structure Variant, Tandem Repeat）/
Analysis & Tools（Genome Browser）/ Somatic Mosaicism / Download / Tissue / Consortium

### Search the Atlas

按**基因名 / 组织 / 供体 / 样本号 / 染色体区间**搜索，支持实时自动补全、表头筛选、
表格分页（10/25/50/100 条每页）、全列排序、详情侧边面板。

搜索框下方有一行**可点示例**（点一下直接填进搜索框并查询）：
`CSMD1` · `Whole Blood` · `AK231` · `AK231-0160` · `chr1:10000000-40000000`
（依次是 基因 / 组织 / 供体 / 样本 / 染色体区间）。
搜索框的 placeholder 也写明了可搜的维度。

**结果表 = 21 个 CSV 列 + Visualization，共 22 列**（2026-09-24 改造，此前只有 13 列）：
`Chr | Position | Ref | Alt | Depth | VAF | Type | Ti/Tv | Trinucleotide | Gene | Region |
Sample | Donor | Tissue | Ref Origin | Tissue Shared | Infiltration PP | Infiltration |
COSMIC Signature | CADD | Regulatory Score | Visualization`

- 除 `Visualization` 外**全部可点表头排序**；字典列按文字排（不是按字典下标）
- **表头筛选 8 组**（漏斗图标）：`Type` `Ti/Tv` `Tissue` `Donor` `Ref Origin`
  `Tissue Shared` `Infiltration` `COSMIC Signature`。
  语义与其他页一致：**组内 OR、组间 AND、一个都不勾 = 不筛**，
  选项旁的计数是 faceted count（统计满足「其它生效筛选」的行数），计数为 0 的选项不显示
- `Download` 导出的 CSV **列名与取值与源表完全一致**（`contig`/`pos`/…/`regulatory_score`），
  可直接和 `variants_website.csv` 对回去
- 表格 `min-width: 2180px`，窄屏横向滚动（`.table-wrap` 本来就是 `overflow-x:auto`）
- **空值统一显示成 `--`**（2026-09-24 由 `NA` 改）。改的时候两处必须同步：
  `COLS` 里各字段的 `empty`、`cellHtml()` 的兜底
  （原来还有第三处 `showDetail()` 详情侧栏的兜底，详情栏已移除，见下文）
- **表头列宽可拖拽**：拖动表头右边缘的细线即可改列宽，双击手柄恢复默认，
  调整结果记在 `localStorage` 的 `gtop.cols.search`。详见「列宽拖拽」一节
- **`Regulatory Score` 列显示成迷你柱状图**（2026-09-24 改）：柱子按「值 ÷ 满格刻度」取宽，
  满格刻度是 **5**（p99）而不是数据里的最大值 11 —— 该列 p50=1、p90=2、p99=5，99% 的值
  都落在 0~5，若按 11 归一化，「1」只有 9% 宽，肉眼分不出高低。6~11 的 645 行（0.6%）
  统一显示满格，真实数值仍写在柱子右边。刻度写在 `COLS` 的 `bar` 字段里。
  排序、导出走的是 `cellPlain()`，不受柱状图影响
- **柱子可点，但只在该行真有覆盖度图时可点**（2026-09-24 改，当天第二轮收紧）：
  点柱子 = 打开这一行的覆盖度图，跟最后一列那个 `Plot` 按钮是同一个弹窗。
  实现在 `cellHtml(r, c, idx)` 的 `bar` 分支（`idx` 只在 `render()` 里传）+
  全局的 `onBarClick(ev, el)`。
  - **没有覆盖度图的行，柱子是纯展示** —— 没有手型光标、没有 `role=button`/`tabindex`、
    没有 `onclick`，`title` 也不提「点击」（只有 `Regulatory Score: 6`）。
    全量 107,852 行里只有 8 行有图，所以绝大多数行的柱子都不可点，
    覆盖度图的入口回到 `Visualization` 列那个 `Plot` 按钮上。
    这么改是为了「看起来能点的东西一定点得动」
  - 早先（同一天第一版）是**无条件可点**：没图时退回打开右侧详情栏。那条路径随详情栏一起删了
  - `click` 仍要 `stopPropagation`：行本身虽然不再可点（见下一条），但保留它成本为零，
    将来若给行加回别的点击行为不会被误触发
  - 柱子高度 `7px → 12px`（同一天 luo：「柱子再粗一点」）。7px 在 12.5px 的行高里太细，
    值 1 和值 2 的柱子几乎看不出差别
  - 可点区域用 `margin: -3px -5px; padding: 3px 5px` 向外扩，悬停高亮不紧贴柱子；
    外扩的 5px 仍在 td 的 `padding` 里，不会被 `overflow: hidden` 裁掉
- **结果行不再整行可点**（2026-09-24 luo：「表格不需要点击行在右侧显示信息」）。
  原来 `<tr class="data-row" onclick="showDetail(idx)">` + `tr.data-row{cursor:pointer}`，
  点行内任何位置都会弹右侧详情栏 —— 想选中单元格文字、或拖拽松手时都会误触。
  现在 `<tr>` 上**没有** `onclick`，光标恢复 `cursor: default`。
  > 改这里时注意：`td.col-plot` 上的 `onclick="event.stopPropagation()"` 也一并删了 ——
  > 它本来是为了挡住行的 `showDetail`，行不可点之后它就没意义了
- **右侧「Variant Detail」详情栏已整体移除**（2026-09-24 第二轮 luo：「右侧详情栏不需要」）。
  它原来由三个入口触发，现在三条路径全关：
  ① 点表格任意一行（上一轮已去掉）；② 没有覆盖度图时那个灰色 `Plot` 按钮
  —— 现在按钮是 `disabled` 的，`title` 只作「该变异暂无覆盖度图」的提示；
  ③ 点 Regulatory Score 柱子但该行没图 —— 现在没图时柱子不可点。
  **表格里因此没有任何「打开右侧面板」的入口**，行内可点的只剩
  `Visualization` 列的 `Plot` 按钮和 `Regulatory Score` 的柱子，两者都指向覆盖度图弹窗。
  去掉不影响信息完整性：详情栏只是把这一行的 21 列又列了一遍，而这些列本来就在表格里。
  - 删掉的东西：`src/index.html` 的 `#detailOverlay` / `#detailPanel` 两个元素、
    `showDetail(i)` / `closeDetail()` 两个函数；`assets/site.css` 的
    `.detail-overlay` / `.detail-panel` / `.detail-head` / `.detail-body` /
    `.detail-row` / `.detail-plot` / `.detail-note` 七组规则
  - 要找回它：`git show be6f0ba` 里有完整实现
  - `.btn.btn-muted` 的 hover 规则加了 `:not(:disabled)` —— 禁用元素在 CSS 里**仍然会匹配
    `:hover`**，不排除掉的话鼠标划过还是会变色，看起来像能点
- **不再有 `Age` / `Sex` 两列** —— 它们来自 `select_sample.xlsx`，不属于这张 CSV，已移除

**表头筛选**：结果表的 `Type` / `Tissue` / `Donor` 三列表头各有一个漏斗按钮，点开是勾选面板。
选项旁的数字是 **faceted count** —— 统计满足「其它生效筛选」的行数，所以勾了 Tissue 之后，
Donor 列表里每个供体还剩多少条一目了然：

- 筛选是在搜索条件**之上**再收窄，即 `搜索命中 ∩ 各列筛选`（例：Whole Blood + INDEL = 378 条）
- 组内 OR、组间 AND；一个都不勾 = 不筛（与 Data Portal 页语义一致），全选也等于不筛
- 生效时表头按钮变蓝并显示已选个数，计数行后面挂 `Tissue: Whole Blood` 这样的标记
- `Donor` 有 68 个选项，面板顶部带组内搜索框；选项列表最高 264px，超出滚动
- 面板用 `position: fixed` 定位（`.table-wrap` 是 `overflow: auto`，绝对定位会被裁掉），
  位置由 JS 按按钮的视口坐标算；下方空间不够时自动翻到按钮上方，并随滚动/改窗口大小重新定位
- 关闭方式：再点按钮、点面板外、按 `Esc`
- `Reset Filters` 会连同三列筛选一起清空

**下载结果**：`Reset Filters` 左边的 `Download` 按钮**直接下载 CSV**（2026-09-24 去掉 TSV：
原先是个 CSV / TSV 二选一的下拉菜单，只剩一个选项的菜单没有意义，改成按钮直接下载，
`toggleDownload()` / `closeDownload()` 与 `.dl-menu` 样式一并移除）。
导出的是**当前搜索 + 筛选后的全部结果**（不只是当前这一页）。
列名与取值**与源表完全一致**，就是 `variants_website.csv` 的 21 列：
`contig / pos / ref / alt / depth / vaf / mutation_type / TiTv / trinucleotide / gene_symbol /
region / sample / donor / tissue / ref_origin / tissue_shared / infiltration_pp / infiltration /
cosmic_signature / CADD_PHRED / regulatory_score`，
文件名形如 `GTOP_somatic_mutations_20260924-1432.csv`。导出带 UTF-8 BOM，Excel 直接打开不乱码。

排序与筛选叠加时，筛选后**保持当前排序**（否则表头箭头还亮着、行却是乱序的）。
顺带修了一个老问题：表头排序箭头以前在 HTML 里写死成 `fa-sort`、JS 从不更新，
现在会随排序列和方向变成 `fa-sort-up` / `fa-sort-down` 并染成主色。

### 列宽拖拽

首页搜索表和 Data Portal 文件列表的**表头右边缘都能拖**：鼠标移上去出现一条细竖线，
拖动即改列宽，双击手柄恢复该列默认宽度，调整结果记在 `localStorage`
（`gtop.cols.search` / `gtop.cols.data`），刷新后仍在。
实现只有一份 `assets/col-resize.js`，两个页面各引一次、在页面底部调 `initColResize()`。

**交互行为**

- **拖谁只改谁，绝不联动别的列。** 表格总宽 = 各列之和，拖宽一列表格就变宽、
  `.table-wrap` 横向滚动；右边的列整体平移、宽度不变。
  双击手柄恢复**该列**的默认宽度，不是恢复全部。
- **每列有自己的下限** = `max(minWidth, 该列表头文字宽 + 28px)`，且不超过该列默认宽度。
  所以一列最少能拖到「刚好放得下自己的列名（含排序图标和筛选按钮）」。

> ⚠️ **「从右邻列借宽度」已于 2026-09-24 移除，不要改回去。**
> 用户反馈：「列的宽度基本固定吧，不要随意乱跳，我筛选之后根本不知道了」。
> 旧行为是拖 A 列时从右邻列借 —— 听起来合理（表格总宽不变、右边不留白），
> 实际很糟：拖 Gene 列 +200px，右邻的 Region 从 **264px 被挤到 64px**，
> 而 Region 是允许折行的列，`Upstream;Promoter;Open chromatin` 于是变成竖排的
> `Upstr / eam;P / romot / er;Op / en; / chrom / atin`，**行高从 50px 涨到 200px+**，
> 整张表没法看。而且「拖一列动两列」不符合任何表格的直觉 ——
> Excel / AG Grid / TanStack Table 全都是只改被拖的那一列。

**几个实现要点**（改之前先读 `assets/col-resize.js` 的文件头注释）

- **必须 `table-layout: fixed`。** auto 布局下给 `th` 写 `width` 只是「建议值」，
  浏览器仍按内容重算，拖起来会跳。所以初始化时先量一遍实测列宽、写成 px，再切成 fixed ——
  这样默认观感和加这个功能之前完全一致
- **表格宽度写死成 `<各列之和>px`，并且 `min-width` 一起钉成同一个值。**
  不能用 `max(<各列之和>px, 100%)`：`table-layout: fixed` 下只要「表格实际宽度 >
  各列之和」，浏览器就会把余量**按比例摊给每一列** —— 你拖出来的宽度不是实际宽度，
  而且余量一变 22 列一起动。两个会触发它的口子现在都堵上了：
  ① `max(..., 100%)`；② `site.css` 里 `table.data-table { min-width: 2180px }`
  （用户把各列拖窄到总和不足 2180px 时会被它顶住）
- **量「表头需要多宽」时，元素节点要用 `getBoundingClientRect()`，不能用 Range。**
  `Range.selectNodeContents(el)` 拿不到 ① 元素自身的内边距（`.th-filter` 的
  `padding: 1px 5px`，实测少 14px）② `::before` 伪元素（Font Awesome 图标就是靠它
  画的，实测直接返回 **0**）。实测 Type 列表头：Range 只量到 47px，真实需要 71px ——
  差了整整一个筛选按钮，拖到下限时按钮会压到右邻列
- 手柄上的 `click` 必须 `stopPropagation`，否则会误触发表头的排序
- 手柄绝对定位在 `th` 右边缘（`right: -3px`，宽 7px），所以 `th` 需要 `position: relative`。
  它会让 `th.scrollWidth` 恒比 `clientWidth` 大 3px —— 写断言时要先把它 `display:none`，
  否则会拿到假阳性

**拖窄之后文字不能压到邻列**（2026-09-24 luo 反馈「列的拖拽好奇怪呀，不正常」）

切到 `table-layout: fixed` 之后列宽就写死成 px 了，于是有两种情况会让文字溢出到右边
一列、两列的字叠在一起：

1. 用户把某列往窄里拖（拖 Chr 列 -60px，Chr 的值会溢出 174px）
2. **没拖过也一样** —— 列宽是按「第 1 页那 10 行」量的，翻到别的页遇到更长的值就溢出。
   实测第 3 页的 Gene（`ENSG00000123456`）压在 Region 上，看起来像 `ENSG00000Intron;NC`

两处都靠 `table.data-table tbody td { overflow: hidden; text-overflow: ellipsis }` 兜住：
溢出被裁掉、再换成 `…`。Data Portal 的 `table.data-list tbody td` 同样加了这两条。

> ⚠️ **写死的 `max-width` 是这类 bug 的元凶，改列宽时一定要一起看。**
>
> 修完上面两条之后 Gene 列**还是**显示成 `ENSG00000…`。查 DOM 才发现问题不在 `td`：
> `td.clientWidth = 150`（列宽已经正常了）而单元格里那个 `<span>` 只有 **92px** ——
> 因为 `site.css` 里有一条 `td.col-gene span { max-width: 92px }`，那是 Gene 列还只有
> 75px 宽时定的上限。列宽后来改成按全量数据定（150px），这个 92px 却把 span 卡死了，
> **用户把列拖宽文字也不会变长** —— 这才是「拖拽好奇怪」的真正原因。
>
> 已改成 `max-width: 100%`，span 跟着单元格走，超出部分由 `td` 的省略号兜底。
> 同一类问题在 Data Portal 的 `td.cell-file { max-width: 200px }` 上也存在（File 列
> 拖到 200px 以上文字就不跟着长了），已收进 `table.data-list:not(.col-resizable)`。
>
> 规律：**凡是写死 px 的 `max-width`，在列宽可变的表里都是定时炸弹。**
> 要么改成百分比，要么用 `:not(.col-resizable)` 限定它只在「量列宽阶段」生效。
> 目前 `site.css` 里还留着的写死 px 上限只有 `td.col-region`（264px，故意的）和
> 布局容器那几个，都在可接受范围内。

**默认列宽按「全量数据」定，不是按当前这一页**（2026-09-24）

只加省略号的话，翻页时 Gene 列会大片显示成 `…`（第 3~8 页每页 10~15 格）—— 治标。
根因是 `initColResize()` 量到的是「当前这一屏」的列宽：初始化时 tbody 里只有第 1 页
那 10 行，Gene 只量到 75px（放得下 8 个字符），而全量 107,852 行里 **90% 的 Gene 值
是 15 个字符**（约 135px）。

所以 `index.html` 里多了一个 `idealColWidths()`，按全量数据算一遍「每列至少要放得下多宽」，
通过 `minColWidths` 传给 `initColResize()`（取「实测值」和「它」里较大的那个）。

- **取 p95 而不是最大值**：Chr 列 95% 的值不超过 5 个字符，但偶发 27 字符的未定位
  contig（`AK231-DMSO.hap1.h1tg000003l`）。为那不到 1% 把 Chr 撑到 200px 不值得，
  交给省略号 + 悬停 `title` 兜底
- **例外是小字典列**（值域 ≤128 个）：像 Tissue 只有 30 个值，按 p95（13 字符）定宽会
  漏掉 `Heart Tricuspid Valve`（21 字符），每页总有 1 格显示成 `Heart Tricuspid V…`。
  这种列直接按最大值定宽
- **成本控制**：不逐行格式化（21 列 × 107,852 行 = 226 万次 `toFixed`/`toLocaleString`，
  要一两秒）。dict 列逐个量字典值（最多的是 gene 的 2.2 万项，全量 measureText 约 40ms），
  数值列利用「定点格式下字符串长度随数值单调递增」取全量最大值格式化一次。**实测 ~55ms**
  - 别改回「按字符数分桶、只量桶里第一个值」—— 试过，不准：同为 15 个字符的基因名
    宽度能差 3~4px（`ENSG00000272438` 要 122.9px），取到的代表值偏窄，算出来的列宽
    就比实际需要少 1px，于是整列 Gene 全变成 `ENSG00000…`
  - `PAD` 是 `24 + 2`：除了左右内边距各 12px，再留 2px 余量。不留的话会卡在
    「内容盒刚好比文字少 0.1px」这种边界上，同样是整列省略号
- 效果：表格总宽 2483 → 2620px（+137px），翻页时被裁的单元格从每页 10~15 格降到 0~1 格
  （只剩 Ref 列那不到 1% 的 49 字符长序列）

顺带把 `td.col-region` 的 `min-width/max-width: 264px` 收进
`table.data-table:not(.col-resizable)` —— 这两个值只在「表格还是 auto、JS 量列宽」
那一瞬间有用；表格切到 fixed 后留着它们会把 td 的盒子卡在 264px，用户把 Region 列拖宽
之后单元格不跟着撑开（实测拖到 414px 时 td 仍是 264px，中间留一条空白）。

> 验证：`/tmp/drag_verify.mjs` 逐列拖窄 -60px 断言「压到邻列 = 0」；
> `/tmp/width_verify.mjs` 翻 10 页断言「被裁单元格 ≤1 格/页」；
> `/tmp/regress.mjs` 5 页 × 5 宽度全过（压到邻列 0、行高恒定、无控制台错误）。

### Browse by Tissue
30 个组织卡片（图标 + 名称）：Esophagus, Trachea, Lung Apex, Lung Base,
Diaphragm, Liver, Gallbladder, Adrenal Gland, Muscle, Stomach,
Pancreas Head/Body/Tail, Small Intestine, Colon, Thoracic Aorta, Aortic Arch,
Heart Right/Left Atrium/Ventricle, Heart Mitral/Tricuspid Valve,
Spleen, Skin, Ovary, Uterus, Adipose, Common Iliac Artery, Whole Blood.

点击卡片跳转搜索该组织的所有突变。

### Our Donors（donors.html）

致谢页：一张侧脸剪影群像横幅（`assets/donors-banner.svg`）+ 致谢正文 + 手写体签名。

横幅由 `scripts/build_donors_banner.py` **程序化生成**（固定 `random.seed(20260923)`，
所以每次重跑结果完全一致），不是设计稿导出的位图。生成后 SVG 只有 8.7 KB。

> ⚠️ **横幅不要留底部空白**（2026-09-24 luo 反馈「留白太多了」）。
>
> 生成脚本里原先 `BAND_H = 214` 而画布 `H = 258`，也就是画布底部空着 **44px**
> （44/258 = 17.1%），在页面上就是横幅下沿一条明显的空白带。
>
> 侧脸轮廓本身是从头顶（局部 y≈4）一路画到躯干底（局部 y=200）的完整半身像，
> 214 的裁剪线落在胸口，把躯干整段切掉了。**现已把 `BAND_H` 改为 `H`（=258）**，
> 剪影自然铺满整幅，底部空白归零（实测墨迹覆盖率 68.9% → 80.5%）。
>
> `BAND_H` 不参与 `random` 调用，所以改它不会移动随机序列 —— 重新生成出来的
> 21 组剪影与旧版**逐字节一致**，只有 `clipPath` 那一处 `214 → 258`。
> 验证方式：`diff` 确认只差 2 个字符；再在 1600/1440/1280/1024/768/640 六档宽度下
> 逐行扫描截图，断言「底部空白 = 0px、标题不出框」。

横幅容器是 `.donor-banner`（`min-height: 258px`，≤640px 视口降到 190px），
底图 `<img>` 用 `object-fit: cover` 铺满，窄屏靠裁掉左右两端来保持高度。

## Data Portal（somatic-data.html）

数据下载门户，展示 GTOP 正常组织与全血的测序文件清单。**页面数据全部来自
`data_source/tissue_genome_data.csv` 真实数据**，不含示例数据。

### 源数据

`data_source/tissue_genome_data.csv`（7,249 行 × 8 列）：

| 列 | 说明 |
|----|------|
| `Donor` | 供体编号，形如 `GTOP-AJ221` |
| `Experimental assay` | `WGS` / `RNA-seq` |
| `Sequencing platform` | `PacBio HiFi` / `DNBSEQ-T7` / `Illumina NovaSeq X` |
| `Tissue` | 组织，下划线写法（`Whole_Blood`、`Adrenal_Gland`…） |
| `Data format` | `bam` / `fastq` / `fasta` / `chain` |
| `File name` | 文件名（7,249 个，无重复） |
| `File size (MB)` | 文件体积，MB |
| `UUID v4` | 文件唯一标识（7,249 个，无重复） |

**规模统计**（脚本每次生成时重新计算，页面上方的概览数字由 `window.GDATA_STATS` 注入）：

| 指标 | 数值 |
|------|------|
| 文件数 | 7,249 |
| 供体数 | 160 |
| 组织数 | 33 |
| 总体积 | 623.8 TB |
| 实验 × 平台 | RNA-seq → Illumina NovaSeq X（4,839）；WGS → DNBSEQ-T7（1,770）、PacBio HiFi（640） |
| 格式分布 | fastq 3,934 / bam 2,771 / chain 408 / fasta 136 |

> 源 CSV 带 UTF-8 BOM，读取时必须用 `encoding='utf-8-sig'`，否则首列名会变成 `\ufeffDonor`。

### 生成脚本

```bash
python3 scripts/build_genome_data.py     # 默认读 data_source/tissue_genome_data.csv → data/genome_data.js
python3 scripts/build_genome_data.py <in.csv> <out.js>
```

`build_genome_data.py` 把 5 个离散字段（供体 / 组织 / 实验 / 平台 / 格式）去重成字典并按字母序固定，
行内只存下标，输出 0.59 MB（原始 CSV 0.86 MB）。输出结构：

```js
window.GDATA = {
  donors: ["AJ141", …],          // 已去掉 "GTOP-" 前缀，便于窄列显示
  tissues: ["Abdominal_aorta", …],
  assays: ["RNA-seq", "WGS"],
  platforms: ["DNBSEQ-T7", …],
  formats: ["bam", "chain", "fasta", "fastq"],
  rows: [[供体, 实验, 平台, 组织, 格式, 大小MB, "文件名", "UUID"], …]
};
window.GDATA_STATS = { files, donors, tissues, totalMB, generated };
```

### 页面描述文案

描述只有一段（2026-09-24 按需求删掉了原来的「GTOP is a multi-tissue genomic resource…」和
「The table below lists the … files … released for these samples.」两段），改用 GTOP 官方口径：
354 个 PCR-free bulk WGS 样本（30 个正常组织类型）；PacBio HiFi 全血 68 供体；
RNA-seq 1,613 样本（33 个组织类型）；`comprising a total of 7,249 files and 623.8 TB of data`；
数据托管在 [cloud environment](https://cloud.smart-nbc.org.cn/)（访问受控，需申请）。

> **链接不要直接显示网址**（2026-09-24 luo 明确）：正文里写的是
> `<a href="https://cloud.smart-nbc.org.cn/" target="_blank" rel="noopener">cloud environment</a>`，
> 页面上显示成蓝色的 `cloud environment` 三个词，悬停才看到网址 —— 而不是把
> `(https://cloud.smart-nbc.org.cn/)` 原样铺在句子里。样式来自 `site.css` 的 `.page-desc a`。
> README 里为可读性用了 Markdown 链接写法，页面上不出现裸网址。

这些数字都跟源 CSV 核对过：

| 文案里的说法 | CSV 里对应 | 实际 |
|--------------|-----------|------|
| 160 donors | `Donor` 去重 | 160 ✓ |
| 33 tissue types | `Tissue` 去重 | 33 ✓ |
| 354 samples spanning 30 normal tissue types | `DNBSEQ-T7` 的 donor×tissue 去重 / 组织去重 | 354 / 30 ✓ |
| PacBio HiFi whole-blood from 68 donors | `PacBio HiFi` 的供体去重 | 68 ✓（组织只有 Whole_Blood） |
| RNA-seq 1,613 samples across 33 tissue types | `RNA-seq` 的 donor×tissue 去重 / 组织去重 | 1,613 / 33 ✓ |

文案里的 `7,249`、`623.8 TB` 由 `<span id="statFiles">` / `<span id="statSize">` 承载，
页面载入后由 `window.GDATA_STATS` 覆盖，所以源 CSV 更新后描述不会和数据表打架；
其余样本数是官方口径，写死。

### 页面结构

沿用设计稿的「左侧筛选 + 右侧列表」双栏结构（`.filter-layout`）。
页面标题与面包屑为 `Somatic Mosaicism Data Portal`（原来叫 `Somatic-data List`）。

**筛选面板**（5 组，选项、计数均由数据生成）：

| 组 | 选项数 | 取值列 |
|----|--------|--------|
| Tissue | 33 | `Tissue`（原名 Primary Site） |
| Donor | 160 | `Donor` |
| Assay | 2 | `Experimental assay` |
| Platform | 3 | `Sequencing platform` |
| Format | 4 | `Data format` |

筛选逻辑：**组内 OR、组间 AND**。选中任意项后标题栏出现 `Clear all (n)` 按钮，
分组标题上也会挂一个「已选 N 项」的角标。选项数超过 20 的组（Donor）会额外带一个组内搜索框。

三处与 ENCODE 对齐的增强：

1. **每个选项后面显示文件数**（faceted count：统计满足「其它生效筛选」的行数），
   并且**计数为 0 的选项直接不显示**。所以勾了 `Assay = RNA-seq` 之后，
   Platform 组里只剩 `Illumina NovaSeq X`，`DNBSEQ-T7` / `PacBio HiFi` 自动消失
   —— 这就是「按 assay 自动识别平台」的实现方式，不用写死映射表。
2. **Donor 可以展开**：每个供体左边有个三角，点开列出这个供体有数据的组织
   （数据来自启动时建的 `DONOR_TISSUES` 索引），点组织 chip 直接钻到
   「这个供体 × 这个组织」（同时设置 donor 与 tissue 两组筛选）。
3. **Data Matrix**：表格上方一个可折叠面板，是 `Tissue × Assay` 的文件数热图
   （33 行 × 2 列，含行列合计），格子底色按列内最大值分 4 档深浅，
   点行名只看该组织、点格子只看「组织 × assay」。默认收起。

**Data Matrix 与左侧筛选的联动**（2026-09-24 加）：

矩阵的计数会跟随左侧筛选，但**只跟随「Tissue / Assay 之外」的筛选**（Donor / Platform / Format）。
口径与筛选面板的 faceted count 完全一致：某组自己的计数不受该组的筛选影响。

- 勾 `Donor = AJ141` → 矩阵合计从 7,249 收到 21，没有数据的组织行整行压暗
- 勾 `Tissue = Adipose` → 矩阵合计**不变**，只是把 Adipose 那一行高亮

为什么把这两轴排除掉：矩阵本身就是 Tissue × Assay 的格子图。若把 Tissue 筛选也算进计数，
勾一个组织之后矩阵就只剩一行——既看不出别的组织还剩多少，也没法换着点。
排除之后，矩阵始终是一张可用的「导航图」：无论当前选中了什么，都能直接点另一个格子切过去。

界面上对应三处：

- 面板内多一条提示条，写明「Counts cover 21 of 7,249 files, narrowed by Donor.」，
  以及「Tissue / Assay selections are highlighted but not applied to these counts」
- 选中的组织行 / assay 列：行头列头加浅蓝底 + 主色条 + 加粗
  （**只加在行头列头，不动格子底色**——格子深浅是热图本身的信息量）
- 当前口径下没有数据的组织行：整行压暗

实现要点：`matrixBase()` 返回「除 Tissue / Assay 外生效筛选」命中的行；
`renderFilters()` 末尾在 `dmOpen` 为真时调 `renderMatrix()` 重画
（`dmOpen` 的声明必须早于 `renderFilters()`，否则踩 TDZ）；重画前记下
`.dm-scroll` 的 `scrollTop/scrollLeft` 并在画完后还原。

**列宽**（2026-09-25 修，luo：「data matrix 的第一列是不是太宽了」）：是。实测第一列
**570px**，而它最长的一条内容（`Heart Tricuspid Valve`）只要 130.8px，421px 是纯浪费。

原因在 **auto 布局的分配规则**：`table.dm-table { width: 100% }`（1116px）、4 列，
多余空间按各列 **max-content 的比例**摊给各列。第一列的 max-content 是 168px（行头文字），
另外三列各约 45px —— 比例约 3.7 : 1 : 1 : 1，于是第一列独吞了 570px。
给它单加 `max-width` 没用（auto 布局下 td/th 的 `max-width` 不可靠），
只能换成 **`table-layout: fixed`**、把第一列的宽度写死。

- `table.dm-table` 加 `table-layout: fixed`；`.dm-corner` / `.dm-rowhead` 写死
  `width: 168px`（原本就有 `min-width: 168px`，但 auto 布局不认它，现在才真正生效）
- fixed 布局下**没给出宽度的列平分剩下的空间**，所以后三列自动变成
  `(1116 − 168) / 3 = 316px`，三列等宽
- 表格仍然 `width: 100%`、仍然填满面板 —— 试过「按内容收缩」（表格 433px，右半边空一大片）
  和「限宽 720px 居中 / 左对齐」（居中和面板标题 `Data Matrix` 对不齐；左对齐右边留白 396px），
  都不如填满
- `.dm-rowhead button` 补了 `max-width: 100% + text-overflow: ellipsis` 兜底：
  fixed 布局下列宽不会自己撑开，万一将来出现更长的组织名就截断，而不是溢出压到热力格上。
  当前 33 个组织名最长 118.8px、列内可用 156px，用不到这条

实测（视口 1600 / 1440 / 1280 / 1024）：第一列恒为 168px、余量 37.2px、无截断；
后三列随面板宽度平分（316 / 316 / 268 / 185px）；行高恒为 25.4px × 33 行；矩阵内无横向滚动。

**表格列**（9 列，`table-layout: fixed`）：`Lock | File | Donor | Tissue | Assay | Platform |
Format | Size | UUID`。

- 组织名展示时把下划线换成空格（`Whole_Blood` → `Whole Blood`），供体去掉 `GTOP-` 前缀。
- **文件名单行 + 尾部省略号**（`.with-uuid td.cell-file a` 用 `text-overflow: ellipsis`；
  完整文件名留在 `<a title>` 里，悬停可见），点击跳到云平台（`href` 指向
  `https://cloud.smart-nbc.org.cn/`，新标签页；页面上不显示裸网址）。
- `UUID` 列在最后一列，36 字符单行显示。**字体字号与表内其它列完全一致**
  （2026-09-24 第二轮 luo：「与其它列一致」）—— 正文 `"Source Sans 3"` / 12.5px。
  原来是 `ui-monospace` / 10.5px，比其它列小两号，一眼能看出「这列的字不一样」。
  > 顺带删掉了 `td.cell-uuid` 上两条**从来没生效过**的声明：`color: var(--muted)` 和
  > `line-height: 1.35`，都被 `table.data-list tbody td` 的 `color: var(--text-2)` /
  > `line-height: 1.42` 盖掉 —— 优先级 (0,1,3) > (0,1,1)，**跟书写顺序无关**。
  > 同样的坑还压在 `td.cell-lock` 和 `td.cell-size` 的 `color: var(--muted)` 上，
  > 一并删了（像素级不变）。**改这几列的 color / line-height，选择器必须写成
  > `table.data-list tbody td.cell-x` 才有效。**
  > （`font-size` 之所以生效，是因为表格那条是 `table.data-list{font-size:12.5px}` 属于
  > **继承**，继承值永远输给直接写在 td 上的规则。）
- `Size` 按 MB/GB/TB 自动换算（≥1024 MB 显示 GB，≥1024 GB 显示 TB）。
- 除 Lock 列外每列都可点击排序（首次升序、再点降序，表头箭头同步）。
  **可排序表头是 `cursor: pointer`**（2026-09-24 补）：首页搜索表一直有这条
  （`table.data-table thead th.sortable`），Data Portal 的 `table.data-list` 漏了，
  于是鼠标移到 File / Donor 这些表头上仍是默认箭头，看起来像不可点。现在两张表一致
  （含悬停底色 `#eef2fa`）。表头右边缘那 7px 是列宽拖拽手柄，它自己的
  `cursor: col-resize` 优先级更高，两者不冲突

**列宽怎么定的（2026-09-24，先后修了两次）**：这张表是 `table-layout: fixed` + `width: 100%`，
**没写宽度的列会把全部剩余空间独吞**。原先只有 `File` 列没写宽度，于是它拿到 422px
（内容最长只要 288px），而 `UUID` 明明需要 248px 却只剩 134px，被迫折成两行。

修法是把 9 列都写成百分比（合计 100%）。**第二次修**把 `File` 从 26% 收到 17.3%：
全量 7,249 个文件名里 **91% 不超过 23 字符**（p90=23），只有 5.6% 是 36~40 字符的
`*.liftover.chain`。为这 5.6% 让整列保持 290px，代价是其余 94% 的行右侧都空出约 120px ——
看起来就是「这列怎么这么宽」。现在按 p90 定宽、超出的尾部用省略号（完整名在 `<a title>` 里，
悬停可见，点进云端也能看到）；`Lock` 列则因为「锁图标 + Lock」实测要 63px 而补到 6.1%：

| 列 | Lock | File | Donor | Tissue | Assay | Platform | Format | Size | UUID |
|---|---|---|---|---|---|---|---|---|---|
| 百分比 | 6.1% | 17.3% | 6% | 12.1% | 7.1% | 13.1% | 5% | 7.3% | 26% |
| 1440 下实测 px | 68 | 193 | 67 | 135 | 79 | 146 | 56 | 81 | 290 |

单元格横向内边距在第一次修时已从 10px 收到 8px（9 列共腾出 36px）。

**第三次修**（2026-09-24 第二轮）：`UUID` 字号从等宽 10.5px 改成正文 12.5px 后，
同样 36 个字符从 227.6px 涨到 **266.5px**，原来 23.7%（≈265px）装不下，会折成两行、
行高 41 → 58.5px。于是把 `Tissue` 从 14.4% 收到 **12.1%**、`UUID` 从 23.7% 放到 **26%**。
选 `Tissue` 是因为它是 9 列里余量最大的一列：实测最长值 `Pancreas Head` 只要 104px，
而它原来占 161px；让出来的 2.3%（≈25.7px）正好给 `UUID`。

> ⚠️ 第一版只让了 1.6%（`UUID` 25.3%）**不够**：那样 `UUID` 列 282px、可用 266px，
> 而实测最长的那条 UUID 文字要 266.5px —— 差 0.5px，照样折行。
> **别卡在边界上**，按「需要的文字宽 + 8px 余量」倒推百分比。

配套把 `table.data-list` 的 `min-width` 从 1060px 提到 **1116px**
（= 最宽布局下 `.table-wrap` 的可用宽度）。取「正好等于可用宽度」是为了让 `UUID` 列
在最窄的情况下也放得下 36 个字符：最宽布局下表格正好填满、不出滚动条，
视口更窄时**不再压缩列宽**，而是让 `.table-wrap` 横向滚动 ——
与首页搜索表 `min-width:2180px` 的做法一致。

> ⚠️ **min-width 和表头那组百分比是互相咬合的**：各列百分比 × 1116px 必须不小于该列
> 「不折行 / 不溢出」所需的最小宽度。当前实测（×1116px）：
> `Lock` 68.1（需 43.8）· `File` 193.1（需 176）· `Donor` 67.0（需 52.4）·
> `Tissue` 135.0（需 104.1）· `Assay` 79.2（需 68.6）· `Platform` 146.2（需 128.5）·
> `Format` 55.8（表头文字 54.1，**最紧的一列**）· `Size` 81.5（需 61.1）·
> `UUID` 290.2（需 282.5）。
> 2026-09-24 一度把下限从 1112 降到 1045 却没同步校准，结果 1280 / 1120 / 980 三个宽度下
> `UUID` 折行、行高 41→53px。**改任何一边都要把另一边重算一遍。**

> 📌 **已知遗留（未修，改动前就有）**：`Format` 列表头文字（含排序图标）实测要 54.1px，
> 而列宽只有 56px、内容盒 40px —— 溢出 11px，表头会挤到右邻 `Size` 列上。
> 改动前后逐视口量过，数值完全一致（`over: 11`），不是本轮引入的。
> 要修的话从 `Tissue` 再让 1.3%（→ 10.8%）给 `Format`（→ 6.3%）即可，同样要重算咬合。

验证方式：headless Chrome 逐页翻完 **145 页 / 7,249 行**，断言「行高恒为 41px」（单一值
即无任何单元格折行）；1600 / 1440 / 1280 / 1120 / 980 五种宽度下均通过，
并逐格量过「文字有没有越过自己的右边界」—— 全为 0。

> 列宽现在还能在页面上直接拖，见「列宽拖拽」一节；上面这些百分比只是**初始值**。

**分组标题里的数字**（2026-09-24 修）：`Tissue (33)` 括号里的数字以前取的是固定的
选项总数 `g.opts.length`，不随筛选变化。于是勾了 `Tissue = Abdominal aorta` 之后，
Donor 组下面只剩 1 个人、标题却还写着 `Donor (160)`，标题和列表对不上。
现在改成统计「实际列出的选项数」（计数 > 0 或已勾选），与 `optHtml` 的渲染条件同一套判定。
没有任何筛选时每个选项计数都 > 0，算出来等于选项总数，所以默认状态外观不变。

**分页**：每页 50 条，共 145 页；左下角显示 `Showing 1–50 of 7,249 files`，右下角是翻页按钮
（首页/上一页/页码窗口/下一页/末页）。翻页后自动滚回表格顶部。

### 与设计稿的差异

| | 设计稿 | 实现 |
|---|--------|------|
| 列（不含 Lock） | File, Assay, Platform, Format, Data Type, Seq Center | File, Donor, Tissue, Assay, Platform, Format, Size, UUID |

设计稿的 `Data Type`、`Seq Center` 在真实数据里没有对应字段，已去掉；换成真实存在的
`Donor`、`Tissue`，并按下载场景补了 `Size` 列，最后再加一列 `UUID`（文件唯一标识，源 CSV 自带）。
`Tissue` 前移到 `Assay` 之前，因为 Tissue 是这里最主要的筛选维度。锁图标列、表头样式、
行高、蓝色链接色等外观未动。设计稿表格里的数据本身是 COLO829 示例数据，已整体替换为真实 GTOP 清单。

另外两处属于「新增、未改动原有规则」的调整：

- `.filter-layout` 在 `max-width: 980px` 下原来是 `grid-template-columns: 1fr`，单列时该列的
  min-content 被表格的 `min-width` 撑开，连带左侧筛选栏一起把页面顶出横向滚动条
  （768px 下溢出 147px）。改成 `minmax(0, 1fr)` 后由 `.table-wrap` 自己横向滚动。
  该规则只有本页用到。
- 列表有 7,249 行，滚动后筛选栏会移出视口，因此双栏（≥981px）下给 `aside` 加了吸顶。

### 布局容器宽度

`.container` 的 `max-width` 由 **1200px 调到 1440px**，对齐线上生产站 `https://bioinfo.szbl.ac.cn/GTOP/`
的 `max-w-(--ui-container)`（实测 1440px，1920 视口下两侧各留 236px）。同时补了一条
`@media (min-width: 1440px) { .container { padding: 0 32px } }`，让大屏下的左右留白和线上的
`lg:px-8` 一致——两者叠加后内容区正好 1376px，与线上完全相同。

起因是 Data Portal 的 `File` 列太窄（1200px 容器下只有约 200px），长文件名被压得很难看。
放宽后表格区变宽，但 `File` 列又反过来独吞了全部余量（422px），2026-09-24 用上面那套
百分比方案收敛到 **193px**。当前实测（1600 / 1440 / 1280 / 1120 / 980 五档走查）：

| 视口 | Data Portal 表格区 | File 列 | UUID 列 |
|---|---|---|---|
| 1600 / 1440 | 1116（刚好填满，不出滚动条） | 193 | 265 |
| 1280 / 1120 / 980 | 1063（横向滚动） | 183 | 251 |

`≤1248px` 的视口不受影响（`1200 + 24×2` 都没到，容器本来就是流式的）。
`.container-wide` 同步抬到 1560px，保持「wide > 默认」的语义（该 class 目前无人使用）。

改完重跑了 5 页 × 6 宽度（1440/1200/980/768/480/375）走查，**0 控制台错误、0 横向溢出**。

## SomaCard Annotation

输入突变列表（TXT 或 VCF），选取组织，后端调用 `mutation_annotation.py`
进行调控元注释和优先级打分，结果以表格展示并可下载 TSV。

### 页面来源：从 10.6.109.183 取回（2026-09-25）

线上 GTOP 站跑在 **10.6.109.183（主机名 mtcook）** 的
`/media/Rome/home/luodl/website/smatcp-website`，由
`python somacard/server.py --host 0.0.0.0 --port 8080` 托管，对外是
`https://bioinfo.szbl.ac.cn/GTOP/`。它的 SomaCard 页 `somatic-annotation.html`
已经迭代到 **「GTOP Somatic final v6」**（`README.txt` 记了 v4/v5/v6 三轮），
比本地 `src/somacard.html` 新一代，所以把内容整体取回了本地。

**搬回来的是什么**

- `page-hero` 文案 → 线上版（`Somatic Mutation Annotation` + 新的两行说明）
- 三步流程条 `wizard-steps`：`1 Input File / 2 Select Tissues / 3 Run & Download`
- 两张卡片带 `STEP 1` / `STEP 2` 角标；Step 2 的组织选择从**文字按钮网格**换成
  **带缩略图的滚动列表**（`tissue-select-card` + `Select All` / `Clear All` +
  `N of 30 tissues selected`）
- `Run Annotation` 从右卡片里挪到两卡片下方居中
- 结果区 `annotation-results` + `Download TSV`
- **登录门**：`assets/somatic-auth.js`（与线上逐字节一致，md5
  `dbe37accecd4c48c9f2a46999d5346ed`）
- 线上那份内联 `<style>`（约 1300 行）**原样保留**，保证视觉与线上一致

**为了适配本地结构改了三处**（其余逐字未动）

| 改动 | 原因 |
|------|------|
| `tissue/<名>.png` → `../assets/tissue/<名>.png` | 页面在 `src/`，组织图在 `assets/tissue/`（30 个名字本地全都有） |
| CDN Font Awesome → `../assets/fontawesome/css/all.min.css` | 本地那份就是 6.5.0，与线上 CDN 同版本，图标不缺 |
| `body { padding-top: 64px }` → `0`（共 3 处） | 线上页头是 `position:fixed` 的导航条，才需要留 64px；本地 `.site-header` 是 `position:sticky`（占位在文档流里），不归零会多 64px 空白 |

**没搬的两样（有意保留本地做法）**

- **页头 / 页脚**：线上用 `nav-component.js` 渲染 GTOP 导航（无工具条），
  本地保留全站统一的 `<header class="site-header">` / `<footer class="site-footer">`，
  否则本页会跟其它 4 页的页头长得不一样。
  代价：线上导航里登录后的**用户 pill**（User Center / Log out）本地没有
- **`nav-component.js` 本身**没有进仓库。页面里那句
  `GtopNav.render('gtopNav', 'default', 'annotation')` 已删除

**登录门怎么工作 / 怎么绕过**

`somatic-auth.js` 默认只认文件名 `somatic-annotation.html`，本地这页叫
`somacard.html`，所以靠根元素上的 **`data-somatic-auth="required"`** 触发
（脚本原生支持这个属性，不用改脚本）。线上没配 `window.__GOOGLE_CLIENT_ID`，
走的是**兜底密码登录**，密码 `window.__SOMATIC_PASSWORD || 'somatic2024'`，
页面上还会显示一条黄色「Google OAuth not configured」提示 —— 这是线上现状。

本地调试想跳过登录门：

```js
// 控制台执行后刷新
sessionStorage.setItem('somatic_authenticated', 'true')
```

或直接填密码 `somatic2024`。

**改完的实测**（1600 / 1440 / 1280 / 1024 / 768 五个视口）

| 项 | 结果 |
|---|---|
| 组织卡片 / 图片 | 30 / 30，断图 0 |
| 页头高度 vs hero 顶距 | 均 81px（**无 64px 空隙**，说明 padding-top 改对了） |
| 交互 | 点卡片 → 选中 + 计数；Select All → 30；Clear All → 0；TXT/VCF 切换正常 |
| 横向溢出 / 控制台异常 / 失败请求 | 0 / 0 / 0 |
| 全站 5 页回归 | 溢出 0、断图 0、异常 0、失败请求 0 |

### API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | `{"status":"ok","script":"...","script_exists":true,"tmp_dir":"..."}` |
| `/api/example/<fmt>` | GET | 返回 `server/examples/test_mutation.<fmt>` 内容 |
| `/api/annotate` | POST | `{"mutations":"...","file_type":"txt|vcf","tissues":[...]}` → 返回 TSV |

### 注释流程

1. 解析输入（TXT：chrom/pos/ref/alt；VCF：标准格式）
2. 查询 TF binding（TFBS / motif / footprint）→ 确定 TF 等级（1-4）
3. 查询开放染色质（ATAC / CTCF / DNase）
4. 计算 score_mutation（M1-M8）
5. 关联靶基因（7 种方法：3D-Chromatin, ABC, rE2G, EPIraction, GraphRegLR, CRISPR, eQTLs）+ TSS 距离
6. 计算 score_link（L1-L5）
7. 评估基因约束度 pLI → score_gene（0/1）
8. 组织特异性驱动基因 → score_tissue_specific（0/1）
9. 综合优先级 score_priority（0-13）

**输出列（21 列）：**
`tissue`, `mutation_key`, `regulatory_gene`, `tss_distance`, `cCRE`,
`cCRE_type`, `TFBS`, `TF_motif`, `TF_footprint`, `in_ATAC`, `in_CTCF`,
`in_DNase`, `link_3D-Chromatin`, `link_ABC`, `link_rE2G`, `link_EPIraction`,
`link_GraphRegLR`, `link_CRISPR`, `tissue_enriched_gene`, `pLI`, `score_priority`

### 命令行示例

```bash
# 直接运行注释
python server/mutation_annotation.py \
    --file-type txt \
    --input server/examples/test_mutation.txt \
    --tissue Adrenal_Gland Muscle \
    -o server/examples/annotation.tsv

# API 调用
curl -X POST http://127.0.0.1:5502/api/annotate \
  -H "Content-Type: application/json" \
  -d '{"mutations":"chrom\tpos\tref\talt\nchr1\t1158636\tA\tG","file_type":"txt","tissues":["Adrenal_Gland","Muscle"]}'
```

## 数据依赖路径

`mutation_annotation.py` 依赖以下外部参考数据：

| 数据 | 路径 |
|------|------|
| TF ChIP-seq | `/media/iceland/share/Datasets/Archives/luodl/somatic/TF_chip/TF_merged.sorted.bed.gz` |
| TF Motif | `/media/iceland/share/Datasets/Archives/luodl/somatic/motif/TF_motif.sorted.bed.gz` |
| TF Footprint | `/media/iceland/share/Datasets/Archives/luodl/somatic/footprint/tissue/` |
| cCRE | `/media/iceland/share/Datasets/Archives/luodl/somatic/cCRE/GRCh38-cCREs.bed.gz` |
| cRE 组织数据 | `/media/iceland/share/Datasets/Archives/luodl/somatic/tissue/` |
| Gene Link | `/media/iceland/share/Datasets/Archives/luodl/somatic/gene_link/` |
| TSS 位置 | `/media/Rome/home/luodl/reference/hg38/annotation/tss_pos.bed`（由 gencode v38 生成，59,385 个基因） |
| pLI 约束度 | `/media/iceland/share/Datasets/Archives/luodl/somatic/gnomad.v2.1.1.lof_metrics.by_gene.txt.bgz` |
| 组织特异性基因 | `/media/london_A/kewei/2025.04.16_somatic/Project_SNV/2026.03.09_tissue_specific_genes/tissue_specific_genes.csv` |
| 覆盖度图集 | `/media/london_C/alps1/zhangyun/2024-2-19-Asian-GTEx/2026-03-30-Somatic/coverage_plot/7_plot_high_score_regulatory_variants/`（详见下文） |
| motifbreakR 脚本 | `server/motifbreakR_query.R`（与 `server.py` 同目录） |

## 覆盖度图（Coverage plots）

搜索结果表里每行的 **Plot** 按钮对应一张该变异的覆盖度图（PDF）。图集放在服务器上，
站点通过「本地示例 + 可切换的图集基址」两种方式引用。

### 图集位置与命名规则

| 项 | 内容 |
|----|------|
| 完整图集路径 | `/media/london_C/alps1/zhangyun/2024-2-19-Asian-GTEx/2026-03-30-Somatic/coverage_plot/7_plot_high_score_regulatory_variants/` |
| 文件数 / 体积 | 645 个 PDF，约 78 MB |
| 命名规则 | `<供体>-<组织>-<chr><位置>-<ref>-<alt>.pdf` |
| 示例 | `AJ221-Heart_Tricuspid_Valve-chr10-106826223-C-A.pdf` |

两点必须注意：

1. **组织名用下划线**，且写法必须与 `data/variants_data.js` 里 `tissues` 数组完全一致
   （如 `Heart_Tricuspid_Valve`、`Whole_Blood`）。因此文件名与索引键可以直接互转：
   把键里的 `|` 换成 `-` 并加 `.pdf` 后缀即可。
2. 图集覆盖 21 个组织、仅限 high-score regulatory variants。用 `data/variants_data.js`
   逐条比对，**645 张图中有 621 张能对上变异记录**，另有 24 张对应的变异不在当前
   CSV 中（多为早期版本或已被过滤的位点）。

### 站点里的实现

| 文件 | 作用 |
|------|------|
| `assets/plots/` | 示例 PDF 目录（当前只放 8 张，便于演示与仓库瘦身） |
| `data/plots_index.js` | 自动生成的可用图索引，导出 `window.PLOT_BASE`、`window.PLOT_KEYS` 与 `window.PLOT_META` |
| `scripts/build_plots_index.py` | 索引生成脚本 |

按钮行为：命中索引 → 实心蓝色按钮，**先在页内弹窗里预览覆盖度图**，弹窗右上角可再选择
「Open in new tab」用浏览器完整阅读器打开 PDF（缩放 / 下载 / 打印）；
未命中 → 描边弱化的按钮，**`disabled`，不可点**，`title` 只提示「该变异暂无覆盖度图」。

> 2026-09-24 第二轮之前，未命中的按钮是可点的，点了打开该变异的右侧详情栏
> （提示 `No coverage plot available for this variant.`）。详情栏整体删掉之后，
> 这个按钮只剩「本行没有图」的提示作用，所以改成 `disabled` ——
> 一个点了没反应的按钮比一个灰掉的按钮更让人困惑。

覆盖度图在**结果表里只有一个入口**：`Visualization` 列的蓝色 `Plot` 按钮。
（`Regulatory Score` 的柱子是同一个弹窗的快捷方式，但只在该行真有图时才可点，
见「Search the Atlas」一节。）

#### 弹窗（Plot modal）的几点实现说明

- 弹窗内的 `<iframe>` 地址带 `#toolbar=0&navpanes=0&view=FitH`，隐藏 Chrome 自带 PDF 工具栏，
  弹窗里呈现的就是一张干净的图；需要完整工具时点「Open in new tab」。
- 弹窗尺寸按图的原始宽高比自适应：`build_plots_index.py` 会读取每个 PDF 首页的
  `MediaBox`，写入 `window.PLOT_META = { "键": [宽, 高] }`。弹窗按
  `可用宽度 × 高/宽 + 标题栏高度` 定高（上限 88vh），避免上下留出 PDF 阅读器的深色底。
  示例图的宽高比在 1.27~1.74 之间，差异明显，所以这一步是必要的。
- 关闭方式：点右上角 ×、点弹窗外的遮罩、或按 `Esc`。关闭时先播淡出动画，
  260ms 后再卸载 `<iframe>`，避免闪白。
- 用服务器清单生成索引（`python3 scripts/build_plots_index.py plot_files.txt`）时读不到 PDF 内容，
  `PLOT_META` 会是空的——此时弹窗回退到固定尺寸，功能不受影响。

当前随仓库提供的 8 张示例图（每个供体一张，组织与染色体尽量分散）：

```
AJ221-Heart_Tricuspid_Valve-chr10-106826223-C-A.pdf
AJ231-Adrenal_Gland-chr2-152175470-C-T.pdf
AK091-Colon-chr7-100966697-A-G.pdf
AK111-Whole_Blood-chr14-31457661-G-A.pdf
AK112-Esophagus-chr1-25906221-A-C.pdf
AK231-Whole_Blood-chr11-113114524-C-T.pdf
AK281-Adrenal_Gland-chr17-78378857-G-A.pdf
AL271-Whole_Blood-chr1-43974765-C-T.pdf
```

### 启用完整图集

**方式一：把全部 PDF 拷进站点**（自包含，仓库会增大约 78 MB）

```bash
# 从服务器同步全量图集
rsync -a <user>@<host>:/media/london_C/alps1/zhangyun/2024-2-19-Asian-GTEx/\
2026-03-30-Somatic/coverage_plot/7_plot_high_score_regulatory_variants/ plots/

# 重新生成索引（不带参数时扫描 assets/plots/）
python3 scripts/build_plots_index.py
```

**方式二：只改基址，图集由 Web 服务托管**（推荐，仓库保持轻量）

先导出服务器上的完整文件清单并生成索引（无需下载 PDF）：

```bash
ssh <user>@<host> "ls -1 /media/london_C/alps1/zhangyun/2024-2-19-Asian-GTEx/\
2026-03-30-Somatic/coverage_plot/7_plot_high_score_regulatory_variants/" > plot_files.txt

python3 scripts/build_plots_index.py plot_files.txt
```

再把 `data/plots_index.js` 顶部的 `window.PLOT_BASE` 改成图集被托管的 URL 前缀，例如：

```js
window.PLOT_BASE = 'https://<your-host>/plots/';
```

这样站点只保留索引，PDF 由 Web 服务直接提供。

## 本地开发

```bash
# 前端（VS Code Live Server 插件，port 5501）—— 入口是 src/ 下的页面
# 或直接 python 静态服务（在项目根跑）
python3 -m http.server 5501        # → http://127.0.0.1:5501/src/index.html

# 后端
python server/server.py --host 0.0.0.0 --port 5502

# Demo 模式（跳过数据依赖）
SOMACARD_DEMO=1 python server/server.py --host 0.0.0.0 --port 5502

# 更新前端数据（只读这一张 CSV，21 列全量）
python3 scripts/build_variants_data.py data_source/variants_website.csv data/variants_data.js

# 更新覆盖度图索引（会顺带读取每张 PDF 的尺寸写入 PLOT_META）
python3 scripts/build_plots_index.py

# 更新 Data Portal 文件清单
python3 scripts/build_genome_data.py

# 重新生成供体页横幅
python3 scripts/build_donors_banner.py > assets/donors-banner.svg

# 构建发布快照
bash scripts/build_publish.sh
```

> `file://` 方式直接打开页面时，浏览器会拦截本地 PDF 跳转，请用上方的静态服务方式预览。

## 数据处理流程

```
服务器：data_source/variants_website.csv（21 列 / 107,852 行，首页搜索的唯一数据源）
  ↓ scripts/build_variants_data.py（字典编码：contig/基因/区域/样本/供体等去重成索引）
data/variants_data.js（8.3 MB，21 列全量）
  ↓ src/index.html 引用
浏览器搜索 / 筛选 / 排序 / 导出 / 打开覆盖度图

服务器：coverage_plot/7_plot_high_score_regulatory_variants/*.pdf
  ↓ scripts/build_plots_index.py（文件名 → 索引键，并读取 MediaBox 记尺寸）
data/plots_index.js（PLOT_BASE + PLOT_KEYS + PLOT_META）

data_source/tissue_genome_data.csv（7,249 行 × 8 列）
  ↓ scripts/build_genome_data.py（离散字段去重成字典 + 行内只存下标）
data/genome_data.js（GDATA + GDATA_STATS，0.59 MB）
  ↓ src/somatic-data.html 引用
筛选 / 排序 / 分页 / 概览数字
```

## Git 历史

```
22ae66c Improve demo annotate output for VCF input
2ac5086 Serve repo static assets and use current host API endpoint
22be10e Add root route to serve index.html on Render
b3e550d Add demo mode, requirements and Procfile for Render demo deployment
9ed31b9 Update website content
72f4740 update website
b4d5003 Initial website upload
```
