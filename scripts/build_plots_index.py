#!/usr/bin/env python3
"""生成覆盖度图（coverage plot）索引 plots_index.js。

站点里只放少量示例 PDF，完整图集存放在服务器：
  /media/london_C/alps1/zhangyun/2024-2-19-Asian-GTEx/2026-03-30-Somatic/coverage_plot/7_plot_high_score_regulatory_variants/

文件名规则（PDF）：
  <供体>-<组织>-<chr><位置>-<ref>-<alt>.pdf
  例：AJ221-Heart_Tricuspid_Valve-chr10-106826223-C-A.pdf
  注意组织名用下划线，且必须与 variants_data.js 里 tissues 数组的写法一致。

用法：
  # 只扫描本地 plots/ 目录（默认）
  python3 scripts/build_plots_index.py

  # 用服务器上的完整文件清单（从远端 ls 导出到文本）生成完整索引
  ssh <host> "ls -1 <远端目录>" > plot_files.txt
  python3 scripts/build_plots_index.py plot_files.txt
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent      # scripts/
PROJECT = ROOT.parent                                # 项目根
OUT = PROJECT / "data" / "plots_index.js"

MEDIABOX = re.compile(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]")


def page_size(path: pathlib.Path) -> tuple[float, float] | None:
    """读出 PDF 第一页的 MediaBox 宽高，用于让弹窗按图的比例自适应。"""
    try:
        head = path.open("rb").read(4096)
    except OSError:
        return None
    m = MEDIABOX.search(head)
    if not m:
        return None
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    w, h = x1 - x0, y1 - y0
    return (w, h) if w > 0 and h > 0 else None


def key_of(filename: str) -> str | None:
    """把 PDF 文件名转成索引键 donor|tissue|chr|pos|ref|alt"""
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    parts = stem.rsplit("-", 4)
    if len(parts) != 5:
        return None
    head, chrom, pos, ref, alt = parts
    if not chrom.startswith("chr") or not pos.isdigit():
        return None
    if "-" not in head:
        return None
    donor, tissue = head.split("-", 1)
    return f"{donor}|{tissue}|{chrom}|{pos}|{ref}|{alt}"


def collect() -> tuple[list[str], dict[str, tuple[float, float]]]:
    """返回 (索引键列表, {键: (宽, 高)})。尺寸只有本地有文件时才能读到。"""
    if len(sys.argv) > 1:
        listing = pathlib.Path(sys.argv[1])
        names = [l.strip() for l in listing.read_text().splitlines() if l.strip()]
        src = f"清单 {listing}"
        local = None
    else:
        files = sorted((PROJECT / "assets" / "plots").glob("*.pdf"))
        names = [p.name for p in files]
        src = "assets/plots/"
        local = {p.name: p for p in files}

    keys, sizes = set(), {}
    for n in names:
        k = key_of(n)
        if not k:
            continue
        keys.add(k)
        if local and n in local:
            sz = page_size(local[n])
            if sz:
                sizes[k] = sz
    print(f"来源 {src}：文件 {len(names)} 个 → 有效索引 {len(keys)} 条，"
          f"含尺寸 {len(sizes)} 条", file=sys.stderr)
    return sorted(keys), sizes


def main() -> None:
    keys, sizes = collect()
    body = ",\n".join(f'"{k}"' for k in keys)
    meta = ",\n".join(f'"{k}":[{w:.1f},{h:.1f}]' for k, (w, h) in sorted(sizes.items()))
    OUT.write_text(
        "/* 自动生成，请勿手改。生成脚本: build_plots_index.py\n"
        "   完整图集路径见 README「覆盖度图（Coverage plots）」一节。 */\n"
        "window.PLOT_BASE = '../assets/plots/';\n"
        "window.PLOT_KEYS = new Set([\n" + body + "\n]);\n"
        "/* 每张图的原始宽高（PDF MediaBox），弹窗按此比例自适应 */\n"
        "window.PLOT_META = {\n" + meta + "\n};\n"
    )
    print(f"输出 {OUT.name}（{OUT.stat().st_size} 字节）", file=sys.stderr)


if __name__ == "__main__":
    main()
