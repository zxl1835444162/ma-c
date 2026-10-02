#!/bin/bash
# =============================================================================
#  寒山小说发布工具 · macOS「打不开」一键诊断
#
#  用法（二选一）：
#    A) 把「寒山小说发布工具.app」直接拖到本文件图标上松手
#    B) 双击本文件（会自动去 ~/Downloads 和桌面找 .app）
#
#  首次双击可能被拦：右键 → 打开 → 「打开」；
#  或在终端执行一次：  chmod +x 诊断.command
#
#  它只读不写，不会修改或删除任何东西。
# =============================================================================

APP=""

# A) 拖拽进来的路径
if [ -n "$1" ]; then
  APP="$1"
fi

# B) 没给参数就自己找
if [ -z "$APP" ] || [ ! -d "$APP" ]; then
  for d in "$HOME/Downloads" "$HOME/Desktop" "$HOME" /Applications; do
    found="$(find "$d" -maxdepth 3 -name '寒山小说发布工具.app' -type d 2>/dev/null | head -1)"
    if [ -n "$found" ]; then APP="$found"; break; fi
  done
fi

line() { printf '%s\n' "────────────────────────────────────────────────────────"; }
hdr()  { echo; line; printf '  %s\n' "$*"; line; }

clear 2>/dev/null || true

line
echo "  寒山小说发布工具 · macOS 诊断报告"
printf '  时间: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
line

# ---------------------------------------------------------------- 1. 系统环境
hdr "1. 这台 Mac 的环境"
printf '  macOS 版本 : %s (%s)\n' "$(sw_vers -productVersion)" "$(sw_vers -buildVersion)"
printf '  CPU 架构   : %s\n' "$(uname -m)"
printf '  芯片型号   : %s\n' "$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 未知)"
MODE="$(defaults read -g AppleInterfaceStyle 2>/dev/null || echo Light)"
printf '  外观模式   : %s\n' "$MODE"
case "$(uname -m)" in
  arm64) echo "  → Apple Silicon。必须用 arm64 或 universal 的安装包。" ;;
  x86_64)
    if sysctl -n sysctl.proc_translated >/dev/null 2>&1; then
      echo "  → Intel Mac。必须用 x86_64 或 universal 的安装包（arm64 的包一定打不开）。"
    fi ;;
esac
if [ "$MODE" = "Dark" ]; then
  echo "  ⚠ 你当前是深色模式。Tk 8.6 在深色外观下取色会抛 NSException 直接崩溃，"
  echo "    这是本次崩溃的头号嫌疑，务必看第 7 节的判定结果。"
fi

# ---------------------------------------------------------------- 2. App 定位
hdr "2. 找到的 App"
if [ -z "$APP" ] || [ ! -d "$APP" ]; then
  echo "  ✗ 没找到「寒山小说发布工具.app」。"
  echo "    请把 .app 直接拖到本文件的图标上再试一次。"
  echo
  read -n 1 -s -r -p "  按任意键关闭…"
  exit 1
fi
printf '  路径: %s\n' "$APP"

# 注意：artifact 下载下来如果解压了两次，这里可能只找到一个 .zip 而不是 .app
if [ ! -f "$APP/Contents/Info.plist" ]; then
  echo "  ✗ 这不是一个完整的 .app（缺 Contents/Info.plist）。"
  echo "    很可能你解压出来的只是中间那层 zip。请继续解压，直到看到 .app。"
  echo
  read -n 1 -s -r -p "  按任意键关闭…"
  exit 1
fi
echo "  ✓ 目录结构正常"

# ---------------------------------------------------------------- 3. 架构匹配
hdr "3. 架构是否和本机匹配"
BIN="$APP/Contents/MacOS/$(defaults read "$APP/Contents/Info.plist" CFBundleExecutable 2>/dev/null)"
[ -f "$BIN" ] || BIN="$(find "$APP/Contents/MacOS" -maxdepth 1 -type f 2>/dev/null | head -1)"
printf '  主程序: %s\n' "$BIN"
if [ -f "$BIN" ]; then
  ARCHS="$(lipo -archs "$BIN" 2>/dev/null || echo '读取失败')"
  printf '  包内架构: %s\n' "$ARCHS"
  printf '  本机架构: %s\n' "$(uname -m)"
  case " $ARCHS " in
    *" $(uname -m) "*) echo "  ✓ 架构匹配，可以运行" ;;
    *) echo "  ✗✗ 架构不匹配！这就是打不开的原因。"
       echo "     请下载与你的 Mac 对应的版本重新安装。"
       echo "     （Apple Silicon 要 arm64，Intel 要 x86_64 / universal）" ;;
  esac
  printf '  可执行位: %s\n' "$(test -x "$BIN" && echo '有 (+x)' || echo '✗ 丢失 —— 包在传输中被破坏，需重新下载')"
fi

# ---------------------------------------------------------------- 4. 系统版本门槛
hdr "4. 系统版本门槛"
MIN="$(defaults read "$APP/Contents/Info.plist" LSMinimumSystemVersion 2>/dev/null || echo '未声明')"
printf '  App 要求最低 macOS: %s\n' "$MIN"
printf '  本机 macOS       : %s\n' "$(sw_vers -productVersion)"
if [ "$MIN" != "未声明" ]; then
  CUR_MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
  MIN_MAJOR="$(echo "$MIN" | cut -d. -f1)"
  if [ "$CUR_MAJOR" -lt "$MIN_MAJOR" ] 2>/dev/null; then
    echo "  ✗✗ 你的系统版本低于 App 的要求，macOS 会直接拒绝启动它。"
    echo "     这是「打不开且没有任何提示」的典型原因。"
  else
    echo "  ✓ 系统版本满足要求"
  fi
fi

# ---------------------------------------------------------------- 5. 隔离属性
hdr "5. Gatekeeper 隔离属性（最常见原因）"
QUAR="$(xattr -l "$APP" 2>/dev/null | grep -c quarantine || true)"
if [ "$QUAR" -gt 0 ]; then
  echo "  ✗ 检测到 com.apple.quarantine —— 这是从网络下载的文件被系统标记，"
  echo "    未公证的 App 会因此被拦。"
  echo
  echo "  修复命令（直接复制到终端执行）："
  printf '    xattr -dr com.apple.quarantine "%s"\n' "$APP"
else
  echo "  ✓ 没有隔离属性"
fi

# ---------------------------------------------------------------- 6. 签名
hdr "6. 代码签名状态"
codesign --verify --deep --strict --verbose=2 "$APP" 2>&1 | sed 's/^/  /'
echo
codesign -dv "$APP" 2>&1 | sed 's/^/  /'
echo
echo "  --- Gatekeeper 评估 ---"
spctl --assess --type execute --verbose=4 "$APP" 2>&1 | sed 's/^/  /'
echo "  （ad-hoc 签名显示 rejected 是正常的，未公证一律如此）"

# ---------------------------------------------------------------- 6.5 深色模式 / Tk
hdr "6.5 深色模式与 Tcl/Tk 版本（Tk 崩窗口问题）"
BID="$(defaults read "$APP/Contents/Info.plist" CFBundleIdentifier 2>/dev/null || echo 未声明)"
printf '  Bundle ID: %s\n' "$BID"
FORCED="$(defaults read "$BID" NSRequiresAquaSystemAppearance 2>/dev/null || echo '未设置')"
printf '  App 是否被强制浅色: %s\n' "$FORCED"
if [ "$FORCED" = "1" ]; then
  echo "  ✓ 已强制浅色（这是规避 Tk 深色模式崩溃的正确设置）"
else
  echo "  ✗ 未强制浅色。如果系统是深色模式，Tk 8.6 会在创建窗口时崩溃。"
  echo "    修复命令（复制到终端执行，不影响系统其它外观）："
  printf '      defaults write %s NSRequiresAquaSystemAppearance -bool YES\n' "$BID"
  echo "      killall cfprefsd"
fi

# 看包内是否真的有 Tcl/Tk
TK_FOUND=""
for d in "$APP/Contents/Frameworks" "$APP/Contents/Resources" "$APP/Contents/MacOS"; do
  [ -d "$d" ] || continue
  f="$(find "$d" -maxdepth 3 -name 'libtk8.6.dylib' 2>/dev/null | head -1)"
  if [ -n "$f" ]; then TK_FOUND="$f"; break; fi
done
if [ -n "$TK_FOUND" ]; then
  echo "  包内 libtk8.6.dylib ✓（Tcl/Tk 确实打进去了，不是缺库问题）"
else
  echo "  ✗ 包内没找到 libtk8.6.dylib（Tcl/Tk 可能真没打进去）"
fi
echo "  提示：Tk 8.6.9 及更早对 macOS 深色模式支持很差；8.6.12 也只是部分修好。"

# ---------------------------------------------------------------- 7. 真跑一次
hdr "7. 直接运行主程序，抓真实报错"
echo "  下面会直接启动 App 本体并捕获输出（最多等 15 秒）…"
echo
LOG="$(mktemp)"
( "$BIN" >"$LOG" 2>&1 ) &
PID=$!
for _ in $(seq 1 15); do
  sleep 1
  kill -0 "$PID" 2>/dev/null || break
done

if kill -0 "$PID" 2>/dev/null; then
  echo "  ✓ 进程存活，界面应该已经起来了（下面把它关掉）"
  kill "$PID" 2>/dev/null
  wait "$PID" 2>/dev/null
  echo "  → 结论：程序本身能跑，打不开纯粹是被 Gatekeeper 拦住，"
  echo "    按第 5 节那条 xattr 命令处理后即可。"
else
  wait "$PID" 2>/dev/null
  echo "  ✗ 程序启动即退出。真实输出如下："
  echo
  sed 's/^/    /' "$LOG"
  echo

  # ---- 关键：把 NSException 的原因单独拎出来 ----
  REASON="$(grep -m1 -E 'Terminating app due to uncaught exception|NSException' "$LOG" 2>/dev/null)"
  if [ -n "$REASON" ]; then
    echo "  ══════════════════════════════════════════════════════"
    echo "  ★ 关键线索（NSException 原因）："
    echo "    $REASON"
    echo "  ══════════════════════════════════════════════════════"
    echo
  fi

  if grep -q 'TkpGetColor' "$LOG" 2>/dev/null; then
    echo "  ★★ 判定：这是 Tk 的 macOS 取色函数崩溃。"
    echo "     TkpGetColor() 依赖 NSAppearance.currentAppearance，"
    echo "     在深色外观下会失败并抛 NSException（Tk 工单 3e9e82bc）。"
    echo "     Python 层接不住这个 Objective-C 异常，直接 SIGABRT。"
    echo
    echo "     解法（任选，都不用重新打包）："
    echo "       ① 上面第 6.5 节那条 defaults write 命令，给这个 App 单独强制浅色"
    echo "       ② 或：系统设置 → 外观 → 选「浅色」，再打开 App"
    echo "     根治：Info.plist 里 NSRequiresAquaSystemAppearance 必须为 True，"
    echo "           同时 rthook 在 Tk 之前把外观钉成 Aqua —— 改完后重新打包。"
    echo
  fi

  echo "  --- 常见结论对照 ---"
  echo "  ModuleNotFoundError: tkinter / _tkinter"
  echo "      → 打包时 Tcl/Tk 没打进去，是构建问题，需要重新打包（不要用 Homebrew 版 Python 做基座）。"
  echo "  PermissionError: .../playwright/driver/node"
  echo "      → node 丢了可执行位。临时修："
  echo "        chmod +x \"$APP/Contents/Frameworks/playwright/driver/node\""
  echo "  Library not loaded: /opt/homebrew/..."
  echo "      → 包里残留了构建机的 Homebrew 路径，只能在构建机上跑，必须重新打包。"
  echo "  什么都没输出就退出"
  echo "      → 看下面的崩溃日志。"
fi
echo
echo "  --- 最近的崩溃日志（如果有）---"
CRASHDIR="$HOME/Library/Logs/DiagnosticReports"
if [ -d "$CRASHDIR" ]; then
  ls -t "$CRASHDIR" 2>/dev/null | head -5 | while read -r f; do
    printf '    %s\n' "$f"
  done
  NEWEST="$(ls -t "$CRASHDIR"/寒山小说发布工具*.ips 2>/dev/null | head -1)"
  [ -n "$NEWEST" ] || NEWEST="$(ls -t "$CRASHDIR"/*.ips 2>/dev/null | head -1)"
  if [ -n "$NEWEST" ]; then
    echo
    printf '  最新一份: %s\n' "$NEWEST"
    echo "  --- 异常摘要 ---"
    grep -oE '"(exception|termination|asi|exceptionReason)"[^}]{0,260}' "$NEWEST" 2>/dev/null \
      | head -4 | sed 's/^/    /'
    echo "  --- 崩溃线程最顶部几帧（真正的出错点）---"
    grep -oE '"[0-9]+ +[^"]{0,140}"' "$NEWEST" 2>/dev/null | head -8 | sed 's/^/    /'
  fi
else
  echo "    （无）"
fi

# ---------------------------------------------------------------- 8. 结论
hdr "8. 该把什么发给别人"
echo "  把上面完整的终端输出复制走即可。重点看："
echo "    · 第 3 节「架构不匹配」→ 换对应架构的包"
echo "    · 第 4 节「系统版本不足」→ 换台新一点的 Mac"
echo "    · 第 5 节「有隔离属性」→ 执行那条 xattr 命令"
echo "    · 第 6.5 节「未强制浅色」→ 执行那条 defaults write 命令（Tk 崩窗口的头号原因）"
echo "    · 第 7 节「TkpGetColor」→ 确认是 Tk 深色模式崩溃，该节里有现成的解法"
echo "    · 第 7 节「启动即退出」→ 是打包问题，贴它的输出"
echo
read -n 1 -s -r -p "  按任意键关闭…"
echo
