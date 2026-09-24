#!/usr/bin/env python3
"""生成 Our Donors 横幅插画（侧脸剪影群像）。

配色取样自设计稿，形状为程序化生成的侧脸人像轮廓。
用法: python3 scripts/build_donors_banner.py > assets/donors-banner.svg
"""
import random
import sys

W, H = 1440, 258
BAND_H = 214          # 人像band高度，其余留白（与设计稿一致）
random.seed(20260923)

# 从设计稿横幅采样出的配色（青绿 / 赭橙 / 军绿 / 肤色 / 砖红）
PALETTE = [
    "#8fb9ab", "#6f9a90", "#5d8a82", "#4f6b48", "#6b7a45",
    "#c96a20", "#b45a1c", "#a04a16", "#c99a80", "#b58267",
    "#8e3b2e", "#6e2f2a", "#d9a88f", "#3f5b57", "#7d9e7a",
]
DARK = ["#6e2f2a", "#4f6b48", "#3f5b57", "#8e3b2e", "#5d8a82"]

# 侧脸轮廓（面朝右），基准盒 100 × 170，头顶在 y≈4
FACE = (
    "M24 46"
    "C16 24 30 6 52 4"
    "C74 2 88 15 91 32"
    "C92 40 88 45 86 49"
    "C84 53 90 58 96 66"
    "C99 70 94 72 88 72"
    "C86 73 89 75 90 78"
    "C91 80 85 81 84 81"
    "C85 84 90 87 89 91"
    "C88 95 84 99 78 103"
    "C73 106 68 110 66 116"
    "L64 200"
    "L34 200"
    "L32 118"
    "C22 108 18 78 24 46"
    "Z"
)

# 只描轮廓线的版本（额头→鼻→唇→下巴）
FACE_LINE = (
    "M52 6C74 4 88 16 91 33C92 41 88 46 86 50"
    "C84 54 90 59 96 67C99 71 94 73 88 73"
    "C86 74 89 76 90 79C91 81 85 82 84 82"
    "C85 85 90 88 89 92C88 96 84 100 78 104"
)


def hair(kind, color):
    """附加发型：丸子头 / 蓬松卷发 / 无"""
    if kind == "bun":
        return f'<circle cx="24" cy="20" r="15" fill="{color}"/>'
    if kind == "curls":
        pts = [(30, 16, 15), (46, 8, 14), (62, 10, 12), (18, 32, 14), (76, 16, 11)]
        return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>' for x, y, r in pts)
    return ""


def head(color, scale, tx, ty, kind, line_art=False, line_color=None):
    g = [f'<g transform="translate({tx:.1f} {ty:.1f}) scale({scale:.3f})">']
    g.append(hair(kind, color))
    g.append(f'<path d="{FACE}" fill="{color}"/>')
    if line_art:
        g.append(
            f'<path d="{FACE_LINE}" fill="none" stroke="{line_color}" '
            f'stroke-width="2.4" stroke-linecap="round" stroke-opacity=".55"/>'
        )
    g.append("</g>")
    return "".join(g)


def build():
    # 后排：主体群像。人像面朝右，因此右侧的头像必须画在左侧头像之下，
    # 才能保证每个人的侧脸轮廓都露出来 —— 这里先生成参数，再按右→左输出。
    heads = []
    x = -60.0
    i = 0
    while x < W + 80:
        color = PALETTE[i % len(PALETTE)]
        if i and color == PALETTE[(i - 1) % len(PALETTE)]:
            color = PALETTE[(i + 3) % len(PALETTE)]
        scale = random.uniform(1.40, 1.76)
        ty = random.uniform(4, 40)
        kind = random.choice(["none", "none", "curls", "bun"])
        line = (i % 5 == 2)
        heads.append((color, scale, x, ty, kind, line))
        x += 58 * scale * random.uniform(0.94, 1.06)
        i += 1

    parts = [head(c, s, tx, ty, k, ln, "#2f4a63") for (c, s, tx, ty, k, ln) in reversed(heads)]

    # 前排：稍小的深色头像，制造层次
    for j, fx in enumerate([150, 560, 950, 1310]):
        color = DARK[j % len(DARK)]
        parts.append(head(color, random.uniform(1.05, 1.25), fx, random.uniform(58, 86), "none"))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice" role="img">'
        f'<defs><clipPath id="band"><rect x="0" y="0" width="{W}" height="{BAND_H}"/></clipPath></defs>'
        f'<g clip-path="url(#band)">'
        + "".join(parts)
        + "</g></svg>\n"
    )


if __name__ == "__main__":
    sys.stdout.write(build())
