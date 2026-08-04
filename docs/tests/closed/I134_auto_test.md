# I134 自動テスト（issue_template 背景/目的プレースホルダ追加＋open イシュー形式統一 sweep）

- 関連: docs/issues/open/I134.md / docs/plans/open/plan_I134.md / GitHub #242 / Draft PR #249
- 対象: `docs/issues/templates/issue_template.md`・`scripts/claude/check-issue-background.sh`（新規）・`docs/issues/open/*.md`（sweep 25 件）・GitHub open イシュー本文（実行時点の全件。初回 sweep 38 件＋レース追補分＝件数は実施記録参照）
- テストレベル: 決定論 TC のみ（grep / awk / diff・合否判定は exit code に統一・合格=exit 0）。ユニット/結合/E2E は対象コードが無いため非該当。

## 決定論ゲート（自動実走）

TC-01 の 2 コマンド（読み取り専用・ALLOW 分類）。code-review.sh が毎回実走し exit code を証跡注入する。

```bash
grep -q '^\*\*背景\*\*:' docs/issues/templates/issue_template.md
grep -q '^\*\*目的\*\*:' docs/issues/templates/issue_template.md
```

TC-02〜06 は宣言しない: TC-02 のチェッカーは allowlist（`bash scripts/claude/tests/*.sh` のみ）外・TC-03 はネットワーク依存（gh で open 全件走査）・TC-04〜06 は実行時にしか存在しない比較基準（コミット・スナップショット・退避原本）が必要なため、formal gate 化すると false-red になる。スクリプト実行形（手順欄参照）で実施し実施記録に exit code を残す。

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-01 | テンプレートにプレースホルダ 2 行が存在（AC-1/2） | 上記「決定論ゲート（自動実走）」の grep 2 本（code-review.sh が毎回自動実走） | (a)(b) とも **exit 0** | Claude |
| TC-02 | wt-harness open 全件にラベル 2 行が存在（AC-3） | `bash scripts/claude/check-issue-background.sh docs/issues/open` | **exit 0**（`OK: all <走査件数> files have 背景/目的 labels`。dir 不在は exit 2・走査 0 件は exit 1 の fail-closed＝敵対レビュー周回1 対応） | Claude |
| TC-02-inject | TC-02 チェッカーの検知能力（実装後の注入再確認） | scratchpad にラベル無しダミー md を置いたディレクトリへ `bash scripts/claude/check-issue-background.sh <dir>` | **exit 1**（MISSING 列挙）→ ダミー削除 | Claude |
| TC-03 | **実行時点の** GitHub open 全件の本文にラベル 2 行が反映（AC-4・レース窓規定＝計画「実装後追記」参照） | 計画書「検証スクリプト全文」の tc03_gh_labels.sh を scratchpad に保存し `bash <scratchpad>/tc03_gh_labels.sh` を実行 | **exit 0**（`total=<実行時点の open 件数> missing=0`。total は実施記録に記録する — 計画時 41・2026-07-20 実測 44） | Claude |
| TC-04 | tracked 分の無改変保証（挿入のみ・削除ゼロ） | 計画書「検証スクリプト全文」の tc04_no_deletion.sh を scratchpad に保存し `bash <scratchpad>/tc04_no_deletion.sh` を実行 | **exit 0**（削除列がすべて 0）。fail-closed: I134.md 不在 → **exit 1**（FILE-DELETED・周回2）／基底 ref `origin/develop` 不解決 → **exit 2**（周回3） | Claude |
| TC-05 | ローカル分の無改変保証（挿入のみ＋**ファイル消失検出**） | 計画書「検証スクリプト全文」の tc05_untracked_insert_only.sh を scratchpad に保存し `bash <scratchpad>/tc05_untracked_insert_only.sh <snapshot_dir>` を実行（比較基準はステップ2-1 のスナップショット。スナップショット側駆動＝敵対レビュー周回1 H1 対応。I134.md 自身は TC-04 と同一の理由で除外） | **exit 0**（`checked=<スナップショット件数−1>`・削除行/消失なし。dir 不在・走査 0 件は exit 2） | Claude |
| TC-07 | 引き継ぎスニペット集合の実態一致（**AC-5 の決定論判定**・周回3 Medium 対応） | 計画書「検証スクリプト全文」の tc07_handoff_snippets.sh を scratchpad に保存し `bash <scratchpad>/tc07_handoff_snippets.sh /mnt/c/app/study-app-multitenant` を実行 | **exit 0**（`OK: snippet set matches (<N> file(s))`。隣 worktree のラベル未保有かつ GitHub open イシュー無しのファイル集合＝計画書のスニペット見出し集合。本ブランチで commit 済みのファイルは develop 取り込みで配布されるため対象外）。fail-closed: 集合不一致 → **exit 1**（差分を出力）／対象 dir・計画書の不在・0 件走査 → **exit 2** | Claude |
| TC-06 | GitHub 直接更新分の無改変保証（挿入のみ・期待件数突合） | 計画書「検証スクリプト全文」の tc06_gh_insert_only.sh を scratchpad に保存し `bash <scratchpad>/tc06_gh_insert_only.sh <退避dir> <期待件数>` を実行（比較基準はステップ3-1 の退避原本。期待件数は退避時の実件数＝原本保存漏れの fail-closed） | **exit 0**（`checked=<N> expected=<N>` 一致・全件で削除行なし）。fail-closed: 0 バイト原本 → **exit 1**（EMPTY-ORIGINAL・周回3）／件数不一致 → **exit 1**／dir 不在・0 件走査・期待件数が非正整数または 6 桁超 → **exit 2**（周回2/3） | Claude |

注:
- 合否判定インターフェースは全 TC で exit code に統一（合格=exit 0）。不在・無削除の判定は `! grep -q` / awk の exit 畳み込み形。
- TC-03〜06 はスクリプトファイル実行形（`bash <file>`）に統一する（plan-review Warning 対応: パイプ複合コマンドの直接実行を避け、allowlist 単体形 `bash` 1 コマンドで走らせる）。**スクリプト全文は計画書 `plan_I134.md`「検証スクリプト全文（TC-03〜06・scratchpad 実行用）」に記載**（本文書に fenced で掲載すると omission-lint が宣言外ゲートと誤認するため計画書側へ配置。code-review 20260719_2210 High 対応・診断記録 `I134_fix_diagnosis_20260719_2221.md` 案 A）。
- TC-02 のチェッカー・TC-03〜06 を決定論ゲートセクションへ宣言しない理由は同セクション末尾の注記参照。
- ラベル判定は行頭アンカー（`^\*\*背景\*\*:`）。引用ブロック内の同形行との誤検知限界は計画 リスク2 に記録済み（現状の該当は I134 本文のみで実害なし）。

## false-green 自己検証

### 計画時に前倒し実施済み（2026-07-19）
- **TC-01 相当（G1）**: 未実装のテンプレートに対し grep 2 本 → **両方 exit 1（NG）** 実測＝欠落を正しく検知。実装後の exit 0 転化が合否。
- **TC-02 相当（G2）**: チェッカーロジックを現状 `docs/issues/open` へ実行 → **exit 1・MISSING 25 件**（計画 調査結果 (A) と同一リスト）。合格系（I134 のみの dir）→ **exit 0**。注入系（ラベル無しダミー混入）→ **exit 1** 復帰。
- **TC-03 相当（G3）**: GitHub 41 件走査 → **exit 1・missing=38**（計画 調査結果 (B) と同一リスト）。
- **TC-04 相当（G4）**: awk 判定へ削除 0 入力 → exit 0・削除 1 入力 → **exit 1** 実測。
- **TC-05/06 相当（G5・同一ロジック）**: diff 判定へ挿入のみ → 合格・行削除入り → **不合格（`^<` 検知）** 実測。

### 実装後に実施
- **TC-02-inject**: リポジトリ常設のチェッカー本体に対する注入再確認（ダミーファイル方式・上表）。他の TC は入力注入型で計画時実証から判定ロジックが変わらないため再注入不要。

## 実施記録
- 2026-07-19（/implement 実施 ✅）:
  - TC-01: (a) `^\*\*背景\*\*:` (b) `^\*\*目的\*\*:` とも **exit 0**（計画時の NG 実証 exit 1×2 から合格へ転化＝AC-1 達成）。
  - TC-02: `bash scripts/claude/check-issue-background.sh docs/issues/open` → **exit 0**（`OK: all files have 背景/目的 labels`・対象 25 件すべて挿入済み）。
  - TC-02-inject: ラベル無しダミー md を置いた scratchpad ディレクトリへ常設チェッカーを実行 → **exit 1**（`MISSING` 列挙・`NG: 1 file(s)`）→ ダミー削除。検知能力を実装後にも確認。
  - TC-03: 41 件ループ走査 → **exit 0**（`total=41 missing=0`。計画時 missing=38 から全件反映へ転化＝AC-4 達成）。
  - TC-05: sweep 前スナップショットと `docs/issues/open/*.md` 全件（tracked 12 件含む 26 件）を diff → **exit 0**（削除行なし＝挿入のみ。要求の untracked 13 件より広く全ファイルで確認）。
  - TC-06: 退避原本 38 件（要求の直接更新 26 件＋paired 12 件も含めて拡大実施）と更新後 body を diff → **exit 0**（全 38 件で削除行なし）。
  - TC-04: sweep コミット（5488652）作成後に `git diff --numstat origin/develop...HEAD -- docs/issues/ ':(exclude)docs/issues/open/I134.md'` の削除ゼロ判定 → **exit 0**（DELETION 出力なし。コミット全体の 4 deletions は pathspec 対象外の plan/auto_test の記録更新行）。
  - 実装時の事実訂正: 見出し無し本文は #10・#220 の 2 件のみ（#42/#44 は見出し実在のため見出し直下挿入）。計画書に訂正記録済み。

- 2026-07-20（敵対的レビュー周回1 修正後の再実走 ✅）:
  - TC-01: run_declared_gates 実走 → grep 2 本とも **exit=0**・GATE_VERDICT=OK・omission-lint=OK。
  - TC-02: 強化版チェッカー → **exit 0**（`OK: all 27 files`・I139 追加後の 27 件）。注入: dir 不在 → **exit 2**・空 dir → **exit 1**・ラベル無しダミー → **exit 1**（fail-closed 3 方向を実証）。
  - TC-03: **exit 0**（**total=44 missing=0**）。sweep 後に隣 worktree で I140〜I142（#251〜#253）が旧テンプレ起票され missing=3 が再発 → 同一手順で追補（周回1 High 対応）。さらに隣セッションの /plan-issue I140 本文再同期で #251 のラベルが一度消失 → 規定どおり冪等に再追補（レース窓の実例 2 件目・原本退避も現行本文で更新）。
  - TC-04: **exit 0**（削除ゼロ維持）。
  - TC-05（強化版・スナップショット駆動＋I134.md 除外）: **exit 0**（checked=25・削除行/消失なし）。注入: ファイル消失（スナップショットに在るファイルを現物から除いた temp repo）→ **exit 1・FILE-DELETED 検出**・スナップショット dir 不在 → **exit 2**（周回1 H1 の盲点解消を実証）。
  - TC-06（強化版・期待件数突合）: **exit 0**（checked=41 expected=41・全件削除行なし）。注入: 期待件数 42 指定 → **exit 1・count mismatch**（原本保存漏れの fail-closed を実証）。
  - GitHub 本文の宣言外挿入の記録（周回1 Medium 対応）: paired 12 件の `--body-file` 全文同期により、ローカル側にのみ存在した `- GitHub Issue: #NNN` 行が 11 件（#179/#180/#189/#191/#207/#208/#216/#230/#233/#244/#245）の GitHub 本文へ追加挿入されていた。全件が自番号と一致する挿入のみ（削除ゼロ・TC-06 で機械確認済み）で、bootstrap 由来の正当なメタ行の同期であるため**受容**（是正不要・ここに記録）。
  - 挿入ラベルの恒久記録: `docs/reviews/I134_sweep_inserted_labels.md`（周回1 Medium「一覧未記録」対応・計画 ステップ4-1 の履行）。

- 2026-07-20（敵対的レビュー周回2 修正後の追加検証 ✅）:
  - TC-04（強化版・I134.md 存在チェック追加）: 本走 **exit 0**。注入: I134.md 不在の temp repo → **exit 1・FILE-DELETED**（丸ごと削除の無警報を解消。numstat 除外による行置換の許容は設計どおり維持）。
  - TC-06（強化版・引数検証追加）: 本走 41 件 → **exit 0**。注入: 非数値引数 `5x` → **exit 2**・空 dir → **exit 2**（0 件走査 fail-closed）・`EXPECTED=0` → **exit 2**（非数値時に照合が素通りする false-green を解消）。
  - TC-03 仕様行の旧値（41 件固定）を「実行時点の open 全件」へ是正（周回2 High・AC-4 再定義の未伝播解消）。イシュー・計画書・レビューチェックリスト・manual No.1 の固定件数残存も同時整合。
  - 恒久記録へ #239(I131) を追補（sweep 時 open・記録初版前にクローズされ欠落していた分。母集合を「open 全件」でなく「更新した全件」に是正）。
  - 受容（記録のみ）: TC-05/06 の比較基準（scratchpad スナップショット）は実行セッション自身が管理する ephemeral な基準であり原理的に自己証明の限界を持つ。tracked 12 件は origin/develop とバイト一致を独立確認済み（周回2 で実証）・GitHub 側は編集履歴が恒久監査経路・untracked 分はこの限界を明記して受容する。

- 2026-07-20（敵対的レビュー周回3 修正後の追加検証 ✅）:
  - TC-04（基底 ref 検証を追加）: 本走 **exit 0**。注入: `origin/develop` を持たない temp repo → **exit 2**（従来は git の fatal を awk が空入力で飲み込み exit 0 に化けていた fail-open を解消）。
  - TC-06（0 バイト原本検出・期待件数の桁数上限を追加）: 本走 41 件 **exit 0**。注入: 0 バイト原本を 1 件混入（件数は一致させる）→ **exit 1・EMPTY-ORIGINAL**（退避時 gh 失敗の痕跡で削除検出とロールバック原本が同時に無効化される穴を解消）・桁あふれ引数 → **exit 2**（`[ -ne ]` のエラーで照合が素通りする残穴を解消）。
  - 実データの健全性: `find gh_orig -name '*.md' -size 0` → 0 件/41 件（今回の退避に 0 バイト原本なし）。

- 2026-07-20（敵対的レビュー周回3・文書整合検査後の対応 ✅）:
  - **レース窓の 3・4 例目**: TC-03 再実走で missing=2（**#255(I143)** = sweep 後の旧テンプレ新規起票・**#253(I142)** = 隣セッションの本文再同期による再消失）→ 規定どおり冪等に追補し **total=44 missing=0** で合格。累計のレース事例: #251〜#253（周回1 新規）・#251（再同期消失）・#255（新規）・#253（再同期消失）。
  - **TC-07 新設（AC-5 の決定論判定）**: 引き継ぎスニペットの集合が隣 worktree の実態と一致するかを機械検証。本走 → **exit 0**（`OK: snippet set matches (4 file(s))`＝I074/I086/I114/I122）。注入: スニペット未整備ファイルを 1 件混入 → **exit 1**（差分に当該ファイルを出力）・対象 dir 不在 → **exit 2**。判定は「本ブランチで commit 済み＝develop 取り込みで配布される」ファイルを除外する（初回実装時にこの除外が無く tracked 12 件で偽 NG が出たため是正）。
  - TC 表への fail-closed 仕様の反映（TC-04 の I134.md 存在・基底 ref／TC-06 の EMPTY-ORIGINAL・引数検証）とレビューチェックリストの同期、恒久記録の母集合定義の明確化（**#250(I139) は新テンプレ起票＝本イシューの挿入ではない**旨を明記）、計画書に残っていた「41 件」固定表記 2 箇所の是正、manual No.1 の未追跡ファイル説明の更新を実施。

- 2026-07-21（**/test 実施 ✅ 全 TC PASS**）:
  - TC-01: run_declared_gates → grep 2 本とも **exit=0**・GATE_VERDICT=OK・omission_lint=OK。
  - TC-02: `bash scripts/claude/check-issue-background.sh docs/issues/open` → **exit 0**（`OK: all 27 files`）。
  - TC-02-inject: ラベル無しダミー dir → **exit 1**（検知能力を再確認）。
  - TC-03: **exit 0**（`total=44 missing=0`）。※初回実行では `missing=1`（#253）で NG → レース窓規定どおり冪等に追補して再実走で合格（下記「レース窓の観測」参照）。
  - TC-04: **exit 0**（tracked 削除ゼロ・I134.md 存在・基底 ref 解決を確認）。
  - TC-05: **exit 0**（`checked=25`・削除行/ファイル消失なし）。
  - TC-06: **exit 0**（`checked=42 expected=42`・全件で削除行なし）。※初回実行では `checked=42 expected=41` の件数不一致＋#253 の DELETED-LINES で NG → 退避原本が #255 追補で 42 件に増えていたため期待件数を実態（42）へ更新し、#253 は再追補で原本も更新して合格。**期待件数はレース追補のたびに退避原本の実件数へ更新する**（固定値ではない）。
  - TC-07: **exit 0**（`OK: snippet set matches (4 file(s))`＝I074/I086/I114/I122）。
  - pytest / Jest / E2E: **非該当**（BE/FE コード変更ゼロ。本文書冒頭の宣言どおり）。
  - **レース窓の観測（重要・運用上の残課題）**: #253(I142) のラベルが**計 3 回**消失した（隣セッションが I142 のローカルファイル＝ラベル未保有版を `gh issue edit --body-file` で再同期するたびに上書きされる）。#251 も 1 回消失。**GitHub 側の状態は、隣 worktree のローカルファイルにラベルが入るまで安定しない**（＝引き継ぎ手順の実施が恒久解）。TC-03/TC-06 は「実行時点の実態」を fail-closed で正しく検出しており、検証体系としては健全（消失を見逃していない）。

## 再発防止記録（fix-loop 2026-07-19・code-review HIGH 対応）
- **なぜ失敗したか**: 本文書に `## 決定論ゲート（自動実走）` セクションが無く（自動実走可能な TC-01 の grep 2 本が未宣言）、かつ TC-03〜06 のスクリプト全文を fenced で掲載したため、omission-lint（宣言セクション外の fenced 内 allowlist パターン検出）が HIGH を返した。
- **何を変えたか**: ①決定論ゲートセクションを新設し TC-01 の grep 2 本を宣言（code-review ごとに自動実走・証跡注入される）②スクリプト全文を計画書「検証スクリプト全文」節へ移設し本文書は参照化 ③チェッカーに formal gate 化時の移動制約コメントを追記（code-review Medium 対応）。検証: omission-lint OK 転化・ゲート 2 本 ALLOW 実走 exit 0・隠れゲート形の HIGH 検知維持・TC-02 無回帰（docs/reviews/I134_fix_test_result_20260719_2239.md）。
- **セキュリティ上の考慮点**: 該当なし（文書構成とコメントのみ・宣言した 2 コマンドは読み取り専用 grep）。
- **次回どう防ぐか**: 自動実走可能な TC は最初から決定論ゲートセクションに宣言する。スクリプト全文の参考掲載は auto_test の fenced に置かない（現行 lint は隠れゲートと区別しないため計画書側へ）。lint の弁別と allowlist の check-*.sh 拡張という根治は I139(#250) で対応（I130 マージ後着手）。
