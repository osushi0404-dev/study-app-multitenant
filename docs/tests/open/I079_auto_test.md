# I079 自動テスト（決定論）

対象: `.claude/settings.json`。実装（deny 追加・bash allow コミット）完了後に実行する。

| TC | 内容 | コマンド | 期待値 |
|----|------|----------|--------|
| TC-A1 | settings.json が有効な JSON | `python3 -m json.tool .claude/settings.json > /dev/null && echo OK` | `OK`（exit 0） |
| TC-A2-allow | allow に必須3系統が含まれる | `python3 - <<'PY'`（下記スクリプト①） | exit 0（全エントリ存在） |
| TC-A2-deny | deny に高リスク群が Write/Edit 両方で含まれる | `python3 - <<'PY'`（下記スクリプト②） | exit 0（全20エントリ存在） |
| TC-A3 | 既存の機密ファイル deny が維持＋pem/key の Edit/Write も deny | `python3 - <<'PY'`（下記スクリプト③） | exit 0（env/secrets の Read/Edit/Write、pem/key の Read/Edit/Write が全て存在） |

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
        "Read(**/*.pem)","Edit(**/*.pem)","Write(**/*.pem)",
        "Read(**/*.key)","Edit(**/*.key)","Write(**/*.key)"]
missing = [e for e in need if e not in deny]
sys.exit(f"MISSING secret-deny: {missing}" if missing else 0)
```

## false-green 自己検証（実測記録・2026-06-27）
- TC-A2-deny: 実装前の状態で実行すると **20/20 missing で NG（非ゼロ）** を確認済み（失敗注入成立）。実装後は全20件 present で **OK** を確認済み。
- TC-A2-allow: 失敗注入を実施済み — `allow` から `Edit(backend/**)` を一時除外したコピーで判定すると `missing=['Edit(backend/**)']` を返し **NG を検出**することを確認（2026-06-27、インメモリ注入）。実装後の実ファイルでは全5件 present で **OK**。
- TC-A3: スクリプト③は TC-A2-allow と同一の membership 判定（`[e for e in need if e not in deny]`）であり、欠落エントリを NG として検出する（TC-A2-allow の注入で同型ロジックを実証済み）。実装後の実ファイルでは env/secrets/pem/key の全15件 present で **OK** を確認済み。
