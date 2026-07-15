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
- 自動: **AT-01〜08 全 PASS**（2026-07-15 /test 実走・詳細は I107_auto_test.md）。決定論ゲート G1〜G5 exit=0（/code-review 実走）。AT-05=0（無し/二重付与ゼロ）・AT-06=承認済み25行と過不足なし（増分 #205=I109 のみ・許容条件適合）・AT-07=9/17（#205 増分込み・AT-06 と整合）。CI（PR #202）全6ジョブ pass。
- 手動: **No1〜6 全 OK**（No1〜5 = Claude 実施・No6 = Human 実施 2026-07-15 スクリーンショット確認: `label:track:harness` で Open 17件・紫ラベル視認。詳細は I107_manual_test.md）。結論: OK。
- /code-review（2026-07-15）: VERDICT **OK**（Blocker/High なし。Low 1件 = issue-flow.md 空行非対称 → commit `856951d` で修正済み・ゲート再実走 PASS）。記録: docs/reviews/I107_code_review_20260715_1050.md
- ※ CI ブロッカー（Pillow CVE = I108/#203）は I108 完了（PR #204 マージ）で解消済み。origin/develop 取り込み後 CI グリーン確認済み。

## 計画との差分
- なし（実装は計画の全ステップどおり・逸脱なし。plan-review 指摘の反映経緯は plan_I107.md「レビュー指摘への対応記録」参照）

## ロールバック
- ラベル: `gh label delete "track:app" --yes` / `gh label delete "track:harness" --yes`（付与済みイシューからも自動で外れる）。個別解除は `gh issue edit <番号> --remove-label`。
- 文書: git revert または feature ブランチ破棄。
