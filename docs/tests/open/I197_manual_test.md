# I197 手動テスト: 実装の検証（レビュー）の仕組みを白紙から作り直す

実際の claude を使う通しの確認。承認画面が出るかの判定は、このセッションの自動承認モードの影響を受けないよう、スクリプトが起動する新しい `claude -p`（承認なし・`--setting-sources user --settings .claude/settings.json`）の出力で確かめる。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | 実装の後、このブランチ（コミット済み・作業ツリーがきれいな状態）で `bash scripts/claude/adversarial-review.sh I197` を Bash ツールの `run_in_background: true` で実行し、完了の通知を待つ（計画の `## 必ず確かめる項目（I197 自身の敵対的レビューが使う）` の V1〜V10 を一覧として使う） | ①記録 `docs/reviews/I197_adversarial_review_<ts>.md` の「人の応答待ち: 0」の行があり、このセッションに確認画面が 1 度も出ていない（拒否があれば「観点ごとの実行」の拒否の列と「実験」の節に出ている）②「所要時間」が 600 秒以下 ③「確かめる項目の結果」の表に V1〜V10 の 10 行があり、各行の報告が「実験で確認／読んで確認／未実施」のどれかで、判定が「確認済み」か「未検証」。最後の 3 行が `REVIEWED_COMMIT: <実行時の HEAD>`・`ROUNDS:`・`VERDICT:` | Claude | claude -p の判定（スクリプトが起動する別プロセス） |  | VERDICT が HIGH（指摘・未検証あり）でも、この No の合否は ①②③ が記録にあるかで決める（指摘の対応は review-gate が行う）。所要時間が 600 秒を超えたら NG（計画をやり直す）。各観点の費用（ログの `total_cost_usd`）も記録する（retro で既定の予算を見直す材料） |
| 2 | `REVIEW_LIB_SOURCE_ONLY=1` で `scripts/claude/adversarial-review.sh` を読み込むスクリプトを scratchpad に書き、実験役の関数に 2 つの実験を渡して実行する: (a) 波かっこを含む heredoc で scratchpad に Python のファイルを書いて実行する（`cat > <scratchpad>/i197_m2.py <<'EOF'` ／ `d = {1: 2}` ／ `print(d[1])` ／ `EOF` ／ `python3 <scratchpad>/i197_m2.py`）(b) 見張りが確認を求める、実行されても困らない代わりの操作 `docker compose cp /nonexistent-i197-m2 backend:/tmp/i197-m2` | (a) は「実行した」で出力の先頭に `2`。(b) は「拒否された」でコマンドが記録に出る。どちらも待たずに終わる（全体が 120 秒以内）。本体のワークツリー隔離チェック（「too complex to verify」）の拒否は出ない | Claude | claude -p の判定（スクリプトが起動する別プロセス） |  | (b) は S3 で拒否を確かめた操作。もし実行されても、存在しないファイルのコピーが失敗するだけ |
| 3 | `.claude/skills/review-gate/SKILL.md` §3 を読み、計画 §4.5 の review-gate の行と突き合わせる | 終了コード 0・1・2・3・4 と `ADVERSARIAL_VERDICT:` 行が無いときの扱いが、計画の表と一致する。Agent ツールでの起動・タイマー・`TaskStop` の手順が無い。未検証の直し方（決定論の TC で覆う・確かめ方を下げるのはそのときだけ）が書かれている | Claude | ― |  | |
| 4 | 実装の後、`gh issue view 328 --json state,stateReason,comments` を実行する | `state` が `CLOSED`・`stateReason` が `NOT_PLANNED`。最新のコメントに統合先 `#332` と理由（確かめる項目の一覧に含まれる）がある | Claude | ― |  | |

| 5 | （2026-10-27 追加）I197 自身の review-gate の記録（`docs/reviews/I197_code_review_*.md`）を時刻順に読む | §4.8 を入れた後の最初の記録が `LEDGER_ROUND: 1`（全体のレビュー）。それ以降にやり直しがあれば `LEDGER_ROUND: 2` 以降で、記録の「見た範囲」が前の記録の `REVIEWED_COMMIT` からの直した差分だけ、前回の open の指摘ごとに `STATUS=resolved` か `open` の行があり、VERDICT が台帳の合否と一致する。やり直しが無く 1 回で OK なら、そのことを記録する | Claude | ― |  | AC12 の実地の確認 |

結論: （test-gate 段階で記入）
