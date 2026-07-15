# I103 実装レビュー（越境 subject 書き込み防止）

- 関連: docs/issues/open/I103.md / docs/plans/open/plan_I103.md / GitHub #193
- レビュー対象コミット: （実装後に追記）

## レビュー観点（計画に対応）

### 1. 認可・テナント境界（最重要）
- [ ] `perform_create` に org 一致検証（`subject.organization_id != request.user.organization_id`）が追加され、越境時 403 で拒否される
- [ ] `generate_ai`・`generate_adaptive` にも同一検証が `Subject.objects.get` 直後・生成の前に追加されている
- [ ] 3経路の判定式が完全一致（コピペずれ・`!=`/`==` 反転がない）
- [ ] `save_to_db=False` でも org チェックが効く（生成前に返る）
- [ ] 越境時に外部 AI 呼び出し・DB 書き込みの副作用が発生しない（チェックが手前にある）

### 2. status/レスポンス
- [ ] `perform_create` は `PermissionDenied`（403・`{"detail":...}`）、AI経路は `Response({"error":...}, 403)`
- [ ] message は `他組織の科目には問題を作成できません` で統一
- [ ] 越境拒否が 403 で、既存 upload/delete=403 と一致（400 になっていない）

### 3. 既存挙動の非破壊
- [ ] 自組織の create（201）・AI 経路（非403）が従来どおり
- [ ] `perform_update` SEC-1（400）を本イシューで変更していない（別イシュー）
- [ ] `ProblemSerializer`/`ProblemService` に不要な変更がない（queryset 二重防御は不採用）

### 4. テスト
- [ ] TC-AUTO-01〜06 が追加され全 PASS
- [ ] 否定 TC（01/02/03）が実装前に RED を確認済み（false-green でない）
- [ ] 既存 50 件が回帰なし

### 5. 計画との一致
- [ ] 変更ファイルが `views.py` と新規テストのみ（計画外の変更がない）
- [ ] 実装位置・コードが計画書の例と一致

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- 3経路以外に Problem を作成する経路が本当に無いか（管理コマンド・import・signal 等）を再走査し、取りこぼしを反証する。
- `perform_create` で subject が None のケース（必須のはずだが）に検証がスキップされ NULL 経路が抜けないか。
- `generate_ai` の count>1（batch）で subject が1つに固定される前提が崩れないか。

## 結果
（実装・テスト後に記入）
