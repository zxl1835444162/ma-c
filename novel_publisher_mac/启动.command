#!/bin/bash
# =============================================================================
#  寒山小说发布工具 · macOS 免打包启动器（备用路线）
#
#  双击本文件即可运行；首次运行会自动建虚拟环境并装依赖（约 1-3 分钟）。
#
#  这条路不生成 .app，直接从源码跑 —— 当你不想等 PyInstaller、
#  或者打包出来的 .app 有奇怪问题时，用这个最快。
#
#  想生成可双击的 .app，请改用：./build_mac.sh
# =============================================================================
set -uo pipefail

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
APP_NAME="寒山小说发布工具"
VENV="$ROOT/.venv-run"

echo "=============================================="
echo "  $APP_NAME · 启动中"
echo "=============================================="
echo

# ---------------------------------------------------------------- 0. 平台
if [ "$(uname -s)" != "Darwin" ]; then
  echo "[!] 本脚本面向 macOS。其他平台请直接执行： python3 app.py"
  exit 1
fi

# ---------------------------------------------------------------- 1. 解释器
find_python() {
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
[✗] 没找到带 tkinter 的 Python 3.10。

本工具由 Python 3.10 字节码还原而来，必须用 3.10 运行。二选一：

  A) 官网安装包（自带 tkinter，最省事）
     https://www.python.org/downloads/release/python-31011/
     选 "macOS 64-bit universal2 installer"

  B) Homebrew
     brew install python@3.10 python-tk@3.10

装好后重新双击本文件。
EOF
  echo
  read -n 1 -s -r -p "按任意键关闭…"
  exit 1
fi
echo "[1/3] 解释器: $("$PY" -V 2>&1)"

# ---------------------------------------------------------------- 2. 环境
if [ ! -x "$VENV/bin/python" ]; then
  echo "[2/3] 首次运行，创建虚拟环境并安装依赖（请稍候）…"
  "$PY" -m venv "$VENV" || { echo "[✗] 创建虚拟环境失败"; read -n 1 -s -r; exit 1; }
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r requirements-mac.txt \
    || { echo "[✗] 依赖安装失败，请检查网络后重试"; read -n 1 -s -r; exit 1; }
  echo "      依赖安装完成"
else
  echo "[2/3] 复用已有虚拟环境"
fi
VPY="$VENV/bin/python"

# tkinter 兜底检查
$VPY -c 'import tkinter' 2>/dev/null || {
  echo "[✗] 虚拟环境里没有 tkinter。请改用官网版 Python 3.10 后删除 .venv-run 重试。"
  read -n 1 -s -r -p "按任意键关闭…"
  exit 1
}

# ---------------------------------------------------------------- 3. 启动
echo "[3/3] 启动应用…"
echo
echo "----------------------------------------------"
echo "  数据目录: ~/Library/Application Support/$APP_NAME/"
echo "  关闭本窗口不会退出应用，请用应用窗口的关闭按钮。"
echo "----------------------------------------------"
echo

exec "$VPY" app.py
