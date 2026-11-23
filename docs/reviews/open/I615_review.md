# I615 レビュー: 外で動く入口をレビュー済みの写しで動かし、人に `!` を頼まなくする

## 変更概要
- 外で動く入口（`OUTSIDE_SCRIPTS`）を、作業ツリーがレビュー済みかを問わず BASE の写しで動かす。入口か部品・レビュー役の定義を変えたときと写しを作れないときだけ、終了コード 75 で止めて `!` を案内する
- 写しの作り方を `.claude/hooks/reviewed-snapshot.sh` にまとめ、F1（写しを消す競合）を直す。F2（フックの子の python に `-I`）を直す
- 見張りが、作業ツリーを書き換える git の操作を中で動く形で流すのを止める（I586 の事故の予防）

## 変更点
- `.claude/hooks/reviewed-hook.sh`: 写しの作り方の正（`reviewed_snapshot`・`--snapshot`）・置き場所 `claude-reviewed-snapshots`・置いてある写しを消さない（F1）
- `.claude/hooks/unreviewed.py`: `run` が写しの入口を動かす・部品（`parts`）とブランチの変更が重なれば 75
- `scripts/claude/hooks/pretooluse_guard.py`: ほかの判定が通す形のうち、git の更新を中で動く形で流すものを止める
- `scripts/claude/hooks/sessionstart_context.py`: 子に `-I`（F2）
- `scripts/claude/fix-diagnosis-review.sh`: 部品を同じフォルダから読む
- テスト・手順書（danger-ops.md・harness-audit.md）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/hooks/`（起動役）・`scripts/claude/hooks/`（見張り・セッション開始のフック）・`scripts/claude/fix-diagnosis-review.sh`・`scripts/claude/tests/`・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`

## テスト結果
- 自動: `test_i599_unreviewed_scripts.sh` pass=56・見張りのテスト一式・CI すべて OK（`docs/tests/open/I615_auto_test.md`「実行記録」）。コードレビュー OK（止める指摘なし・Low/Medium 6 件は台帳）・敵対的レビュー OK（V1〜V6 確認済み）
- 手動: No.1〜No.6 すべて OK（実施者はすべて Claude）

## 計画との差分
- あり: 写しの作り方を新しいファイルでなく `reviewed-hook.sh` の中に置いた（Write が拒まれたため）・見張りの判定をほかの判定の後に置いた（既存の確認を上書きしないため）・`test_pretooluse_checkout_guard.sh` の期待を 3 件直した（計画変更記録）

## ロールバック
- PR を revert する。`~/.cache/claude-reviewed-snapshots/` は消してよい

## 振り返り

### かんたんなまとめ
**良かった点**
- このイシューの中で、もう効果が出た: `scripts/claude/` を変えているこのブランチで、コードレビュー・敵対的レビュー・イシューの本文の読み出しを、あなたに `!` を頼まずに自動で起動できた（理由: 直した起動役は `.claude/hooks/` にあり、書き換えた瞬間から効くため）
- 計画の前の小さな実験（写しの場所から入口を動かす・部品を機械でたどる）で、計画どおりに動くことを先に確かめられた（理由: 実装で方式が崩れなかった）
- 「両方流す」の問題（周の上限を使い切る・2 回目は何も見ない）を計画の段階で見つけ、実装の前にあなたに聞き直せた

**今回の問題への直接の対処**
- 見張りの新しい判定を最初は「ほかの判定より前」に置いたため、既存の見張りのテスト 61 件とぶつかった（承認画面で人が見ていた危ない形まで止めに変わり、ヒアドキュメントの中の文字も命令と取り違えた）。→ ほかの判定が「通す」としたものにだけかける形に直し、既存のテスト一式を流して確かめた
- 新しいファイルを作る道具がこのセッションの途中で使えなくなった。→ 写しの作り方を既存の起動役のファイルの中に置いた（結果は同じ）
- 実装中に、Claude 自身が `git commit … | grep` とつないで流し、サンドボックスの中で失敗した（直している落とし穴そのもの）。害は無く、単独で流し直して済んだ

**同じ問題を次回から防ぐ改善**
- つないで流す失敗を `git commit` まで広げるか・見張りのテスト（作業記録との比べ）がサンドボックスの中で動かない件は、同じ種類を扱う #613 に同梱した（理由: 新しいイシューを増やさず、つないだ形を止める設計を 1 か所で決める）
- 「道具を直した PR は新しい版を正式な結果にする」という今回の決まりは、#593（変えた後の基準で自分を審査させない）と向きが逆なので、#593 に共有した
- 写しのすり替え（基準の参照の書き換え・置き場所の書き換え）の残りは #600 に同梱した

### 詳細版
#### 良かった点
- 起動役の変更が即時に効き、I615 自身の review-gate（code-review.sh・adversarial-review.sh）と test-gate（issue-source.sh）が `!` なしで動いた。fix-diagnosis-review.sh（ブランチで変更）は 75 で止まった（manual No.1・No.2）
- 計画前のスパイク（写しからの起動・部品のたどり）で調査結果 6・8 を実証し、方式の崩れが無かった
- 設計確認メモ「両方流す」の実現不能（周の上限・差分レビュー）を plan で発見し、implement 前にユーザーへ再確認した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 技術選択 | 見張りの新判定を `_route` 直後に置き、既存の確認・停止の判定より先に止めた。git の命令を文字の区切りで探し、読み解き（ヒアドキュメント・包み）を使わなかった | 最後の `_pass()` の前に移し、`_analyze` の `git_update`（`_git_find`）から受け取る形にした。既存の見張りのテスト一式（manual No.5 を含む）で確かめた（計画変更記録 implement） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | 予期しない問題 | 外に出す型の一覧に当たる命令を、ほかの命令とつないで流すとサンドボックスの中で動く。止める一覧（作業ツリーを書き換える git）に、中で書き込みに失敗するほかの命令（pre-commit を動かす commit）が入っていない | つないだ形を止める判定の対象を、外に出す型の命令のうち中で失敗するもの全体で決め直す（#613 に同梱） | `scripts/claude/hooks/pretooluse_guard.py`・`.claude/hooks/unreviewed.py` |
| P2 | スキル・規約 | 見張りを直したら流す決まりのテストが、書き込み先を利用者のキャッシュに決め打ちしており、Claude の Bash（中）では動かない | 書けないときは一時の置き場所に向ける（I610 の run-all.sh と同じ直し方）（#613 に同梱） | `scripts/claude/tests/guard_corpus_diff.py` |

## 自律判断の記録
- [plan] 設計確認メモの「両方流す」を、ユーザーに確かめて「入口か部品を変えたときは、その入口だけ新しい版を `!` で流し正式な結果にする」に変えた — 敵対的レビューの周の上限を 1 回で使い切り、2 回目は差分だけを見て何もレビューしないため（2026-11-22・ユーザーの回答）
- [plan] 「人に `!`」の終了コードを 3 から 75 に変えた — 入口そのものの終了コード 3（CI 待ちの時間切れなど）とスキルの分岐で重ならないため
- [plan] 新しい版を頼む手順はスキルに書かず、起動役の案内の文と danger-ops.md に置いた — どの入口でも同じ動きで、写しを増やさないため
- [implement] 写しの作り方を新しいファイルでなく reviewed-hook.sh の中に置いた — Write が拒まれ、.claude/hooks/ はサンドボックスから書けないため（結果は同じ・計画変更記録）
- [implement] 見張りの新しい判定は、ほかの判定がすべて通すとしたコマンドにだけかける — 既存の確認（承認画面）の判定を止めに変えないため（計画変更記録）
- [implement] /simplify の指摘のうち、部品の対応表化・設定から外に出る語を作る案・一覧の一本化は見送った — 計画で決めた方式・決まり（計画変更記録）
- [test-gate] 作業記録との比べ（manual No.5）は HOME を一時フォルダに向けて流した — キャッシュの置き場所 ~/.cache がサンドボックスの中から書けないため（作業記録は同じものを読む）
- [retro] 台帳の残り 6 件（F1〜F6）はすべて一覧 `docs/reviews/backlog/I615.md`（Low・再現なし。後続イシューの行は 0 件）
- [retro] つないだ `git commit` の失敗と作業記録との比べのサンドボックスの件 → #613 に同梱（同じ種類の設計を 1 か所で決めるため）
- [retro] 新しい版を正式な結果にする決まり → #593 に共有（向きが逆の要件のため、設計で決め直す）
- [retro] セキュリティ設計レビューの残り Medium 2 件 → #600 に同梱（git・docker の設定経由の穴の範囲）
- [retro] 見送り: 「grill-me で、選択肢が既存の道具の制約（周の上限・記録の数え方）で実現できるかを先に確かめる」— 計画の段階で捕まり手戻りは質問 1 回だけ（4 問の 2）。Write が使えなくなった件 — 環境の事象で、方式を変えずに置き場所で吸収できた。見張りのテストとの衝突 — implement で既存のテストを流して捕まった

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro
