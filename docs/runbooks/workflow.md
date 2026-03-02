# Vibe Coding 運用フロー（安全寄り）

## ディレクトリ規約
- docs/issues/open, docs/issues/in_progress, docs/issues/closed
- docs/plans/open, docs/plans/closed
- docs/tests/open, docs/tests/closed
- docs/reviews/open, docs/reviews/in_progress, docs/reviews/closed

## フロー（あなたの運用をそのまま型にする）
1. /issue-bootstrap → ユーザーがイシューファイル確認（OK/NG）
2. /plan I### → ユーザーが計画書確認（OK/NG）
3. /implement I### → 実装＆自動検証 → ユーザー検証（OK/NG）
4. NG の場合 /fix-loop I###（差分計画→承認→修正→再検証）
5. OK の場合 /close I###（open→closed へ移動、PR説明を整備、マージ依頼）

詳細なイシューフローは docs/runbooks/issue-flow.md を参照。

## ゲート
- 計画承認（OK）前にコード変更を開始しない
- Danger Ops は明示承認（danger-approved + DANGER_OK=1）なしに実行しない
- develop/main への直 push を禁止（PR経由）

---

## Claude Code実行ルール

- **コマンド実行前に必ず説明する**: 実行するコマンドが何をするものか、なぜ実行するのかを日本語で説明してから実行すること
- 例: 「PostgreSQLのデータベース一覧を確認するため、docker-compose exec db psql -U postgres -c "\l"を実行します」

- **ロジック修正提案時に必ず説明する**: フロント・バックエンド問わず、ロジック修正を提案する際は以下を必ず説明すること
  1. **修正の意図**: なぜこの修正が必要なのか
  2. **修正前の問題点**: 現状どういう問題があるのか（具体的に）
  3. **修正後の改善内容**: 修正するとどう改善されるのか（具体的に）
  - 例: 「現在のコードでは科目が1件のみでも科目選択UIが表示されてしまい、ユーザーが余計な操作を強いられています。科目が1件の場合は自動遷移させることで、ユーザーは『クイズを始める』ボタンを1回押すだけで即座にクイズを開始できるようになります」

---

## 作業実行前の確認ルール

### 必須承認ワークフロー
指示を受けた際は、必ず以下のワークフローに従う：

1. **調査・分析**: 問題特定とログ確認
2. **対応方針検討**: 調査結果に基づいて具体的な対応方針を検討
3. **計画書作成**: `docs/plans/open/plan_[タイプ]_[概要]_[連番].md`に詳細記録
4. **承認待ち宣言**: 以下のメッセージを必ず出力
   ```
   📋 計画書完了: [ファイルパス]
   ⏸️ **承認待ち中** - 修正作業は開始しません
   ✅「OK」で承認、❌ 修正指示をお願いします
   ```
5. **承認確認**: 「OK」「承認」「進めてください」等の明示的指示まで待機
6. **承認記録**: 計画書に承認情報を追記
7. **作業開始宣言**: 修正作業開始を明示
8. **修正実施**: 実際の修正・テスト・検証

### 修正ツール使用前チェック（必須）
Edit/Write/MultiEdit等の実行前に必ず確認：
- 計画書作成済み？
- ユーザー承認取得済み？
- 承認記録が計画書に記載済み？

### 承認記録ルール
ユーザーから承認を得た場合は、必ず以下を実行：

1. **計画書への承認記録**
```bash
echo "## ユーザー承認" >> "$LATEST_PLAN"
echo "- **承認日時**: $(date)" >> "$LATEST_PLAN"
echo "- **承認者**: ユーザー" >> "$LATEST_PLAN"
echo "- **承認内容**: OK/承認を確認" >> "$LATEST_PLAN"
```

2. **作業開始宣言**
```
✅ 承認を確認しました
🚀 修正作業を開始します
```

### TodoWrite連携ルール
TodoWriteツール使用時は承認ステータスも管理：

```javascript
{
  "content": "計画書の承認待ち",
  "status": "in_progress",
  "activeForm": "承認待ち中",
  "approval_required": true,
  "approval_status": "pending"
}
```

承認後に修正タスクのステータスを更新：
```javascript
{
  "content": "修正作業実施",
  "status": "in_progress",
  "activeForm": "修正作業中",
  "approval_required": true,
  "approval_status": "approved"
}
```

---

## ブランチ戦略

### 基本方針: 3ブランチ戦略（本番環境対応版）

**ブランチ構成**:
- **main**: 本番環境（AWS）デプロイ用、常に安定版のみ、リリース済みコードのみ
- **develop**: 開発統合・ステージング環境用、機能開発の統合ブランチ
- **feature/Ixxx-xxx**: 各イシュー開発用の作業ブランチ
- **hotfix/xxx**: 本番環境の緊急修正用ブランチ

**ブランチの役割**:
```
main (本番環境 - AWS) ← リリース時のみマージ
  ↑
develop (開発統合・ステージング) ← 日常的な開発はここに集約
  ↑
feature/Ixxx-xxx (各イシュー開発) ← イシューごとに作成
```

**ブランチ命名規則**:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例: `feature/I030-media-asset-models`

### 現在のブランチ確認
作業開始前に必ず現在のブランチを確認：
```bash
git branch --show-current
```
適切なブランチで作業していない場合は警告を出す。

### イシュー完了時のマージフロー

**詳細は「イシューフロー（統合ルール）」セクションを参照**

マージはイシューフローのステップ25で実行する。
- 全てのドキュメント更新（テストケース、エラー管理、計画書、イシューファイル）完了後にマージ
- マージ後にレビューファイルをclosedに移動してクローズ完了

### 本番リリースフロー（重要）

**developの複数機能を本番環境（main）にリリースする場合のみ実行**:

```bash
git checkout main
git merge develop --no-ff -m "Release: vX.X.X ..."
git tag -a v1.0.0 -m "バージョン1.0.0リリース"
git push origin main
git push origin v1.0.0
```

**重要な注意事項**:
- mainへのマージは慎重に行う（十分なテスト完了後のみ）
- 必ずバージョンタグを付ける
- リリースノートを残す
- developからmainへは定期的（週1回、月1回等）にまとめてマージ

### 緊急修正（hotfix）のブランチ運用

本番環境で緊急のバグ修正が必要な場合：

```bash
git checkout main
git checkout -b hotfix/critical-bug-description
# 修正・コミット
git checkout main
git merge hotfix/critical-bug-description --no-ff
git push origin main
# developにもマージ（必須）
git checkout develop
git merge hotfix/critical-bug-description --no-ff
git push origin develop
git branch -d hotfix/critical-bug-description
```

**hotfixの重要ポイント**: mainとdevelop**両方**にマージすること。
- mainとdevelop**両方**にマージすること（忘れると修正が失われる）
- 本番環境への影響を最小限にするため、修正は最小限に
- テストは迅速だが確実に実施

### ブランチ作成例外ルール
以下の場合はブランチ作成を省略可能：
1. **ドキュメントのみの修正**: README更新、typo修正等
2. **緊急の1行修正**: 明らかな設定ミス等
3. **ユーザーが明示的に指示**: 「ブランチ作成不要」等の指示がある場合

ただし、**イシューファイル作成依頼の場合は必ずブランチを作成**すること。
