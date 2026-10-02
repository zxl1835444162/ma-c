#!/usr/bin/env bash
# =============================================================================
#  寒山小说发布工具 · macOS 一键打包
#
#  用法（在 macOS 上，工程根目录内执行）：
#      chmod +x build_mac.sh && ./build_mac.sh
#
#  可选环境变量：
#      TARGET_ARCH=arm64|x86_64|universal2   目标架构（默认：当前机器）
#      PYTHON=/path/to/python3.10            指定解释器（默认自动探测）
#      MAKE_DMG=1                            构建完成后顺带产出 .dmg
#      SIGN_ID="Developer ID Application: xxx (TEAMID)"
#                                            有开发者证书时做正式签名
#      NOTARIZE=1 + APPLE_ID/APPLE_TEAM_ID/APPLE_APP_PASSWORD
#                                            签名后自动公证（对外分发才需要）
#
#  产物：dist/寒山小说发布工具.app
#        MAKE_DMG=1 时另有 dist/寒山小说发布工具-2.2.8.dmg
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"
APP_NAME="寒山小说发布工具"
VERSION="2.2.8"
VENV="$ROOT/.venv-build"
DIST_APP="dist/${APP_NAME}.app"

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
info()  { printf '  \033[36m→\033[0m %s\n' "$*"; }
ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn()  { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()   { printf '  \033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 0. 平台检查
bold "== 0/8 平台检查 =="
if [ "$(uname -s)" != "Darwin" ]; then
  cat <<'EOF'
  ✗ 当前不是 macOS。

  PyInstaller 不支持交叉编译：Windows / Linux 上无法产出可运行的 .app。
  请在 macOS 机器（或 macOS 虚拟机 / 云 Mac）上执行本脚本。

  需要转移的文件：整个 novel_publisher_mac/ 目录（用 zip 打包即可）。
EOF
  exit 1
fi
ok "$(sw_vers -productVersion) / $(uname -m)"
if ! xcode-select -p >/dev/null 2>&1; then
  warn "未检测到 Xcode Command Line Tools（codesign 会不可用）"
  warn "如需签名请先执行：xcode-select --install"
fi

# ---------------------------------------------------------------- 1. 解释器
bold "== 1/8 探测 Python 解释器 =="
find_python() {
  if [ -n "${PYTHON:-}" ]; then echo "$PYTHON"; return; fi
  for c in python3.10 /usr/local/bin/python3.10 /opt/homebrew/bin/python3.10 \
           /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys,tkinter; sys.exit(0 if sys.version_info[:2]==(3,10) else 1)' 2>/dev/null; then
        command -v "$c"; return
      fi
    fi
  done
  echo ""
}
PY="$(find_python)"
if [ -z "$PY" ]; then
  cat <<'EOF'
  ✗ 没找到带 tkinter 的 Python 3.10。

  原程序是 Python 3.10 字节码还原而来，必须用 3.10 打包。两种装法：

  A) 官网安装包（自带 tkinter，最省事）
     https://www.python.org/downloads/release/python-31011/
     下载 "macOS 64-bit universal2 installer"

  B) Homebrew
     brew install python@3.10 python-tk@3.10

  装好后重跑本脚本，或显式指定：
     PYTHON=/usr/local/bin/python3.10 ./build_mac.sh
EOF
  exit 1
fi
ok "$PY -> $("$PY" -V 2>&1)  ($("$PY" -c 'import sys;print(sys.executable)'))"
info "tkinter: $("$PY" -c 'import tkinter;print(tkinter.TkVersion)' 2>/dev/null || echo '缺失')"

# ---------------------------------------------------------------- 2. 虚拟环境
bold "== 2/8 准备构建虚拟环境 =="
if [ ! -d "$VENV" ]; then
  "$PY" -m venv "$VENV"
  ok "已创建 $VENV"
else
  ok "复用已有 $VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
VPY="$VENV/bin/python"
info "$($VPY -V 2>&1)"
$VPY -c 'import tkinter' 2>/dev/null || die "虚拟环境里没有 tkinter。请换用官网版 Python 3.10。"

# ---------------------------------------------------------------- 3. 依赖
bold "== 3/8 安装依赖 =="
$VPY -m pip install --quiet --upgrade pip
$VPY -m pip install --quiet -r requirements-mac.txt
ok "依赖安装完成"
$VPY -m PyInstaller --version | sed 's/^/  PyInstaller /'

# ---------------------------------------------------------------- 4. 冒烟测试
bold "== 4/8 打包前冒烟测试 =="
$VPY - <<'PYCODE'
import ast, pathlib, sys
root = pathlib.Path('.')
bad, n = [], 0
for p in sorted(root.rglob('*.py')):
    if any(part in {'.venv-build', 'build', 'dist', '__pycache__', '.git'} for part in p.parts):
        continue
    n += 1
    try:
        ast.parse(p.read_text(encoding='utf-8'))
    except SyntaxError as e:
        bad.append(f'  {p}:{e.lineno}: {e.msg}')
if bad:
    print('\n'.join(bad)); sys.exit(1)
print(f'  {n} 个 .py 语法通过')
PYCODE
$VPY -c "
import sys
for m in ('tkinter','playwright','pystray','PIL','requests','lxml','parsel','AppKit'):
    __import__(m)
print('  运行期依赖全部可导入（含 AppKit 托盘后端）')
"
$VPY selftest_business.py 2>&1 | tail -3

# ---------------------------------------------------------------- 5. 图标
bold "== 5/8 生成应用图标 =="
if [ -f assets/app.icns ]; then
  ok "已存在 assets/app.icns（如需重做：rm assets/app.icns 后重跑）"
else
  if [ -f assets/app_icon.png ]; then
    ( cd assets && bash make_icns.sh ) && ok "已由 PNG 生成 app.icns"
  else
    warn "缺少 assets/app_icon.png，本次打包不带图标"
  fi
fi

# ---------------------------------------------------------------- 6. 构建
bold "== 6/8 PyInstaller 构建 =="
info "TARGET_ARCH=${TARGET_ARCH:-$(uname -m)}"
rm -rf build dist
$VPY -m PyInstaller --noconfirm --clean --log-level=WARN novel_publisher_mac.spec

[ -d "$DIST_APP" ] || die "构建失败：未生成 $DIST_APP"

# ---------------------------------------------------------------- 7. 修权限+签名
bold "== 7/8 修权限与签名 =="
NODE_BIN="$(find "$DIST_APP" -type f -name node -path '*playwright/driver*' 2>/dev/null | head -1 || true)"
if [ -n "$NODE_BIN" ]; then
  chmod +x "$NODE_BIN"
  ok "已恢复 node driver 可执行位（$(du -h "$NODE_BIN" | cut -f1)）"
else
  warn "未在包内找到 playwright/driver/node，首次运行可能需要联网执行 playwright install"
fi

if [ -n "${SIGN_ID:-}" ]; then
  info "使用开发者证书签名"
  codesign --force --deep --options runtime --timestamp --sign "$SIGN_ID" "$DIST_APP"
  codesign --verify --deep --strict --verbose=2 "$DIST_APP" && ok "签名校验通过"
  if [ "${NOTARIZE:-0}" = "1" ]; then
    info "提交公证（可能耗时数分钟）"
    ZIP_FOR_NOTARY="dist/${APP_NAME}-notarize.zip"
    ditto -c -k --keepParent "$DIST_APP" "$ZIP_FOR_NOTARY"
    xcrun notarytool submit "$ZIP_FOR_NOTARY" \
      --apple-id "${APPLE_ID:?需要 APPLE_ID}" \
      --team-id "${APPLE_TEAM_ID:?需要 APPLE_TEAM_ID}" \
      --password "${APPLE_APP_PASSWORD:?需要 APPLE_APP_PASSWORD}" --wait
    xcrun stapler staple "$DIST_APP" && ok "已装订公证票据"
    rm -f "$ZIP_FOR_NOTARY"
  fi
else
  info "ad-hoc 签名（本机自测够用；对外分发请设 SIGN_ID）"
  codesign --force --deep --sign - "$DIST_APP"
  xattr -dr com.apple.quarantine "$DIST_APP" 2>/dev/null || true
  ok "已 ad-hoc 签名并清除隔离属性"
fi

# ---------------------------------------------------------------- 8. 自检
bold "== 8/8 产物自检 =="
PLIST="$DIST_APP/Contents/Info.plist"
[ -f "$PLIST" ] && ok "Info.plist 存在"
for k in CFBundleName CFBundleIdentifier CFBundleShortVersionString; do
  v="$(/usr/libexec/PlistBuddy -c "Print :$k" "$PLIST" 2>/dev/null || echo '')"
  [ -n "$v" ] && info "$k = $v"
done
MAIN_BIN="$DIST_APP/Contents/MacOS/$APP_NAME"
[ -f "$MAIN_BIN" ] && ok "主可执行文件存在" || die "缺少主可执行文件"
if [ -f "$DIST_APP/Contents/Resources/app.icns" ]; then
  ok "图标已嵌入"
else
  warn "包内无 app.icns"
fi
info "包体积：$(du -sh "$DIST_APP" | cut -f1)"

SIZE="$(du -sm "$DIST_APP" | cut -f1)"
[ "$SIZE" -gt 150 ] || warn "包体积偏小（${SIZE}MB），playwright driver 可能没打进去"

# ---------------------------------------------------------------- DMG
if [ "${MAKE_DMG:-0}" = "1" ]; then
  bold "== 额外：构建 DMG =="
  bash make_dmg.sh
fi

cat <<EOF

$(printf '\033[1m构建完成\033[0m')

  产物：$(pwd)/$DIST_APP
  运行：open "$DIST_APP"

  首次打开若提示「无法验证开发者」（ad-hoc 签名必然如此）：
    右键 App → 打开 → 再点「打开」
  或执行：
    xattr -dr com.apple.quarantine "$(pwd)/$DIST_APP"

  数据目录（配置、登录态、分身）：
    ~/Library/Application Support/${APP_NAME}/

EOF
