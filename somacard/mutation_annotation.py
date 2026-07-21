"""
mutation_annotation.py
=======================

单条突变注释 + 打分（对应 run_score.sh + 1_cCRE_anno_v2.R + 2_score_v2.R 里
score_priority 那部分逻辑），并在每个关键步骤上记录耗时，方便定位瓶颈。

用法：
    result = annotate_mutation("chr1", 1158636, "chr1_1158636_A_G", "Whole_Blood")
    print(result)

    # 批量跑完之后，看哪一步最耗时：
    report_step_times()

命令行用法：
    # 处理 VCF 文件:
    python mutation_annotation.py --input input.vcf.gz --file-type vcf --tissue Whole_Blood -o output.tsv

    # 处理 TXT 文件（组织由 --tissue 指定，可指定多个）:
    python mutation_annotation.py --input input.txt --file-type txt --tissue Whole_Blood Liver -o output.tsv

    # 处理单条/多条 Mutation ID:
    python mutation_annotation.py --mutation-id chr1_1158636_A_G --tissue Whole_Blood

关于 motifbreakR：
    motifbreakR 每次调用都要重新加载 BSgenome / MotifDb 等大型 R 包（几秒到十几秒的固定开销）。
    VCF/TXT/多 mutation-id 批量注释时，本模块会先解析出全部待注释变异、按坐标去重后，
    一次性调用 motifbreakR_query.R 的 --batch 模式算出所有结果，再逐条查表使用——
    整个批次里 R 进程只会启动一次，而不是每条变异启动一次。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import gzip
import subprocess
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache

import pandas as pd

# ──────────────────────────────────────────────────────────────────────────
# 日志配置
# ──────────────────────────────────────────────────────────────────────────
logger = logging.getLogger("mutation_annotation")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)  # 想看每一步的详细耗时就调成 logging.DEBUG

# 全局累计计时：{step_name: {"total": 秒, "count": 次数}}
_STEP_TIMES: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0.0, "count": 0})


@contextmanager
def _timer_ctx(step_name: str, local_times: dict | None = None):
    """给某一段代码计时：既累计进全局 _STEP_TIMES，也可选择性地写进单次调用的 local_times。"""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        _STEP_TIMES[step_name]["total"] += elapsed
        _STEP_TIMES[step_name]["count"] += 1
        if local_times is not None:
            local_times[step_name] = local_times.get(step_name, 0.0) + elapsed
        logger.debug(f"  [{step_name}] {elapsed * 1000:.2f} ms")


def report_step_times(top_n: int | None = None) -> pd.DataFrame:
    """
    汇总打印各步骤的累计耗时排行（降序），用来定位整个批次里最耗时的步骤。
    在跑完一批 annotate_mutation() 之后调用。
    """
    rows = [
        {
            "step": step,
            "total_seconds": round(d["total"], 4),
            "count": d["count"],
            "avg_ms": round(d["total"] / d["count"] * 1000, 2) if d["count"] else 0.0,
        }
        for step, d in _STEP_TIMES.items()
    ]
    df = pd.DataFrame(rows).sort_values("total_seconds", ascending=False).reset_index(drop=True)
    if top_n:
        df = df.head(top_n)
    logger.info("── 各步骤累计耗时排行（降序）──\n" + df.to_string(index=False))
    return df


def reset_step_times() -> None:
    """清空累计计时（比如你想分批统计的时候）。"""
    _STEP_TIMES.clear()


# ──────────────────────────────────────────────────────────────────────────
# 全局路径配置（照抄 run_score.sh / 2_score_v2.R 的硬编码路径，按需修改）
# ──────────────────────────────────────────────────────────────────────────
CONFIG = {
    "TFBS": "/media/iceland/share/Datasets/Archives/luodl/somatic/TF_chip/TF_merged.sorted.bed.gz",
    "TF_motif": "/media/iceland/share/Datasets/Archives/luodl/somatic/motif/TF_motif.sorted.bed.gz",
    "TF_footprint_dir": "/media/iceland/share/Datasets/Archives/luodl/somatic/footprint/tissue",
    "cCRE_bed": "/media/iceland/share/Datasets/Archives/luodl/somatic/cCRE/GRCh38-cCREs.bed.gz",
    "cRE_base": "/media/iceland/share/Datasets/Archives/luodl/somatic/tissue",
    "tss_pos_bed": os.path.expanduser("~/reference/hg38/annotation/tss_pos.bed"),  # 列: tss_pos, gene_name, strand
    "gene_link_dir": "/media/iceland/share/Datasets/Archives/luodl/somatic/gene_link",
    # 同目录下的 motifbreakR 查询脚本；见 _tf_motif_via_motifbreakr() / _tf_motif_via_motifbreakr_batch()
    "motifbreakR_script": os.path.join(os.path.dirname(os.path.abspath(__file__)), "motifbreakR_query.R"),
    "pli_file": "/media/iceland/share/Datasets/Archives/luodl/somatic/gnomad.v2.1.1.lof_metrics.by_gene.txt.bgz",
    "tissue_specific_genes_file": "/media/london_A/kewei/2025.04.16_somatic/Project_SNV/2026.03.09_tissue_specific_genes/tissue_specific_genes.csv",
    "cRE_categories": ["ATAC", "CTCF", "DNase"],
}

TISSUE_ALIAS = {
    "Whole_Blood": "blood",
    "Adrenal_Gland": "adrenal_gland",
    "Gallbladder": "gallbladder",
    "Heart": "heart",
    "Liver": "liver",
    "Muscle": "muscle",
    "Pancreas": "pancreas",
    "Skin": "skin",
}


# 与下游 mutation 表合并时使用的标准化注释字段及固定列顺序。
LINK_COLUMNS = (
    "link_3D-Chromatin",
    #"link_eQTLs",
    "link_ABC",
    "link_rE2G",
    "link_EPIraction",
    "link_GraphRegLR",
    "link_CRISPR",
)

STANDARD_OUTPUT_COLUMNS = (
    "tissue",
    "mutation_key",
    "regulatory_gene",
    "tss_distance",
    "cCRE",
    "cCRE_type",
    "TFBS",
    "TF_motif",
    "TF_footprint",
    "in_ATAC",
    "in_CTCF",
    "in_DNase",
    *LINK_COLUMNS,
    "tissue_enriched_gene",
    "pLI",
    "score_priority",
)


def normalize_tissue(tissue: str) -> str:
    """对应 bash 里的 normalize_tissue()：先做别名替换，再转小写。"""
    return TISSUE_ALIAS.get(tissue, tissue).lower()


def _standardize_annotation_output(row: pd.DataFrame) -> pd.DataFrame:
    """统一下游合并使用的注释列名、链接证据列和输出顺序。"""
    row = row.rename(columns={
        "gene_name": "regulatory_gene",
        "is_ts_driver": "tissue_enriched_gene",
    })
    for column in LINK_COLUMNS:
        if column not in row.columns:
            row[column] = 0
        else:
            row[column] = row[column].fillna(0).astype(int)
    if "tissue_enriched_gene" not in row.columns:
        row["tissue_enriched_gene"] = False
    # 没有匹配到候选靶基因 / TSS距离时，统一写成 "."（而不是空/NaN）
    if "regulatory_gene" in row.columns:
        row["regulatory_gene"] = row["regulatory_gene"].fillna(".")
    else:
        row["regulatory_gene"] = "."
    if "tss_distance" in row.columns:
        row["tss_distance"] = row["tss_distance"].fillna(".")
    else:
        row["tss_distance"] = "."
    if "pLI" in row.columns:
        row["pLI"] = row["pLI"].fillna(".")
    else:
        row["pLI"] = "."
    for column in STANDARD_OUTPUT_COLUMNS:
        if column not in row.columns:
            row[column] = None
    return row.loc[:, STANDARD_OUTPUT_COLUMNS].reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────
# 小工具：使用系统 tabix 命令做索引查询，不依赖 pysam
# ──────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=None)
def _tabix_available() -> bool:
    """检查系统环境中是否可以调用 tabix。"""
    try:
        result = subprocess.run(
            ["tabix", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _fetch_rows(chrom: str, pos: int, bed_file: str) -> list[list[str]]:
    """
    使用系统 tabix 查询 BED.gz 中与 1-based 位置 pos 重叠的记录。

    查询区域写成 chrom:pos-pos。对于标准 BED（0-based, half-open）建立的
    tabix 索引，这与原先 pysam.fetch(chrom, pos-1, pos) 的含义一致。
    """
    if bed_file is None or not os.path.exists(bed_file):
        return []
    if not os.path.exists(bed_file + ".tbi") and not os.path.exists(bed_file + ".csi"):
        logger.warning(f"未找到索引文件 {bed_file}.tbi/.csi，请先使用 tabix -p bed 建索引。")
        return []
    if not _tabix_available():
        raise RuntimeError("系统中未找到 tabix 命令；请先安装 htslib/tabix 并加入 PATH。")

    region = f"{chrom}:{pos}-{pos}"
    result = subprocess.run(
        ["tabix", bed_file, region],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        message = result.stderr.strip() or "unknown tabix error"
        raise RuntimeError(f"tabix 查询失败: {bed_file} {region}: {message}")
    return [line.split("\t") for line in result.stdout.splitlines() if line.strip()]


def _presence(chrom: str, pos: int, bed_file: str) -> int | None:
    """判断该位置是否落在 bed_file 任意区间内；文件不存在时返回 None。"""
    if bed_file is None or not os.path.exists(bed_file):
        return None
    return 1 if _fetch_rows(chrom, pos, bed_file) else 0


def _tail_fields(chrom: str, pos: int, bed_file: str, n_fields: int) -> list[str] | None:
    """取第一条命中 BED 记录的末尾字段，并追加一个模拟 overlap 标记。"""
    if bed_file is None or not os.path.exists(bed_file):
        return None
    rows = _fetch_rows(chrom, pos, bed_file)
    if not rows:
        return ["."] * (n_fields - 1) + ["0"]
    fields = rows[0]
    tail = fields[-(n_fields - 1):] if n_fields > 1 else []
    return tail + ["1"]


def _parse_ref_alt_from_mutation_key(chrom: str, pos: int, mutation_key: str) -> tuple[str | None, str | None]:
    """从形如 {chrom}_{pos}_{ref}_{alt} 的 mutation_key 中解析出 ref/alt（解析失败返回 None, None）。"""
    prefix = f"{chrom}_{pos}_"
    if not mutation_key.startswith(prefix):
        return None, None
    remainder = mutation_key[len(prefix):]
    parts = remainder.split("_")
    if len(parts) != 2:
        return None, None
    ref, alt = parts
    return (ref or None), (alt or None)


def _parse_motifbreakr_tsv(stdout_text: str) -> dict[str, list[str]]:
    """
    解析 motifbreakR_query.R 的 TSV 输出，按 SNP_id 分组，返回
    {SNP_id: [去重后的 geneSymbol 列表]}（没有命中任何记录时返回空 dict）。
    """
    lines = [ln for ln in stdout_text.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return {}

    header = lines[0].split("\t")
    try:
        gene_idx = header.index("geneSymbol")
        snp_idx = header.index("SNP_id")
    except ValueError:
        logger.warning(f"motifbreakR 输出缺少必要列: {header}")
        return {}

    names_per_snp: dict[str, list[str]] = defaultdict(list)
    seen_per_snp: dict[str, set[str]] = defaultdict(set)
    for line in lines[1:]:
        fields = line.split("\t")
        if snp_idx >= len(fields) or gene_idx >= len(fields):
            continue
        sid = fields[snp_idx].strip()
        name = fields[gene_idx].strip()
        if not sid or not name or name == "NA":
            continue
        if name not in seen_per_snp[sid]:
            seen_per_snp[sid].add(name)
            names_per_snp[sid].append(name)
    return names_per_snp


def _tf_motif_via_motifbreakr(chrom: str, pos: int, ref: str, alt: str, config: dict = CONFIG) -> str | None:
    """
    调用同目录下的 motifbreakR_query.R（单条模式），用 motifbreakR 判断该位点是否破坏已知 TF motif。

    只在没有预先算好的批量结果（motif_lookup）可用时才会被调用——正常走 VCF/TXT/
    多 mutation-id 批量流程时，请优先用 _tf_motif_via_motifbreakr_batch()，这个函数
    每次调用都要重新加载 BSgenome/MotifDb 等大型 R 包，单次调用可能要数十秒甚至更久，
    大批量注释时会显著拖慢整体速度。

    R 脚本内部只保留 effect=="strong" & alleleDiff<0 & dataSource=="jaspar2022" 的记录，
    这里再取其中的 geneSymbol，去重、逗号拼接后返回，格式和原来 bed 查询出的 TF_motif 字段一致。
    没有命中任何符合条件的记录时返回 "."；脚本缺失/调用失败/超时时返回 None，
    调用方应在收到 None 时决定是否回退到 bed 查询。
    """
    script = config.get("motifbreakR_script")
    if not script or not os.path.exists(script):
        logger.warning(f"motifbreakR 脚本不存在: {script}，无法用 motifbreakR 识别 TF_motif。")
        return None

    try:
        result = subprocess.run(
            ["Rscript", script, chrom, str(pos), ref, alt],
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
    except FileNotFoundError:
        logger.warning("系统中未找到 Rscript 命令，无法用 motifbreakR 识别 TF_motif。")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"motifbreakR 调用超时: {chrom}:{pos}:{ref}:{alt}")
        return None

    if result.returncode != 0:
        logger.warning(
            f"motifbreakR 调用失败 ({chrom}:{pos}:{ref}:{alt})，returncode={result.returncode}: "
            f"{result.stderr.strip()[-500:]}"
        )
        return None

    names_per_snp = _parse_motifbreakr_tsv(result.stdout)
    if not names_per_snp:
        return "."
    # 单条模式下只会有一个 SNP_id，直接取全部即可
    names: list[str] = []
    seen: set[str] = set()
    for names_list in names_per_snp.values():
        for name in names_list:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return ",".join(names) if names else "."


def _tf_motif_via_motifbreakr_batch(
    variants: list[tuple[str, int, str, str]],
    config: dict = CONFIG,
) -> dict[str, str]:
    """
    一次性用 motifbreakR_query.R 的 --batch 模式对一批变异做 motif 查询，
    整批变异只启动一次 R 进程（避免每条变异都重新加载 BSgenome/MotifDb 等大型
    R 包——那才是逐条调用时真正的耗时大头）。

    参数:
        variants: [(chrom, pos, ref, alt), ...]，重复的会自动去重。

    返回:
        dict: f"{chrom}:{pos}:{ref}:{alt}" -> 逗号拼接的 geneSymbol 字符串。
        对每一个传入的变异都保证有对应的 key；没有命中任何符合条件记录的
        变异，其值为 "."。脚本缺失/调用失败/超时时返回空 dict（调用方应对
        每条变异回退到单条查询或 bed 查询）。
    """
    script = config.get("motifbreakR_script")
    if not script or not os.path.exists(script):
        logger.warning(f"motifbreakR 脚本不存在: {script}，无法用 motifbreakR 批量识别 TF_motif。")
        return {}
    if not variants:
        return {}

    dedup_variants = sorted(set(variants))
    snp_ids = [f"{c}:{p}:{r}:{a}" for c, p, r, a in dedup_variants]

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="motifbreakr_batch_", suffix=".tsv")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            for c, p, r, a in dedup_variants:
                f.write(f"{c}\t{p}\t{r}\t{a}\n")

        try:
            # 批量任务体量可能很大，给足超时时间；R 侧内部已经把并行度控制好了。
            result = subprocess.run(
                ["Rscript", script, "--batch", tmp_path],
                capture_output=True,
                text=True,
                check=False,
                timeout=max(1800, 5 * len(dedup_variants)),
            )
        except FileNotFoundError:
            logger.warning("系统中未找到 Rscript 命令，无法用 motifbreakR 批量识别 TF_motif。")
            return {}
        except subprocess.TimeoutExpired:
            logger.warning(f"motifbreakR 批量调用超时（{len(dedup_variants)} 个变异）")
            return {}

        if result.returncode != 0:
            logger.warning(
                f"motifbreakR 批量调用失败（{len(dedup_variants)} 个变异），"
                f"returncode={result.returncode}: {result.stderr.strip()[-1000:]}"
            )
            return {}

        names_per_snp = _parse_motifbreakr_tsv(result.stdout)
        lookup: dict[str, str] = {}
        for sid in snp_ids:
            names = names_per_snp.get(sid)
            lookup[sid] = ",".join(names) if names else "."
        return lookup
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ──────────────────────────────────────────────────────────────────────────
# 需要预处理一次、可复用的参考文件（缓存，避免每条突变都重新读一遍大文件）
# ──────────────────────────────────────────────────────────────────────────
GENE_LINK_METHODS = (
    "3D-Chromatin",
    "ABC",
    "CRISPR",
    "EPIraction",
    "eQTLs",
    "GraphRegLR",
    "rE2G",
)

# CRISPR 不分组织，用全部数据；其余方法使用组织特异数据。
# 组织特异文件路径形如：
#   {gene_link_dir}/by_tissue/{tissue}/{method}.sorted.bed.gz
# 其中 {tissue} 用原始组织名（如 Adrenal_Gland），不是 normalize_tissue() 之后的别名。
GENE_LINK_TISSUE_SPECIFIC_METHODS = frozenset(GENE_LINK_METHODS) - {"CRISPR"}


def _gene_link_bed_path(method: str, tissue: str) -> str:
    """按方法决定该用全部数据还是组织特异数据的 bed 文件路径。"""
    if method in GENE_LINK_TISSUE_SPECIFIC_METHODS:
        return os.path.join(CONFIG["gene_link_dir"], "by_tissue", tissue, f"{method}.sorted.bed.gz")
    return os.path.join(CONFIG["gene_link_dir"], f"{method}.sorted.bed.gz")


def _fetch_gene_links(chrom: str, pos: int, ccre: str, tissue: str) -> pd.DataFrame:
    """
    按突变坐标从各方法的 Tabix 索引文件查询，再用 cCRE ID 精确匹配。
    不加载旧的全量 Gene-Links 表或 GTF；BED 第五列的 target 直接作为基因名使用。

    CRISPR 使用全部（非组织特异）数据；其余方法（3D-Chromatin / ABC / EPIraction /
    eQTLs / GraphRegLR / rE2G）使用 tissue 对应的组织特异数据。
    """
    records = []

    for method in GENE_LINK_METHODS:
        bed_file = _gene_link_bed_path(method, tissue)
        for fields in _fetch_rows(chrom, pos, bed_file):
            # BED: chrom, start, end, cCRE, comma-separated target genes, details
            if len(fields) < 5 or fields[3] != ccre:
                continue
            for target in fields[4].split(","):
                target = target.strip()
                if not target or target == ".":
                    continue
                records.append((ccre, target, target, method))

    return pd.DataFrame(
        records, columns=["cCRE", "gene_id", "gene_name", "link_type"]
    ).drop_duplicates()


@lru_cache(maxsize=1)
def _load_pli() -> pd.DataFrame:
    return pd.read_csv(
        CONFIG["pli_file"], sep="\t", compression="gzip",
        usecols=["gene", "pLI", "oe_lof", "oe_lof_upper"],
    )


@lru_cache(maxsize=1)
def _load_tss_pos() -> pd.DataFrame:
    df = pd.read_csv(CONFIG["tss_pos_bed"], sep="\t", header=None)
    df = df.iloc[:, [2, 3, 5]]
    df.columns = ["tss_pos", "gene_name", "strand"]
    return df


@lru_cache(maxsize=1)
def _load_ts_gene_tissue() -> pd.DataFrame:
    """
    对应 2_score_v2.R 开头：
        tissue.specific.genes <- fread(...)
        tissue.specific.genes <- tissue.specific.genes[n_strategies >= 2, ]
        ts_gene_tissue <- distinct(gene, ts_tissue = tissue)
    """
    df = pd.read_csv(CONFIG["tissue_specific_genes_file"])
    df = df[df["n_strategies"] >= 2].iloc[:, :3]
    df.columns = ["gene", "tissue", "method"]
    ts = df[["gene", "tissue"]].rename(columns={"tissue": "ts_tissue"}).drop_duplicates()
    return ts


# ──────────────────────────────────────────────────────────────────────────
# 打分逻辑（对应 2_score_v2.R）—— 完全不变
# ──────────────────────────────────────────────────────────────────────────
def _match_tf(a, b) -> bool:
    """对应 R 里的 match_tf()：两个逗号分隔的名字列表是否有交集。"""
    def _empty(x):
        return x is None or (isinstance(x, float) and pd.isna(x)) or str(x) in ("", ".")
    if _empty(a) or _empty(b):
        return False
    set_a = {x.strip() for x in str(a).split(",") if x.strip()}
    set_b = {x.strip() for x in str(b).split(",") if x.strip()}
    return len(set_a & set_b) > 0


def _compute_score(r: dict) -> dict:
    """
    对单行注释结果计算 score_mutation / score_link / score_gene /
    score_tissue_specific / score_priority，逻辑照抄 2_score_v2.R。
    """
    # ── 维度一：突变功能性评分（motif/TFBS/footprint + 开放染色质）──────────
    TF_motif = r.get("TF_motif")
    TFBS = r.get("TFBS")
    TF_footprint = r.get("TF_footprint")

    has_any_motif = TF_motif not in (None, "", ".") and not (isinstance(TF_motif, float) and pd.isna(TF_motif))
    has_any_tfbs = TFBS not in (None, "", ".") and not (isinstance(TFBS, float) and pd.isna(TFBS))
    has_any_fp = TF_footprint not in (None, "", ".") and not (isinstance(TF_footprint, float) and pd.isna(TF_footprint))
    has_matched_tfbs = _match_tf(TF_motif, TFBS)
    has_matched_fp = _match_tf(TF_motif, TF_footprint)
    has_matched_fp_tfbs = _match_tf(TFBS, TF_footprint)

    if has_matched_fp_tfbs and has_matched_tfbs and has_matched_fp and (has_any_motif or has_any_fp or has_any_tfbs):
        motif_tier = 1
    elif has_matched_fp_tfbs or has_matched_tfbs or has_matched_fp:
        motif_tier = 2
    elif has_any_motif or has_any_fp or has_any_tfbs:
        motif_tier = 3
    else:
        motif_tier = 4

    has_open = (r.get("in_ATAC") == 1) or (r.get("in_DNase") == 1)

    if motif_tier == 1 and has_open:
        score_mutation = "M1"
    elif motif_tier == 1:
        score_mutation = "M2"
    elif motif_tier == 2 and has_open:
        score_mutation = "M3"
    elif motif_tier == 2:
        score_mutation = "M4"
    elif motif_tier == 3 and has_open:
        score_mutation = "M5"
    elif has_open:
        score_mutation = "M6"
    elif motif_tier == 3:
        score_mutation = "M7"
    else:
        score_mutation = "M8"

    # ── 维度二：gene-link 评分 ───────────────────────────────────────────────
    def _flag(col):
        v = r.get(col, 0)
        return 0 if v is None or (isinstance(v, float) and pd.isna(v)) else int(v)

    link_CRISPR = _flag("link_CRISPR")
    link_3d = _flag("link_3D-Chromatin")
    link_rE2G = _flag("link_rE2G")
    link_ABC = _flag("link_ABC")
    link_EPIraction = _flag("link_EPIraction")
    link_GraphRegLR = _flag("link_GraphRegLR")

    has_CRISPR = link_CRISPR == 1
    has_3d = link_3d == 1
    has_active = link_rE2G == 1 or link_ABC == 1 or link_EPIraction == 1 or link_GraphRegLR == 1
    n_link = int(has_CRISPR) + int(has_3d) + int(has_active)
    n_compute = link_EPIraction + link_GraphRegLR + link_rE2G + link_ABC

    tss_distance = r.get("tss_distance")
    near_tss = tss_distance is not None and not pd.isna(tss_distance) and abs(tss_distance) <= 2000

    if n_link >= 3 or near_tss:
        score_link = "L1"
    elif n_link >= 2:
        score_link = "L2"
    elif n_compute >= 2:
        score_link = "L3"
    elif n_link >= 1:
        score_link = "L4"
    else:
        score_link = "L5"

    # ── 维度三：基因约束评分（pLI）────────────────────────────────────────────
    pLI = r.get("pLI")
    if pLI is None or (isinstance(pLI, float) and pd.isna(pLI)):
        score_gene = 0
    elif pLI >= 0.9:
        score_gene = 1
    else:
        score_gene = 0

    # ── 组织特异 driver 基因 ────────────────────────────────────────────────
    is_ts_driver = False
    gene_name = r.get("gene_name")
    tissue = r.get("tissue")
    if gene_name and tissue:
        ts = _load_ts_gene_tissue()
        is_ts_driver = not ts[(ts["gene"] == gene_name) & (ts["ts_tissue"] == tissue)].empty
    score_tissue_specific = 1 if is_ts_driver else 0

    # ── 归一化 & 综合优先级 ──────────────────────────────────────────────────
    rank_mutation = int(score_mutation[1:])
    rank_link = int(score_link[1:])
    norm_mutation = 8 - rank_mutation   # M1→7 ... M8→0
    norm_link = 5 - rank_link           # L1→4 ... L5→0
    norm_gene = score_gene

    score_priority = norm_mutation + norm_link + norm_gene + score_tissue_specific

    return {
        "motif_tier": motif_tier,
        "score_mutation": score_mutation,
        "score_link": score_link,
        "score_gene": score_gene,
        "is_ts_driver": is_ts_driver,
        "score_tissue_specific": score_tissue_specific,
        "norm_mutation": norm_mutation,
        "norm_link": norm_link,
        "norm_gene": norm_gene,
        "score_priority": score_priority,
    }


# ──────────────────────────────────────────────────────────────────────────
# 主函数：输入 1 条突变，输出该突变的完整注释 + 打分
# ──────────────────────────────────────────────────────────────────────────
def annotate_mutation(
    chrom: str,
    pos: int,
    mutation_key: str,
    tissue: str,
    config: dict = CONFIG,
    ref: str | None = None,
    alt: str | None = None,
    use_motifbreakr: bool = True,
    motif_lookup: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    输入一条突变，返回标准化的调控注释 + score_priority（DataFrame，可能不止一行——
    当它落在某个 cCRE 上且该 cCRE 连了多个候选靶基因时会展开成多行）。

    use_motifbreakr: 默认 True，即 TF_motif 优先用 motifbreakR 识别；
        传 False 则跳过 motifbreakR，直接用原来的 TF_motif bed 文件查询。
        ref/alt 只在 use_motifbreakr=True 时用得到；不传时会尝试从
        mutation_key（{chrom}_{pos}_{ref}_{alt} 格式）里解析。
    motif_lookup: 可选，预先用 _tf_motif_via_motifbreakr_batch() 批量算好的
        {f"{chrom}:{pos}:{ref}:{alt}": geneSymbol串} 查找表。传入时直接查表，
        不会再为这条突变单独起一次 R 进程；只有查表未命中（理论上不应发生，
        除非传入的变异不在批量结果里）时才会回退到单条 subprocess 调用。
        不传时（None）沿用旧行为：每条突变各自调用一次 motifbreakR。
    """
    t_start = time.perf_counter()
    local_times: dict[str, float] = {}
    logger.info(f"开始处理 mutation_key={mutation_key} tissue={tissue}")

    atac_tissue = normalize_tissue(tissue)
    base = {
        "mutation_key": mutation_key,
        "chrom": chrom,
        "pos": pos,
        "tissue": tissue,
    }

    # ── 1. cRE 注释：ATAC / CTCF / DNase ───────────────────────────────
    with _timer_ctx("cRE_annotation", local_times):
        for anno in config["cRE_categories"]:
            anno_bed = f"{config['cRE_base']}/{anno}/{atac_tissue}.bed.gz"
            base[f"in_{anno}"] = _presence(chrom, pos, anno_bed)

    # ── 2. cCRE 注释 ──────────────────────────────────────────────
    with _timer_ctx("cCRE_annotation", local_times):
        cCRE_bed_gz = config["cCRE_bed"] if config["cCRE_bed"].endswith(".gz") else config["cCRE_bed"] + ".gz"
        fields = _tail_fields(chrom, pos, cCRE_bed_gz, n_fields=4)
        if fields is None:
            base["cCRE"] = "."
            base["cCRE_type"] = "."
            base["in_cCRE"] = 0
        else:
            cCRE_id1, cCRE, cCRE_type, overlap = fields
            base["cCRE"] = "." if cCRE == "." else cCRE
            base["cCRE_type"] = "." if cCRE_type == "." else cCRE_type
            base["in_cCRE"] = 1 if overlap not in ("0", None) else 0

    # ── 3. TF 注释：TFBS（全局）/ motif（全局）/ footprint（组织特异）──
    # 一个位置可能同时落在多条TF记录里（比如多个TF的motif/ChIP-peak重叠），
    # 这里把该bed文件里所有命中记录的TF名字都取出来，去重后用逗号拼接输出，
    # 而不是像原来 _tail_fields() 那样只取第一条命中记录。
    def _tf_hit_all(bed_file: str) -> str | None:
        if bed_file is None or not os.path.exists(bed_file):
            return None
        rows = _fetch_rows(chrom, pos, bed_file)
        if not rows:
            return "."
        names: list[str] = []
        seen: set[str] = set()
        for fields in rows:
            value = fields[-1].strip() if fields else ""
            if not value or value == ".":
                continue
            for part in value.split(","):
                part = part.strip()
                if part and part not in seen:
                    seen.add(part)
                    names.append(part)
        return ",".join(names) if names else "."

    with _timer_ctx("TFBS_annotation", local_times):
        base["TFBS"] = _tf_hit_all(config["TFBS"])
    with _timer_ctx("TF_motif_annotation", local_times):
        motif_value = None
        if use_motifbreakr:
            call_ref, call_alt = ref, alt
            if call_ref is None or call_alt is None:
                call_ref, call_alt = _parse_ref_alt_from_mutation_key(chrom, pos, mutation_key)
            if call_ref is not None and call_alt is not None:
                if motif_lookup is not None:
                    snp_id = f"{chrom}:{pos}:{call_ref}:{call_alt}"
                    motif_value = motif_lookup.get(snp_id)
                    if motif_value is None:
                        logger.warning(
                            f"批量 motifbreakR 结果中未找到 {snp_id}（不应发生），回退到单条查询"
                        )
                        motif_value = _tf_motif_via_motifbreakr(chrom, pos, call_ref, call_alt, config)
                else:
                    motif_value = _tf_motif_via_motifbreakr(chrom, pos, call_ref, call_alt, config)
            else:
                logger.warning(
                    f"无法从 mutation_key={mutation_key} 解析 ref/alt，"
                    f"motifbreakR 识别跳过，回退到 bed 查询。"
                )
        if motif_value is None:
            motif_value = _tf_hit_all(config["TF_motif"])
        base["TF_motif"] = motif_value
    with _timer_ctx("TF_footprint_annotation", local_times):
        footprint_bed = f"{config['TF_footprint_dir']}/{tissue}.sort.bed.gz"  # 用原始 tissue 名，不是 normalize 后的
        footprint_val = _tf_hit_all(footprint_bed)
        if footprint_val and footprint_val != ".":
            footprint_val = footprint_val.replace("-human", "").replace(",_", ",")
        base["TF_footprint"] = footprint_val

    row = pd.DataFrame([base])

    # ── 4. Gene-Link 展开（按 cCRE 关联的候选靶基因，可能一对多）──────
    with _timer_ctx("gene_link_expansion", local_times):
        if base["cCRE"] and base["cCRE"] != ".":
            hits = _fetch_gene_links(chrom, pos, base["cCRE"], tissue)
            if not hits.empty:
                link_types = sorted(hits["link_type"].unique())
                expanded_rows = []
                for gene_name, grp in hits.groupby("gene_name"):
                    rr = row.iloc[0].to_dict()
                    rr["gene_name"] = gene_name
                    rr["gene_id"] = grp["gene_id"].iloc[0]
                    present = set(grp["link_type"])
                    for lt in link_types:
                        rr[f"link_{lt}"] = 1 if lt in present else 0
                    expanded_rows.append(rr)
                row = pd.DataFrame(expanded_rows)
            else:
                row["gene_name"] = None
                row["gene_id"] = None
        else:
            row["gene_name"] = None
            row["gene_id"] = None

    # ── 5. pLI（按 gene_name）───────────────────────────────────────
    with _timer_ctx("pLI_merge", local_times):
        pli = _load_pli()
        row = row.merge(pli, how="left", left_on="gene_name", right_on="gene", suffixes=("", "_pli"))
        if "gene" in row.columns:
            row = row.drop(columns=["gene"])

    # ── 6. TSS distance（按 gene_name 关联预生成 tss_pos_bed）────────
    with _timer_ctx("tss_distance", local_times):
        try:
            tss_pos_df = _load_tss_pos()
            row = row.merge(tss_pos_df, how="left", on="gene_name")
            row["tss_distance"] = row.apply(
                lambda rr: (
                    (rr["tss_pos"] - rr["pos"]) if rr.get("strand") == "-"
                    else (rr["pos"] - rr["tss_pos"])
                )
                if pd.notna(rr.get("tss_pos")) else None,
                axis=1,
            )
        except Exception:
            row["tss_pos"] = None
            row["strand"] = None
            row["tss_distance"] = None

    # ── 7. score_priority（对应 2_score_v2.R）────────────────────────
    with _timer_ctx("score_priority", local_times):
        score_records = [_compute_score(rr) for rr in row.to_dict(orient="records")]
        score_df = pd.DataFrame(score_records)
        row = pd.concat([row.reset_index(drop=True), score_df.reset_index(drop=True)], axis=1)

    row = row.reset_index(drop=True)

    total_elapsed = time.perf_counter() - t_start
    if local_times:
        slowest_step = max(local_times, key=local_times.get)
        logger.info(
            f"完成 mutation_key={mutation_key}，总耗时 {total_elapsed * 1000:.1f} ms，"
            f"最耗时步骤：{slowest_step} ({local_times[slowest_step] * 1000:.1f} ms)"
        )
        for step, elapsed in sorted(local_times.items(), key=lambda kv: -kv[1]):
            logger.debug(f"    - {step}: {elapsed * 1000:.2f} ms")

    return _standardize_annotation_output(row)


# ──────────────────────────────────────────────────────────────────────────
# VCF 批量处理：读取 VCF/VCF.gz/BCF，逐条变异构造 mutation_key，
# 调用 annotate_mutation() 并把结果拼成一张大表。
# ──────────────────────────────────────────────────────────────────────────
def _normalize_vcf_chrom(chrom: str, add_chr_prefix: bool | None) -> str:
    """
    统一VCF里的染色体命名和参考bed文件(chr1/chr2/...)保持一致。
    add_chr_prefix:
        None / True  -> 缺"chr"前缀时自动补上(默认行为，适配大多数只写"1"/"2"的VCF)
        False        -> 原样返回，不做任何改动(VCF本身已是chr1/chr2风格时用这个)
    """
    if add_chr_prefix is False:
        return chrom
    return chrom if chrom.startswith("chr") else f"chr{chrom}"


def _parse_vcf_info(info_text: str) -> dict[str, str | bool]:
    """把 VCF INFO 字段解析成简单字典；flag 型字段的值为 True。"""
    info: dict[str, str | bool] = {}
    if not info_text or info_text == ".":
        return info
    for item in info_text.split(";"):
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            info[key] = value
        else:
            info[item] = True
    return info


def _resolve_variant_tissues(
    chrom: str,
    pos: int,
    info: dict[str, str | bool],
    tissue,
    tissue_info_field: str | None,
) -> list[str]:
    """决定一条 VCF 记录使用的组织列表。"""
    if tissue is not None:
        return [tissue] if isinstance(tissue, str) else list(tissue)

    if tissue_info_field and tissue_info_field in info:
        value = info[tissue_info_field]
        if value is not True:
            tissues = [x.strip() for x in str(value).split(",") if x.strip()]
            if tissues:
                return tissues

    raise ValueError(
        f"无法确定变异 {chrom}:{pos} 的组织来源：既未传入固定 tissue，也未在 "
        f"INFO/{tissue_info_field} 中找到组织信息。"
    )


def _keep_best_annotation(annotated: pd.DataFrame) -> pd.DataFrame:
    """每个 mutation_key + tissue 只保留 score_priority 最高的一条注释。"""
    if annotated.empty:
        return annotated
    n_before = len(annotated)
    annotated = annotated.sort_values(
        ["mutation_key", "tissue", "score_priority"],
        ascending=[True, True, False],
        kind="stable",
    ).drop_duplicates(["mutation_key", "tissue"], keep="first")
    logger.info(f"去重: {n_before:,} 行 -> {len(annotated):,} 行（每个 mutation_key + tissue 保留最高分）")
    return annotated.reset_index(drop=True)


def _parse_mutation_id(mutation_id: str) -> tuple[str, int, str, str, str]:
    """解析 chr_pos_ref_alt 或 chr:pos:ref:alt 格式的 mutation ID。"""
    separator = ":" if mutation_id.count(":") == 3 else "_"
    fields = mutation_id.rsplit(separator, 3)
    if len(fields) != 4:
        raise ValueError(
            f"mutation ID 格式错误: {mutation_id!r}；应为 chr_pos_ref_alt 或 chr:pos:ref:alt"
        )
    chrom, pos_text, ref, alt = fields
    try:
        pos = int(pos_text)
    except ValueError as exc:
        raise ValueError(f"mutation ID 的位置不是整数: {mutation_id!r}") from exc
    chrom = _normalize_vcf_chrom(chrom, add_chr_prefix=True)
    mutation_key = f"{chrom}_{pos}_{ref}_{alt}"
    return chrom, pos, ref, alt, mutation_key


def _build_motif_lookup(
    variants: list[tuple[str, int, str, str]],
    use_motifbreakr: bool,
    config: dict,
) -> dict[str, str] | None:
    """给一批变异（可能带重复）批量算 motifbreakR 结果；use_motifbreakr=False 或列表为空时返回 None。"""
    if not use_motifbreakr or not variants:
        return None
    unique_variants = sorted(set(variants))
    logger.info(f"开始批量调用 motifbreakR，共 {len(unique_variants):,} 个去重后的变异（整批只起一次 R 进程）")
    t_motif = time.perf_counter()
    lookup = _tf_motif_via_motifbreakr_batch(unique_variants, config)
    n_hit = sum(1 for v in lookup.values() if v not in (None, "."))
    logger.info(
        f"motifbreakR 批量调用完成，耗时 {time.perf_counter() - t_motif:.1f}s，"
        f"{n_hit:,}/{len(unique_variants):,} 个变异命中 strong+jaspar2022 motif"
    )
    return lookup


def annotate_mutation_ids(
    mutation_ids: list[str],
    tissue: str | list[str],
    deduplicate: bool = True,
    config: dict = CONFIG,
    use_motifbreakr: bool = True,
) -> pd.DataFrame:
    """批量注释 mutation ID；每个 ID 可以对一个或多个组织分别运行。"""
    tissues = [tissue] if isinstance(tissue, str) else list(tissue)
    parsed = [_parse_mutation_id(mid) for mid in mutation_ids]  # (chrom,pos,ref,alt,mutation_key)

    motif_lookup = _build_motif_lookup(
        [(c, p, r, a) for c, p, r, a, _ in parsed], use_motifbreakr, config
    )

    all_rows: list[pd.DataFrame] = []
    for chrom, pos, ref, alt, mutation_key in parsed:
        for current_tissue in tissues:
            all_rows.append(
                annotate_mutation(
                    chrom, pos, mutation_key, current_tissue, config,
                    ref=ref, alt=alt, use_motifbreakr=use_motifbreakr,
                    motif_lookup=motif_lookup,
                )
            )
    annotated = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame(columns=STANDARD_OUTPUT_COLUMNS)
    return _keep_best_annotation(annotated) if deduplicate else annotated


def annotate_txt(
    txt_path: str,
    tissue: str | list[str],
    output_path: str | None = None,
    add_chr_prefix: bool | None = None,
    deduplicate: bool = True,
    config: dict = CONFIG,
    use_motifbreakr: bool = True,
) -> pd.DataFrame:
    """
    读取固定格式的制表符分隔 TXT 文件并批量注释。

    文件必须包含表头，且恰好使用以下 4 列（列顺序固定）：
        chrom    pos    ref    alt

    每一行表示一个变异；pos 必须为 1-based 整数坐标。
    组织不从 TXT 文件读取，必须通过 tissue 参数指定；可一次指定一个或多个组织。
    每个变异会在每个指定组织中分别进行注释。
    """
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"找不到TXT文件: {txt_path}")

    tissues = [tissue] if isinstance(tissue, str) else list(tissue)
    if not tissues:
        raise ValueError("TXT注释必须至少指定一个组织")
    invalid_tissues = [x for x in tissues if x not in TISSUE_ALIAS]
    if invalid_tissues:
        raise ValueError(
            f"不支持的 tissue: {', '.join(invalid_tissues)}；"
            f"可选值: {', '.join(sorted(TISSUE_ALIAS))}"
        )

    required_columns = ["chrom", "pos", "ref", "alt"]
    df = pd.read_csv(txt_path, sep="\t", dtype=str, comment="#")
    if list(df.columns) != required_columns:
        raise ValueError(
            "TXT输入格式错误：必须是制表符分隔、包含表头，且列顺序严格为 "
            + "\t".join(required_columns)
            + f"；当前列为: {list(df.columns)}"
        )

    # ── 先把所有行解析好，收集待注释的变异，供后面一次性批量 motifbreakR 用 ──
    parsed: list[tuple[str, int, str, str, str]] = []  # (chrom, pos, ref, alt, mutation_key)
    for line_no, rr in enumerate(df.itertuples(index=False), start=2):
        try:
            chrom = _normalize_vcf_chrom(str(rr.chrom).strip(), add_chr_prefix)
            pos = int(str(rr.pos).strip())
            ref = str(rr.ref).strip()
            alt = str(rr.alt).strip()
            if not all((chrom, ref, alt)):
                raise ValueError("存在空字段")
            mutation_key = f"{chrom}_{pos}_{ref}_{alt}"
            parsed.append((chrom, pos, ref, alt, mutation_key))
        except Exception as exc:
            raise ValueError(f"TXT第 {line_no} 行解析失败: {exc}") from exc

    motif_lookup = _build_motif_lookup(
        [(c, p, r, a) for c, p, r, a, _ in parsed], use_motifbreakr, config
    )

    all_rows: list[pd.DataFrame] = []
    for chrom, pos, ref, alt, mutation_key in parsed:
        for current_tissue in tissues:
            try:
                all_rows.append(
                    annotate_mutation(
                        chrom, pos, mutation_key, current_tissue, config=config,
                        ref=ref, alt=alt, use_motifbreakr=use_motifbreakr,
                        motif_lookup=motif_lookup,
                    )
                )
            except Exception as exc:
                raise ValueError(f"变异 {mutation_key} 注释失败: {exc}") from exc

    annotated = (
        pd.concat(all_rows, ignore_index=True)
        if all_rows else pd.DataFrame(columns=STANDARD_OUTPUT_COLUMNS)
    )
    if deduplicate:
        annotated = _keep_best_annotation(annotated)
    if output_path:
        annotated.to_csv(output_path, sep="\t", index=False)
        logger.info(f"[write] 已写入: {output_path}")
    return annotated


def _open_text_auto(path: str):
    """按扩展名自动打开普通文本或 gzip/bgzip 压缩文本。"""
    if path.endswith((".gz", ".bgz")):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def annotate_vcf(
    vcf_path: str,
    tissue: str | list[str] | None = None,
    tissue_info_field: str | None = "TISSUE",
    output_path: str | None = None,
    add_chr_prefix: bool | None = None,
    skip_filtered: bool = True,
    skip_symbolic_alt: bool = True,
    deduplicate: bool = True,
    config: dict = CONFIG,
    progress_every: int = 1000,
    use_motifbreakr: bool = True,
) -> pd.DataFrame:
    """
    读取 VCF 或 VCF.gz 文本文件，不依赖 pysam。

    注意：该实现不支持 BCF，因为 BCF 是二进制格式。若输入为 BCF，请先运行：
        bcftools view input.bcf -Oz -o input.vcf.gz

    实现分两遍：
      第一遍只解析 VCF、收集所有待注释的 (chrom, pos, ref, alt, mutation_key, tissues)，
      不做任何耗时的注释查询；解析完之后按坐标去重，一次性批量调用 motifbreakR
      （而不是每条变异都单独起一次 R 进程重新加载包/基因组/MotifDb，那才是真正的
      耗时大头）。
      第二遍才真正调用 annotate_mutation() 做逐条注释，TF_motif 直接从批量结果里
      查表，不会再触发额外的 R 进程。
    """
    if not os.path.exists(vcf_path):
        raise FileNotFoundError(f"找不到VCF文件: {vcf_path}")
    if vcf_path.lower().endswith(".bcf"):
        raise ValueError("当前无 pysam 版本不支持 BCF；请先用 bcftools view 转为 VCF/VCF.gz。")

    t_start = time.perf_counter()
    logger.info(f"开始读取VCF文件: {vcf_path}")
    n_records = 0
    n_variants_attempted = 0
    n_skipped_filtered = n_skipped_symbolic = n_errors = 0

    # ── 第一遍：只解析，不注释 ──────────────────────────────────────
    pending: list[tuple[str, int, str, str, str, list[str]]] = []  # (chrom,pos,ref,alt,mutation_key,tissues)

    with _open_text_auto(vcf_path) as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line or line.startswith("#"):
                continue
            n_records += 1
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 7:
                n_errors += 1
                logger.warning(f"VCF第 {line_no} 行列数不足8列，已跳过")
                continue

            if len(fields) < 8:
                chrom_raw, pos_text, _id, ref, alt_text, _qual, filter_text = fields[:7]
                info_text = ""
            else:
                chrom_raw, pos_text, _id, ref, alt_text, _qual, filter_text, info_text = fields[:8]

            try:
                pos = int(pos_text)
            except ValueError:
                n_errors += 1
                logger.warning(f"VCF第 {line_no} 行 POS 不是整数，已跳过")
                continue

            if skip_filtered and filter_text not in ("PASS", ".", ""):
                n_skipped_filtered += 1
                continue

            chrom = _normalize_vcf_chrom(chrom_raw, add_chr_prefix)
            info = _parse_vcf_info(info_text)
            try:
                variant_tissues = _resolve_variant_tissues(
                    chrom, pos, info, tissue, tissue_info_field
                )
            except ValueError as exc:
                logger.warning(str(exc))
                n_errors += 1
                continue

            for alt in alt_text.split(","):
                alt = alt.strip()
                if skip_symbolic_alt and (
                    not alt or alt.startswith("<") or alt == "*" or "[" in alt or "]" in alt
                ):
                    n_skipped_symbolic += 1
                    continue
                mutation_key = f"{chrom}_{pos}_{ref}_{alt}"
                pending.append((chrom, pos, ref, alt, mutation_key, variant_tissues))

            if progress_every and n_records % progress_every == 0:
                elapsed = time.perf_counter() - t_start
                logger.info(f"...已解析VCF {n_records:,} 条记录，耗时 {elapsed:.1f}s")

    logger.info(
        f"VCF解析完成，共 {n_records:,} 条记录，待注释变异条目 {len(pending):,} 个，"
        f"耗时 {time.perf_counter() - t_start:.1f}s"
    )

    # ── 批量 motifbreakR：对所有 pending 变异（按 chrom/pos/ref/alt 去重）一次性查询 ──
    motif_lookup = _build_motif_lookup(
        [(c, p, r, a) for c, p, r, a, _mk, _ts in pending], use_motifbreakr, config
    )

    # ── 第二遍：逐条真正注释（TF_motif 直接查表，不再起 R 进程）──────────
    all_rows: list[pd.DataFrame] = []
    t_annotate = time.perf_counter()
    for idx, (chrom, pos, ref, alt, mutation_key, variant_tissues) in enumerate(pending, start=1):
        for current_tissue in variant_tissues:
            n_variants_attempted += 1
            try:
                all_rows.append(
                    annotate_mutation(
                        chrom, pos, mutation_key, current_tissue, config=config,
                        ref=ref, alt=alt, use_motifbreakr=use_motifbreakr,
                        motif_lookup=motif_lookup,
                    )
                )
            except Exception:
                n_errors += 1
                logger.exception(
                    f"注释失败，跳过该条: mutation_key={mutation_key} tissue={current_tissue}"
                )
        if progress_every and idx % progress_every == 0:
            elapsed = time.perf_counter() - t_annotate
            logger.info(f"...已注释 {idx:,}/{len(pending):,} 个变异条目，耗时 {elapsed:.1f}s")

    annotated = (
        pd.concat(all_rows, ignore_index=True)
        if all_rows else pd.DataFrame(columns=STANDARD_OUTPUT_COLUMNS)
    )
    if deduplicate:
        annotated = _keep_best_annotation(annotated)

    total_elapsed = time.perf_counter() - t_start
    logger.info(
        f"[done] VCF处理完成: {vcf_path}\n"
        f"  VCF记录总数: {n_records:,}\n"
        f"  跳过(未通过FILTER): {n_skipped_filtered:,}\n"
        f"  跳过(符号型ALT): {n_skipped_symbolic:,}\n"
        f"  尝试注释的(变异x组织)组合数: {n_variants_attempted:,}\n"
        f"  失败/异常数: {n_errors:,}\n"
        f"  最终输出行数: {len(annotated):,}\n"
        f"  总耗时: {total_elapsed:.1f}s"
    )
    if output_path:
        annotated.to_csv(output_path, sep="\t", index=False)
        logger.info(f"[write] 已写入: {output_path}")
    return annotated


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Annotate regulatory evidence for somatic variants and calculate score_priority by tissue.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Input formats:

1) VCF or TXT input via --input & --file-type
   - For VCF (--file-type vcf): require --tissue.
   - For TXT (--file-type txt): fixed columns (chrom, pos, ref, alt); require --tissue.
     Multiple tissues may be specified, and each variant is annotated in every tissue.

2) Mutation ID input
   Use --mutation-id together with --tissue. IDs may be chr_pos_ref_alt or chr:pos:ref:alt.

Examples:
  %(prog)s --input variants.vcf.gz --file-type vcf --tissue Whole_Blood --output annotation.tsv
  %(prog)s --input variants.txt --file-type txt --tissue Whole_Blood Liver --output annotation.tsv
  %(prog)s --mutation-id chr1_1158636_A_G --tissue Liver
""",
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", metavar="FILE", help="Input file path (VCF/VCF.gz or TXT; BCF is not supported)")
    input_group.add_argument(
        "--mutation-id", nargs="+", metavar="ID",
        help="One or more mutation IDs in chr_pos_ref_alt or chr:pos:ref:alt format",
    )
    
    parser.add_argument(
        "--file-type", choices=["vcf", "txt"],
        help="Type of the file supplied to --input (vcf or txt); vcf supports .vcf/.vcf.gz",
    )
    parser.add_argument(
        "--tissue", nargs="+", choices=sorted(TISSUE_ALIAS), metavar="TISSUE",
        help="One or more tissues for VCF, TXT, or --mutation-id. Choices: " + ", ".join(sorted(TISSUE_ALIAS)),
    )
    parser.add_argument("-o", "--output", metavar="TSV", help="Output TSV file; write to standard output when omitted")
    parser.add_argument("--keep-all", action="store_true", help="Keep all candidate-gene rows instead of retaining the highest score per mutation ID and tissue")
    parser.add_argument("--include-filtered", action="store_true", help="Include VCF records with FILTER values other than PASS")
    parser.add_argument("--keep-symbolic-alt", action="store_true", help="Include symbolic ALT alleles")
    parser.add_argument("--no-chr-prefix", action="store_true", help="Do not automatically convert chromosome 1 to chr1")
    parser.add_argument(
        "--no-motifbreakr", action="store_true",
        help="Disable motifbreakR-based TF_motif identification and fall back to the static TF_motif bed file "
             "(motifbreakR is used by default)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed timing and diagnostic logs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    tissues = args.tissue
    use_motifbreakr = not args.no_motifbreakr

    try:
        if args.input:
            if not args.file_type:
                parser.error("使用 --input 时必须同时指定 --file-type (vcf 或 txt)")
            
            if args.file_type == "txt":
                if not tissues:
                    raise ValueError("使用 --file-type txt 时必须同时指定 --tissue，可指定一个或多个组织")
                result = annotate_txt(
                    args.input,
                    tissue=tissues,
                    output_path=None,
                    add_chr_prefix=False if args.no_chr_prefix else None,
                    deduplicate=not args.keep_all,
                    use_motifbreakr=use_motifbreakr,
                )
            elif args.file_type == "vcf":
                if not tissues:
                    raise ValueError("使用 --file-type vcf 时必须同时指定 --tissue")
                result = annotate_vcf(
                    args.input,
                    tissue=tissues,
                    output_path=None,
                    add_chr_prefix=False if args.no_chr_prefix else None,
                    skip_filtered=not args.include_filtered,
                    skip_symbolic_alt=not args.keep_symbolic_alt,
                    deduplicate=not args.keep_all,
                    use_motifbreakr=use_motifbreakr,
                )
        else:
            if args.file_type:
                logger.warning("--file-type 参数仅在配合 --input 时生效，将被忽略")
            if not tissues:
                raise ValueError("使用 --mutation-id 时必须同时指定 --tissue")
            result = annotate_mutation_ids(
                args.mutation_id, tissue=tissues, deduplicate=not args.keep_all,
                use_motifbreakr=use_motifbreakr,
            )
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error(str(exc))
        return 2

    if args.output:
        result.to_csv(args.output, sep="\t", index=False)
        logger.info(f"结果已写入: {args.output}")
    else:
        result.to_csv(sys.stdout, sep="\t", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

    