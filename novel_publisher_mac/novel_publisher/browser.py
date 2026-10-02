'''浏览器启动与管理'''

import os

import requests

from playwright.sync_api import sync_playwright

BROWSER_ARGS = [

    '--disable-popup-blocking',

    '--disable-web-security',

    '--disable-features=IsolateOrigins,site-per-process',

    '--disable-blink-features=AutomationControlled']

BROWSER_IGNORE_ARGS = [

    '--enable-automation']

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def open_browser(p = None, custom_browser_path = None, keep_browser_open = None, auth_file = None, on_browser_not_found = None):

    '''打开浏览器，返回 (browser, context)。


    - 如果 custom_browser_path 是纯数字，采用 CDP 接管模式（端口连接）。

    - 否则使用指定路径启动新浏览器实例。

    '''

    if custom_browser_path.isdigit():

        try:

            requests.get(f'http://localhost:{custom_browser_path}/json/version', timeout=5)

        except Exception:

            print('错误：指定浏览器未开启')

            if on_browser_not_found:

                on_browser_not_found()

        print(f'采用浏览器接管模式，端口号：{custom_browser_path}')

        cdp_url = f'http://localhost:{custom_browser_path}/'

        browser = p.chromium.connect_over_cdp(cdp_url)

        return (browser, browser.contexts[0])

    browser = p.chromium.launch(headless=keep_browser_open, executable_path=custom_browser_path, args=BROWSER_ARGS, ignore_default_args=BROWSER_IGNORE_ARGS)

    # 登录态文件缺失时按「未登录」处理，否则 Playwright 会抛 FileNotFoundError
    usable_auth = auth_file if (auth_file and os.path.exists(auth_file)) else None
    if auth_file and usable_auth is None:
        print(f'未找到登录状态文件 {auth_file}，以未登录状态打开浏览器')
    context = browser.new_context(user_agent=DEFAULT_USER_AGENT, storage_state=usable_auth)

    return (browser, context)


def launch_browser_for_sstory(p = None, browser_path = None, auth_file = None):

    '''为短故事发布启动浏览器（headless=False，不使用 CDP）。'''

    browser = p.chromium.launch(headless=False, executable_path=browser_path if browser_path else None, args=BROWSER_ARGS, ignore_default_args=BROWSER_IGNORE_ARGS)

    if not os.path.exists(auth_file):

        from tkinter import messagebox

        messagebox.showerror('错误', f'''未找到认证文件 {auth_file} 请先执行登录操作''')

        return (None, None)

    context = browser.new_context(user_agent=DEFAULT_USER_AGENT, storage_state=auth_file)

    return (browser, context)


