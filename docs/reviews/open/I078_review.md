# I078 実装レビュー（正解選択肢の表示・編集保持 / is_correct 露出分離）

- 関連: docs/issues/open/I078.md / docs/plans/open/plan_I078.md / GitHub #156 / Draft PR #218
- レビュー対象コミット: （実装後に追記）

## レビュー観点（計画に対応）

### 1. 情報露出の分離（最重要・答え漏洩防止）
- [ ] `ChoiceAdminSerializer`/`ProblemAdminSerializer` が新設され、参照は定義＋`ProblemViewSet.serializer_class`＋import のみ（grep で全件確認）
- [ ] 既存 `ProblemSerializer`・`ChoiceSerializer`・`ChoiceDisplaySerializer`・`ProblemDisplaySerializer`・`QuizAnswerDetailSerializer` に**1文字も変更がない**
- [ ] `generate_ai`/`generate_adaptive` の応答が `ProblemSerializer(...)` のまま（`ProblemAdminSerializer` に変わっていない）
- [ ] 出題（next_problem）・結果（quiz retrieve）・AI 応答に is_correct が漏れない否定 TC（TC-AUTO-05/06/07）が PASS

### 2. 管理経路の露出と読み書き両可
- [ ] admin の list/retrieve レスポンスの各 choice に `is_correct` が含まれ、値が DB と一致（TC-AUTO-01/02）
- [ ] create/update で is_correct が従来どおり保存され、レスポンスにも返る（TC-AUTO-03/04）
- [ ] `permission_classes` を変更していない（I102 の `IsAuthenticated + IsOrgAdmin` のまま）

### 3. フロントエンド
- [ ] `ProblemPreview.tsx`: 正解選択肢にチェックアイコン＋「正解」Chip（緑・色のみ非依存）、緑枠・緑背景は維持。不正解行にマークなし
- [ ] `QuizManagement.tsx` にコード変更がない（計画どおり動作確認のみ）
- [ ] `services/types.ts` に変更がない

### 4. テスト
- [ ] TC-AUTO-01〜08 が追加され全 PASS・既存 61 件回帰なし・FE Jest 7 件回帰なし
- [ ] 露出系 TC（01〜04）の実装前 RED を確認・記録済み（TDD）
- [ ] 非露出系 TC（05/06/07）の false-green 注入検証（RED 確認）を実施・記録済み

### 5. 計画との一致
- [ ] 変更ファイルが `serializers.py`・`views.py`・`ProblemPreview.tsx`・新規テストのみ（計画外の変更がない）
- [ ] 実装位置・コードが計画書のコード例と一致

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- `ProblemSerializer` を継承した `ProblemAdminSerializer` で、`Meta.extra_kwargs` 等の継承挙動により意図しないフィールド可視性の変化が**choices 以外**に生じていないか（fields 全キーの差分を実レスポンスで比較して反証せよ）。
- is_correct が漏れる**未列挙の経路**が本当に無いか: `ChoiceSerializer`/`ProblemSerializer` の全 import・全インスタンス化箇所（`submit_answer` の `correct_choices` 明示返却は仕様内）、`ProblemMediaAssetSerializer` 等の間接経路、API スキーマ生成やログ出力経由の露出を再走査して反証せよ。
- `to_internal_value`（JSON 文字列 choices のパース）が `ChoiceAdminSerializer` 経由でも同一に機能するか（multipart 実送信で反証せよ）。
- 編集ダイアログ初期選択が「single では動くが multiple で全滅する」等の型分岐バグがないか（`watch`/`setValue` の実挙動で反証せよ）。
- キャッシュ（user_id ベース・TTL 1h）に旧形式が残った場合に FE がクラッシュしないか（`is_correct === undefined` 経路の後方互換）。

## 結果
（実装・テスト後に記入）
