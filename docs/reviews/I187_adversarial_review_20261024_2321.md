# I187 敵対的レビュー記録（2026-10-24）

- 起動元: `/code-review I187`（基本レビュー `docs/reviews/I187_code_review_20261024_2237.md` は FINAL_VERDICT: OK・ADVERSARIAL_STAGE: REQUIRED）
- 上限: 1 体 15 分・攻め筋 3 本・1 周 3 体・イシュー全体で 2 周
- 結果: **上限到達・未収束**（2 周目に High 1 件。修正は入れたが、修正を反証する周回が上限で残っていない）

## 1 周目（範囲: `origin/develop...HEAD`・開始 HEAD 88fe48e）

| 観点 | 時間切れ | 新規 Critical | 新規 High |
|---|---|---|---|
| ロジック回避・実機 repro | なし | 0 | 1 |
| テストの false-green・tautology | なし | 0 | 1（上と同じ穴） |
| 要件・脅威モデルの網羅漏れ | なし | 0 | 0 |

### findings
| 重大度 | 指摘 | 該当箇所 | 対応 |
|---|---|---|---|
| High | allow `Bash(docker compose --profile e2e run --rm e2e*)`（前置きあり版も）が末尾を何でも受ける。見張りは `npm test`・`npm run test`・`npx jest` などを判断せずに通すため、`npm test -- --output=.`（ホストの `e2e/` を消しうる。`e2e/.env.e2e` は GitHub から戻せない）・`--config`・`--update-snapshots` が承認なしで動く。TC-05 C60〜C68 は `npx playwright test` の形しか見ておらず false-green | `.claude/settings.json:67-68`・`pretooluse_guard.py:2346` | 修正（5faacc6）: allow を既定コマンドの完全一致と `... e2e npx playwright test *` の 4 つに絞った。見張りに直接入力して再現を確認したうえで修正。計画変更記録 3 |
| Medium | 同じ allow が `e2e-init` にも一致（`migrate` などが承認なしで通る） | 同上 | 上と同じ修正で対処 |
| Medium | auto mode では `browser_run_code_unsafe` などの確認が自動判断になり、`.env` を書きうる。runbook に注意が無い | `pretooluse_guard.py:3465-3473`・`frontend-verify.md:81` | 見送り（記録のみ・/retro で扱う） |
| Medium | `check-frontend-evidence.sh` が古い行・古い画像・「実際の結果」が NG の行でも合格する | `check-frontend-evidence.sh:40-85` | 見送り（記録のみ・/retro で扱う） |
| Low | `--reporter=html` が手元で配信サーバーを立てて止まる | `pretooluse_guard.py:1280` | 見送り |
| Low | 判定が `frontend/src/` だけ・未コミットの変更・`core.quotepath` の引用符で対象外になる | `check-frontend-evidence.sh:22-30` | 見送り |
| Low | `docker compose run -v …`・`-e NODE_OPTIONS=…` は見張りを通る（allow 外なので確認は出る） | `pretooluse_guard.py:1588` | 見送り |
| Low | テストの変異（ファイル名の正規表現・`..`・`frontend/` への拡大・`c["compose"]`・`isinstance`）が生き残る | 各テスト | 見送り |

## 2 周目（範囲: `88fe48e...HEAD`・開始 HEAD 5faacc6）

| 観点 | 時間切れ | 新規 Critical | 新規 High |
|---|---|---|---|
| ロジック回避・実機 repro | なし | 0 | 0 |
| テストの false-green・tautology | なし | 0 | 1 |
| 要件・脅威モデルの網羅漏れ | なし | 0 | 0 |

### findings
| 重大度 | 指摘 | 該当箇所 | 対応 |
|---|---|---|---|
| High | TC-03 ⑤b' が「許可の文字列に `run --rm e2e` を含むか」しか見ていない。`Bash(docker compose --profile e2e run *)`・`--rm` 抜き・`--service-ports` 入り・順番違いなどで広い許可を足し直しても合格する（`SETTINGS_JSON` で差し替えた設定で実測） | `test_i187_frontend_verify_config.sh` ⑤b' | 修正（この記録と同じコミット）: 危ない代表コマンド（e2e・e2e-init の `npm test -- --output=.`・`npx jest`・`migrate` を、よくある書き方 2×2×9×3 通りで並べたもの）に、allow のどのルールもワイルドカードとして一致しないことを判定する形にした（⑤b'）。既定コマンドと `npx playwright test` が一致することも確かめる（⑤b''）。広い許可 14 通りを足した設定で、どれも不合格になることを確かめた。本物の設定では 13/13 合格 |
| Low | `--reporter` の値は形だけを見ており、組み込みでない名前（`dotenv` など）で node_modules のパッケージが読み込まれる | `pretooluse_guard.py:2296` | 見送り |
| Low | ⑤b'（修正前）は `--rm` 抜き・`-e` 入りの形を見逃す | 同上 | 上の修正で対処 |

### 範囲外の観察（件数外・別途判断）
- `Bash(rm *)`・`Bash(mv *)`・`Bash(cp *)` が以前から allow にあり、`rm e2e/.env.e2e`・`echo x > backend/.env` は単体でも見張りを通る。I187 で増えた穴ではない（ベースライン）。GitHub から戻せない `.env` の扱いは danger-ops の方針（I182・I179）の判断になる

## 種類ごとの集計
| 種類 | 1 周目 | 2 周目 |
|---|---|---|
| 「承認なしで通る範囲」を、許可ルールの文字列の形で決めたり確かめたりしていて、実際に一致するコマンドとずれる | High 1（allow の `e2e*` が広すぎ） | High 1（テストが許可の文字列の形しか見ない） |
| 判定スクリプトが記録の新しさ・中身を見ない | Medium 1・Low 1 | — |
| 見張りの選択肢の判定が形だけ | Low 1 | Low 1 |

同じ種類が 2 周続いた。2 周目の修正では、判定を「文字列の形」から「代表コマンドへの一致」に替えた（止める場所・方式の見直しにあたる）。ただし、この修正を反証する周回は上限のため行っていない。

REVIEWED_COMMIT: 5faacc6bb41462a2e385c495a016c2eeb36d6231
ROUNDS: 2
VERDICT: HIGH
