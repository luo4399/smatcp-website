#!/usr/bin/env python3
"""
从 tissue_genome_data.csv 生成 data portal（somatic-data.html）用的紧凑数据文件 genome_data.js。

CSV 原始列：
  Donor, Experimental assay, Sequencing platform, Tissue, Data format,
  File name, File size (MB), UUID v4

输出结构（字典编码，行内只放整数下标，减小体积）：
  window.GDATA = {
    donors:    ["AJ221", ...],          // 去掉 "GTOP-" 前缀，便于窄列显示
    tissues:   ["Adrenal_Gland", ...],
    assays:    ["RNA-seq", "WGS"],
    platforms: ["DNBSEQ-T7", ...],
    formats:   ["bam", ...],
    rows: [[di, ai, pi, ti, fi, sizeMB, "file name", "uuid"], ...]
  };
  window.GDATA_STATS = { files, donors, tissues, totalMB, generated };

用法:
  python3 scripts/build_genome_data.py [输入.csv] [输出.js]
"""
import csv
import json
import pathlib
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent      # scripts/
PROJECT = ROOT.parent                                # 项目根
DEFAULT_CSV = PROJECT / "data_source" / "tissue_genome_data.csv"
DEFAULT_OUT = PROJECT / "data" / "genome_data.js"

COLS = ["Donor", "Experimental assay", "Sequencing platform", "Tissue",
        "Data format", "File name", "File size (MB)", "UUID v4"]


def main(src: pathlib.Path, out: pathlib.Path) -> None:
    raw = []
    # utf-8-sig：源 CSV 带 BOM，直接按 utf-8 读会让首列名变成 "\ufeffDonor"
    with open(src, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"CSV 缺少列: {missing}\n实际列: {reader.fieldnames}")
        for r in reader:
            raw.append(tuple((r[c] or "").strip() for c in COLS))

    # 去重并按字母序固定下来，保证每次生成的 JS 一致（便于 diff）
    def uniq(values):
        return sorted({v for v in values if v})

    donors = uniq(r[0][5:] if r[0].startswith("GTOP-") else r[0] for r in raw)
    assays = uniq(r[1] for r in raw)
    platforms = uniq(r[2] for r in raw)
    tissues = uniq(r[3] for r in raw)
    formats = uniq(r[4] for r in raw)

    di = {v: i for i, v in enumerate(donors)}
    ai = {v: i for i, v in enumerate(assays)}
    pi = {v: i for i, v in enumerate(platforms)}
    ti = {v: i for i, v in enumerate(tissues)}
    fi = {v: i for i, v in enumerate(formats)}

    rows = []
    skipped = 0
    total_mb = 0.0
    for donor, assay, platform, tissue, fmt, name, size, uuid in raw:
        code = donor[5:] if donor.startswith("GTOP-") else donor
        if code not in di or tissue not in ti or not name:
            skipped += 1
            continue
        try:
            mb = round(float(size), 1)
        except ValueError:
            mb = None
        else:
            total_mb += mb
        rows.append([di[code], ai.get(assay, 0), pi.get(platform, 0), ti[tissue],
                     fi.get(fmt, 0), mb, name, uuid])

    rows.sort(key=lambda r: (r[0], r[3], r[2], r[1], r[6]))

    payload = {
        "donors": donors,
        "tissues": tissues,
        "assays": assays,
        "platforms": platforms,
        "formats": formats,
        "rows": rows,
    }
    stats = {
        "files": len(rows),
        "donors": len(donors),
        "tissues": len(tissues),
        "totalMB": round(total_mb, 1),
        "generated": date.today().isoformat(),
    }

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    js = (
        "/* 自动生成，请勿手改。源: tissue_genome_data.csv\n"
        "   生成脚本: build_genome_data.py */\n"
        "window.GDATA=" + body + ";\n"
        "window.GDATA_STATS=" + json.dumps(stats, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )
    out.write_text(js, encoding="utf-8")

    print(f"文件 {len(rows):,} 行（跳过 {skipped} 行）")
    print(f"供体 {len(donors)} / 组织 {len(tissues)} / 实验 {len(assays)} / 平台 {len(platforms)} / 格式 {len(formats)}")
    print(f"总体积 {total_mb / 1024 / 1024:.1f} TB")
    print(f"输出 {out.name}  {out.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV,
         pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT)
