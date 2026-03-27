# Celery アプリを Django 起動時にロードして shared_task が利用できるようにする
from .celery import app as celery_app

__all__ = ('celery_app',)
