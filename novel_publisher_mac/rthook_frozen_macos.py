"""PyInstaller 运行时钩子（仅 macOS 挂载）。

解决两个打包后的实测问题：

1. **Playwright 的 node driver 丢可执行位**
   `playwright/driver/node` 是通过 collect_data_files 作为「数据文件」收集的，
   PyInstaller 拷进 .app 后不保证保留 +x 权限，导致启动时报
   `PermissionError: [Errno 13] Permission denied: '.../playwright/driver/node'`。
   这里在解释器启动最早期（任何 playwright 模块被导入之前）把权限补回去。

2. **macOS 上 tkinter 需要显式声明为前台进程**
   否则从终端/访达启动后窗口可能落在其他应用后面，用户以为「双击没反应」。
   同时把 Tcl/Tk 的缩放调到与 Retina 匹配。
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
