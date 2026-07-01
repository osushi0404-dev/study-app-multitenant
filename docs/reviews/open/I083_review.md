# I083 レビュー記録

- **対象イシュー**: #166 / docs/issues/open/I083.md
- **計画書**: docs/plans/open/plan_I083.md
- **Draft PR**: #171
- **レビュー対象**:
  - `scripts/claude/hooks/pretooluse_guard.py`（`_is_force_flag`/`_push_has_force`/`_push_is_dynamic` 追加・force 判定置換・末尾 ask 追加）
  - `scripts/claude/tests/test_pretooluse_push_guard.sh`（I083 TC 追記・`cka`/`runj` ヘルパー）
  - `docs/claude-code-structure.md`（限界注記更新）

## レビュー観点（計画段階で確定・実装後に /code-review・敵対的サブエージェントで実施）

### 1. 正当性（欠陥根治）
- [ ] 6 動的回避形が全て ask（exit0＋ask JSON）になるか（TC-D1〜D8）。
- [ ] force 取りこぼし形（`-f`/`-uf`/`--force-with-lease`/`--force-if-includes`/複合）が exit2 block か（TC-F1〜F6）。
- [ ] 現行 `re.match` の潜在誤 block が根治され安全 push が pass するか（TC-FP1〜FP4）。

### 2. 誤検知・誤 ask（過剰防御の回避）
- [ ] 静的安全 push が無確認通過（ask も block も無し）か（TC-S1〜S3）。
- [ ] ラッパーキーワードを名前に含む安全 push（`bash-feature`/`sh-fix`/`eval-remote`/非 alias `-c`）が pass するか（TC-W1〜W4）＝構造的検出が効いているか。
- [ ] 動的 feature push が exit2（誤検知）されないか（TC-D7）。

### 3. 兄弟ルール一貫性・順序（敵対的観点）
- [ ] 動的 ask が全 hard-block の**後**に置かれ、`git push origin $VAR && rm -rf x` で rm -rf block が先に効くか（TC-D9）。
- [ ] force block が dynamic ask より優先（`git push -f origin $VAR` → exit2）か。
- [ ] DANGER_OK escape が動的・force・ラッパー隠蔽 force すべてで維持されるか（TC-DOK1〜3）。

### 4. テスト健全性（false-green 禁止）
- [ ] 新判定行（`_push_has_force`/`_is_force_flag` 短縮分岐/`_push_is_dynamic`/構造的ラッパー `eval`・`sh -c` 分岐/`-c alias.` 分岐）が load-bearing であることを注入で対裏取り（TC-FG-G/H/I/J/K）。
- [ ] ask 判定が exit code だけでなく `permissionDecision=ask` の stdout（`runj`/`rungj`）で確認されているか（**ask と pass は exit0 同一**＝exit code 比較では false-green を見逃す）。
- [ ] 限界注記の更新が決定論 grep（TC-DOC1a/b/c）で固定されているか。

### 5. ドキュメント整合・スコープ
- [ ] 限界注記が「対応済み」へ更新され、残余既知限界（`eval "$VAR"` 完全隠蔽＝脅威モデル外）が明記されているか（honest scoping）。
- [ ] `.claude/settings.json` 不変か。
- [ ] スコープ外（reset/checkout/rm・静的形）に手を入れていないか。

### 6. 設計判断のトレーサビリティ
- [ ] 実装が I083 設計確認メモ Q1〜Q8 の確定値と一致しているか（方式(a)/誤検知=hard block 定義/settings 不変/visible-intent 限定/動的範囲=push 引数全体/force=pure `_segments`/ラッパー隠蔽 force=ask・`-c alias.` 限定/構造的ラッパー検出）。

## 既知の残余限界（仕様・対象外）
- push トークンを完全隠蔽する偽装形（`eval "$VAR"`／`sh -c "$CMD"` で push が文字列に一切現れない）は脅威モデル（事故防止）外。`DANGER_OK=1` 解除に委ね、`docs/claude-code-structure.md` に明記する。

## code-review 検出事項の処理（後続イシューへ繰り延べ）
- 実装後の独立 code-review（再レビュー・docs/reviews/I083_code_review_20260701_1602.md）が **Medium** を検出: `--all`/`--mirror`/`--repo` 判定が force と同型の貪欲正規表現のまま残り、複合コマンド跨ぎで安全 push を誤 block（`git push origin feature && ls --all` → exit 2・`; foo --repo=x` → exit 2 を実測）。
- 判断: I080 由来の pre-existing 欠陥・本 PR の変更対象外（I083 スコープの「含まない」に該当）・本 PR は悪化させない。→ **差し戻さず I088(#172) に切り出して根治**（同一原因・同一修正＝`_segments` 化）。
- その他の Low 指摘（`-rf` 短縮クラスタ判定＝文書化済み許容・`runj` の `$?` タイミング＝注記のみ）は対応不要。

## レビュー結果
- plan-issue-review ×3（20260701 0055/0222/1655）＝すべて VERDICT OK。3回目で TC-DOK の runj 漏れ Warning を検出・spec 整合済み。
- code-review ×2（20260701 0301/1602）＝すべて VERDICT OK。2回目で `--all/--mirror/--repo` 兄弟バグ Medium を検出 → I088(#172) へ繰り延べ。

## /test 実行結果（20260701）
- 自動（決定論・canonical）: `test_pretooluse_push_guard.sh` = **87 PASS / 0 fail**（既存40＋I083 追加47）／`test_pretooluse_checkout_guard.sh` = **14 PASS / 0 fail**（無回帰）。
- pytest/Jest/E2E = **非該当**（Backend/Frontend 変更なし・auto_test.md 指定どおり）。
- 手動 No.1〜5（Claude 実施）= すべて ✅ OK（テスト実行・構文・限界注記 grep・settings 不変）。
- 手動 No.6〜7（Human・プレーン default 新規セッション）= 実施依頼中（ask プロンプト描画・安全 push 無確認通過のハーネス統合目視）。
