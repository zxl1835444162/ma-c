#!/usr/bin/env bash
# =============================================================================
#  把 dist/寒山小说发布工具.app 打成 .dmg
#
#  用法：  ./make_dmg.sh
#  前置：  已执行 ./build_mac.sh 生成 .app
#
#  产出的 dmg 里含一个「应用程序」快捷方式，拖拽即可安装。
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")"
APP_NAME="寒山小说发布工具"
VERSION="2.2.8"
APP="dist/${APP_NAME}.app"
DMG="dist/${APP_NAME}-${VERSION}.dmg"
STAGE="dist/_dmg_stage"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
die()  { printf '  \033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || die "make_dmg.sh 只能在 macOS 上运行（hdiutil 是 macOS 专有工具）"
[ -d "$APP" ] || die "未找到 $APP，请先执行 ./build_mac.sh"

bold "== 准备 DMG 内容 =="
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/应用程序"
ok "已暂存 App 与「应用程序」快捷方式"

bold "== 生成 DMG =="
VOL_NAME="${APP_NAME} ${VERSION}"
hdiutil create \
  -volname "$VOL_NAME" \
  -srcfolder "$STAGE" \
  -ov -format UDZO \
  -fs HFS+ \
  "$DMG"
ok "已生成 $(du -h "$DMG" | cut -f1)  $DMG"

rm -rf "$STAGE"

# 有签名证书时顺手签 dmg（分发到 Gatekeeper 更友好）
if [ -n "${SIGN_ID:-}" ]; then
  codesign --force --sign "$SIGN_ID" "$DMG" && ok "DMG 已签名"
fi

cat <<EOF

$(printf '\033[1m完成\033[0m')

  挂载试用：open "$DMG"
  校验镜像：hdiutil verify "$DMG"

  分发提示：ad-hoc 签名的 App 在别人机器上会被 Gatekeeper 拦截。
  对陌生人分发请走正式签名 + 公证：
      SIGN_ID="Developer ID Application: xxx (TEAMID)" \\
      NOTARIZE=1 APPLE_ID=... APPLE_TEAM_ID=... APPLE_APP_PASSWORD=... \\
      ./build_mac.sh && MAKE_DMG=1 ./build_mac.sh
EOF
