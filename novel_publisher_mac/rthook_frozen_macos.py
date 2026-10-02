"""PyInstaller 运行时钩子（仅 macOS 挂载）。

解决三个打包后的实测问题：

1. **Playwright 的 node driver 丢可执行位**
   `playwright/driver/node` 是通过 collect_data_files 作为「数据文件」收集的，
   PyInstaller 拷进 .app 后不保证保留 +x 权限，导致启动时报
   `PermissionError: [Errno 13] Permission denied: '.../playwright/driver/node'`。
   这里在解释器启动最早期（任何 playwright 模块被导入之前）把权限补回去。

2. **强制浅色外观，规避 Tk 在深色模式下的崩溃（最关键）**
   实测崩溃栈：
       TkpGetColor → Tk_GetColor → Tk_Get3DBorder → Tk_InitOptions
       → CreateFrame → Initialize → Tkapp_New
   抛 `NSException`，Python 层无人接管，最终 `libc++abi: terminating ... SIGABRT`。
   Tk 官方工单 3e9e82bc 指出：`TkpGetColor()` 依赖 `NSAppearance.currentAppearance`，
   而它并不总是在 `TkMacOSXSetupDrawingContext()` 区间里被调用，深色外观下取色会失败。
   PyInstaller 也为此打过补丁（#5827，把 bootloader 声明的 SDK 版本压到 10.11
   以阻止系统启用深色模式），但那只覆盖 SDK 10.9 的 Intel python.org 构建，对本项目不生效。
   本钩子在 Tk 之前把 NSApplication 的外观钉死为 Aqua。
   （Info.plist 里 NSRequiresAquaSystemAppearance=True 是主要手段，此处是双保险。）

3. **macOS 上 tkinter 需要显式声明为前台进程**
   否则从终端/访达启动后窗口可能落在其他应用后面，用户以为「双击没反应」。
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

    # ------------------------------------------------------------------
    # 3. 强制浅色（Aqua）外观 —— 必须在 Tk 创建根窗口之前生效
    #
    #    这是那次实测崩溃的真正原因。Tk 8.6 的 TkpGetColor() 依赖
    #    NSAppearance.currentAppearance，在深色外观下取色失败会抛 NSException；
    #    崩溃点在创建根窗口时：
    #        TkpGetColor → Tk_GetColor → Tk_Get3DBorder → Tk_InitOptions
    #        → CreateFrame → Initialize
    #    Python 层没有对应的异常处理，最终 SIGABRT。
    #
    #    Info.plist 里的 NSRequiresAquaSystemAppearance=True 是主要手段；
    #    这里再显式设一次 NSApp.appearance 作为双保险（Tk 只认这一处的最早期时机，
    #    晚于 Tk() 就来不及了）。
    #
    #    想回到深色模式做对照实验：设环境变量 NOVELPUB_ALLOW_DARK=1 即可。
    # ------------------------------------------------------------------
    def _force_aqua_appearance():
        if os.environ.get('NOVELPUB_ALLOW_DARK'):
            print('[rthook] NOVELPUB_ALLOW_DARK 已设置，跳过强制浅色外观')
            return
        try:
            from AppKit import (
                NSApplication,
                NSAppearance,
                NSAppearanceNameAqua,
            )
            app = NSApplication.sharedApplication()
            aqua = NSAppearance.appearanceNamed_(NSAppearanceNameAqua)
            if aqua is not None:
                app.setAppearance_(aqua)
                print('[rthook] 已强制浅色（Aqua）外观，规避 Tk 深色模式崩溃')
        except Exception as exc:          # pragma: no cover - 平台相关
            print(f'[rthook] 强制浅色外观失败（不阻断启动）: {exc}')

    # 必须在 Tk 之前
    try:
        _force_aqua_appearance()
    except Exception:
        pass

    def _bring_to_front():
        try:
            from AppKit import (
                NSApplication,
                NSApplicationActivationPolicyRegular,
            )
            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            app.activateIgnoringOtherApps_(True)
        except Exception:
            pass

    try:
        _bring_to_front()
    except Exception:
        pass
