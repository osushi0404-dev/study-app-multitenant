# I151 TC-AUTO-10 判定 3・4 用: beat スケジュールの全タスクを、ログの時間窓に頼らずに確かめる
# 実行: docker compose exec -T backend python manage.py shell < docs/tests/open/I151_celery_probe.py > /tmp/i151_celery_probe.txt 2>&1
# 出力の各行は TC-AUTO-10 の判定式で照合する（このファイル自体は合否を決めない）
from core.celery import app

# I151 診断（docs/reviews/I151_fix_diagnosis_20261016_1740.md）の既知の既存不具合。根治イシューのマージ時に空にする
KNOWN_UNREGISTERED = {'core.tasks.cache_maintenance_task'}

scheduled = sorted({entry['task'] for entry in app.conf.beat_schedule.values()})
targets = [name for name in scheduled if name not in KNOWN_UNREGISTERED]
print(f'SCHEDULED {len(scheduled)} TARGETS {len(targets)}')

# 判定 3: 応答した worker ごとに、スケジュールされた対象タスクの登録漏れを出す
replies = app.control.inspect(timeout=10).registered() or {}
print(f'NODES {len(replies)}')
for node, registered in sorted(replies.items()):
    missing = [name for name in targets if name not in registered]
    print(f'NODE {node} MISSING {",".join(missing) or "-"}')

# 判定 4: 対象タスクを worker で実際に実行し、戻り値を検査する
# studylogs のタスクは例外を捕まえて {'error': ...} を返し、celery 上は succeeded になるため、戻り値まで見る
ok = 0
for name in targets:
    try:
        result = app.send_task(name).get(timeout=60)
    except Exception as exc:  # 未登録・タイムアウト・タスク内の未捕捉例外
        print(f'NG {name} EXC {type(exc).__name__}: {exc}')
        continue
    if isinstance(result, dict) and 'error' not in result:
        ok += 1
        print(f'OK {name} {result}')
    else:
        print(f'NG {name} RESULT {result}')
print(f'SUMMARY targets={len(targets)} ok={ok}')
