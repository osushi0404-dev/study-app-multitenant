# I079 自動テスト（決定論・案D）

対象: `.claude/settings.json`（permissions＋hooks）、`scripts/claude/hooks/pretooluse_guard.py`。

> 🔴 **設計変更（fix-loop I079・2026-06-27 / 案D）**: 高リスク群の保護は settings `deny` ではなく **PreToolUse フック**で行う。理由: Edit/Write では `deny` が重複 allow に勝てず、かつ settings `deny` の挙動は自動テストできない（fail-open・検証不能）。**フックなら決定論的に単体テスト可能**（TC-H1〜H3）。旧 TC-A2-deny（高リスク deny の存在チェック）は、保護がフックへ移ったため**廃止**。

| TC | 内容 | コマンド（概念） | 期待値 |
|----|------|----------|--------|
| TC-A1 | settings.json が有効な JSON | `python3 -m json.tool .claude/settings.json > /dev/null && echo OK` | `OK`（exit 0） |
| TC-A2-allow | allow に必須3系統が含まれる | スクリプト①（membership） | exit 0（全5件存在） |
| TC-A3 | 既存の機密ファイル deny（env/secrets/pem/key の Read/Edit/Write）が維持 | スクリプト③（membership） | exit 0（全15件存在） |
| TC-A4 | 実効しない高リスク deny（Dockerfile/deps/migrations 等の Edit/Write）が settings から**撤去**されている | スクリプト④ | exit 0（該当エントリが0件） |
| **TC-H1** | フックが高リスクパスの Edit/Write に **`permissionDecision: "ask"`** を返す（プロンプト化） | 高リスク file_path の JSON を hook に stdin 投入 | stdout に `"permissionDecision": "ask"` を含む（exit 0） |
| **TC-H2** | フックがアプリソースの Edit/Write を**素通し** | アプリ file_path の JSON を hook に投入 | ask を出さない（exit 0・decision 出力なし） |
| **TC-H3** | TC-H1 の**失敗注入**（false-green 排除） | 判定対象から1パターン外した状態で高リスクパスを投入 | ask が出なくなる＝**判定が効いていることの裏取り**（注入で素通りを確認後、本実装に戻す） |
| **TC-H4** | 危険 bash の既存ハードブロックが維持 | `git push --force` 等の JSON を hook に投入 | **exit 2**（ブロック・回帰防止） |

### TC-H1/H2 実行例（フック実装後）
```bash
# TC-H1: 高リスク → ask を返す。M2〜M4 相当を網羅
for p in backend/Dockerfile frontend/Dockerfile frontend/Dockerfile.dev frontend/nginx.conf \
         backend/requirements.txt frontend/package.json frontend/package-lock.json \
         backend/pyproject.toml backend/init-db.sql backend/problems/migrations/0001_initial.py; do
  out=$(echo "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$p\"}}" \
    | python3 scripts/claude/hooks/pretooluse_guard.py)
  echo "$out" | grep -q '"permissionDecision": *"ask"' && echo "  $p -> ASK(OK)" || echo "  $p -> NG(askなし)"
done   # すべて ASK(OK) を期待

# TC-H2: アプリソース → 素通し（ask なし）
for p in backend/problems/views.py frontend/src/App.tsx; do
  out=$(echo "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$p\"}}" \
    | python3 scripts/claude/hooks/pretooluse_guard.py)
  echo "$out" | grep -q '"permissionDecision"' && echo "  $p -> NG(誤ask)" || echo "  $p -> 素通し(OK)"
done   # すべて 素通し(OK) を期待
```
- 絶対パス（`/mnt/.../backend/Dockerfile`）でも TC-H1 が ask を返すこと（パス正規化漏れ確認）を併せて実施。
- Write でも同様（`"tool_name":"Write"`）に1ケース確認。
- TC-H4: `{"tool_name":"Bash","tool_input":{"command":"git push --force origin x"}}` を投入し **exit 2**（既存ハードブロック維持）を確認。

### スクリプト①（allow 存在チェック）
```python
import json, sys
allow = json.load(open(".claude/settings.json"))["permissions"]["allow"]
need = ["Write(backend/**)","Edit(backend/**)","Write(frontend/**)","Edit(frontend/**)","Bash(bash scripts/claude/*)"]
missing = [e for e in need if e not in allow]
sys.exit(f"MISSING allow: {missing}" if missing else 0)
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

### スクリプト④（実効しない高リスク deny の撤去確認）
```python
import json, sys
deny = json.load(open(".claude/settings.json"))["permissions"]["deny"]
obsolete_paths = ["backend/requirements*.txt","backend/pyproject.toml","frontend/package.json",
                  "frontend/package-lock.json","**/migrations/*.py","backend/init-db.sql",
                  "backend/Dockerfile","frontend/Dockerfile","frontend/Dockerfile.dev","frontend/nginx.conf"]
present = [f"{op}({p})" for p in obsolete_paths for op in ("Edit","Write") if f"{op}({p})" in deny]
sys.exit(f"STILL PRESENT (撤去漏れ): {present}" if present else 0)
```

## false-green 自己検証（案D）
- **TC-H3 が中核**: 高リスク判定の決定論ゲートは、判定パターンを1つ外した状態で高リスクパスを投入し **ask が出なくなる（素通りになる）こと** を確認してから本実装に戻す。これにより「ask を出しているのは判定ロジックのおかげ」を裏取りする（常に ask を出すだけの false-green を排除）。
  - 具体手順例: `pretooluse_guard.py` の高リスクパターン定義（例 `DANGEROUS_EDIT_PATTERNS`）の先頭1件（例 `backend/Dockerfile` 相当）を一時コメントアウト → そのパスで TC-H1 を実行し **ask が出ない**ことを確認（＝判定が効いている裏取り）→ コメントアウトを戻して TC-H1 が再び ask を返すことを確認。
- TC-A1/A2-allow/A3/A4 は membership/JSON の決定論チェック（実装後に実行・記録）。TC-A2-allow は欠落注入で NG を返すこと（同型ロジック）を確認済み。
- 旧 TC-A2-deny は廃止（保護はフックへ移管。settings の高リスク deny は実効しないため存在チェックに意味がない）。
