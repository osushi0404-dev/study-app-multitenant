# I151 TC-AUTO-10 判定 3・4 用: beat スケジュールの全タスクを、ログの時間窓に頼らずに確かめる
# 実行（リポジトリのルートで 1 行のコマンドとして実行する）:
#   docker compose exec -T backend python manage.py shell
#     < docs/tests/open/I151_celery_probe.py > /tmp/i151_celery_probe.txt 2>&1
# 出力の各行は TC-AUTO-10 の判定式で照合する（このファイル自体は合否を決めない）
import logging
import sys

from django.conf import settings
from django.test.utils import override_settings

from core.celery import app

# 開発環境（手元の compose・DEBUG=True）専用。本番相当の環境では、スケジュール外の時刻に定期処理が増えるので実行しない
if not settings.DEBUG:
    print('NG PROBE ABORTED: settings.DEBUG is False (development only)')
    sys.exit(0)

# 更新前（develop・Django 4.2.30）でも未登録だったことを実測した既知の既存不具合（2026-10-16）。
# 根治イシューのマージ時に空にし、TC-AUTO-10 判定 3s・4a の期待値（SCHEDULED / SUMMARY の件数）も改める
KNOWN_UNREGISTERED = {'core.tasks.cache_maintenance_task'}

# 外部へ実際に送信するタスク。worker で動かすと SMTP（SendGrid）で実在のアドレスへメールが送られうるため、
# このスクリプトが足す 1 回分は、このプロセス内でメールをメモリに溜める設定にして実行する
# （backend と worker は別イメージだが、依存の版は一致する）。beat の定期実行は対象外で、worker は SMTP のまま
RUN_LOCALLY_WITHOUT_SENDING = {'studylogs.tasks.send_study_reminders_task'}


class _ErrorCounter(logging.Handler):
    """実行中に出た ERROR 以上のログを数える（ユーザー単位の失敗を戻り値に出さないタスク向け）"""

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.count = 0

    def emit(self, record):
        self.count += 1


app.loader.import_default_modules()  # worker 起動時と同じタスクの読み込み（ローカル実行のため）

scheduled = sorted({entry['task'] for entry in app.conf.beat_schedule.values()})
targets = [name for name in scheduled if name not in KNOWN_UNREGISTERED]
print(f'SCHEDULED {len(scheduled)} TARGETS {len(targets)}')

# 判定 3: 応答した worker ごとに、スケジュールされた対象タスクの登録漏れを出す
replies = app.control.inspect(timeout=10).registered() or {}
print(f'NODES {len(replies)}')
for node, registered in sorted(replies.items()):
    missing = [name for name in targets if name not in registered]
    print(f'NODE {node} MISSING {",".join(missing) or "-"}')

# 判定 4: 対象タスクを実際に実行し、戻り値（と、ローカル実行分はエラーログ）を検査する。
# 'error' キー（タスク全体の失敗）と 0 でない error_count（ユーザー単位の失敗の件数）を NG にする。
# worker で実行したタスクのエラーログは、このスクリプトの後に取る celery ログの判定 2a・2b で拾う
ok = 0
for name in targets:
    local_errors = 0
    try:
        if name in RUN_LOCALLY_WITHOUT_SENDING:
            counter = _ErrorCounter()
            logging.getLogger().addHandler(counter)
            try:
                with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
                    result = app.tasks[name].apply().get()
            finally:
                logging.getLogger().removeHandler(counter)
            local_errors = counter.count
            where = 'LOCAL'
        else:
            result = app.send_task(name).get(timeout=60)
            where = 'WORKER'
    except Exception as exc:  # 未登録・タイムアウト・タスク内の未捕捉例外
        print(f'NG {name} EXC {type(exc).__name__}: {exc}')
        continue
    failed = (
        not isinstance(result, dict)
        or 'error' in result
        or result.get('error_count', 0) != 0
        or local_errors != 0
    )
    if failed:
        print(f'NG {name} {where} RESULT {result} ERROR_LOGS {local_errors}')
    else:
        ok += 1
        print(f'OK {name} {where} {result}')
print(f'SUMMARY targets={len(targets)} ok={ok}')
