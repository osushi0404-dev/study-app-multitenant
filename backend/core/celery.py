"""
Celery 設定

非同期タスク処理とスケジュールタスクのための設定
"""

import os
from celery import Celery
# Django設定モジュールを設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('learning_app')

# Django設定から設定値を読み込み
app.config_from_object('django.conf:settings', namespace='CELERY')

# タスクの自動検出
app.autodiscover_tasks()

# 定期タスクの設定
app.conf.beat_schedule = {
    # 毎日午前2時に学習分析データを更新
    'update-daily-analytics': {
        'task': 'studylogs.tasks.update_daily_analytics_task',
        'schedule': 30.0,  # 30秒ごと（開発環境用）
        # 'schedule': crontab(hour=2, minute=0),  # 本番環境では毎日午前2時
    },

    # 毎日午前7時に学習リマインダーを送信
    'send-study-reminders': {
        'task': 'studylogs.tasks.send_study_reminders_task',
        'schedule': 60.0,  # 1分ごと（開発環境用）
        # 'schedule': crontab(hour=7, minute=0),  # 本番環境では毎日午前7時
    },

    # 週1回間違いパターンを分析
    'analyze-mistake-patterns': {
        'task': 'studylogs.tasks.analyze_mistake_patterns_task',
        'schedule': 300.0,  # 5分ごと（開発環境用）
        # 'schedule': crontab(day_of_week=1, hour=3, minute=0),  # 本番環境では毎週月曜午前3時
    },

    # 期限切れの学習提案をクリーンアップ
    'cleanup-expired-suggestions': {
        'task': 'studylogs.tasks.cleanup_expired_suggestions_task',
        'schedule': 3600.0,  # 1時間ごと
        # 'schedule': crontab(minute=0),  # 本番環境では毎時0分
    },

    # キャッシュのメンテナンス
    'cache-maintenance': {
        'task': 'core.tasks.cache_maintenance_task',
        'schedule': 1800.0,  # 30分ごと
        # 'schedule': crontab(minute='*/30'),  # 本番環境では30分ごと
    },
}

app.conf.timezone = 'Asia/Tokyo'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
