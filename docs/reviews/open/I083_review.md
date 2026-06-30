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
- [ ] 新判定行（`_push_has_force`/`_is_force_flag` 短縮分岐/`_push_is_dynamic`/構造的ラッパー分岐）が load-bearing であることを注入で対裏取り（TC-FG-G/H/I/J）。
- [ ] ask 判定が exit code だけでなく `permissionDecision=ask` の stdout で確認されているか（exit0 を pass と取り違えない）。

### 5. ドキュメント整合・スコープ
- [ ] 限界注記が「対応済み」へ更新され、残余既知限界（`eval "$VAR"` 完全隠蔽＝脅威モデル外）が明記されているか（honest scoping）。
- [ ] `.claude/settings.json` 不変か。
- [ ] スコープ外（reset/checkout/rm・静的形）に手を入れていないか。

### 6. 設計判断のトレーサビリティ
- [ ] 実装が I083 設計確認メモ Q1〜Q8 の確定値と一致しているか（方式(a)/誤検知=hard block 定義/settings 不変/visible-intent 限定/動的範囲=push 引数全体/force=pure `_segments`/ラッパー隠蔽 force=ask・`-c alias.` 限定/構造的ラッパー検出）。

## 既知の残余限界（仕様・対象外）
- push トークンを完全隠蔽する偽装形（`eval "$VAR"`／`sh -c "$CMD"` で push が文字列に一切現れない）は脅威モデル（事故防止）外。`DANGER_OK=1` 解除に委ね、`docs/claude-code-structure.md` に明記する。

## レビュー結果
（実装後に記入）
