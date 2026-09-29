#!/usr/bin/env bash
#
# 构建发布快照 publish/（「发布为应用」的部署对象，不是项目根目录）。
#
# 为什么要这个脚本：
#   仓库里页面在 src/，静态资源在 assets/ 和 data/，页面用 ../assets/ 这类相对路径；
#   但线上要的是**扁平结构**（首页就是 /index.html，不是 /src/index.html），
#   所以这里把 src/*.html 拷到 publish 根，并把路径里的 ../ 前缀去掉。
#
# 用法：bash scripts/build_publish.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

echo "项目根: $(pwd)"

rm -rf publish
mkdir -p publish

# ---- 静态资源：原样拷贝 ----
cp -R assets data publish/

# ---- 登录门脚本不随发布产物上线 ----
# 2026-09-25 luo「取消密码登录的设置」后，页面已不再引用它；
# 文件里带一个硬编码兜底密码（DEV_PASSWORD），没必要放进公开链接。
# 源文件仍保留在 assets/somatic-auth.js，将来恢复登录门时直接引用即可。
rm -f publish/assets/somatic-auth.js

# ---- 页面：拷到发布根，去掉 ../ 前缀 ----
# ⚠️ 不要只匹配「双引号开头的」`"\.\./assets/` —— 单引号 / 无引号的引用会漏掉。
#    2026-09-29 发现的漏点：src/index.html 里 `window.PLOT_BASE || '../assets/plots/'`
#    这个单引号兜底值，以及 src/somacard.html 顶部注释里的路径。
#    一律按「出现即抹掉」处理，反正发布产物是扁平结构，任何 ../ 都是错的。
for f in src/*.html; do
  sed -e 's|\.\./assets/|assets/|g' \
      -e 's|\.\./data/|data/|g' \
      "$f" > "publish/$(basename "$f")"
done

# ---- 图集基址：生成的 js 里也带 ../，同样要抹掉 ----
sed -e 's|\.\./assets/|assets/|g' -e 's|\.\./data/|data/|g' \
    data/plots_index.js > publish/data/plots_index.js

# ---- 自检：发布产物里不该再有 ../ ----
# 扫 html / js / css。⚠️ 必须排除 fontawesome：它自己的 all.min.css 里有一堆
# `url(../webfonts/...)`，那是相对该 CSS 自身解析的、完全正确，误报会挡住发布。
#
# 用 find + grep -l 而不是 `grep -r --exclude-dir=` —— 本机 grep 是 toybox 版，
# 与 GNU/BSD grep 的选项支持不一致（`\|` 交替就静默失效过），find 的写法到哪都能跑。
_leak() {
  find publish -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' \) \
       -not -path '*/fontawesome/*' \
       -exec grep -lE '\.\./(assets|data)/' {} + 2>/dev/null
}
if [ -n "$(_leak)" ]; then
  echo "❌ 发布产物里仍有 ../ 相对路径：" >&2
  find publish -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' \) \
       -not -path '*/fontawesome/*' \
       -exec grep -nE '\.\./(assets|data)/' {} + >&2
  exit 1
fi

echo "✅ publish/ 重建完成（自检通过）"
du -sh publish
ls publish
