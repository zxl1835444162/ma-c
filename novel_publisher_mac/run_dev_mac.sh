#!/usr/bin/env bash
# 开发模式直接运行（不打包），用于在 macOS 上快速验证功能
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3.10}"
$PY -m pip install -r requirements-mac.txt
exec $PY app.py "$@"
