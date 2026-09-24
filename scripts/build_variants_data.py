#!/usr/bin/env python3
"""
从 variants_website.csv 生成网站首页搜索用的紧凑数据文件 data/variants_data.js。

**唯一数据来源**：
  /media/london_A/kewei/2025.04.16_somatic/Project_SNV/2026.07.15_website/variants_website.csv
  （本地副本 data_source/variants_website.csv，md5 与服务器一致）

CSV 的 21 列全部保留、全部输出，不加任何来自其它文件的信息
（曾经拼进来的 Age / Sex 来自 2025.11.19.select_sample.xlsx，已移除 —— 混两个来源会误导读者）。

用法:
  python3 scripts/build_variants_data.py <variants_website.csv> <输出 data/variants_data.js>
"""
import csv
import json
import re
import sys
from pathlib import Path

# CSV 列 → 输出字段。顺序即页面上从左到右的展示顺序。
# 前 3 类编码方式不同：
#   dict  = 低/中基数字符串，存成字典下标（省体积）
#   num   = 数值，直接存（可指定小数位）
#   bool  = TRUE/FALSE，存 0/1
FIELDS = [
    # name                kind   精度
    ('contig',           'dict', None),
    ('pos',              'int',  None),
    ('ref',              'raw',  None),
    ('alt',              'raw',  None),
    ('depth',            'int',  None),
    ('vaf',              'num',  6),
    ('mutation_type',    'dict', None),
    ('TiTv',             'dict', None),
    ('trinucleotide',    'dict', None),
    ('gene_symbol',      'dict', None),
    ('region',           'dict', None),
    ('sample',           'dict', None),
    ('donor',            'dict', None),
    ('tissue',           'dict', None),
    ('ref_origin',       'dict', None),
    ('tissue_shared',    'bool', None),
    ('infiltration_pp',  'num',  4),
    ('infiltration',     'bool', None),
    ('cosmic_signature', 'dict', None),
    ('CADD_PHRED',       'num',  3),
    ('regulatory_score', 'int',  None),
]


def clean_donor(v):
    """CSV 里的 donor 是 'GTOP-GTOP-AK231' 这种重复前缀，取最后一段。"""
    return (v or '').split('-')[-1]


_CHR_FIXED = {'X': 23, 'Y': 24, 'M': 25, 'MT': 25}


def contig_rank(c):
    """自然染色体顺序：chr1..chr22, chrX, chrY, chrM，其它排最后。"""
    m = re.match(r'^chr(\d+)$', c)
    if m:
        return (0, int(m.group(1)), '')
    m = re.match(r'^chr([XYM]|MT)$', c)
    if m:
        return (0, _CHR_FIXED[m.group(1)], '')
    return (1, 0, c)


def as_num(v, nd):
    s = (v or '').strip()
    if not s:
        return None
    try:
        x = float(s)
    except ValueError:
        return None
    return round(x, nd) if nd is not None else x


def as_int(v):
    s = (v or '').strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def as_bool(v):
    s = (v or '').strip().upper()
    if s == 'TRUE':
        return 1
    if s == 'FALSE':
        return 0
    return None


def main(csv_path, out_path):
    dicts = {name: [] for name, kind, _ in FIELDS if kind == 'dict'}
    pos_in_dict = {name: {} for name in dicts}

    def d_idx(name, val):
        d = pos_in_dict[name]
        i = d.get(val)
        if i is None:
            i = len(dicts[name])
            d[val] = i
            dicts[name].append(val)
        return i

    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        missing = [c for c, _, _ in FIELDS if c not in reader.fieldnames]
        if missing:
            raise SystemExit(f'CSV 缺少列: {missing}\n实际列: {reader.fieldnames}')
        extra = [c for c in reader.fieldnames if c not in {c for c, _, _ in FIELDS}]
        if extra:
            print(f'⚠️  CSV 里还有未使用的列（已忽略）: {extra}')

        for r in reader:
            out = []
            for name, kind, nd in FIELDS:
                if kind == 'dict':
                    v = r[name]
                    if name == 'donor':
                        v = clean_donor(v)
                    out.append(d_idx(name, v))
                elif kind == 'num':
                    out.append(as_num(r[name], nd))
                elif kind == 'int':
                    out.append(as_int(r[name]))
                elif kind == 'bool':
                    out.append(as_bool(r[name]))
                else:                      # raw
                    out.append(r[name])
            rows.append(out)

    # 按自然染色体顺序、位置排序，保证首屏是 chr1 从头开始
    rank = {i: contig_rank(c) for i, c in enumerate(dicts['contig'])}
    rows.sort(key=lambda x: (rank[x[0]], x[1] if x[1] is not None else 0))

    payload = {
        'fields': [c for c, _, _ in FIELDS],
        'dicts': {k: v for k, v in dicts.items()},
        'rows': rows,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    js = ('/* 自动生成，请勿手改。\n'
          '   源: variants_website.csv（21 列全量，无外部拼接字段）\n'
          '   生成脚本: scripts/build_variants_data.py */\n'
          'window.VDATA=' + body + ';\n')
    Path(out_path).write_text(js, encoding='utf-8')

    print(f'变异记录: {len(rows):,}  /  列: {len(FIELDS)}')
    for k, v in dicts.items():
        print(f'  {k:18s} 去重 {len(v):>6,}')
    print(f'输出: {out_path}  ({len(js) / 1024 / 1024:.2f} MB)')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
