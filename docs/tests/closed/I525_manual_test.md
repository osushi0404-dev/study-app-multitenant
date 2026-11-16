# I525 手動テスト: 敵対的レビューの延長を引数で受け取り、Claude の Bash からサンドボックスの外で起動できるようにする

実施環境: このイシューのセッションの Bash（Claude Code のサンドボックスが効いている状態。`.claude/settings.json` の `sandbox.excludedCommands` を実際に照合する）。決定論のテスト（auto_test）は一時のリポジトリで流すので、サンドボックスの照合は確かめられない。その部分をここで実機で確かめる。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | （失敗の注入）このワークツリーで、前置きの形 `ADV_ROUND_LIMIT=2 bash scripts/claude/adversarial-review.sh I525` を Bash で流す（作業ツリーはきれい・通算の周が 2 未満の時点） | 出力の最後が `ADVERSARIAL_ERROR: DIRTY`・exit 2。一覧に `.bashrc`・`.gitconfig` など装置ファイルが出る。記録は増えない（claude を呼ぶ前に止まる） | Claude | このセッションの Bash | OK（2026-11-16・HEAD 時点。exit 2・最後の行 `ADVERSARIAL_ERROR: DIRTY`・`.bash_profile` 〜 `.zshrc` の 18 件を列挙・記録は作られない） | 古い書き方が実機で落ちることを確かめ、No.2 が空の合格でないことを示す |
| 2 | 引数の形 `bash scripts/claude/adversarial-review.sh --round-limit 2 I525` を Bash の `run_in_background` で流す。review-gate で敵対的レビューが要るときは、その 1 周目をこの形で起動する。要らない判定なら test-gate で 1 回だけこの形で起動する | `ADVERSARIAL_ERROR: DIRTY` が出ない。`ADVERSARIAL_RECORD:` 行と `ADVERSARIAL_VERDICT:` 行が出て、`docs/reviews/I525_adversarial_review_<時刻>.md` が作られる（周が始まった） | Claude | このセッションの Bash | OK（2026-11-16・review-gate は NOT_REQUIRED のため test-gate で起動。exit 0・DIRTY なし・`ADVERSARIAL_RECORD: docs/reviews/I525_adversarial_review_20261116_0229.md`・`UNVERIFIED: 0`・`ADVERSARIAL_VERDICT: OK`） | 2 は既定値と同じで延長ではない（承認の決まりに触れない） |

結論: OK
