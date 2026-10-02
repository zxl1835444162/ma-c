"""PyInstaller 运行时钩子（仅 macOS 挂载）。

⚠️ 这个文件里【绝对不能】在 Tk 之前碰 AppKit / NSApplication。
   踩过一次大坑，完整记录在这里，别再犯：

   ---------------------------------------------------------------------------
   【事故】`-[NSApplication macOSVersion]: unrecognized selector sent to instance`
   ---------------------------------------------------------------------------
   崩溃栈（macOS 15.6 实测）：

       TkSetMacColor + 2500
       TkSetMacColor + 408 / + 1972
       Tk_GetColor + 288
       Tk_Get3DBorder + 292
       Tk_Alloc3DBorderFromObj + 496
       Tk_InitOptions + 3072 / + 612 / + 96
       Tk_PkgInitStubsCheck + 50944
       TkCreateFrame + 656
       Tk_Init + 3032
       Tkinter_TkInit → Tcl_AppInit → Tkapp_New → _tkinter_create
       libc++abi: terminating due to uncaught exception of type NSException

   原因：Tk 的 macOS 实现把 `macOSVersion` 等方法加在自己的 NSApplication
   子类 `TKApplication` 上（见 tkMacOSXColor.c 里的 `@implementation
   TKApplication(TKColor)`），并期望 `NSApp` 就是 `TKApplication`。
   而本钩子以前在 Tk 之前调了 `NSApplication.sharedApplication()`，
   于是 AppKit 抢先创建了一个**普通 NSApplication** 并把它设为全局单例；
   Tk 之后无法替换，等到创建根窗口取色时就报
   `-[NSApplication macOSVersion]: unrecognized selector` → SIGABRT。

   所以：
     · 权限修复（下面第 1 项）放进这个钩子 —— 它不碰 AppKit，是安全的；
     · 任何「前台激活 / 外观设置」都必须等到 Tk 根窗口建好之后再做，
       放在 `macos_support.apply_darwin_tk_defaults()` 里（那里已经是正确时机）。
     · 想强制浅色外观，用 Info.plist 的 NSRequiresAquaSystemAppearance，
       那是纯声明式的，不涉及任何 AppKit 调用。

   ---------------------------------------------------------------------------

本文件目前只做一件事：

**Playwright 的 node driver 丢可执行位**
`playwright/driver/node` 是通过 collect_data_files 作为「数据文件」收集的，
PyInstaller 拷进 .app 后不保证保留 +x 权限，导致启动时报
`PermissionError: [Errno 13] Permission denied: '.../playwright/driver/node'`。
这里在解释器启动最早期（任何 playwright 模块被导入之前）把权限补回去。
"""
import os
import stat
import sys

if sys.platform != 'darwin':
    # 钩子只在 macOS 生效，其他平台直接跳过
    pass
else:
    _meipass = getattr(sys, '_MEIPASS', None)

    def _candidate_paths():
        roots = []
        if _meipass:
            roots.append(_meipass)
        # onedir .app：可执行文件在 Contents/MacOS，资源在 Contents/Frameworks
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        roots.append(exe_dir)
        if exe_dir.endswith('MacOS'):
            roots.append(os.path.join(os.path.dirname(exe_dir), 'Frameworks'))
        for r in roots:
            yield os.path.join(r, 'playwright', 'driver', 'node')
            yield os.path.join(r, 'playwright', 'driver', 'node.exe')

    def _restore_exec_bit():
        fixed = []
        for path in _candidate_paths():
            if not os.path.isfile(path):
                continue
            try:
                mode = os.stat(path).st_mode
                if not (mode & stat.S_IXUSR):
                    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    fixed.append(path)
            except OSError:
                pass
        return fixed

    try:
        _fixed = _restore_exec_bit()
        if _fixed:
            print(f'[rthook] 已恢复 node driver 可执行位: {_fixed}')
    except Exception:
        # 运行时钩子绝不能因为自身异常阻断应用启动
        pass
