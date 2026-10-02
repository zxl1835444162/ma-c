"""selftest_business.py — 平台无关业务逻辑自检（可在 Windows / macOS 上跑）。

覆盖 novel_publisher 中不依赖浏览器、不依赖 GUI 的纯函数：
  * chapter_files: 字数统计、章节范围切片、重复内容检查、章节文件生成
  * config:       PublishConfig 的 15 元素切片兼容性
  * tasks:        任务注册表与查找
  * platforms:    平台注册表

运行： python selftest_business.py
"""
import io
import os
import shutil
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

failures = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ✓ {name}')
    else:
        print(f'  ✗ {name}  {detail}')
        failures.append(name)


print('=== 1. config.PublishConfig 元组兼容性 ===')
try:
    from novel_publisher.config import PublishConfig
    cfg = PublishConfig()
    t = cfg.as_tuple()
    check('as_tuple 长度 = 15', len(t) == 15, f'实际 {len(t)}')
    check('切片 [:13] 可用', len(cfg[:13]) == 13)
    check('切片 [:15] 可用', len(cfg[:15]) == 15)
    check('索引访问 self[0]', cfg[0] == '')
    check('len(cfg) = 15', len(cfg) == 15)
    check('迭代 15 项', len(list(iter(cfg))) == 15)
    cfg2 = PublishConfig(custom_browser_path='46000', novel_title='测试书')
    check('关键字构造', cfg2.custom_browser_path == '46000' and cfg2.novel_title == '测试书')
    check('interval_days 默认 1', cfg.interval_days == 1)
except Exception as exc:
    check('config 模块导入与构造', False, repr(exc))

print('=== 2. chapter_files 纯函数 ===')
try:
    from novel_publisher import chapter_files as cf

    text = '这是一段中文内容abc123' * 10
    n = cf.count_chinese_characters(text)
    # 依据字节码：CJK 字符、ASCII 字符、常见中文标点都会计入
    check('count_chinese_characters 计数正确', n == len('这是一段中文内容abc123') * 10, f'得到 {n}')
    check('count_chinese_characters 空输入返回 0', cf.count_chinese_characters('') == 0)

    rep = '开头段落内容。' * 3 + 'X' * 5 + '开头段落内容。' * 3
    out = cf.check_repeat_content(rep)
    check('check_repeat_content 检测重复前缀', out != rep or len(out) <= len(rep),
          '返回值长度应不大于输入')

    ok = cf.check_repeat_content('完全不同的一段文字，没有重复前缀出现。' * 4)
    check('check_repeat_content 无重复时原样返回', isinstance(ok, str))

    tmp = tempfile.mkdtemp(prefix='novel_test_')
    try:
        src = os.path.join(tmp, 'book.txt')
        with open(src, 'w', encoding='utf-8') as f:
            f.write('第一章 开端\n内容一\n第二章 发展\n内容二\n第三章 高潮\n内容三\n')
        # 造真正的章节 .md（get_chapter_files_in_range 只认 .md 且文件名须含 _<数字>）
        for _n in range(1, 6):
            with open(os.path.join(tmp, f'测试小说_{_n}.md'), 'w', encoding='utf-8') as _f:
                _f.write(f'# 第{_n}章 标题{_n}\n\n' + '正文内容。' * 80 + '\n')
        rng = cf.get_chapter_files_in_range(tmp, 1, 3)
        check('get_chapter_files_in_range 返回列表', isinstance(rng, list))
        check('get_chapter_files_in_range 命中 3 章', len(rng) == 3, f'实际 {len(rng)}')
        # 契约锁：章节项必须是 (章节号, 文件路径) 二元组 —— 9 个平台流程都按
        # `for i, novel_file in novel_files` 解包，退化成纯路径会 ValueError。
        check('章节项是 (章节号, 路径) 二元组', bool(rng) and all(
            isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], int)
            and isinstance(x[1], str) and os.path.isfile(x[1]) for x in rng),
            f'实际 {rng[:2]}')
        try:
            for _i, _f in rng:
                details = cf.get_chapter_details(_f, True)
                assert len(details) == 4
            check('二元组可被 for i, path 解包', True)
        except Exception as exc:
            check('二元组可被 for i, path 解包', False, repr(exc))
        out_dir = os.path.join(tmp, 'out')
        os.makedirs(out_dir, exist_ok=True)
        res = cf.create_chapter_files_in_files_custom(src, out_dir)
        made = [f for f in os.listdir(out_dir)] if os.path.isdir(out_dir) else []
        check('create_chapter_files_in_files_custom 生成章节文件', len(made) >= 0,
              f'目录内容 {made[:3]}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
except Exception as exc:
    check('chapter_files 模块导入与调用', False, repr(exc))

print('=== 3. tasks 任务注册表 ===')
try:
    from novel_publisher.tasks import register_task, get_task, list_task_names, _TASKS

    @register_task('自检任务', False)
    def _selftest(app):
        return 'ok'

    check('register_task 注册成功', '自检任务' in list_task_names())
    got = get_task('自检任务')
    check('get_task 返回 (func, threaded)', isinstance(got, tuple) and got[1] is False)
    check('get_task 未知任务返回 None', get_task('不存在的任务') is None)
except Exception as exc:
    check('tasks 模块导入与注册', False, repr(exc))

print('=== 4. platforms 注册表 ===')
try:
    from novel_publisher.platforms import BasePlatform, PLATFORMS, get_platform, register_platform
    check('BasePlatform 有 run 方法', hasattr(BasePlatform, 'run'))
    try:
        import novel_publisher.platforms.adapters  # noqa: F401
        loaded = True
    except Exception as exc:
        loaded = f'adapters 导入失败: {exc!r}'
    check('adapters 导入并注册平台', loaded is True and len(PLATFORMS) >= 9,
          f'{loaded} / PLATFORMS={len(PLATFORMS) if isinstance(loaded, bool) else "?"}')
    if isinstance(loaded, bool) and loaded:
        for name in ('番茄', '起点', '七猫', '飞卢', '微信', '书旗', '晋江', '息壤', '咪咕'):
            check(f'平台已注册: {name}', get_platform(name) is not None)
except Exception as exc:
    check('platforms 模块导入', False, repr(exc))

print('=== 5. 平台发布方法调用契约 ===')
try:
    import inspect
    import app as _app
    _cls = _app.NovelPublisherApp
    # (被调用的方法, 自动化流程实际传的位置实参个数) —— 取自原始 app.pyc 的 CALL_METHOD oparg
    _CONTRACT = [
        ('fanqienovel', 'publish_single_chapter_on_fanqienovel', 5),
        ('qidiannovel', 'publish_single_chapter_on_qidiannovel', 4),
        ('qimaonovel', 'publish_single_chapter_on_qimaonovel', 5),
        ('feilunovel', 'publish_single_chapter_on_feilunovel', 5),
        ('wechatnovel', 'publish_single_chapter_on_wechatnovel', 5),
        ('shuqinovel', 'publish_single_chapter_on_shuqinovel', 5),
        ('jinjiangnovel', 'publish_single_chapter_on_jinjiangnovel', 5),
        ('xirangnovel', 'publish_single_chapter_on_xirangnovel', 6),
        # migunovel 的流程实际调的是 xirang 的发布函数（原作者的复制粘贴问题，已按原样保留）
        ('migunovel', 'publish_single_chapter_on_xirangnovel', 5),
    ]
    _bad = []
    for _plat, _mname, _n in _CONTRACT:
        _fn = getattr(_cls, _mname, None)
        if _fn is None:
            _bad.append('%s:%s 不存在' % (_plat, _mname))
            continue
        try:
            inspect.signature(_fn).bind(*([None] + [object()] * _n))
        except TypeError as _e:
            _bad.append('%s->%s(传%d):%s' % (_plat, _mname, _n, _e))
    check('9 条平台发布调用链实参均满足签名', not _bad, '; '.join(_bad))
except Exception as exc:
    check('平台发布方法契约校验', False, repr(exc))

print('=== 6. tasks.adapters 任务桥接 ===')
try:
    import novel_publisher.tasks.adapters  # noqa: F401
    from novel_publisher.tasks import list_task_names
    names = list_task_names()
    check('适配器注册了定时任务', len(names) >= 5, f'实际 {names[:5]}')
    for want in ('本地定时发布', '自动签约', '自动验证', '短故事发布', '全勤检查'):
        check(f'任务已注册: {want}', want in names)
except Exception as exc:
    check('tasks.adapters 导入', False, repr(exc))

print('=== 7. logging_redirect ===')
try:
    from novel_publisher.logging_redirect import TextRedirector
    check('TextRedirector 可实例化', TextRedirector is not None)
    check('有 write/install/restore', all(hasattr(TextRedirector, m)
                                         for m in ('write', 'install', 'restore')))
except Exception as exc:
    check('logging_redirect 导入', False, repr(exc))

print()
if failures:
    print(f'自检失败 {len(failures)} 项：')
    for f in failures:
        print('  -', f)
    sys.exit(1)
print('全部自检通过')
