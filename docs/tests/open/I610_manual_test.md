<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I610 手動テスト: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | Claude の Bash（サンドボックスの中）で、`UV_CACHE_DIR` を付けずに `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i193_official_flow.sh` | `run-all: pass=1 fail=0`（F9 の 3 件を含む）。標準エラーに `uv のキャッシュ … に書けないので … を使います` の 1 行 | Claude | OK（2026-11-21・HEAD e6d699e5）: `（uv のキャッシュ /home/tacic/.cache/uv に書けないので /tmp/claude-1000/uv-cache を使います・サンドボックスの中など）` の 1 行が出て `run-all: pass=1 fail=0`（F9 を含む test_i193 が合格） |  |
| 2 | `UV_CACHE_DIR` に一時フォルダ（スクラッチパッドの下の新しい名前）を付けて同じテストを流す | `run-all: pass=1 fail=0`。案内の 1 行が出ない。指定したフォルダが作られている | Claude | OK: `UV_CACHE_DIR="$TMPDIR/i610-m2-cache"` で `run-all: pass=1 fail=0`・案内の行なし・`/tmp/claude-1000/i610-m2-cache` が作られた |  |
| 3 | 本物のフックの起動役に、見張りが止める入力 `{"tool_name":"Bash","tool_input":{"command":"git push --force origin develop"}}` を標準入力で渡す: `bash .claude/hooks/reviewed-hook.sh scripts/claude/hooks/pretooluse_guard.py`（いつも写しの道を通る） | 終了コード 2 で、標準エラーに `[guard] force push requires DANGER_OK=1` が出る。`[reviewed-hook]` の理由の行は出ない | Claude | OK: `[guard] force push requires DANGER_OK=1`・`exit=2`・`[reviewed-hook]` の行なし（変更前と同じ） | 変更後もフックが動くことの確かめ（R1・R3）。期待は実装の前（2026-11-21・変更前の起動役）に同じ入力で観測した値（exit=2・同じ文字列） |
| 3b | 本物の起動役で、ほかの 2 つのフックを写しの道で起こす: (a) `bash .claude/hooks/reviewed-hook.sh scripts/claude/hooks/posttooluse_check.py` に、Write の入力 `{"tool_name":"Write","tool_input":{"file_path":"<一時の JSON ファイル>"}}`（中身が壊れた JSON）を渡す (b) `bash .claude/hooks/reviewed-hook.sh scripts/claude/hooks/sessionstart_context.py` に `{"hook_event_name":"SessionStart","source":"startup"}` を渡す | (a) 壊れた JSON の構文の誤りを知らせる出力が出る（写しから動き、写しの中の `code-review.sh` などを見つけられる）(b) `[sessionstart]` で始まる作業の状態の出力が出る。どちらも `[reviewed-hook]` の行と Python の例外（Traceback）が出ない | Claude | OK: (a) `[posttooluse] syntax error in …/i610_broken.json: Expecting property name enclosed in double quotes` で exit=2 (b) `[sessionstart] 作業の状態…` が出て exit=0。どちらも `[reviewed-hook]` の行と Traceback なし。(b) の「未コミットの変更: 17 件」「取得できませんでした」は、確かめのために Claude のサンドボックスの中から起こしたため（中ではふさぎの印を変更と数え、GitHub に届かない。本物のフックは外で動く） | 計画レビュー（20261121_1739）の Warning: 変更が無いときもすべてのフックが写しから動くようになったため |
| 4 | `docs/runbooks/plan-writing-rules.md` の「外と中の境目を動かす計画」の節を読む | 外に出す型・外で動くスクリプトの一覧を変える計画で、中へ移るスクリプトごとに、中でだけ見える物を読まないか・中で書けない場所に書かないかを、計画の前にサンドボックスの中で 1 回流して確かめ、調査結果に書く、がある | Claude | OK: 節「外と中の境目を動かす計画（…・I610）」に、中へ移るスクリプトの (a) 中でだけ見える物 (b) 中で書けない場所 の確かめと、外へ移るスクリプトの根拠がある |  |
| 5 | Claude の Bash（サンドボックスの中・本物のふさぎの印が見える）で `bash scripts/claude/gate-check.sh I610` を流す（test-gate の 1 で流すもの） | `GATE_CHECK: FAIL REASON=dirty` にならない（`.bashrc` などの印を数えない）。`ls -la .bashrc` が文字デバイスであることも記録する | Claude | OK: `GATE_CHECK: OK`（dirty にならない）。`.bashrc`・`.gitconfig`・`.idea` は `crw-rw-rw- 1 nobody nogroup 1, 3`（文字デバイス） | 本物の bind mount の印の道（TC-03 の G9c の補い） |

結論: OK（No.1〜No.5・No.3b すべて OK）
