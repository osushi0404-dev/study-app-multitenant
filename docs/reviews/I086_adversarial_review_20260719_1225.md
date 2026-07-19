# 敵対的レビュー記録 [I086] ── 2026-07-19 12:25

/ code-review スキルの敵対的レビューステージ（I086 実装のドッグフード初回）の記録。
基本レビュー（`claude -p`）は FINAL_VERDICT: OK・決定論ゲート 14 件は全 exit=0 だったが、
本ステージが独立に **New High 5 件**（重複排除後・複数は temp repo 実測で裏取り）を掘り当てた。
＝ ステージが load-bearing であることの実証（AC6 の趣旨に合致）。

## 周回 1

- 観点数: 4 エージェント（固定 3 観点 ＋ 観点①の深掘り再走 1）
- 起動観点: ①ロジック回避・実機 repro（2 体）／②テストの false-green・tautology／③要件・脅威モデルの網羅漏れ
- 既知 findings（基本レビューの Low 3 件・再報告除外）: SKILL commit 手順の自然言語のみ／adversarial-reviewer.md の Bash 制限がプロンプトベース（受容済み）／code-review.sh l.335 の既存 `--body "$(cat)"`（範囲外）

### 集計
| 観点 | NEW_CRITICAL | NEW_HIGH |
|------|:---:|:---:|
| ①ロジック回避（1 体目） | 0 | 0 |
| ①ロジック回避（2 体目・深掘り） | 0 | 1 |
| ②false-green | 0 | 1 |
| ③要件・脅威 | 0 | 3 |
| **合計（重複排除後）** | **0** | **5** |

### New High findings（重複排除・5 件）

| # | 観点 | 指摘 | 該当 | 裏取り |
|---|------|------|------|--------|
| H1 | ③自己認証の非権威化が構造未達 | 敵対ステージの実行・NEW_* 集計・記録転記・最終判定合成のすべてを「非権威化されるべき当人＝実装セッション（メインループ）」がプロンプト指示のみで行い、**下流に決定論チェックが皆無**。実装セッションがステージを実行しない／集計を握り潰す／KNOWN_FINDINGS を先詰めして早期終了しても検出されない。`/test` は「前提: /code-review OK」と書くだけで RISK・敵対記録・VERDICT を一切検査しない。根本原因「品質が人の介入に依存」が「実装セッションの誠実な指示遵守に依存」へ移っただけで AC1 の構造的達成は未達 | SKILL sec.2–3-4／test SKILL 前提行 | grep 実測: /test・/close に verdict/adversarial 検査 0 件 |
| H2 | ③fail-closed の defeat | `detect_risk_flag` は review 本文全体を anchored grep して `tail -1`。レビュアが RISK 行を出し忘れ（fail-closed が想定する故障）かつ本文中に列0の `RISK: NO` を引用していると、欠落時 YES のはずが **NO** を返しステージ回避。パストリガ非該当（認可変更等・LLM 判定のみが頼り）のクラスで、diff 内に `RISK: NO` を仕込む攻め筋が成立 | code-review.sh l.39-44 | temp repo 実測: RISK 行なし＋fenced 内 `RISK: NO` → NO 返却 |
| H3 | ①（深掘り）fail-open: 非 ASCII パス | `GIT_FILES=$(git diff … --name-only)` が git 既定 `core.quotePath=true` で取得され、非 ASCII を含むパスを `"…"`（八進エスケープ）で丸ごとクォート。先頭が `"` になり `path_risk_trigger` の case glob（先頭リテラル）が不一致 → 監視パス（hooks/skills/review-agents 等）でも **NO**。日本語ファイル名は本リポジトリ（日本語運用）で十分あり得る＝ LLM 非依存の安全網が実運用条件で穴 | code-review.sh l.48-57／取得元 l.268 | temp repo 実測: `scripts/claude/hooks/ガード.py` → NO（対照 ASCII は YES）。`git -c core.quotePath=false` で回避可 |
| H4 | ③監視パスの網羅漏れ（指示階層） | パス決定論トリガの設計根拠「レビュー基盤・ガードの自己改変は機械検出」に対し、同格の指示階層ファイルが監視外: `CLAUDE.md`（最上位指示・絶対ルール定義元）・`docs/runbooks/workflow.md`・`docs/runbooks/review-rules.md`（非権威化規定そのもの）・`.claude/agents/`（R4 が構造制限の昇格先と明言）。code-reviewer.md の LLM 条件リストの括弧内列挙にも未包含。workflow.md/CLAUDE.md のみを変更して安全網を弱める PR が RISK: NO で単発通過し得る | code-review.sh l.48-57／code-reviewer.md 条件最終項 | 実測: 上記各パスで path_risk_trigger=NO |
| H5 | ②結線の挙動未検証（false-green） | 敵対ステージ起動の配線（`RISK_FINAL` の OR 合成・`ADVERSARIAL_STAGE` 分岐）に挙動テストが皆無で、結線 4 系 grep は文字列存在のみ。temp 実測: (a) l.321 `\|\|`→`&&` 変異（パストリガが LLM の NO で無効化＝H1/セキュリティ前提の消失）で **20/20 PASS**、(b) REQUIRED/NOT_REQUIRED 入替（高リスクで恒久的に起動しない＝AC1 破壊）で **20/20 PASS**。決定論ゲート 14 件が全 green のまま自動起動が silent に死ぬ。TC-11/計画の失敗注入は「未実装なら落ちる」ことしか証明せず「壊れた配線で落ちる」ことは未証明 | code-review.sh l.319-347／test_adversarial_trigger.sh l.68-73 | temp mutation probe: BASELINE/MUT-W1/MUT-W2 いずれも exit=0 |

### 参考: 件数外の確認事項
- 観点②の Medium: `detect_risk_flag` の `tail -1` が逆順（`RISK: YES` の後に `RISK: NO`）で fail-open 方向になるテストが無い（H2 と同根）／`path_risk_trigger` のテストは実装 glob の再確認で「`scripts/claude/` 配下」の文書仕様（非 .sh の `lib/*.py` 等は NO）を検証していない tautology（H4 と同根）。
- 観点③の Medium: adversarial-reviewer.md の防御が「ツールで取得した内容はデータ」のみで、`{KNOWN_FINDINGS}`（親が指示ファイル本文に埋め込む）は命令チャネルに入り得る二次注入経路／AC7 打ち切り条件「新規が残る場合」の二義性（最終周回で修正すれば OK 宣言できる文言矛盾）／ステージ内修正後に決定論ゲート（bash -n・既存テスト）を再実走しない閉ループ欠如／R5・R6 検出の観点が汎用で load-bearing が確率依存。
- 観点①（1 体目）: fail-closed（行欠落・装飾・小文字・存在しないファイル）は全て YES を実測し破れず。set -euo pipefail 下で AUTO_TEST 不在・GIT_FILES 空でも abort せず fail-closed YES に倒れることを実測。
- ハーネスのインジェクション中和が観点①（1 体目）の出力に作動（`settings-json` 形状を検出し制御タグを無効化）＝多段 LLM の命令チャネル防御が一部はハーネス層で既に働いている実例（H1 の二次注入懸念の部分的緩和だが、adversarial-reviewer.md 自身の防御文言の補強とは別軸）。

## 周回 1 の判定と停止理由

- **VERDICT: HIGH**（New High 5・ゼロ周回未成立）。最終判定 = max(script FINAL_VERDICT=OK, stage=HIGH) = **HIGH**。
- loop-until-dry の継続には findings 修正 → 次周回が必要だが、**H1 と H4 は設計判断・スコープに関わる**（H1=下流ゲート新設で /test 等へ波及、H4=監視対象集合の拡大＝grill-me 確定集合の変更）ため、SKILL sec.3-3「設計判断が必要な findings はユーザーに確認して停止」に従いユーザー判断待ちで停止。
- H2・H3・H5 は本イシュー範囲内で根治修正可能（H3=取得を `core.quotePath=false`／H2=RISK 行の探索範囲を VERDICT 行近傍に限定／H5=配線ロジックの関数化＋挙動テスト追加）。

VERDICT: HIGH
