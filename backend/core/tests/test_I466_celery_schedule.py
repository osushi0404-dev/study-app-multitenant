"""
I466: 定期処理（celery beat）の予定

- どの予定も時刻（crontab）で決まる（開発用の秒の間隔に戻さない。リマインダーのメールが 1 分ごとに送られた）
- 登録したタスクが実在する（消したタスクを指したままにしない）

TC-32（docs/tests/open/I466_auto_test.md）に対応。時刻の値そのものはテストに写さない（設定の写しになるため）。
"""
import importlib

from celery.schedules import crontab

from core.celery import app

REMOVED = {"analyze-mistake-patterns", "cleanup-expired-suggestions", "send-study-reminders"}  # I492


def _non_crontab(schedule):
    return sorted(name for name, entry in schedule.items()
                  if not isinstance(entry["schedule"], crontab))


def _missing_tasks(schedule):
    missing = []
    for name, entry in schedule.items():
        module_name, _, func_name = entry["task"].rpartition(".")
        try:
            func = getattr(importlib.import_module(module_name), func_name)
        except (ImportError, AttributeError):
            missing.append(name)
            continue
        if not hasattr(func, "delay"):
            missing.append(name)
    return sorted(missing)


def test_every_schedule_is_a_crontab():
    assert _non_crontab(app.conf.beat_schedule) == []


def test_every_scheduled_task_exists():
    assert _missing_tasks(app.conf.beat_schedule) == []


def test_removed_schedules_are_gone():
    assert not REMOVED & set(app.conf.beat_schedule)


def test_checks_catch_interval_and_missing_task():
    """失敗の注入: 秒の間隔と、消したタスクを指す予定を足すと、それぞれ見つかる"""
    broken = dict(app.conf.beat_schedule)
    broken["dev-interval"] = {"task": "core.tasks.cache_maintenance_task", "schedule": 30.0}
    broken["gone"] = {
        "task": "studylogs.tasks.analyze_mistake_patterns_task", "schedule": crontab(minute=0)}
    assert _non_crontab(broken) == ["dev-interval"]
    assert _missing_tasks(broken) == ["gone"]
