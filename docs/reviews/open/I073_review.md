# レビュー: I073 問題編集時の画像更新（追加・差し替え・削除・並び替え）

- **関連イシュー**: #150
- **計画書**: docs/plans/open/plan_I073.md
- **Draft PR**: #151

## レビュー対象
バックエンド・フロントエンドのコード変更（DB スキーマ変更なし）:
- `backend/problems/services/problem_service.py`（`_save_image_as_asset` 抽出・`update_problem_with_images` 実装・`_reconcile_images` 新規・`_process_images` リファクタ）
- `backend/problems/views.py`（`ProblemViewSet.perform_update` で order/files 取り出し・service 呼び出し・キャッシュ無効化）
- `frontend/src/pages/QuizManagement.tsx`（編集ダイアログ: 既存画像ロード・items 化・multipart 送信）
- `frontend/src/components/ImageUploadArea.tsx`（既存/新規混在・↑↓並び替え・削除・a11y）
- `frontend/src/services/quiz.service.ts`（`updateProblem` を multipart 転用）
- `frontend/src/services/types.ts`（`EditableImage` 型追加）
- `backend/problems/tests/test_I073_image_update.py`（TC-AUTO-00〜11）

## レビュー観点（本イシュー固有）
- [ ] トランザクション原子性: `update_problem_with_images` 全体が `@transaction.atomic` で、途中失敗時に画像/選択肢/テキストの部分更新が残らない（TC-AUTO-07/08 で担保）
- [ ] **物理削除の遅延順序**: `_reconcile_images` が「新規保存→link再構築→★最後に物理削除」の順序を厳守し、途中失敗時に残すべき物理ファイルが消えない（TC-AUTO-07 で「物理・DB ともに元のまま」を担保）
- [ ] position UNIQUE 制約: 並び替えが link 行 delete→recreate で実装され、インプレース更新による制約違反が起きない（TC-AUTO-04）
- [ ] 共有画像保護: 削除前に他問題の有効 link を確認し、共有時は紐づけ解除のみ・物理削除しない（TC-AUTO-05）
- [ ] 認可/テナント境界: 他組織 404（queryset スコープ）・他問題アセットUUID混入の 400 拒否（TC-AUTO-06/09）
- [ ] **SEC-1 テナント越境（subject 付け替え）**: 画像保存の org/subject が問題の永続化済み subject を権威とし、subject の他組織付け替えを 400 で拒否。他組織ストレージへ新規ファイルが書き込まれない（TC-AUTO-12）
- [ ] null/空値の二値仕様: `*_images_order` 非送信＝当該種別無変更 / `[]`＝全削除 が一貫実装（TC-AUTO-02/03、R5）
- [ ] DRY/C7: 新規ファイル保存が `_save_image_as_asset` で作成・更新フロー共通化され、`_process_images` の外部挙動が回帰していない（TC-AUTO-00）
- [ ] 物理削除失敗時のログのみ続行（既存 `delete_problem` 踏襲）が維持されているか
- [ ] フロント: 既存画像のプレビュー（URL）と新規（`URL.createObjectURL`）の両対応、↑↓の端無効化、削除の保存前取り消し可、`aria-label` 付与
- [ ] フロント: 作成フロー（`handleCreateProblem`）の挙動が items 化後も従来通り（order を送らず positional `*_image_i`）
- [ ] 入力バリデーション: 新規ファイルが既存 `validate_image_file` を通る／order の JSON パース失敗・上限超過を 400 で拒否
- [ ] 否定・回帰系 TC（02/04/05/06/07/09）が失敗注入で NG を返すことを確認・記録済みか（false-green でないこと）

## セキュリティチェック
- [ ] IDOR 防止: 編集対象問題・参照アセットがともに request.user.organization スコープに限定されているか
- [ ] パストラバーサル: storage_key / ファイル名が既存ユーティリティ（`sanitize_filename`/`get_storage_path`）経由で生成されているか
- [ ] bandit MEDIUM 以上・flake8 の新規違反なし、npm audit high/critical の新規発生なし

## 指摘記録欄
（plan-issue-review / code-review 実行時に記入）

| 重大度 | 観点 | 指摘内容 | 該当箇所 | 対応 |
|--------|------|---------|---------|------|
| | | | | |
</content>
