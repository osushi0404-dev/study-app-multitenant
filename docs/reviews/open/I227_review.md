# I227 レビュー: レビューの判定を機械が読む形・変数に置き換える

## 変更概要
- `/security-review` の「差分なし」の判定を、表示の文字列の部分一致から本体の変数 `NO_DELTA`（引数）に替える
- 判定の行（`<名前>: <数>`）の正規表現を `findings_line_present()` の 1 か所にまとめる
- 組み込みのレビューの「読めたか」を、種類ごとの決まった形（`/security-review` は `SECURITY_FINDINGS` の行・`/code-review` は JSON として読める指摘の配列）だけで決める

## 変更点
- `scripts/claude/code-review.sh`: `findings_line_present()`（新規・判定の行の正規表現の 1 か所）・`official_findings_json_present()`（新規・JSON の指摘の配列）・`official_output_readable()`（種類ごとの決まった形）・`run_official_review()`（第 2 引数を種類に）・`official_security_verdict()`（`NO_DELTA` を引数で受ける）・呼び出し 3 か所
- テスト: `test_i212_review_base.sh` に U9・U10・FG-U9・FG-U10・FG-E2、U7・FG-U7 を新しい形に。`test_i193_official_flow.sh` の C8・C12・C23 を新しい引数の形に
- `.claude/skills/review-gate/SKILL.md:36` の文（I212 F5 同梱）・`docs/reviews/backlog/I212.md` から F5・F7 を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config（ハーネス）: `scripts/claude/code-review.sh`・`scripts/claude/tests/test_i212_review_base.sh`・`scripts/claude/tests/test_i193_official_flow.sh`・`.claude/skills/review-gate/SKILL.md`・`docs/reviews/backlog/I212.md`

## テスト結果
- 自動: OK（決定論ゲート 10 本が review-gate の実走ですべて exit=0・CI 全緑・gate-check OK）
- 手動: OK（M-01 本物の `/code-review` が読めた・M-02 本物の `/security-review` の判定 OK・M-03 記録の注意と実際が一致。すべて Claude）

## 計画との差分
- 計画変更記録 2（/simplify の整理）。振る舞いは計画どおり

## ロールバック
- PR を revert する（設定・データの変更なし）

## 自律判断の記録
- [plan] `/code-review` の「読めたか」を判定の行ではなく公式の決まった出力の形（JSON の指摘の配列）で決める — スパイク 2 回で `/code-review` が `--append-system-prompt` の指示に従わず、囲みの JSON 配列だけを出したため。受け入れ条件 2 の狙い（文の形に左右されない）は変えず、文言を合わせた
- [plan] 「差分なし」は既存の変数 `NO_DELTA` を引数で渡す — 判定の前にいつも決まっていて、中身の照合を残さない
- [plan] 一覧の I212 F5・F7 を同梱、ほかは残す — F7 は受け入れ条件 3 そのもの、F5 は直す行と同じ行の文言
- [plan-review] Warning 3 件（囲みの言語名・M-01 のやり直し方針・C23 の注意文）を計画に反映し、再レビューはしない — 方式・範囲・受け入れ条件は変えない
- [implement] /simplify の指摘のうち 5 件を直し、6 件を見送った（計画変更記録 2）— 見送りは計画どおりの形・範囲の外・軽微なもの。FG-E2 は grep に替えず、通しで退行を止める形を残した
- [review-gate] 基本レビュー 1 周目 OK（`I227_code_review_20261108_0208.md`・止める指摘なし・Low 5 件は台帳に残し retro へ）・敵対的レビューは NOT_REQUIRED — 計画レビューの判定 No・パス判定 NO
- [test-gate] M-01〜M-03 をすべて Claude が実施し OK（Human の項目なし）— 本物の `/code-review`・`/security-review` を新しい版の関数で動かして確かめた
- [retro] 台帳の残り: 後続イシュー 0 件。F1〜F5 は `docs/reviews/backlog/I227.md` へ — `--route` の振り分けどおり（すべて Low・再現なし）
- [retro] 改善案 R1（`drop_cli_warnings` が新しい形の警告を除かない）・R2（ほかのテストの代役が「指摘なし」を返す）は見送り、`docs/reviews/backlog/I227.md` に残した — どちらも判定に影響せず手戻りなし。次に `code-review.sh` を触る計画で一覧から拾える
- [retro] 予防処置の新規起票・同梱なし — 想定外だった `/code-review` の振る舞いは計画前のスパイクで捕まり、手戻りが無かった（既存の「外部挙動依存のスパイク実証」の決まりが効いた）
- [retro] I224 の push の回数: このイシューは plan-issue・review-gate の 2 回、close で 3 回目の予定（fix-loop なし・最少の形）

## 振り返り

### かんたんなまとめ

**良かった点**
- イシューは「`/code-review` にも判定の 1 行を出させればよい」と見込んでいました。計画を書く前に本物で 2 回試したところ、`/code-review` はその指示に従わず、公式の決まった形（指摘の JSON の一覧）だけを出すと分かりました。そこで計画の時点で「JSON の一覧として読めるかで決める」方式に切り替え、実装のやり直しは起きませんでした（理由: 「よく分からない外の仕組みに頼るときは、計画の前に小さく試す」という既存の決まりが、そのまま効いた）
- テストを先に書き、直す前の版で「差分なしの文字列を引用しただけで OK になる」「和文の『指摘はありません』で読めたになる」穴を実際に再現してから直しました。わざと壊すと落ちるテストも 4 本つけ、どれも成立しました
- レビューは 1 周で OK、手動テストもすべて Claude が本物の Claude を動かして確かめられ、人に頼む項目はありませんでした

**今回の問題への直接の対処**
- なし（受け入れ条件はすべて満たし、レビューで止める指摘も出ませんでした）

**同じ問題を次回から防ぐ改善**
- 新しく足す改善はありません。途中の小さなつまずき（テスト名の中の記号で構文が壊れた・shellcheck の注意・作業場所の安全装置が一時スクリプトの実行を止めた）は、どれもその場で機械のチェックに捕まり、手戻りがありませんでした
- 軽い気づき 2 件（記録に余計な警告の行が毎回 3 行入る・ほかのテストの代役の返す文が古い）は、判定に影響しないので、軽い指摘の一覧に残しました。次に同じファイルを触るときに拾えます

### 詳細版

#### I227 振り返り

##### 良かった点
- 外部挙動依存のスパイク（`plan-writing-rules.md`「外部/ハーネス挙動依存のスパイク実証」）で、`/code-review` が `--append-system-prompt` の判定の行の指示に従わないことを計画の前に実証し、受け入れ条件 2 の達成手段を JSON 配列の読み取りに置き換えた（手戻りゼロ）
- TDD: U9・U10 を先に書き、直す前の関数で F1 の穴（引用で OK）と言い回しでの「読めた」を再現。FG-U7・FG-U9・FG-U10・FG-E2 がすべて成立
- review-gate 1 周 OK・test-gate の手動テスト 3 件すべて Claude で実施

##### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| （なし） | | | |

##### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| （なし） | | | | |

##### 見送り（理由つき）
- R1 `drop_cli_warnings` が新しい形の警告（`Permission allow rule "…" adds nothing`）を除かない: 実害は記録の雑音だけ（判定は囲みで探すので影響なし）。手戻りなし → 一覧 `docs/reviews/backlog/I227.md`
- R2 ほかのテストの組み込みのレビューの代役が「指摘なし」を返す: 合否に影響せず差分の外 → 一覧
- テスト名の中の ``` がダブルクォートの中でコマンド置換になり構文エラー: 実行ですぐ捕まった（`bash -n`・テストの実行）
- shellcheck SC2016（Python のコードを単一引用符で渡す）: pre-commit で捕まり、その場で注記した
- 作業場所の安全装置が、`git` の語を含む heredoc や `bash -c` の文字列を止めた: Edit ツール・一時スクリプトへの切り替えで回避でき、手戻りなし（安全装置の守る範囲は「普通の書き方の事故」・I179 の決まりどおり）
- 4 観点: 成果（受け入れ条件 4 件すべて満たした）・プロセス（フローどおり）・セキュリティ（出力は信用せず `json.loads` で読むだけ・`python3 -I`・標準入力）・設計ルール昇格（design-security-review は無し・review-gate の `/security-review` はパス判定 NO で無し → スキップ）・指示ファイル（plan-reviewer・code-reviewer に足す観点なし）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
