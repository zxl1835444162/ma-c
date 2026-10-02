'''任务适配器：将现有的 scheduled_* 方法桥接到任务注册表。'''

from novel_publisher import tasks as _tasks
register_task = _tasks.register_task

def scheduled_publish(app):

    app.scheduled_publish()

scheduled_publish = register_task('本地定时发布')(scheduled_publish)

def scheduled_sign(app):

    app.scheduled_sign()

scheduled_sign = register_task('自动签约')(scheduled_sign)

def scheduled_verify(app):

    app.scheduled_verify()

scheduled_verify = register_task('自动验证')(scheduled_verify)

def publish_sstory(app):

    app.publish_sstory()

publish_sstory = register_task('短故事发布', threaded=False)(publish_sstory)

def scheduled_publish_story_batch(app):

    app.scheduled_publish_story_batch()

scheduled_publish_story_batch = register_task('短故事批量发布')(scheduled_publish_story_batch)

def schedule_command_by_name(app):

    app.schedule_command_by_name()

schedule_command_by_name = register_task('书测')(schedule_command_by_name)

def schedule_command_by_cover(app):

    app.schedule_command_by_cover()

schedule_command_by_cover = register_task('封测')(schedule_command_by_cover)

def schedule_check_attendance(app):

    app.schedule_check_attendance()

schedule_check_attendance = register_task('全勤检查')(schedule_check_attendance)

def process_check(app):

    app.process_check()

process_check = register_task('发布进度自检')(process_check)

def cancel_scheduled_task(app):

    app.cancel_scheduled_task()

cancel_scheduled_task = register_task('取消定时')(cancel_scheduled_task)

def create_book_from_outline(app):

    app.create_book_from_outline()

create_book_from_outline = register_task('快速创书')(create_book_from_outline)
