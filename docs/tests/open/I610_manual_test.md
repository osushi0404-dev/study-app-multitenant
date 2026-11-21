<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I610 手動テスト: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | Claude の Bash（サンドボックスの中）で、`UV_CACHE_DIR` を付けずに `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i193_official_flow.sh` | `run-all: pass=1 fail=0`（F9 の 3 件を含む）。標準エラーに `uv のキャッシュ … に書けないので … を使います` の 1 行 | Claude |  |  |
| 2 | `UV_CACHE_DIR` に一時フォルダ（スクラッチパッドの下の新しい名前）を付けて同じテストを流す | `run-all: pass=1 fail=0`。案内の 1 行が出ない。指定したフォルダが作られている | Claude |  |  |
| 3 | 本物のフックの起動役に、見張りが止める入力（`git push --force` を流そうとする PreToolUse の JSON）を標準入力で渡す: `bash .claude/hooks/reviewed-hook.sh scripts/claude/hooks/pretooluse_guard.py` | 見張りの止める答え（`permissionDecision` が `deny`、または止める理由の出力と 0 以外の終了コード）が返る。`[reviewed-hook]` の理由の行が出ない（基準は求められる） | Claude |  | 変更後もフックが動くことの確かめ（R1・R3） |
| 4 | `docs/runbooks/plan-writing-rules.md` の「外と中の境目を動かす計画」の節を読む | 外に出す型・外で動くスクリプトの一覧を変える計画で、中へ移るスクリプトごとに、中でだけ見える物を読まないか・中で書けない場所に書かないかを、計画の前にサンドボックスの中で 1 回流して確かめ、調査結果に書く、がある | Claude |  |  |
| 5 | Claude の Bash（サンドボックスの中・本物のふさぎの印が見える）で `bash scripts/claude/gate-check.sh I610` を流す（test-gate の 1 で流すもの） | `GATE_CHECK: FAIL REASON=dirty` にならない（`.bashrc` などの印を数えない）。`ls -la .bashrc` が文字デバイスであることも記録する | Claude |  | 本物の bind mount の印の道（TC-03 の G9c の補い） |

結論: OK / NG
