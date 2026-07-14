# I107 レビュー: GitHubイシューのトラック軸ラベル分類（track:app / track:harness）導入

## 基本情報
- **対象計画書**: docs/plans/open/plan_I107.md
- **関連イシュー**: docs/issues/open/I107.md（GitHub Issue: #200 / Draft PR: #202）
- **レビュー目的**: トラック軸ラベル（track:app / track:harness）の新設・起票フロー文書の2軸必須化・オープンイシュー25件のバックフィルが、承認済み分類表・イシューのACどおりに実施されたかを評価する
- **期待する成果**: `gh issue list --label track:*` でトラック別一覧が取得でき、以後の起票で両軸ラベルが必須付与される運用が文書で担保されること

## 変更概要
- （2026-07-15 実装完了・commit `3838144`）トラック軸ラベル `track:app`（#0e8a16）/ `track:harness`（#5319e7）を GitHub に新設し、起票フロー文書を種別＋トラックの2軸必須付与（`--label` 分割形式・対象パスベースの判定基準つき）に更新。オープンイシュー25件へ承認済み分類表どおりバックフィル（app 8件 / harness 17件）。

## 変更点
- GitHubラベル: `track:app` / `track:harness` 新設（既存10ラベルは無変更）
- `.claude/skills/issue-bootstrap/SKILL.md`: step 4 を2軸必須化＋トラック判定基準追記
- `docs/runbooks/issue-flow.md`: ラベル設定2箇所（自動実行フロー ステップ3・統合ルール ステップ2）を同一粒度で2軸化
- `docs/runbooks/worktree.md`: §10 トラック構成表に「対応 GitHub ラベル」列を追加
- `scripts/claude/tests/test_i107_track_label_docs.sh`: 新設（文書回帰ゲート G5。false-green 実証: 文書更新前 exit=1 → 更新後 exit=0。記録は I107_auto_test.md AT-08）
- GitHub イシュー25件: トラックラベル付与（実装時サニティチェック: track無し/二重付与 0件・app 8件・harness 17件）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: GitHubラベル定義・オープンイシューのラベル・運用文書2ファイル（.claude/skills/issue-bootstrap/SKILL.md / docs/runbooks/issue-flow.md）

## テスト結果
- 自動: （/test 実行後に記入。AT-01〜08・決定論ゲート G1〜G5。実装時サニティチェックでは AT-05=0・AT-07=8/17・G5=exit 0 を確認済み）
- 手動: （テスト後に記入。No1〜5 = Claude / No6 = Human）
- ※ /code-review は CI ブロッカー（Pillow CVE = I108/#203）解消待ち。再開手順はイシューファイルの「現在地と再開手順」参照。

## 計画との差分
- なし（実装は計画の全ステップどおり・逸脱なし。plan-review 指摘の反映経緯は plan_I107.md「レビュー指摘への対応記録」参照）

## ロールバック
- ラベル: `gh label delete "track:app" --yes` / `gh label delete "track:harness" --yes`（付与済みイシューからも自動で外れる）。個別解除は `gh issue edit <番号> --remove-label`。
- 文書: git revert または feature ブランチ破棄。
