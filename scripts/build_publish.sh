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

# ---- 页面：拷到发布根，去掉 ../ 前缀 ----
for f in src/*.html; do
  sed -e 's|"\.\./assets/|"assets/|g' \
      -e 's|"\.\./data/|"data/|g' \
      "$f" > "publish/$(basename "$f")"
done

# ---- 图集基址：生成的 js 里也带 ../，同样要抹掉 ----
sed "s|'\.\./assets/plots/'|'assets/plots/'|" data/plots_index.js > publish/data/plots_index.js

# ---- 自检：发布产物里不该再有 ../ ----
if grep -rlE '"\.\./(assets|data)/' publish --include='*.html' >/dev/null 2>&1; then
  echo "❌ 发布产物里仍有 ../ 相对路径：" >&2
  grep -rnE '"\.\./(assets|data)/' publish --include='*.html' >&2
  exit 1
fi
if grep -q "\.\./assets/plots/" publish/data/plots_index.js; then
  echo "❌ plots_index.js 的 PLOT_BASE 没改写成功" >&2
  exit 1
fi

echo "✅ publish/ 重建完成（自检通过）"
du -sh publish
ls publish
