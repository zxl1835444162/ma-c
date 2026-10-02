#!/bin/bash
# =============================================================================
#  寒山小说发布工具 · 一键修复并打开
#
#  双击本文件即可。它会：
#    1. 找到「寒山小说发布工具.app」
#    2. 清除 macOS 的隔离属性（这是「打不开」最常见的原因）
#    3. 打开它
#
#  首次双击若被拦：右键点本文件 → 打开 → 弹框里再点「打开」。
#  之后就能直接双击了。
# =============================================================================

cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"

echo "=============================================="
echo "   寒山小说发布工具 · 一键修复"
echo "=============================================="
echo

# ---------------------------------------------------------------- 找 .app
APP=""
if [ -n "$1" ] && [ -d "$1" ]; then
  APP="$1"
fi

if [ -z "$APP" ]; then
  # 先看自己所在目录（从 zip 解压出来时 app 就在旁边）
  CAND="$(find "$HERE" -maxdepth 2 -name '*.app' -type d 2>/dev/null | head -1)"
  if [ -n "$CAND" ]; then APP="$CAND"; fi
fi

if [ -z "$APP" ]; then
  for d in "$HOME/Downloads" "$HOME/Desktop" /Applications "$HERE"; do
    CAND="$(find "$d" -maxdepth 3 -name '寒山小说发布工具.app' -type d 2>/dev/null | head -1)"
    if [ -n "$CAND" ]; then APP="$CAND"; break; fi
  done
fi

if [ -z "$APP" ]; then
  echo "✗ 没找到「寒山小说发布工具.app」。"
  echo
  echo "  请这样做：把 .app 直接拖到本文件图标上松手，再试一次。"
  echo "  或者先把下载的 zip 解压开（双击 zip 即可），再双击本文件。"
  echo
  read -n 1 -s -r -p "  按任意键关闭…"
  exit 1
fi

echo "找到：$APP"
echo

# ---------------------------------------------------------------- 检查完整性
if [ ! -f "$APP/Contents/Info.plist" ]; then
  echo "✗ 这不是一个完整的 .app。"
  echo "  很可能你只解压了一层 —— 下载的压缩包解开后里面还有一层同名压缩包，"
  echo "  再解压一次才是真正的 .app。"
  echo
  read -n 1 -s -r -p "  按任意键关闭…"
  exit 1
fi

# ---------------------------------------------------------------- 架构
BIN="$APP/Contents/MacOS/$(defaults read "$APP/Contents/Info.plist" CFBundleExecutable 2>/dev/null)"
[ -f "$BIN" ] || BIN="$(find "$APP/Contents/MacOS" -maxdepth 1 -type f 2>/dev/null | head -1)"
MINE="$(uname -m)"
ARCHS="$(lipo -archs "$BIN" 2>/dev/null || echo 未知)"
echo "你的 Mac 架构 : $MINE"
echo "这个包的架构  : $ARCHS"
case " $ARCHS " in
  *" $MINE "*)
    echo "✓ 架构匹配"
    ;;
  *)
    echo
    echo "✗✗ 架构不匹配！这个包在你的 Mac 上无论怎么弄都打不开。"
    case "$MINE" in
      arm64) echo "   你的 Mac 是 Apple Silicon，需要 arm64 或 universal 的安装包。" ;;
      x86_64) echo "   你的 Mac 是 Intel，需要 x86_64 或 universal 的安装包。" ;;
    esac
    echo "   请重新下载对应架构的版本，再双击本文件。"
    echo
    read -n 1 -s -r -p "  按任意键关闭…"
    exit 1
    ;;
esac
echo

# ---------------------------------------------------------------- 清隔离属性
echo "── 清除 macOS 隔离属性 ──"
BEFORE="$(xattr -l "$APP" 2>/dev/null | grep -c quarantine || true)"
if [ "$BEFORE" -gt 0 ]; then
  echo "  发现隔离属性，正在清除…"
else
  echo "  没发现隔离属性，仍然清除一遍以防万一…"
fi
xattr -dr com.apple.quarantine "$APP" 2>/dev/null
echo "  ✓ 完成"
echo

# ---------------------------------------------------------------- 补可执行位
if [ -f "$BIN" ] && [ ! -x "$BIN" ]; then
  echo "── 补回主程序可执行权限 ──"
  chmod +x "$BIN" && echo "  ✓ 完成"
  echo
fi

# ---------------------------------------------------------------- 打开
echo "── 打开应用 ──"
open "$APP" || {
  echo "  ✗ 打开失败，改用直接启动主程序："
  "$BIN"
}
echo

sleep 3
if pgrep -f "$(basename "$BIN")" > /dev/null 2>&1; then
  echo "✓ 应用已经起来了，去 Dock 或窗口里找它。"
  echo
  echo "  如果窗口躲在别的窗口后面，按 Command + Tab 切过去。"
else
  echo "⚠ 应用似乎没起来。请双击旁边的「打不开就先双击我-诊断.command」，"
  echo "  它会打印出真正的原因。"
fi

echo
echo "（本窗口可以直接关掉，不影响应用运行）"
read -n 1 -s -r -p "按任意键关闭本窗口…"
echo
