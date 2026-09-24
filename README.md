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
│   └── somacard.html               # SomaCard 突变注释（调 server/ 的后端 API）
├── assets/                         # 静态资源（CSS / 图片 / 图标 / 字体）
│   ├── site.css                    # 全站共享设计系统
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
| Individuals | 160 | 与 Data Portal 的 160 供体一致 |
| Tissues | 33 | 与 Data Portal 的 33 组织一致 |
| Short-read WGS | 300x | |
| PacBio HiFi WGS | 40x | 原标签是 `Long-read`，2026-09-24 改为 `WGS` |
| Somatic variants | 107,852 | 由 `data/variants_data.js` 的实际行数注入（`#statVariants`） |

> ⚠️ **口径说明**：搜索用的变异数据（`data/variants_data.js`）只覆盖 **68 供体 / 30 组织 / 107,852 条**，
> 与统计条和 Data Portal 的 160 / 33 **不是同一批样本**（前者是「有体细胞变异检出」的样本，
> 后者是全部测序样本）。2026-09-24 luo 明确：**搜索就以
> `…/2026.07.15_website/variants_website.csv` 这一张表为准**（本地副本与其逐字节相同），
> 不再从其它表拼接字段。所以这里的 68/30 是**预期值**，不是待修的 bug。

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
- `Download` 导出的 CSV/TSV **列名与取值与源表完全一致**（`contig`/`pos`/…/`regulatory_score`），
  可直接和 `variants_website.csv` 对回去
- 表格 `min-width: 2180px`，窄屏横向滚动（`.table-wrap` 本来就是 `overflow-x:auto`）
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

**下载结果**：`Reset Filters` 左边的 `Download` 按钮提供 CSV / TSV 两种格式，导出的是
**当前搜索 + 筛选后的全部结果**（不只是当前这一页）。列名与取值**与源表完全一致**，
就是 `variants_website.csv` 的 21 列：
`contig / pos / ref / alt / depth / vaf / mutation_type / TiTv / trinucleotide / gene_symbol /
region / sample / donor / tissue / ref_origin / tissue_shared / infiltration_pp / infiltration /
cosmic_signature / CADD_PHRED / regulatory_score`，
文件名形如 `GTOP_somatic_mutations_20260924-1432.csv`。导出带 UTF-8 BOM，Excel 直接打开不乱码。

排序与筛选叠加时，筛选后**保持当前排序**（否则表头箭头还亮着、行却是乱序的）。
顺带修了一个老问题：表头排序箭头以前在 HTML 里写死成 `fa-sort`、JS 从不更新，
现在会随排序列和方向变成 `fa-sort-up` / `fa-sort-down` 并染成主色。

### Browse by Tissue
30 个组织卡片（图标 + 名称）：Esophagus, Trachea, Lung Apex, Lung Base,
Diaphragm, Liver, Gallbladder, Adrenal Gland, Muscle, Stomach,
Pancreas Head/Body/Tail, Small Intestine, Colon, Thoracic Aorta, Aortic Arch,
Heart Right/Left Atrium/Ventricle, Heart Mitral/Tricuspid Valve,
Spleen, Skin, Ovary, Uterus, Adipose, Common Iliac Artery, Whole Blood.

点击卡片跳转搜索该组织的所有突变。

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
数据托管在 `https://cloud.smart-nbc.org.cn/`（访问受控，需申请）。

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

**表格列**（9 列，`table-layout: fixed`）：`Lock | File | Donor | Tissue | Assay | Platform |
Format | Size | UUID`。

- 组织名展示时把下划线换成空格（`Whole_Blood` → `Whole Blood`），供体去掉 `GTOP-` 前缀。
- **文件名完整显示、不截断**（`.with-uuid td.cell-file a` 改成 `white-space: normal` +
  `word-break: break-all`），点击跳到云平台 `https://cloud.smart-nbc.org.cn/`（新标签页）。
- `UUID` 列在最后一列，36 字符按连字符折成两行，用等宽字体。
- `Size` 按 MB/GB/TB 自动换算（≥1024 MB 显示 GB，≥1024 GB 显示 TB）。
- 除 Lock 列外每列都可点击排序（首次升序、再点降序，表头箭头同步）。

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
  min-content 被表格的 `min-width: 880px` 撑开，连带左侧筛选栏一起把页面顶出横向滚动条
  （768px 下溢出 147px）。改成 `minmax(0, 1fr)` 后由 `.table-wrap` 自己横向滚动。
  该规则只有本页用到。
- 列表有 7,249 行，滚动后筛选栏会移出视口，因此双栏（≥981px）下给 `aside` 加了吸顶。

### 布局容器宽度

`.container` 的 `max-width` 由 **1200px 调到 1440px**，对齐线上生产站 `https://bioinfo.szbl.ac.cn/GTOP/`
的 `max-w-(--ui-container)`（实测 1440px，1920 视口下两侧各留 236px）。同时补了一条
`@media (min-width: 1440px) { .container { padding: 0 32px } }`，让大屏下的左右留白和线上的
`lg:px-8` 一致——两者叠加后内容区正好 1376px，与线上完全相同。

起因是 Data Portal 的 `File` 列太窄（1200px 容器下只有约 200px），长文件名被压得很难看。
放宽后实测：

| 视口 | 容器 | 首页表格 | Data Portal 表格区 | File 列 |
|---|---|---|---|---|
| 1920 | 1440 | 1374 | 1116 | 422 |
| 1440 | 1431 | 1365 | 1107 | 413 |
| 1280 | 1271 | 1221 | 963 | 269 |

`≤1248px` 的视口不受影响（`1200 + 24×2` 都没到，容器本来就是流式的）。
`.container-wide` 同步抬到 1560px，保持「wide > 默认」的语义（该 class 目前无人使用）。

改完重跑了 5 页 × 6 宽度（1440/1200/980/768/480/375）走查，**0 控制台错误、0 横向溢出**。

## SomaCard Annotation

输入突变列表（TXT 或 VCF），选取组织，后端调用 `mutation_annotation.py`
进行调控元注释和优先级打分，结果以表格展示并可下载 TSV。

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
未命中 → 描边弱化的按钮，点击改为弹出该变异的详情侧栏，并提示
`No coverage plot available for this variant.`

详情侧栏（点击表格任意一行打开）底部同样有 **View coverage plot** 入口，走同一个弹窗。

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
