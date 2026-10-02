# 寒山小说发布工具 · macOS 版

从 Windows 版 `app(1).exe`（PyInstaller + Python 3.10 + tkinter + Playwright）逆向还原并移植到 macOS。

原始程序是一个网文自动发布工具，支持番茄 / 起点 / 七猫 / 飞卢 / 微信 / 书旗 / 晋江 / 息壤 / 咪咕
九个平台，通过 Playwright 驱动真实浏览器完成登录、建书、发章节、自动签约、全勤检查等流程。

---

## 怎么拿到 macOS 应用

### 方式一：用本仓库的 GitHub Actions 自动构建（推荐，不需要 Mac）

1. 打开本仓库的 **Actions** 标签页
2. 左侧选「**构建 macOS 应用**」
3. 右侧点「**Run workflow**」，架构选 `arm64`（Apple Silicon）或 `x86_64`（老 Intel Mac）
4. 等 5-10 分钟
5. 在该次运行的 **Artifacts** 区下载 `寒山小说发布工具-macOS-arm64.zip`
6. 解压得到 `寒山小说发布工具.app`，拷到 Mac 双击

> 公开仓库的 macOS runner 免费无限量。构建发生在 GitHub 托管的真 macOS 机器上，
> 产出的是**自包含**的 .app（内置 Python 运行时），不依赖目标机器上装没装 Python。

### 方式二：在 Mac 上本地构建

```bash
cd novel_publisher_mac
chmod +x *.sh *.command assets/*.sh
./build_mac.sh
```

前置条件：Mac 上要有带 tkinter 的 Python 3.10
（[官网安装包](https://www.python.org/downloads/release/python-31011/) 自带；
Homebrew 需 `brew install python@3.10 python-tk@3.10`）。

### 方式三：不打包，直接跑

```bash
cd novel_publisher_mac
chmod +x 启动.command
./启动.command
```

---

## 首次打开被 macOS 拦截怎么办

CI 构建出来的 .app 是 **ad-hoc 签名**（`codesign --sign -`），不是 Apple 签发的
开发者证书。所以第一次打开会弹：

> Apple 无法验证"寒山小说发布工具"是否包含可能危害 Mac 安全或泄漏隐私的恶意软件。

**这是正常的**，不是文件损坏，也不是打包出错。原因是 Gatekeeper 要求的是
**开发者证书签名 + Apple 公证（notarization）**，而这两样都需要付费开发者账号。

### 解法一：命令行解除隔离（最快，所有 macOS 版本都有效）

```bash
xattr -dr com.apple.quarantine ~/Downloads/寒山小说发布工具.app
```

路径按实际情况改。不确定路径时：在终端里敲 `xattr -dr com.apple.quarantine ` （末尾留空格），
然后把 .app 从访达拖进终端窗口，路径会自动补全，回车即可。

再双击就能打开了。

### 解法二：图形界面

| 你的 macOS | 操作 |
|---|---|
| **macOS 14 Sonoma 及更早** | 右键（或 Control+点击）App → **打开** → 弹出框里再点 **打开** |
| **macOS 15 Sequoia 及更新** | 右键 → 打开 **已被 Apple 移除**。<br>改为：先双击 App 让它弹一次拦截 → 打开 **系统设置 → 隐私与安全性** → 往下滚到「安全性」→ 找到被拦的 App → 点 **仍要打开** → 输入密码确认 |

> macOS 15 移除右键绕过是 Apple 2024 年的收紧策略，对所有未公证软件一视同仁。

### 解法三：彻底解决（需要 Apple Developer 账号）

签名 + 公证后，任何人打开都不会再被拦。本项目的工作流已经预留了这条通道：

1. 准备三样东西：
   - Apple Developer Program 会员（$99/年）
   - `Developer ID Application` 证书（在 Apple 开发者后台创建并导出 .p12）
   - App 专用密码（appleid.apple.com → 登录与安全 → App 专用密码）

2. 在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加：

   | Secret 名 | 值 |
   |---|---|
   | `MACOS_CERT_P12` | 证书 .p12 的 base64（`base64 -i cert.p12 \| pbcopy`） |
   | `MACOS_CERT_PASSWORD` | 导出 .p12 时设的密码 |
   | `APPLE_ID` | 你的 Apple ID |
   | `APPLE_TEAM_ID` | 开发者团队 ID（10 位） |
   | `APPLE_APP_PASSWORD` | App 专用密码 |

3. 重新运行工作流，勾选 `notarize`。构建会走
   `codesign --options runtime` → `notarytool submit --wait` → `stapler staple`，
   产出可直接分发的 .app。

没配这些 secret 时，工作流自动跳过公证步骤，仍产出 ad-hoc 签名的版本。

### 顺便说：这不是"不安全"

这个 App 做的事情就是驱动你自己的浏览器去网文平台发章节，不联网上报任何数据，
不写系统目录，所有可写文件都在 `~/Library/Application Support/寒山小说发布工具/`。
源码全部在本仓库里，你可以自己 `grep` 检查。


---

## 数据目录

应用的可写文件都在 App 包外面：

```
~/Library/Application Support/寒山小说发布工具/
├── config.ini           界面配置
├── auth.json            登录态（Playwright storage_state）
├── 签约信息.txt          自动签约用
├── Shortcuts/
│   ├── contrast.json    笔名 → 调试端口 映射
│   └── <笔名>.command   「浏览器分身」启动器（Windows 版是 .lnk）
└── <端口>/              各分身的浏览器 user-data-dir
```

彻底重置：删掉整个目录即可。

---

## 工程结构

```
.
├── .github/workflows/build-macos.yml    CI：用 macOS runner 打包 .app
└── novel_publisher_mac/
    ├── app.py                           主程序（5700+ 行，135 个函数/方法）
    ├── novel_publisher/                 13 个业务模块
    ├── macos_support.py                 macOS 平台适配层
    ├── platform_patch.py                启动时替换 Windows 专有实现
    ├── browser_detector.py              Chrome/Edge/Chromium 探测
    ├── novel_publisher_mac.spec         PyInstaller 配置
    ├── rthook_frozen_macos.py           macOS 运行时钩子
    ├── gen_icns.py                      纯 Python 生成 .icns
    ├── build_mac.sh / make_dmg.sh       打包脚本
    ├── selftest_business.py             业务自检
    └── README_MAC_BUILD.md              完整打包与排错文档
```

---

## macOS 与原版的差异

| 项 | Windows 原版 | macOS 版 |
|---|---|---|
| 创建分身 | `.lnk`（win32com） | `.command` 脚本（启动参数完全一致） |
| 打开文件/目录 | `os.startfile` | `open` / `open -R` |
| 数据目录 | `%APPDATA%\寒山小说发布工具` | `~/Library/Application Support/寒山小说发布工具` |
| 托盘图标 | `icon.run()` 子线程 | `run_detached(darwin_nsapplication=NSApp)` |
| 结束占用进程 | `taskkill` | `os.kill(pid, 15)` |
| 界面字体 | 微软雅黑 | PingFang SC |

---

## 说明

本工具仅用于学习和研究。还原与移植过程严格以原始字节码为准：
`app.py` 中 134 个 code object 全部在场，83/134 的 `co_code` 逐字节相同，
127/134 的函数签名完全相同，135 处关键字调用参数与原始字节码一致。
