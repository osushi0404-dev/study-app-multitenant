# I187 敵対的レビュー記録（2026-10-25・延長の 1 周）

- 起動元: `/code-review I187`（基本レビュー `docs/reviews/I187_code_review_20261025_0027.md` は FINAL_VERDICT: OK・ADVERSARIAL_STAGE: REQUIRED。Medium 1 件〔`frontend-verify.md` の「承認画面は人に頼む」の残り〕は cb3182a で修正）
- 周回: 前回の記録（`I187_adversarial_review_20261024_2321.md`）で上限の 2 周に到達済み。ユーザーの承認で 1 周だけ延長（3 周目）
- 範囲: `5faacc6...HEAD`（前回レビュー後の typecheck・lint の allow〔2964b03〕と、計画変更記録 7 の承認画面の判定・実施者の判定）・開始 HEAD cb3182a
- 上限: 1 体 15 分・攻め筋 3 本・3 体。時間切れなし（3 体とも 3〜4 分で報告）
- 結果: **新規 High 3 件（うち 2 件は同じ穴）。すべて修正したが、修正を反証する周回は残っていない**

## 3 周目

| 観点 | 時間切れ | 新規 Critical | 新規 High |
|---|---|---|---|
| ロジック回避・実機 repro | なし | 0 | 1 |
| テストの false-green・tautology | なし | 0 | 1（上と同じ穴） |
| 要件・脅威モデルの網羅漏れ | なし | 0 | 1 |

### findings
| 重大度 | 指摘 | 該当箇所 | 対応 |
|---|---|---|---|
| High | `check-manual-test-executor.sh` が awk の `-F'\|'` で列を数えるため、セルの中の `\|`（パイプ付きのコマンド）で列がずれ、Human の行が判定から漏れる。実在の `I184_manual_test.md` の No.2 が漏れていた（2 観点が独立に指摘） | `check-manual-test-executor.sh` の awk | 修正: `\|` を区切りにしない分割に変更。X10・X11 を追加（足す前の本体で不合格を確認）。I184 で No.2 が捕まることを確認 |
| High | 実施者の判定が「承認画面」の 1 語だけを見る。過去の記録では同じ確認を「確認プロンプト」「ダイアログ」「確認が出」「確認画面」とも書いており、理由を書けば Human のまま通る | 同上 | 修正: 承認・確認プロンプト・確認が出・確認画面・確認なし・ダイアログをまとめて止める（過去の記録に実際に出てくる言い方）。X12 を追加。理由の中身の良し悪しは決まった判定では見られないため、`/plan-issue`・`/test` の手順（公式の機能まで探す）に任せる |
| Medium | 実施者の列が見つからない文書・`**Human**`・「ユーザー」の行が合格（0）になる | 同上 | 修正: 列のある表が無ければ 2。太字・「ユーザー」「人」も Human と同じに扱う。X13〜X15 を追加 |
| Medium | `check-permission-prompt.sh` が、`permission_denials` が無い・null・要素に `tool_use_id` が無い・`subtype` が error のときに 0（承認なし）を返す | `check-permission-prompt.sh` の読み取り | 修正: どれも 2（判定できない）に。拒否の行（`permission_denied`）と `permission_denials` の食い違いも 2。Q12〜Q16 を追加（足す前の本体で不合格を確認） |
| Medium | `--settings` で読ませた設定に、元のリポジトリの設定と手元の `settings.local.json`（`Bash(python3 -c *)` など広い許可）が混ざり、マージ後の develop と違う判定になる。危ない操作を確かめると、設定が壊れていれば実際に実行されるのに、文書が「危ない操作に承認画面が出る」を例に挙げていて矛盾 | 同上・`plan-writing-rules.md:505`・`test/SKILL.md:101` | 修正: `--setting-sources user` を追加。本物で再現と修正を確認（`python3 -c "print(1)"` は修正前 0 → 修正後 10。見張りが確認を出す `--config other.config.ts` は 10 で、見張りも読まれている）。文書は「危ない操作は、同じ許可ルール・見張りに当たり実行されても困らない代わりの操作で確かめる」に直した |
| Medium | TC-03 ⑤d が許可の文字列（`exec`・`frontend`・末尾 `*)`）しか見ず、`Bash(docker compose exec *)` を足しても合格する | `test_i187_frontend_verify_config.sh` ⑤d | 修正: exec での代表のコマンド（build・`--fix`・install・sh・migrate を frontend・backend、`-T` あり・なし、`docker-compose` で並べたもの）に一致する許可が無いかで判定する形に変更。広い許可を足した設定で不合格・本物で合格を確認 |
| Low | `test_check_permission_prompt.sh` の作り置きが、いつも「is_error と拒否」が対になっていて、`permission_denials` で判定していることを確かめていない | テスト | 修正: Q17（is_error・拒否なし → 0）を追加 |
| Low | typecheck・lint の許可は、`package.json` の scripts を `--fix` や `prelint` に書き換えると承認なしで動く（コンテナの中・差分に出る） | `.claude/settings.json:67-70` | 見送り（記録のみ） |

## 種類ごとの集計
| 種類 | 1 周目 | 2 周目 | 3 周目 |
|---|---|---|---|
| 判定を文字列の形で決めていて、普通の書き方の揺れ（区切り・言い換え・許可の書き方）とずれる | High 1（allow の `e2e*`） | High 1（⑤b' が形だけ） | High 2（`\|` の列ずれ・「承認画面」の 1 語）・Medium 1（⑤d が形だけ） |
| 判定できないときに合格（0）を返す | — | — | Medium 2（実施者の列なし・出力の形のずれ） |
| 確かめる環境が本番と違う（設定が混ざる） | — | — | Medium 1 |

同じ種類（文字列の形の判定）が 3 周続いた。3 周目の修正は、⑤d は「代表コマンドへの一致」へ方式を変えた。実施者の判定は、言い方を列挙で増やしたもので、列挙の方式のまま。実施者の判定は「普通の書き方の事故」を止めるもので、取りこぼしは `/plan-issue`・`/test` の手順と、レビューで拾う前提にしている。

REVIEWED_COMMIT: cb3182a59b9679203737b81ea57207d04bab0e16
ROUNDS: 1
VERDICT: HIGH
