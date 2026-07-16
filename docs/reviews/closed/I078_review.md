# I078 実装レビュー（正解選択肢の表示・編集保持 / is_correct 露出分離）

- 関連: docs/issues/open/I078.md / docs/plans/open/plan_I078.md / GitHub #156 / Draft PR #218
- レビュー対象コミット: 4714a76（実装）・8a134c4（code-review Low 指摘対応）

## レビュー観点（計画に対応）

### 1. 情報露出の分離（最重要・答え漏洩防止）
- [x] `ChoiceAdminSerializer`/`ProblemAdminSerializer` が新設され、参照は定義＋`ProblemViewSet.serializer_class`＋import のみ（grep で全件確認）
- [x] 既存 `ProblemSerializer`・`ChoiceSerializer`・`ChoiceDisplaySerializer`・`ProblemDisplaySerializer`・`QuizAnswerDetailSerializer` に**1文字も変更がない**
- [x] `generate_ai`/`generate_adaptive` の応答が `ProblemSerializer(...)` のまま（`ProblemAdminSerializer` に変わっていない）
- [x] 出題（next_problem）・結果（quiz retrieve）・AI 応答に is_correct が漏れない否定 TC（TC-AUTO-05/06/07）が PASS

### 2. 管理経路の露出と読み書き両可
- [x] admin の list/retrieve レスポンスの各 choice に `is_correct` が含まれ、値が DB と一致（TC-AUTO-01/02）
- [x] create/update で is_correct が従来どおり保存され、レスポンスにも返る（TC-AUTO-03/04）
- [x] `permission_classes` を変更していない（I102 の `IsAuthenticated + IsOrgAdmin` のまま）

### 3. フロントエンド
- [x] `ProblemPreview.tsx`: 正解選択肢にチェックアイコン＋「正解」Chip（緑・色のみ非依存）、緑枠・緑背景は維持。不正解行にマークなし
- [x] `QuizManagement.tsx` にコード変更がない（計画どおり動作確認のみ）
- [x] `services/types.ts` に変更がない

### 4. テスト
- [x] TC-AUTO-01〜08 が追加され全 PASS・既存 61 件回帰なし・FE Jest 7 件回帰なし
- [x] 露出系 TC（01〜04）の実装前 RED を確認・記録済み（TDD）
- [x] 非露出系 TC（05/06/07）の false-green 注入検証（RED 確認）を実施・記録済み

### 5. 計画との一致
- [x] 変更ファイルが `serializers.py`・`views.py`・`ProblemPreview.tsx`・新規テストのみ（計画外の変更がない）
- [x] 実装位置・コードが計画書のコード例と一致

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- `ProblemSerializer` を継承した `ProblemAdminSerializer` で、`Meta.extra_kwargs` 等の継承挙動により意図しないフィールド可視性の変化が**choices 以外**に生じていないか（fields 全キーの差分を実レスポンスで比較して反証せよ）。
- is_correct が漏れる**未列挙の経路**が本当に無いか: `ChoiceSerializer`/`ProblemSerializer` の全 import・全インスタンス化箇所（`submit_answer` の `correct_choices` 明示返却は仕様内）、`ProblemMediaAssetSerializer` 等の間接経路、API スキーマ生成やログ出力経由の露出を再走査して反証せよ。
- `to_internal_value`（JSON 文字列 choices のパース）が `ChoiceAdminSerializer` 経由でも同一に機能するか（multipart 実送信で反証せよ）。
- 編集ダイアログ初期選択が「single では動くが multiple で全滅する」等の型分岐バグがないか（`watch`/`setValue` の実挙動で反証せよ）。
- キャッシュ（user_id ベース・TTL 1h）に旧形式が残った場合に FE がクラッシュしないか（`is_correct === undefined` 経路の後方互換）。

## 結果
（2026-07-17 記入。記入漏れの是正 — 実体の確認は code-review・/test 時点 2026-07-16 に実施済み）

### 実装結果評価
- 観点 1〜5 全項目 OK（チェック済み）。エビデンス: `docs/reviews/closed/I078_code_review_20260716_0137.md`（受け入れ条件 9 件すべて ✅・VERDICT: OK）＋ `git diff cd546e7..c2daee8` の再確認（コード変更は `serializers.py` +18 行のみ追加・`views.py` import＋`serializer_class` の 2 箇所のみ・`ProblemPreview.tsx`・新規テストの計 4 ファイル。`permission_classes`・`QuizManagement.tsx`・`services/types.ts` は不変更）。
- code-review 指摘は Low 3 件のみ: 2 件（next() デフォルト値・文書スニペット整合）はコミット 8a134c4 で対応済み。1 件（ChoiceAdminSerializer 非継承の二重保守リスク）は設計方針どおり・retro 判断事項として記録。
- 高リスク判定 Yes（答え漏洩 = C2 直撃）だが、否定 TC＋false-green 注入検証＋grep 全件確認により露出経路は構造的に封鎖と判断（code-review 記録と一致）。
- 注: 「敵対的レビュー観点」節の独立サブエージェント実行の記録は残っていない。実体検証は code-review の grep 全件確認・false-green 注入・否定 TC で担保。

### テスト結果
- 自動（/test 2026-07-16）: Backend 68 passed（TC-AUTO-01〜08 含む・回帰なし）・FE Jest 2 suites / 7 passed・E2E 7 passed。TDD RED（実装前 4 failed）・false-green 注入 RED（2 回とも）確認済み（`docs/tests/closed/I078_auto_test.md`）。
- 手動: 全 9 項目 OK（Claude 4・Human 5＝スクリーンショット確認。`docs/tests/closed/I078_manual_test.md`）。
- CI: develop（I121 マージ後）取り込み後の PR #218 で全 6 ジョブ green（2026-07-17）。

### 総合判定
OK — 残作業は PR #218 のマージのみ。
