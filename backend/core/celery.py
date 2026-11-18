"""
Celery 設定

非同期タスク処理とスケジュールタスクのための設定
"""

import os
from celery import Celery
from celery.schedules import crontab
# Django設定モジュールを設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('learning_app')

# Django設定から設定値を読み込み
app.config_from_object('django.conf:settings', namespace='CELERY')

# タスクの自動検出
app.autodiscover_tasks()

# 定期タスクの設定（時刻は app.conf.timezone の日本時間）
# 間隔は crontab の時刻で決める。開発の都合で秒の間隔に変えない（学習リマインダーのメールが 1 分ごとに
# 送られうる。I466）。タスクを消したら、ここからも外す（core/tests/test_I466_celery_schedule.py が見る）
app.conf.beat_schedule = {
    # 毎日午前2時に学習分析データを更新
    'update-daily-analytics': {
        'task': 'studylogs.tasks.update_daily_analytics_task',
        'schedule': crontab(hour=2, minute=0),
    },

    # 毎日午前7時に学習リマインダーを送信
    'send-study-reminders': {
        'task': 'studylogs.tasks.send_study_reminders_task',
        'schedule': crontab(hour=7, minute=0),
    },

    # 30分ごとにキャッシュのメンテナンス
    'cache-maintenance': {
        'task': 'core.tasks.cache_maintenance_task',
        'schedule': crontab(minute='*/30'),
    },
}

app.conf.timezone = 'Asia/Tokyo'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
