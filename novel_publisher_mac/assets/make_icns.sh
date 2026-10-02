#!/usr/bin/env bash
# 在 macOS 上由 PNG 生成 .icns（然后重跑 build_mac.sh 即可带上图标）
set -euo pipefail
cd "$(dirname "$0")"
SRC="app_icon.png"
SET="AppIcon.iconset"
rm -rf "$SET"; mkdir -p "$SET"
for s in 16 32 64 128 256 512; do
  sips -z $s $s        "$SRC" --out "$SET/icon_${s}x${s}.png"      >/dev/null
  sips -z $((s*2)) $((s*2)) "$SRC" --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o app.icns
rm -rf "$SET"
echo "已生成 $(pwd)/app.icns"
