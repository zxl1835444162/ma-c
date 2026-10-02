"""小说自动发布工具 - 核心包。

原 Windows 版本（app(1).exe，PyInstaller/Python 3.10）的包结构：

    novel_publisher/
        browser.py            浏览器启动与 CDP 接管
        chapter_files.py      章节文件读写、字数统计、重复内容检查
        config.py             PublishConfig 数据结构（15 元素元组兼容）
        create_book.py        从大纲/简介创建新书
        downloader.py         番茄/飞卢/起点小说下载
        logging_redirect.py   把 stdout/stderr 重定向到 tkinter 日志区
        navigation.py         各平台页面导航与浮层处理
        platforms.py          平台基类与注册表
        platforms/adapters.py 各平台 run() 到 automation_flow_by_* 的桥接
        sstory.py             番茄短故事自动发布
        tasks.py              定时任务注册表
        tasks/adapters.py     scheduled_* 方法到任务注册表的桥接
        tray.py               系统托盘图标
"""
