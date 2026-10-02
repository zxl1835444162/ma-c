# macOS 打包与运行说明

> `寒山小说发布工具` v2.2.8 —— 由 Windows 版 `app(1).exe` 逆向还原并移植到 macOS。

---

## 0. 一个必须先说清楚的硬事实

**PyInstaller 不支持交叉编译。**
在 Windows / Linux 上跑 `build_mac.sh` 打不出能运行的 `.app`，必须在 **macOS 机器**上执行。

所以本工程交付的是一条「拿到 Mac 上敲一条命令就出包」的流水线：

```
Windows 上：把 novel_publisher_mac/ 整个目录拷到 Mac
Mac 上：    chmod +x *.sh *.command && ./build_mac.sh
```

工程根目录里所有脚本都做了平台自检——在非 macOS 上会直接告诉你原因并退出，不会给你一个坏包。

**打包流水线本身已在实机验证过**：本项目用同一份 `novel_publisher_mac.spec` 在 Windows 上
跑通了完整构建（Analysis → EXE → COLLECT），产物 `寒山小说发布工具.exe` 启动正常、
界面完整、配置正确加载（详见 `re/out/screenshot_frozen_build.png`）。
同一份 spec 在 macOS 上会额外走 `BUNDLE` 分支产出 `.app`。

---

## 1. 两条路线，按需选

| | 路线 A：打包成 .app | 路线 B：免打包直接跑 |
|---|---|---|
| 命令 | `./build_mac.sh` | 双击 `启动.command` |
| 耗时 | 首次 5-10 分钟 | 首次 1-3 分钟 |
| 产物 | `dist/寒山小说发布工具.app` | 无（直接跑源码） |
| 适合 | 交付给别人、做 dmg、长期使用 | 自己调试、打包出问题时兜底 |

两条路都用各自的虚拟环境（`.venv-build` / `.venv-run`），互不干扰。

---

## 2. 路线 A：打包成 .app

### 前置：装 Python 3.10（必须带 tkinter）

**方式一：官网安装包（推荐，自带 tkinter）**

1. 打开 <https://www.python.org/downloads/release/python-31011/>
2. 下载 **macOS 64-bit universal2 installer**
3. 安装

**方式二：Homebrew**

```bash
brew install python@3.10 python-tk@3.10
```

> Homebrew 的 python **不带 tkinter**，必须额外装 `python-tk@3.10`，否则打包出来的
> App 一打开就闪退。`build_mac.sh` 会在打包前检查这一点并明确报错。

### 执行

```bash
cd novel_publisher_mac

# 首次需要赋予脚本可执行权限
chmod +x build_mac.sh make_dmg.sh 启动.command assets/make_icns.sh

# 一键打包
./build_mac.sh
```

脚本会自动完成 8 步：平台检查 → 探测解释器 → 建虚拟环境 → 装依赖 →
语法与依赖冒烟测试 → 生成图标 → PyInstaller 构建 → 修权限/签名 → 产物自检。

### 指定架构

```bash
TARGET_ARCH=arm64      ./build_mac.sh   # Apple Silicon
TARGET_ARCH=x86_64     ./build_mac.sh   # Intel
TARGET_ARCH=universal2 ./build_mac.sh   # 通用二进制（需 universal2 版 Python）
```

### 顺带出 DMG

```bash
MAKE_DMG=1 ./build_mac.sh
# 或打包完成后单独执行
./make_dmg.sh
```

产物：`dist/寒山小说发布工具-2.2.8.dmg`，内含 App 与「应用程序」快捷方式，拖拽即安装。

---

## 3. 路线 B：免打包直接跑（备用）

双击 `启动.command` 即可。首次会自动建 `.venv-run` 并安装依赖。

macOS 可能会拦：**右键 → 打开 → 再点「打开」**；或先在终端执行一次

```bash
chmod +x 启动.command
```

---

## 4. 首次打开被 Gatekeeper 拦截怎么办

`build_mac.sh` 默认做 **ad-hoc 签名**（`codesign --sign -`）。这在**本机**能正常打开，
但拷贝到**别人机器**上仍会被拦，因为不是 Apple 签发的开发者证书。

本机自测，遇到「无法验证开发者」：

- 图形界面：**右键 App → 打开 → 打开**
- 或命令行：

```bash
xattr -dr com.apple.quarantine "dist/寒山小说发布工具.app"
```

对外分发需要 Apple Developer 账号（$99/年）：

```bash
export SIGN_ID="Developer ID Application: 你的名字 (TEAMID)"
export NOTARIZE=1
export APPLE_ID="你的@apple.id"
export APPLE_TEAM_ID="TEAMID"
export APPLE_APP_PASSWORD="app-specific-password"

MAKE_DMG=1 ./build_mac.sh
```

脚本会走完整链路：`codesign --options runtime` → `notarytool submit --wait` → `stapler staple`。

---

## 5. 数据目录

应用所有可写文件都在 App 包外面，**不依赖 App 所在位置**：

```
~/Library/Application Support/寒山小说发布工具/
├── config.ini          # 界面配置
├── auth.json           # 登录态（Playwright storage_state）
├── 签约信息.txt        # 自动签约用（自己按格式建）
├── Shortcuts/
│   ├── contrast.json   # 笔名 -> 调试端口 映射
│   └── <笔名>.command  # 「浏览器分身」启动器（Windows 版是 .lnk）
└── <端口>/             # 各分身的浏览器 user-data-dir
```

> 从源码目录运行时，若同目录下有旧版 `config.ini` / `auth.json` / `签约信息.txt`，
> 启动时会自动迁移到上面这个目录一次（`macos_support.migrate_legacy_files`）。

想彻底重置：直接删掉上面整个目录。

---

## 6. 打包后的已知行为差异

| 项 | Windows 原版 | macOS 移植版 | 说明 |
|---|---|---|---|
| 创建分身 | `.lnk` 快捷方式（win32com） | `.command` 脚本 | 启动参数完全一致：`--remote-debugging-port --user-data-dir --new-window` |
| 打开文件/目录 | `os.startfile` | `open` / `open -R` | |
| 数据目录 | `%APPDATA%\寒山小说发布工具` | `~/Library/Application Support/寒山小说发布工具` | |
| 托盘图标 | `icon.run()` 子线程 | `run_detached(darwin_nsapplication=NSApp)` | macOS 上 pystray 必须挂到 NSApplication |
| 结束占用进程 | `taskkill` | `os.kill(pid, 15)`（`ps` 查找） | |
| 界面字体 | 微软雅黑 | PingFang SC | 原版字体 macOS 没有 |
| 调试代码 | 内置 | 已剥离（`debug()` 不再触发 breakpoint） | |

---

## 7. 常见问题

**Q：`build_mac.sh` 报「没找到带 tkinter 的 Python 3.10」**
按第 2 节装官网版 Python 3.10，或 `brew install python-tk@3.10`。
也可以显式指定：`PYTHON=/usr/local/bin/python3.10 ./build_mac.sh`。

**Q：App 打开闪退 / 没有窗口**
多半是 tkinter 没打进去。在终端直接跑二进制看报错：

```bash
dist/寒山小说发布工具.app/Contents/MacOS/寒山小说发布工具
```

**Q：提示 `Permission denied: .../playwright/driver/node`**
这是 PyInstaller 的已知问题（数据文件丢可执行位）。本工程已用
`rthook_frozen_macos.py` 在启动时自动 `chmod +x` 修复。
若仍出现，手动执行：

```bash
chmod +x "dist/寒山小说发布工具.app/Contents/Frameworks/playwright/driver/node"
```

**Q：包体积多大？**
约 150-200MB（Playwright 的 node driver 本体就接近 100MB）。
浏览器二进制**没有**打进去——应用首次运行时会用它自带的
「自动检测」找你机器上的 Chrome / Edge；找不到时才会用 Playwright 内置 chromium，
那需要联网执行一次 `python3.10 -m playwright install chromium`。

**Q：能打出 Windows 版吗？**
能，同一份 spec 在 Windows 上执行即可（已验证），但同样**必须在该平台上构建**。

**Q：`.command` 双击没反应？**
macOS 首次会拦截未签名的脚本。终端执行一次 `chmod +x 启动.command`，
之后右键 → 打开。

---

## 8. 工程文件一览（打包相关）

```
novel_publisher_mac/
├── app.py                       主程序（5715 行，135 个函数/方法）
├── novel_publisher/             13 个业务模块
├── macos_support.py             macOS 平台适配层（.command/打开/进程/托盘）
├── platform_patch.py            启动时把 Windows 专有方法替换为跨平台实现
├── browser_detector.py          Chrome/Edge/Chromium 探测（含 macOS 路径）
├── icon.py                      base64 内嵌图标
├── font_map.py                  字体映射
├── novel_publisher_mac.spec     PyInstaller 配置（本文件，macOS/Windows 通用）
├── rthook_frozen_macos.py       macOS 运行时钩子（修 node 可执行位 + 前台激活）
├── build_mac.sh                 一键打包（8 步流水线）
├── make_dmg.sh                  产出 .dmg
├── 启动.command                 免打包启动器（备用路线）
├── assets/
│   ├── app_icon.png             图标源图
│   └── make_icns.sh             PNG -> .icns（macOS sips + iconutil）
├── requirements-mac.txt         macOS 依赖
├── selftest_business.py         业务自检（含平台调用契约校验）
└── run_dev_mac.sh               开发期热运行（不建 venv）
```

---

## 9. 打包前建议先跑一次自检

```bash
python3.10 selftest_business.py
```

应输出 `全部自检通过`。它会校验 config 容器、章节文件二元组契约、
任务注册表、平台注册表、9 条平台发布调用链的实参个数、日志重定向。
