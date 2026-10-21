# I180 実装レビュー: Pillow を 13.0.0 に更新（既知脆弱性 8 件の解消）

- 関連: docs/issues/open/I180.md / docs/plans/open/plan_I180.md / GitHub #301 / Draft PR #303
- テスト文書: docs/tests/open/I180_auto_test.md / docs/tests/open/I180_manual_test.md
- レビュー対象コミット: ステップ 1 `9b05819 fix(I180): Pillow を 13.0.0 に更新し既知脆弱性 8 件を解消` / ステップ 2 `f064262 test(I180): 画像アップロード検証の Pillow 依存分岐の再発防止テストを追加` / ステップ 4 `docs(I180): retro スキルに改善案の要否判定手順（2.7）を追加`（2026-10-21 追加）。ほかは docs コミット

## 変更概要
- Pillow 12.3.0 → 13.0.0（`backend/requirements.txt` の 1 行）
- 画像アップロード検証（`validate_image_file`）の Pillow 依存分岐の再発防止テスト 9 件を追加
- 新規テストの false-green 検証用プローブと、その反証用フィクスチャを docs/tests に追加

## レビュー観点（計画に対応）

### 1. 変更の局所性（計画外変更がないこと）
- [ ] docs 以外の差分が `backend/requirements.txt`（Pillow の 1 行）・`backend/problems/tests/test_I180_image_validation.py`（新規）・`.claude/skills/retro/SKILL.md`・`scripts/claude/tests/test_i180_retro_triage.sh`（新規）の 4 ファイルだけである（後 2 つは 2026-10-21 追加のステップ 4）
- [ ] アプリのコード（`backend/problems/utils.py` を含む）に変更がない
- [ ] `backend/Dockerfile`・`docker-compose.yml`・`.github/workflows/*.yml`・`backend/requirements-dev.txt`・`backend/pytest.ini` に変更がない（計画 §2-8）
- [ ] マイグレーションの追加がない
- [ ] コミットが段ごと（依存更新 → テスト追加 → retro スキル）に分かれている

### 2. 依存更新の正確性
- [ ] `Pillow==13.0.0` の `==` 完全固定で、12 系の行が残っていない（TC-AUTO-01）
- [ ] backend / celery / celery-beat のコンテナすべてで `PIL.__version__ == '13.0.0'`（TC-AUTO-03・再ビルド漏れがない）
- [ ] Pillow 以外の依存の版が変わっていない

### 3. 脆弱性の解消
- [ ] `pip-audit -r requirements.txt` が exit 0（TC-AUTO-02）
- [ ] CI の Backend Lint & Security が SUCCESS（TC-AUTO-07）
- [ ] Pillow 以外の新規検出が出ていない（出ていれば別イシューとして記録されている）

### 4. 計画書の記録（AC-7）
- [ ] 計画 §2-3 に 8 件の CVE（ID・GHSA・影響する処理・本リポジトリでの到達性）が記録されている
- [ ] 計画 §2-4 にリリースノートの非互換変更・非推奨の全項目と、利用箇所（`Image.open`・`.size`・`Image.new`・`.save(format="PNG")`）との突き合わせ結果が記録されている

### 5. 再発防止テストの品質
- [ ] 新規テストが計画 §5-2 のコードと一致し、9 件すべて通る（TC-AUTO-04・件数を JUnit XML で判定）
- [ ] 期待値が具体値（`(True, None)`・エラーメッセージの完全一致・固定文の前方一致）で書かれている
- [ ] プローブの 4 種の書き換えをすべて検知する（TC-AUTO-05 判定 1＝exit 0）
- [ ] プローブが中身のないテストを不合格にする（TC-AUTO-05 判定 2＝exit 1）
- [ ] プローブ・フィクスチャのファイル名が `test_*.py` に一致せず、通常の pytest 収集に混ざっていない（全件が 103 件ちょうど・TC-AUTO-06）
- [ ] ruff（pre-commit）が通っている

### 6. 無退行
- [ ] backend 全テストが 103 件 pass（94 + 新規 9・TC-AUTO-06）。skip・削除による緑化がない
- [ ] 画像アップロードの結合テスト（`test_I073_image_update.py`）が全件 pass
- [ ] CI の全 6 チェックが SUCCESS（TC-AUTO-07）
- [ ] 手動テスト No.1〜5 が OK（再ビルド後の backend の起動・celery / celery-beat の起動・WebP / JPEG / PNG の処理系）

### 7. retro スキルの要否判定手順（2026-10-21 追加・AC-8）
- [ ] 手順 2.7 が計画書 §5-5 の文面と一致し、手順 2.5 と 3 の間にある（TC-AUTO-08）
- [ ] 2 基準（ハーネス・ループエンジニアリングのベストプラクティス／スピード）・4 問・3 区分・新規起票の条件・見送り理由の提示がそろっている
- [ ] 手順 3 の選定基準の先頭に「2.7 で採用・同梱と判定したものだけを表に載せる」があり、既存の 2 行目以降が変わっていない
- [ ] 平易化ルールの見出しが「手順2.5/2.7/3/4/5」になり、本文は変わっていない
- [ ] 既存の retro テスト（I114）が 14/14（TC-AUTO-09）
- [ ] 新規テストが変更前のスキルで exit 1 になる（false-green でない）
- [ ] shellcheck（pre-commit）が通っている

## テスト結果
- 自動: TC-AUTO-00〜07 すべて合格（2026-10-21・詳細は auto_test の実施記録）。CI は head `db5d205` で 6 チェックすべて SUCCESS
- 手動: No.1〜5 すべて OK（Claude 実施・Human の手順なし）

## 計画との差分
- なし（新規テスト・プローブのコードは計画書 §5-2・§5-3 と diff 0。変更ファイルは計画 §4 のとおり）

## ロールバック
- 2 コミットを `git revert`（ステップ 2 → 1 の順）し、backend / celery / celery-beat を再ビルドする。データ・マイグレーションの変更なし（計画 §8）

## 結果
- `/code-review`: OK（`docs/reviews/I180_code_review_20261021_1013.md`・決定論ゲート 5 件 exit 0・高リスク No・敵対的レビュー不要）
- `/test`: OK（2026-10-21・自動 TC-AUTO-00〜07 すべて合格・手動 No.1〜5 すべて OK・Human の手順なし）
- `/code-review`（ステップ 4 後・2 回目）: OK・`RISK: YES`（`docs/reviews/I180_code_review_20261021_1053.md`・決定論ゲート 7 件 exit 0）。その後の `/test`（2 回目・head `0732e60`）も OK（自動 TC-AUTO-00〜09 すべて合格・手動 No.1〜5 すべて OK）。敵対的レビューは**ユーザー判断で省略**（例外・`docs/reviews/I180_adversarial_review_20261021_1120.md` に根拠を記録。起動した 3 体はユーザー指示で停止・findings 受領なし）
