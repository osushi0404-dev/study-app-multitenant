# I079 自動テスト（決定論）

対象: `.claude/settings.json`。実装（deny 追加・bash allow コミット）完了後に実行する。

| TC | 内容 | コマンド | 期待値 |
|----|------|----------|--------|
| TC-A1 | settings.json が有効な JSON | `python3 -m json.tool .claude/settings.json > /dev/null && echo OK` | `OK`（exit 0） |
| TC-A2-allow | allow に必須3系統が含まれる | `python3 - <<'PY'`（下記スクリプト①） | exit 0（全エントリ存在） |
| TC-A2-deny | deny に高リスク群が Write/Edit 両方で含まれる | `python3 - <<'PY'`（下記スクリプト②） | exit 0（全20エントリ存在） |
| TC-A3 | 既存の機密ファイル deny が不変 | `python3 - <<'PY'`（下記スクリプト③） | exit 0（5系統×Read/Edit/Write が維持） |

### スクリプト①（allow 存在チェック）
```python
import json, sys
allow = json.load(open(".claude/settings.json"))["permissions"]["allow"]
need = ["Write(backend/**)","Edit(backend/**)","Write(frontend/**)","Edit(frontend/**)","Bash(bash scripts/claude/*)"]
missing = [e for e in need if e not in allow]
sys.exit(f"MISSING allow: {missing}" if missing else 0)
```

### スクリプト②（deny 高リスク群チェック）
```python
import json, sys
deny = json.load(open(".claude/settings.json"))["permissions"]["deny"]
paths = ["backend/requirements*.txt","backend/pyproject.toml","frontend/package.json",
         "frontend/package-lock.json","**/migrations/*.py","backend/init-db.sql",
         "backend/Dockerfile","frontend/Dockerfile","frontend/Dockerfile.dev","frontend/nginx.conf"]
need = [f"{op}({p})" for p in paths for op in ("Edit","Write")]
missing = [e for e in need if e not in deny]
sys.exit(f"MISSING deny: {missing}" if missing else 0)
```

### スクリプト③（既存機密 deny 不変チェック）
```python
import json, sys
deny = json.load(open(".claude/settings.json"))["permissions"]["deny"]
need = ["Read(./.env)","Edit(./.env)","Write(./.env)",
        "Read(./.env.*)","Edit(./.env.*)","Write(./.env.*)",
        "Read(./secrets/**)","Edit(./secrets/**)","Write(./secrets/**)",
        "Read(**/*.pem)","Read(**/*.key)"]
missing = [e for e in need if e not in deny]
sys.exit(f"MISSING secret-deny: {missing}" if missing else 0)
```

## false-green 自己検証（現状の実測に基づく）
- TC-A2-deny: 実装前の現状で実行すると **20/20 missing で NG（非ゼロ）** を確認済み（2026-06-27 実測）＝失敗注入が成立。present→OK は実装後に確認する。
- TC-A2-allow: 現状は作業ツリーに allow 5系統が既に存在し OK を返す（backend/frontend は commit `166d21f`、`Bash(bash scripts/claude/*)` は未コミットだが作業ツリーに存在）。失敗注入は実装時に1系統を一時削除して NG を返すことを1回確認する。
- TC-A3: 対象行を1つ削った状態で NG を返すことを実装時に1回確認する。
