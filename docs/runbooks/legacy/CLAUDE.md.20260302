This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Claude Code 設定・メモ

## プロジェクト概要
学習アプリ - Django REST Framework + React TypeScript

## エラー調査手順
エラーが発生したら以下のコマンドを実行してClaude Codeに情報を渡す：
```bash
# 直近のエラーを操作履歴付きで確認
python manage.py analyze_logs --last-errors=1
```

## よく使用するコマンド

### 開発環境起動
```bash
docker-compose up -d
```

### ログ確認
```bash
tail -f backend/logs/django.log
```

### フロントエンド・バックエンド再起動
```bash
docker-compose restart frontend backend
```

### テスト実行
```bash
# バックエンドテスト
docker-compose exec backend python manage.py test

# フロントエンドテスト  
docker-compose exec frontend npm test
```

## API エンドポイント
- ユーザー登録: `POST /api/auth/register/`
- ユーザー設定: `GET/PATCH /api/settings/`
- 学習ストリーク: `GET /api/streak/`

## 修正済みの問題
1. psutil依存関係エラー - try-catchで処理済み
2. Redis HiredisParserエラー - PARSER_CLASS削除で解決
3. IntegrityErrorエラー - get_or_create使用で解決
4. FRONTEND_URL設定不足 - settings.py追加済み
5. SMTPエラー - 開発環境でスキップ設定
6. 404エラー - フロントエンドURL修正済み

## ディレクトリ構造
```
backend/        - Django REST API
frontend/       - React TypeScript
docs/          - ドキュメント
nginx/         - Nginx設定
```

## 注意事項
- 開発環境ではメール送信をスキップ
- ログファイル: `backend/logs/django.log`
- フロントエンドのURL変更時はキャッシュクリア必要

## Claude Code実行ルール
- **コマンド実行前に必ず説明する**: 実行するコマンドが何をするものか、なぜ実行するのかを日本語で説明してから実行すること
- 例: 「PostgreSQLのデータベース一覧を確認するため、docker-compose exec db psql -U postgres -c "\l"を実行します」

- **ロジック修正提案時に必ず説明する**: フロント・バックエンド問わず、ロジック修正を提案する際は以下を必ず説明すること
  1. **修正の意図**: なぜこの修正が必要なのか
  2. **修正前の問題点**: 現状どういう問題があるのか（具体的に）
  3. **修正後の改善内容**: 修正するとどう改善されるのか（具体的に）
  - 例: 「現在のコードでは科目が1件のみでも科目選択UIが表示されてしまい、ユーザーが余計な操作を強いられています。科目が1件の場合は自動遷移させることで、ユーザーは『クイズを始める』ボタンを1回押すだけで即座にクイズを開始できるようになります」

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

### 違反防止の自動確認
```bash
# 修正前の承認チェック
LATEST_PLAN=$(ls -t docs/plans/open/plan_*.md 2>/dev/null | head -1)
if [ -z "$LATEST_PLAN" ]; then
  echo "❌ エラー: 計画書が作成されていません"
  echo "📋 まず計画書を作成し、承認を得てください"
  exit 1
fi
```

## 計画書と実装の一致性保証ルール（絶対遵守）

### 基本原則
**計画書に記載されていない実装は絶対に行わない。より良い方法があれば必ず提案し、ユーザーに承認を得る。**

### 実装開始前の必須確認（3ステップチェック）

#### ステップ1: 計画書の再確認
```bash
# 対象計画書の最終確認
cat docs/plans/open/plan_[対象計画書].md

# 以下を確認：
# 1. 修正アプローチ：全体方針が理解できているか
# 2. 各修正項目の修正方針：何をどう変えるか明確か
# 3. 具体的なコード例：実装すべき内容が明確か
```

#### ステップ2: 実装内容の事前宣言と改善提案
修正ツール（Edit/Write/NotebookEdit）使用前に**必ず**以下を実施：

**チェックリスト**:
- [ ] この実装は計画書の「修正対象と具体的変更内容」に明記されているか？
- [ ] 計画書に書かれたファイル・メソッド・変数名と一致しているか？
- [ ] 計画書のコード例と実装内容が一致しているか？
- [ ] **より良い実装方法はないか検討したか？**（必須）
- [ ] より良い方法がある場合、ユーザーに提案したか？

**重要**: 計画書通りに実装する前に、必ず以下を自問すること：
- 「この実装方法で本当にベストか？」
- 「パフォーマンス・保守性・セキュリティの観点でより良い方法はないか？」
- 「将来の拡張性を考慮した設計になっているか？」
- 「よりシンプルで分かりやすい実装はないか？」

**より良い方法を発見した場合は、必ずユーザーに提案すること（実装前）**

**あってはならない例**:
- 計画書: 「`list`メソッドを修正」→ 実装: 新しい`by_organization`メソッドを追加
- 計画書: 「エラーメッセージを修正」→ 実装: エラーハンドリングロジックを変更
- 計画書: 「変数名を`user_id`に変更」→ 実装: `userId`に変更（表記が異なる）
- より良い方法を発見したが提案せずに勝手に実装

#### ステップ3: 逸脱検知時の強制停止

実装中に以下に気づいた場合は**即座に作業を中断**：

1. **計画書に記載がない実装が必要**
2. **計画書の方法より良い方法を発見**
3. **計画書の方法では実現不可能**
4. **計画書に記載のないファイル・関数・変数の変更が必要**

**中断後の手順**:
```markdown
1. 作業を中断（修正ツールは使用しない）
2. ユーザーに報告：

   「実装中に計画書との不一致を検出しました」

   - 計画書の記載: [具体的に引用]
   - 実装しようとした内容: [詳細]
   - 不一致の理由: [なぜ異なるのか]
   - 提案: [複数案があれば列挙]

3. ユーザーの承認を待つ
4. 承認された場合のみ、計画書を更新してから実装
```

### より良い方法の検討と提案（必須プロセス）

**「より良い方法の検討」は必須。実装前に必ず実施すること。**

**実装前に必ず検討すべき観点**:

1. **パフォーマンス**: より高速な方法はないか？
2. **保守性**: より読みやすく、理解しやすいコードにできないか？
3. **セキュリティ**: より安全な実装方法はないか？
4. **拡張性**: 将来の機能追加を考慮した設計になっているか？
5. **シンプルさ**: よりシンプルで同じ結果が得られる方法はないか？
6. **一貫性**: 既存コードベースの設計パターンと一貫性があるか？
7. **ベストプラクティス**: フレームワーク・言語の推奨パターンに従っているか？

**提案が必要なケース（例）**:
- 計画書の方法では処理が遅い可能性がある
- より少ないコードで同じ機能が実現できる
- セキュリティリスクがある実装方法が計画書に記載されている
- フレームワークの推奨パターンと異なる方法が計画書に記載されている
- 将来のメンテナンスが困難になる可能性がある

**提案フォーマット**:
```markdown
📋 実装方法の改善提案

## 計画書の記載内容
[計画書から該当部分を引用]

## より良い方法（提案）
[新しい方法の説明]

## 改善理由
[なぜこちらの方が優れているか]

## 比較
| 項目 | 計画書の方法 | 提案する方法 |
|------|-------------|-------------|
| 実装の複雑さ | [評価] | [評価] |
| パフォーマンス | [評価] | [評価] |
| 保守性 | [評価] | [評価] |
| セキュリティ | [評価] | [評価] |
| 拡張性 | [評価] | [評価] |
| リスク | [評価] | [評価] |

## 推奨
[どちらを推奨するか、理由付きで説明]

## 次のアクション
- **計画書通りに実装**: ユーザーが計画書の方法を選択した場合
- **提案方法で実装**: ユーザーが提案を承認した場合（計画書を先に更新）

承認いただけましたら対応します。
```

**重要**: 明らかに問題がある実装方法が計画書に記載されている場合は、**必ず提案すること**。

### 厳守しなければならない実装フロー（必須手順）

**このフローから逸脱することはあってはならない。**

```
ステップ1: 計画書を読む
   ↓
ステップ2: より良い方法がないか検討（必須、最低5分）
   ↓
ステップ3-A: より良い方法あり
   → ユーザーに提案
   → 承認待ち（実装禁止）
   → 承認後に計画書更新
   → 実装開始
   ↓
ステップ3-B: より良い方法なし
   → 計画書通りに実装開始
   ↓
ステップ4: 実装中の継続確認
   → 計画書と一致しているか常に確認
   → 逸脱を検知したら即座に中断
   ↓
ステップ5: 実装完了
   ↓
ステップ6: 一致性検証（必須）
   → 計画書との完全一致を確認
   ↓
ステップ7: ユーザーへ報告
```

**遵守確認**:
各ステップ完了時に以下を記録：
- [ ] ステップ1完了: 計画書読了（該当ファイル: ___）
- [ ] ステップ2完了: 改善案検討実施（検討時間: ___分、結果: ___）
- [ ] ステップ3完了: 提案実施 or 計画書通りの実装決定
- [ ] ステップ4完了: 実装完了（修正ファイル: ___）
- [ ] ステップ5完了: 一致性検証（結果: 一致）
- [ ] ステップ6完了: ユーザー報告

### 実装完了後の一致性検証

修正作業完了時に**必ず**以下を確認：

```bash
echo "=== 計画書との一致性検証 ==="

# 1. 修正したファイル一覧を出力
git diff --name-only

# 2. 計画書に記載された修正対象ファイルと比較
echo "計画書記載の修正対象:"
grep -A 20 "修正対象" docs/plans/open/plan_*.md

# 3. 差分確認
echo "❓ 計画書に記載のないファイルを修正していませんか？"
echo "❓ 計画書の修正方針通りに実装しましたか？"
echo "❓ より良い方法がある場合、提案しましたか？"
```

### 例外ルール（極めて限定的）

以下の場合**のみ**、計画書への事前記載なしで実装可能：

1. **タイポ修正**: 明らかなスペルミス、全角/半角の誤り
2. **インポート文の追加**: 新しいメソッド追加に伴う自明なインポート
3. **フォーマット調整**: インデント、改行等のコードフォーマット

**ただし**、これらも実装後に必ずユーザーに報告すること。

### 徹底のための自己チェック質問

修正ツール使用前に以下を自問：

1. 「この実装は計画書に書いてあるか？」→ YES なら続行、NO なら中断
2. 「計画書のどこに書いてあるか？」→ 該当箇所を特定できるか確認
3. 「計画書の方法と完全に一致しているか？」→ 1文字でも違えば中断
4. 「**より良い方法はないか検討したか？**」→ 検討必須、あれば提案
5. 「ユーザーの承認を得ているか？」→ 得ていなければ絶対に実装しない

**この5つの質問にすべてYESで答えられない限り、修正ツールは使用禁止。**

### 計画書作成ルール
- **作成タイミング**: 調査と対応方針検討が完了してから作成（調査前に作成しない）
- **計画書の内容**: 以下を具体的に記載
  - 作業概要と目的
  - **調査結果**（必須）:
    - エラーの詳細（エラーメッセージ、発生箇所、ログ等）
    - 原因の概要（問題の本質を平易な言葉で説明。例：「APIの呼び出しタイミングが早すぎて、必要なデータがまだ準備されていない」）
    - 詳細な原因分析（なぜエラーが発生したか、技術的な背景を含む）
    - 問題の根本原因（コードレベルでの具体的な問題箇所）
  - **修正対象と具体的変更内容**:
    - **修正アプローチ**: 修正の全体像を日本語で説明（何をどう変えることで問題を解決するか）
    - **各修正項目ごとに修正方針**: 具体的なコード例の前に、その修正で何を達成するか言葉で説明
    - 修正対象ファイル・テーブル・カラム等の具体名
    - 修正方針と手順（どのファイルをどのように変更するか、具体的なコード例を含む）
  - データベース変更の場合は影響範囲とバックアップ方法
  - 外部キー制約・インデックス等への影響
  - 想定されるリスクと対処法
  - 完了条件と検証方法
  - ロールバック方法
- **原因分析の記載方法**: 計画書には必ず以下の順序で記載
  - **原因の概要**: まず問題の本質を1-2文で平易に説明（非技術者でも理解できるレベル）
  - **詳細な原因分析**:
    - エラー発生の流れ（ステップバイステップ）
    - 技術的な詳細（フレームワークの仕様、設定の問題等）
    - なぜこの問題が発生したか（開発時の誤解、仕様変更等）
    - 具体的なコードの問題箇所（ファイル名、行番号、問題のコード）
- **修正内容の説明方法**:
  - まず「修正アプローチ」セクションで全体方針を日本語で説明
  - 各修正項目に「修正方針」を明記し、何を達成するかを言葉で説明
  - その後に具体的なコード例やファイル変更内容を記載
- **計画書ファイル名ルール**: `plan_[タイプ]_[概要]_[連番].md` 形式でdocs/plans/open/に保存
  - **タイプ**: `I[番号]`（イシュー対応）、`BUG`（バグ修正）、`FEAT`（機能追加）、`FIX`（一般修正）、`MAINT`（メンテナンス）、`PERF`（パフォーマンス改善）
  - **概要**: 日本語可、スペースは`_`に変換
  - **連番**: 初回は省略、2回目以降は`_2`、`_3`...を追加
  - **例**: 
    - 初回: `plan_I010_科目サービス修正.md`
    - 追加: `plan_I010_科目サービス修正_2.md`
    - 他例: `plan_BUG_認証エラー対応.md`、`plan_FEAT_新機能実装.md`
- **ファイル名生成手順**:
  ```bash
  # 基本ファイル名構築
  PLAN_TYPE="[タイプ]"  # I010, BUG, FEAT等
  PLAN_SUMMARY="[概要]"  # 日本語可、スペースは_に変換
  BASE_NAME="plan_${PLAN_TYPE}_${PLAN_SUMMARY}"
  
  # 既存ファイル確認と連番決定
  if [ -f "docs/plans/open/${BASE_NAME}.md" ]; then
    COUNTER=2
    while [ -f "docs/plans/open/${BASE_NAME}_${COUNTER}.md" ]; do
      COUNTER=$((COUNTER + 1))
    done
    PLAN_FILE="docs/plans/open/${BASE_NAME}_${COUNTER}.md"
  else
    PLAN_FILE="docs/plans/open/${BASE_NAME}.md"
  fi
  ```
- **承認待ち宣言**: 計画書作成後は必ず以下を出力
  ```
  📋 計画書を作成しました: [実際のファイルパス]
  
  ⏸️ **承認待ち中**: 実際の修正作業は開始しません
  ✅ 承認いただけましたら「OK」または「承認」とお答えください
  ❌ 修正が必要でしたら具体的な指示をお願いします
  ```
- **ストップワード**: "承認待ち中"の表示後は、ユーザーから「OK」「承認」「進めてください」等の明確な指示があるまで**いかなる修正作業も実行禁止**

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

### 計画書完了時のルール
実装作業が完了し、レビューでOKが出た場合は、必ず以下を実行：

1. **計画書の移動**
```bash
# in_progressからclosedディレクトリへ移動
mv docs/plans/in_progress/plan_*.md docs/plans/closed/
```

2. **完了情報の追記**
計画書末尾に以下を追記してから移動：
```bash
echo "## 完了情報" >> "$PLAN_FILE"
echo "- **完了日時**: $(date)" >> "$PLAN_FILE"
echo "- **対応者**: Claude Code" >> "$PLAN_FILE"
echo "- **レビュー結果**: OK" >> "$PLAN_FILE"
```

注意: `completed/`ディレクトリは旧運用の名残です。新規の完了計画書は必ず`closed/`に移動してください。

### 計画書作成例外の禁止ルール

#### 計画書作成を省略してはならないケース
以下のケースは**絶対に**計画書承認ワークフローを省略禁止：

1. **レビューでの不具合発見**: 
   - 「レビュー対応だから例外」は**禁止**
   - レビューNG → 調査 → 計画書作成 → 承認 → 修正

2. **修正規模による判断**: 
   - 「1行だけの修正だから例外」は**禁止**
   - 修正規模に関わらず承認プロセス必須

3. **文脈による例外判断**:
   - 「○○の対応だから例外」という勝手な判断は**禁止**
   - 文脈に関わらず承認プロセスは必須

#### 違反防止の自己チェック質問
修正作業前に**必ず**以下を自問：

```markdown
## 計画書作成チェック
- [ ] ユーザーから修正・実装の指示があったか？（Yes → 計画書必須）
- [ ] 計画書なしで作業を開始しようとしていないか？（確認必須）
```

#### 違反時の対処法
計画書なしで修正してしまった場合：

1. **作業を中断**
2. **事後計画書を作成**: `plan_POST_[概要].md`
3. **違反理由の明記**: なぜルールを守らなかったかを記録
4. **再発防止策の策定**: 具体的な改善方法を明記
5. **ユーザーへの報告**: 違反を報告し、承認を求める

#### 重要な原則
- **「小さな修正だから大丈夫」という思考は危険**
- **どんな文脈でも承認プロセスは必須**
- **勝手な例外判断は品質管理の破綻につながる**

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

## UX重視の設計・実装ルール

### フロントエンド設計時のUX必須確認事項
ロジックの新規作成や修正時は、**必ず以下のUX観点を検討し、計画書に明記**すること：

#### 1. エラー処理のUX原則
- **コンテキスト維持**: エラー時もユーザーの作業コンテキストを保持
  - ❌ 悪い例: 404ページへリダイレクト（コンテキスト喪失）
  - ✅ 良い例: 同一ページ内でエラー表示と回復方法を提示
- **即座のフィードバック**: 問題を早期に検知してユーザーに通知
  - ❌ 悪い例: フォーム送信後にエラー発覚
  - ✅ 良い例: 入力時・ページ読み込み時の事前検証
- **明確な次のアクション**: エラー時に代替案を必ず提示
  - ❌ 悪い例: 「エラーが発生しました」のみ
  - ✅ 良い例: 具体的な修正方法と代替アクションボタン

#### 2. ローディング・待機状態のUX
- **視覚的フィードバック**: 処理中であることを明確に表示
- **スケルトンスクリーン**: 可能な限りコンテンツの形を先に表示
- **プログレス表示**: 長時間処理では進捗を表示
- **キャンセル可能性**: 必要に応じて処理の中断オプション提供

#### 3. フォーム・入力のUX
- **リアルタイムバリデーション**: 入力中に問題をリアルタイムで指摘
- **入力値の保持**: エラー時も入力内容を失わない
- **明確なエラーメッセージ**: 何が問題で、どう修正すべきか具体的に
- **成功時のフィードバック**: 保存・送信成功を明確に通知

#### 4. ナビゲーション・遷移のUX
- **URL設計**: 意味のある、予測可能なURL構造
- **ブラウザ履歴の尊重**: 戻る・進むボタンが期待通り動作
- **状態の永続化**: リロード時も作業状態を可能な限り保持
- **離脱防止**: 未保存データがある場合の警告

#### 5. レスポンシブ・アクセシビリティ
- **モバイル考慮**: タッチ操作しやすいボタンサイズ（最小44px）
- **キーボード操作**: Tab移動、Enter確定、Escキャンセル
- **スクリーンリーダー対応**: 適切なaria-label、role属性
- **カラーコントラスト**: WCAG基準の遵守

### 計画書への必須記載項目（UX観点）
修正計画書には以下のUXセクションを必ず含める：

```markdown
## UX設計
### 現在のUX課題
- [具体的な問題点と影響を受けるユーザー行動]

### 改善後のユーザー体験
- [期待される体験の流れをステップごとに記載]

### エラー・例外時の体験
- [各種エラーケースでのユーザー体験]

### 成功指標
- [改善を測定する具体的な指標]
```

### UX検証チェックリスト
実装完了時に必ず確認：
- [ ] エラー時もコンテキストが維持される
- [ ] すべての操作に適切なフィードバックがある
- [ ] 次のアクションが常に明確
- [ ] モバイルでも操作しやすい
- [ ] キーボードのみで操作可能
- [ ] 処理中・エラー・成功が視覚的に区別できる

## イシュー新規作成時の採番ルール
新しいイシューを作成する際は、必ず以下の手順で番号を採番：

```bash
# open, in_progress, closedの全ディレクトリから最大番号を取得
LAST_NUM=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
if [ -z "$LAST_NUM" ]; then
  ISSUE_NUM="001"
else
  NEXT_NUM=$((LAST_NUM + 1))
  ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
fi
echo "次のイシュー番号: $ISSUE_NUM"
```

**重要**: closedディレクトリも必ず確認すること。

## ブランチ戦略とイシュー作成時の自動化ルール

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

### イシュー作成時の自動実行フロー（必須）

ユーザーから「イシューファイルを作成して」または「新しいイシューを作成して」という指示を受けた場合は、**必ず以下の手順を自動的に実行**すること：

#### 1. イシュー番号の採番
```bash
# 全ディレクトリから最大番号を取得
LAST_NUM=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
if [ -z "$LAST_NUM" ]; then
  ISSUE_NUM="001"
else
  NEXT_NUM=$((LAST_NUM + 1))
  ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
fi
```

#### 2. イシューファイル作成
```bash
# テンプレートからイシューファイル作成
cp docs/issues/templates/issue_template.md docs/issues/open/${ISSUE_NUM}.md
# 内容を編集（タイトル、概要等をユーザーの指示に基づいて記載）
```

#### 3. 作業用ブランチの自動作成（必須）
```bash
# developブランチから分岐してfeatureブランチを作成
git checkout develop
git pull origin develop  # 最新のdevelopを取得（リモートがある場合）
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

**重要**: 必ず**developブランチをベース**にfeatureブランチを作成すること。mainブランチからは作成しない。

**ブランチ命名規則**:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例:
  - `feature/I030-media-asset-models`
  - `feature/I031-dashboard-performance`
  - `feature/I032-user-authentication-fix`

**概要の英語化ルール**:
- 日本語の概要をシンプルな英語に変換
- スペースは`-`（ハイフン）に変換
- 最大5単語程度に要約
- 例:
  - 「問題・解説画像の複数対応」→ `media-asset-models`
  - 「ダッシュボードのパフォーマンス改善」→ `dashboard-performance`
  - 「ユーザー認証のバグ修正」→ `user-authentication-fix`

#### 4. GitHubイシューの登録（必須）
```bash
# ghコマンドでGitHubにイシューを登録
gh issue create \
  --title "I${ISSUE_NUM}: [イシュータイトル]" \
  --body "$(cat docs/issues/open/${ISSUE_NUM}.md)" \
  --label "[種別に応じたラベル]"
```

**ラベル設定**:
- Bug → `bug`
- Feature → `enhancement`
- Documentation → `documentation`
- Refactoring → `refactoring`

**注意事項**:
- GitHubイシュー番号とローカルイシュー番号は異なる場合がある（GitHub側は自動採番）
- ローカルイシュー番号（例: I035）をタイトルに含めることで紐づけを明確にする
- `gh auth login`で認証済みであることが前提

#### 5. ユーザーへの報告
ブランチ作成・GitHubイシュー登録後、必ず以下を報告：

```
✅ イシュー#XXX を作成しました: [タイトル]
📂 ファイル: docs/issues/open/XXX.md
🌿 ブランチ作成: feature/IXXX-[概要]
🔗 GitHubイシュー: [GitHubイシューURL]

このブランチで作業を開始します。
```

### イシュー対応中のブランチ運用

#### コミット時のルール
```bash
# 計画書作成時
git add docs/plans/
git commit -m "docs: イシュー#XXX の計画書作成"

# 実装時（複数コミットOK）
git commit -m "feat: MediaAssetモデル追加（イシュー#XXX）"
git commit -m "feat: API実装（イシュー#XXX）"

# レビュー・クローズ時
git commit -m "docs: イシュー#XXX レビュー完了・クローズ"
```

#### イシュー完了時のマージフロー
**詳細は「イシューフロー（統合ルール）」セクションを参照**

マージはイシューフローのステップ25で実行する。
- 全てのドキュメント更新（テストケース、エラー管理、計画書、イシューファイル）完了後にマージ
- マージ後にレビューファイルをclosedに移動してクローズ完了

### 本番リリースフロー（重要）

**developの複数機能を本番環境（main）にリリースする場合のみ実行**:

```bash
# 1. developで十分な動作確認・テスト完了を確認

# 2. mainブランチに切り替え
git checkout main

# 3. developをmainにマージ
git merge develop --no-ff -m "Release: vX.X.X

リリース内容:
- イシュー#XXX: [機能概要]
- イシュー#YYY: [機能概要]
- バグ修正: [修正内容]

テスト結果:
- 全ユニットテスト: 合格
- 統合テスト: 合格
- 動作確認: 完了

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. バージョンタグを付ける
git tag -a v1.0.0 -m "バージョン1.0.0リリース

リリース内容:
- イシュー#XXX: [機能概要]
- イシュー#YYY: [機能概要]
"

# 5. リモートにプッシュ（本番デプロイのトリガー）
git push origin main
git push origin v1.0.0

# 6. AWS へデプロイ（CI/CDまたは手動）
# ... デプロイ手順 ...
```

**重要な注意事項**:
- mainへのマージは慎重に行う（十分なテスト完了後のみ）
- 必ずバージョンタグを付ける
- リリースノートを残す
- developからmainへは定期的（週1回、月1回等）にまとめてマージ

### 緊急修正（hotfix）のブランチ運用

本番環境で緊急のバグ修正が必要な場合：

```bash
# 1. mainブランチから分岐してhotfixブランチ作成
git checkout main
git checkout -b hotfix/critical-bug-description

# 2. 修正・コミット
git commit -m "hotfix: 緊急バグ修正の説明"

# 3. mainにマージ（本番環境修正）
git checkout main
git merge hotfix/critical-bug-description --no-ff -m "Hotfix: 緊急修正 - [修正内容]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main

# 4. developにもマージ（開発ブランチに修正を反映）
git checkout develop
git merge hotfix/critical-bug-description --no-ff
git push origin develop

# 5. ブランチ削除
git branch -d hotfix/critical-bug-description

# 6. AWS へ緊急デプロイ
```

**hotfixの重要ポイント**:
- mainとdevelop**両方**にマージすること（忘れると修正が失われる）
- 本番環境への影響を最小限にするため、修正は最小限に
- テストは迅速だが確実に実施

### ブランチ作成例外ルール
以下の場合はブランチ作成を省略可能：
1. **ドキュメントのみの修正**: README更新、typo修正等
2. **緊急の1行修正**: 明らかな設定ミス等
3. **ユーザーが明示的に指示**: 「ブランチ作成不要」等の指示がある場合

ただし、**イシューファイル作成依頼の場合は必ずブランチを作成**すること。

### ブランチ作成失敗時の対処
ブランチ作成に失敗した場合：
1. エラー内容をユーザーに報告
2. 原因を説明（例: ブランチ名の重複、git未初期化等）
3. 対処方法を提案

### 現在のブランチ確認
作業開始前に必ず現在のブランチを確認：
```bash
git branch --show-current
```

適切なブランチで作業していない場合は警告を出す。

## イシュー対応時の必須ルール
イシュー番号（例: 001, #1など）を指定されたら、必ず以下を実行：
1. `/docs/issues/open/XXX.md`または`/docs/issues/in_progress/XXX.md`を読み込む（XXXは指定された番号）
2. `/rules/`配下の関連ルールファイルを確認
3. 特にコード変更時はコーディング標準を厳守
4. **UX設計セクションを計画書に必ず含める**
5. テスト実行時は該当するテストルールを参照
6. 完了後は対応内容を報告し、承認を待つ

## イシューフロー（統合ルール）

イシューの作成から完了・クローズまでの統一フローを以下に定める。

### フロー図

```
【イシューフロー】

=== フェーズ1: イシュー準備 ===
1. イシューファイル作成（テンプレート：docs/issues/templates/issue_template.md）
    ↓
2. イシューブランチ作成（feature/IXXX-概要）
    ↓
3. GitHubイシュー登録
    ↓
4. ユーザーがイシューファイルを確認
    ↓
5. ユーザーがイシューファイルを承認
    ↓

=== フェーズ2: 計画・設計 ===
6. 計画書作成
    ↓
7. テストケース作成（2種類を別ファイルで作成）
   - ユーザーテストケース（docs/tests/open/test_IXXX_manual.md）
   - 自動テストケース（docs/tests/open/test_IXXX_auto.md）
    ↓
8. レビューファイル作成（テンプレート：docs/reviews/templates/review_template.md）
   ※実装結果評価セクションは空欄のまま作成
    ↓
9. ユーザーが計画書・テストケースを確認
    ↓
10. ユーザーが計画書・テストケースを承認
    ↓

=== フェーズ3: 実装・テスト ===
11. 実装
    ↓
12. 自動テスト実行（ユニットテスト等）
    ↓
13. レビューファイルに実装結果を記入
    ↓
14. ユーザーがテスト（ユーザーテストケースに基づく）
    ↓
─────────────────────────────────────────
    ↓ OK                    ↓ NG
─────────────────────────────────────────
    ↓                     15. レビューにNG結果記入
    ↓                     16. エラー管理ファイル作成（初回）
    ↓                        または追記（2回目以降）
    ↓                        （docs/tests/templates/error_log_template.md）
    ↓                     17. エラー対応計画書を新規作成
    ↓                        （docs/plans/open/に新規作成、元の計画書は上書きしない）
    ↓                     18. 承認待ち → 修正
    ↓                     19. 再テスト（14に戻る）
─────────────────────────────────────────
    ↓ ←────────────────────┘（OKになったら）
─────────────────────────────────────────

=== フェーズ4: クローズ処理 ===
20. レビューにOK結果記入
21. テストケース → closed/
22. エラー管理ファイル → closed/（該当する場合）
23. 計画書 → closed/（エラー対応計画書含む全て）
24. イシューファイル → closed/
25. featureブランチをdevelopにマージ
26. レビューファイル → closed/
27. GitHubイシューをクローズ
```

### 各ステップの詳細

#### フェーズ1: イシュー準備

**ステップ1: イシューファイル作成**
- テンプレート: `docs/issues/templates/issue_template.md`
- 保存先: `docs/issues/open/`
- 命名規則: `XXX.md`（XXX: 3桁のイシュー番号）

```bash
# イシュー番号の採番
LAST_NUM=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
if [ -z "$LAST_NUM" ]; then
  ISSUE_NUM="001"
else
  NEXT_NUM=$((LAST_NUM + 1))
  ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
fi

# テンプレートからコピー
cp docs/issues/templates/issue_template.md docs/issues/open/${ISSUE_NUM}.md
```

**ステップ2: イシューブランチ作成**
- developブランチをベースにfeatureブランチを作成
- 命名規則: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`

```bash
git checkout develop
git pull origin develop  # 最新のdevelopを取得
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

**ステップ3: GitHubイシュー登録**
```bash
gh issue create \
  --title "I${ISSUE_NUM}: [イシュータイトル]" \
  --body "$(cat docs/issues/open/${ISSUE_NUM}.md)" \
  --label "[種別に応じたラベル]"
```

**ステップ4-5: ユーザー確認・承認**
- ユーザーがイシューファイルの内容を確認
- 承認後、フェーズ2に進む

#### フェーズ2: 計画・設計

**ステップ6: 計画書作成**
- テンプレート: `docs/plans/templates/plan_template.md`
- 保存先: `docs/plans/open/`
- 命名規則: `plan_I{イシュー番号}_{概要}.md`

**ステップ7: テストケース作成**
2種類のテストケースを**別ファイル**で作成：

| 種類 | ファイル名 | 内容 |
|------|-----------|------|
| ユーザーテスト | `test_IXXX_manual.md` | ユーザーしか実施できないテスト項目 |
| 自動テスト | `test_IXXX_auto.md` | ユニットテスト、統合テスト等の自動テスト項目 |

- テンプレート: `docs/tests/templates/test_record_template.md`
- 保存先: `docs/tests/open/`

**ステップ8: レビューファイル作成**
- テンプレート: `docs/reviews/templates/review_template.md`
- 保存先: `docs/reviews/open/`
- 命名規則: `reviewXXX_IYYY.md`（XXX: 通し番号、YYY: イシュー番号）
- **重要**: 実装結果評価セクションは空欄のまま作成

レビューファイルの記載タイミング：
| 記載タイミング | 記載する項目 |
|---------------|-------------|
| ステップ8（実装前） | 基本情報、対象計画書、レビュー目的、期待する成果 |
| ステップ13（実装後） | 実装結果評価、品質評価、技術的評価 |
| ステップ15/20（テスト後） | テスト結果、発見した問題・改善点、最終判定 |

**ステップ9-10: ユーザー確認・承認**
- ユーザーが計画書・テストケースの内容を確認
- 承認後、フェーズ3に進む

#### フェーズ3: 実装・テスト

**ステップ11: 実装**
- 計画書に基づいた実装作業を実施

**ステップ12: 自動テスト実行**
- `test_IXXX_auto.md`に記載された自動テストを実行
- 全テストが成功することを確認

**ステップ13: レビューファイルに実装結果を記入**
- 実装結果評価セクションを記入
- 品質評価、技術的評価を記入

**ステップ14: ユーザーテスト**
- `test_IXXX_manual.md`に基づいてユーザーがテストを実施
- 結果に応じてOK/NGに分岐

#### ステップ15-19: NGの場合のエラー対応ループ

**ステップ15: レビューにNG結果記入**
- レビューファイルにNG結果と発見された問題を記入

**ステップ16: エラー管理ファイル作成/追記**
- 初回: `docs/tests/templates/error_log_template.md`から新規作成
- 2回目以降: 既存ファイルに追記（新規作成しない）
- 保存先: `docs/tests/open/`
- 命名規則: `error_IXXX.md`

**ステップ17: エラー対応計画書を新規作成**
- 元の計画書を上書きしない（`_2`, `_3`...の連番で新規作成）
- 保存先: `docs/plans/open/`

**ステップ18: 承認待ち → 修正**
- ユーザー承認後に修正実施

**ステップ19: 再テスト**
- ステップ14（ユーザーテスト）に戻る

#### フェーズ4: クローズ処理（ステップ20-27）

**ステップ20: レビューにOK結果記入**
```markdown
## テスト結果
- **最終テスト日**: YYYY-MM-DD
- **結果**: OK
- **確認者**: ユーザー
```

**ステップ21: テストケースをclosedに移動**
```bash
# 完了情報を追記（両方のテストファイル）
for TEST_FILE in docs/tests/open/test_IXXX_*.md; do
  echo "## 完了情報" >> "$TEST_FILE"
  echo "- **完了日時**: $(date)" >> "$TEST_FILE"
  echo "- **結果**: OK" >> "$TEST_FILE"
  mv "$TEST_FILE" docs/tests/closed/
done
```

**ステップ22: エラー管理ファイルをclosedに移動（該当する場合）**
```bash
if [ -f "docs/tests/open/error_IXXX.md" ]; then
  echo "## 完了情報" >> docs/tests/open/error_IXXX.md
  echo "- **解決日時**: $(date)" >> docs/tests/open/error_IXXX.md
  mv docs/tests/open/error_IXXX.md docs/tests/closed/
fi
```

**ステップ23: 計画書をclosedに移動**
```bash
# 全ての関連計画書（エラー対応計画書含む）をclosedに移動
for PLAN_FILE in docs/plans/open/plan_IXXX_*.md; do
  echo "## 完了情報" >> "$PLAN_FILE"
  echo "- **完了日時**: $(date)" >> "$PLAN_FILE"
  echo "- **対応者**: Claude Code" >> "$PLAN_FILE"
  echo "- **レビュー結果**: OK" >> "$PLAN_FILE"
  mv "$PLAN_FILE" docs/plans/closed/
done
```

**ステップ24: イシューファイルをclosedに移動**
```bash
cat >> docs/issues/open/XXX.md << 'EOF'

## 完了情報
- **完了日時**: YYYY-MM-DD HH:MM
- **対応者**: Claude Code
- **実施内容の要約**: [実装内容を簡潔に記載]
- **関連ファイル**:
  - 計画書: docs/plans/closed/plan_IXXX_*.md
  - レビュー: docs/reviews/closed/reviewXXX_IXXX.md
  - テスト: docs/tests/closed/test_IXXX_*.md
EOF

mv docs/issues/open/XXX.md docs/issues/closed/
```

**ステップ25: featureブランチをdevelopにマージ**
```bash
git checkout develop

git merge feature/IXXX-[概要] --no-ff -m "$(cat <<'EOF'
Merge feature/IXXX: [イシュータイトル]

- 実施内容の要約
- 関連ファイル
- テスト結果: OK

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

git push origin develop

# 作業完了ブランチを削除（任意）
git branch -d feature/IXXX-[概要]
```

**ステップ26: レビューファイルをclosedに移動**
```bash
echo "## クローズ情報" >> docs/reviews/open/reviewXXX_IXXX.md
echo "- **クローズ日時**: $(date)" >> docs/reviews/open/reviewXXX_IXXX.md

mv docs/reviews/open/reviewXXX_IXXX.md docs/reviews/closed/
```

**ステップ27: GitHubイシューをクローズ**
```bash
# GitHubイシュー番号を確認
gh issue list --state open | grep "IXXX"

# イシューをクローズ
gh issue close [GitHub イシュー番号] --comment "実装完了・ユーザーテストOK

## 実施内容
- [実装内容を箇条書きで記載]

## テスト結果
- [テスト結果を記載]

🤖 Generated with Claude Code"
```

### 重要な注意事項

1. **レビューファイルは実装前に作成**: 実装後に作成を忘れないよう、ステップ8で先に作成する
2. **実装結果は後から記入**: レビューファイルの実装結果評価セクションはステップ13で記入
3. **テストケースは2種類**: ユーザーテスト用と自動テスト用を別ファイルで管理
4. **元の計画書を上書きしない**: エラー対応時は必ず新規計画書を作成（履歴保持のため）
5. **エラー管理ファイルは追記方式**: 同一イシューのエラーは1ファイルで管理
6. **全てのファイルをclosedに移動**: テスト、エラー管理、計画書、イシュー、レビューの全て
7. **マージは最後**: 全てのドキュメント更新後にブランチマージを実行
8. **レビューファイルは最後にクローズ**: 全体の振り返りを含めるため最後に移動
9. **GitHubイシューも必ずクローズ**: ローカルファイルのクローズ後、GitHubイシューも忘れずにクローズ
10. **再テストはステップ14に戻る**: エラー対応後の再テストはユーザーテストから再開

## データベース・モデル整合性チェック必須ルール

### エラー対応・ロジック修正時の自動診断手順
モデル関連のエラーが発生した場合や、ロジック修正を依頼された場合は、**必ず以下の順序で診断・修正を実行**すること：

#### 1. 基本整合性診断（必須実行）
```bash
# 未適用マイグレーション確認
python manage.py showmigrations

# モデル定義チェック
python manage.py check --database default

# 未適用マイグレーション検出
python manage.py makemigrations --check --dry-run
```

#### 2. テーブル・モデル対応チェック（必須実行）
```python
# Djangoシェルで以下を実行
from django.apps import apps
from django.db import connection

# 対象モデルのフィールド一覧取得
model = apps.get_model('app_name', 'ModelName')
model_fields = [f.name for f in model._meta.get_fields() if hasattr(f, 'column')]
print(f"モデルフィールド: {model_fields}")

# データベースの実際のカラム一覧取得
table_name = model._meta.db_table
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", [table_name])
    db_columns = [row[0] for row in cursor.fetchall()]
print(f"DBカラム: {db_columns}")

# 不一致チェック
missing_in_model = set(db_columns) - set([f.column for f in model._meta.get_fields() if hasattr(f, 'column')])
missing_in_db = set([f.column for f in model._meta.get_fields() if hasattr(f, 'column')]) - set(db_columns)
if missing_in_model or missing_in_db:
    print(f"⚠️  不一致検出!")
    print(f"DBにあるがモデルにない: {missing_in_model}")
    print(f"モデルにあるがDBにない: {missing_in_db}")
```

#### 3. 修正優先順位の判定ルール
不一致が検出された場合の対応優先順位：

**A. DBにあるがモデルにないフィールド（高優先度）**
→ モデル定義にフィールド追加が必要
→ マイグレーション漏れの可能性

**B. モデルにあるがDBにないフィールド（中優先度）**  
→ マイグレーション実行が必要
→ `python manage.py migrate`を実行

**C. 型の不一致（低優先度）**
→ マイグレーションでの型変更が必要

#### 4. 自動修正フロー
不一致検出時の標準対応手順：

1. **マイグレーション状態確認**
```bash
python manage.py showmigrations app_name | grep "\[ \]"
```
未適用があれば `python manage.py migrate` を実行

2. **モデル定義修正**
不足フィールドをマイグレーション定義を参考に追加：
```python
# マイグレーションファイルから正しい定義をコピー
# 例: 0004_subject_organization.py の内容を参考にモデルを修正
```

3. **動作確認**
```python
# 修正後の動作確認（必須）
from app.models import Model
instance = Model.objects.first()
print(instance.field_name)  # エラーが発生しないことを確認
```

#### 5. 修正完了の検証ルール（セルフチェック）
修正後は**必ず**以下をすべて実行して問題ないことを確認：

**A. モデルアクセス確認**
```python
model_instance = Model.objects.first()
for field in model._meta.get_fields():
    if hasattr(field, 'name') and hasattr(model_instance, field.name):
        value = getattr(model_instance, field.name)
        print(f"{field.name}: {value}")
```

**B. ORM操作確認** 
```python
# フィルタリング動作確認
queryset = Model.objects.filter(**{修正したフィールド名: テスト値})
print(f"フィルタリング結果: {queryset.count()}件")

# 関連操作確認（ForeignKeyの場合）
if hasattr(model_instance, '修正したフィールド名'):
    related_obj = getattr(model_instance, '修正したフィールド名')
    print(f"関連オブジェクト: {related_obj}")
```

**C. API動作確認**
関連するAPIエンドポイントを実行してエラーが発生しないことを確認

**D. ログ確認**
```bash
tail -f backend/logs/django.log
# エラーログが出力されていないことを確認
```

#### 6. 報告ルール
修正完了時は以下を必ず報告：

1. **検出された不一致の詳細**
2. **実施した修正内容**
3. **修正前後の動作確認結果**
4. **関連する他の箇所への影響確認結果**
5. **再発防止のための提案**（該当する場合）

### 対象となるエラーパターン
以下のエラーが発生した場合は、上記の診断ルールを**必ず**適用：

- `Cannot resolve keyword 'field_name' into field`
- `AttributeError: 'Model' object has no attribute 'field_name'`
- `django.db.utils.OperationalError: no such column`
- `django.core.exceptions.FieldError`
- マイグレーション関連エラー全般

### 例外ルール
以下の場合はこのルールを適用せず、個別対応：
- 新規プロジェクト作成時
- テスト環境のセットアップ時
- システムモデル（auth, contenttypes等）の問題
- サードパーティライブラリ由来の問題

## バックエンド修正時のAPI統合テスト必須ルール

### バックエンドロジック修正後の自動検証手順
バックエンドの修正（モデル、ビュー、サービス等）を行った場合は、**必ず以下の順序でAPI統合テストを実行**すること：

#### 1. 関連API特定（必須実行）
修正したロジックに関連するAPIエンドポイントを特定：
```bash
# 修正対象がSubjectServiceの場合の例
grep -r "subject_service\|SubjectService" backend/ --include="*.py" | grep -E "(views\.py|serializers\.py)"
# → 使用箇所からAPIエンドポイントを特定
```

#### 2. 認証トークン取得（必須実行）
```bash
# テスト用ユーザーでログインしてトークン取得
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com", "password":"testpass"}'

# レスポンスからtokenを抽出して環境変数に設定
export TOKEN="取得したトークン"
```

#### 3. 影響を受けるAPI全てをテスト（必須実行）

**A. ダッシュボード関連API**
```bash
echo "=== ダッシュボードAPI テスト ==="
curl -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'

curl -X GET http://localhost:8000/api/dashboard/analytics/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

**B. 学習統計関連API**
```bash
echo "=== 学習統計API テスト ==="
curl -X GET http://localhost:8000/api/studylogs/statistics/overview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'

curl -X GET http://localhost:8000/api/studylogs/statistics/by_subject/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

**C. 科目関連API**
```bash
echo "=== 科目API テスト ==="
curl -X GET http://localhost:8000/api/problems/subjects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

#### 4. フロントエンド期待レスポンス形式の検証（必須実行）

**A. フロントエンドの期待形式を調査**
```bash
# React コンポーネントから期待するレスポンス形式を確認
grep -r "api.*dashboard\|api.*statistics\|api.*subjects" frontend/src/ --include="*.ts" --include="*.tsx" -A 5 -B 5
```

**B. レスポンス構造の詳細検証**
```bash
# 各APIのレスポンス構造を詳細確認
echo "=== ダッシュボード overview レスポンス構造 ==="
curl -s -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer $TOKEN" | jq 'keys'

echo "=== 学習統計 overview レスポンス構造 ==="
curl -s -X GET http://localhost:8000/api/studylogs/statistics/overview/ \
  -H "Authorization: Bearer $TOKEN" | jq 'keys'

echo "=== 科目一覧 レスポンス構造 ==="
curl -s -X GET http://localhost:8000/api/problems/subjects/ \
  -H "Authorization: Bearer $TOKEN" | jq '.[0] | keys' 2>/dev/null || echo "配列が空または形式が異なる"
```

#### 5. レスポンス内容の妥当性検証（必須実行）

**A. 科目データの整合性確認**
```bash
# 科目データが正しく取得されているか確認
echo "=== 科目データ確認 ==="
SUBJECTS=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN")
echo "$SUBJECTS" | jq '.[].name' # 科目名一覧
SUBJECT_COUNT=$(echo "$SUBJECTS" | jq 'length')
echo "取得した科目数: $SUBJECT_COUNT"
```

**B. ダッシュボードの科目データ確認**
```bash
# ダッシュボードで表示される科目データが正しいか確認
echo "=== ダッシュボード科目データ確認 ==="
DASHBOARD=$(curl -s -X GET http://localhost:8000/api/dashboard/overview/ -H "Authorization: Bearer $TOKEN")
echo "$DASHBOARD" | jq '.subject_progress[]?.subject' 2>/dev/null || echo "科目進捗データなし"
```

**C. 統計画面の科目データ確認**
```bash
# 統計画面で表示される科目データが正しいか確認
echo "=== 統計科目データ確認 ==="
STATS=$(curl -s -X GET http://localhost:8000/api/studylogs/statistics/by_subject/ -H "Authorization: Bearer $TOKEN")
echo "$STATS" | jq '.[].subject_name' 2>/dev/null || echo "統計データなし"
```

#### 6. エラー処理の確認（必須実行）

**A. 不正なリクエストでのエラーレスポンス確認**
```bash
echo "=== エラーハンドリング確認 ==="
# 認証なしでのアクセス
curl -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Content-Type: application/json" -w "%{http_code}\n" -o /dev/null

# 無効なトークンでのアクセス  
curl -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" -w "%{http_code}\n" -o /dev/null
```

#### 7. パフォーマンス確認（推奨実行）
```bash
echo "=== パフォーマンス確認 ==="
# レスポンス時間測定
time curl -s -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# 複数回実行してキャッシュ効果確認
for i in {1..3}; do
  echo "実行 $i 回目:"
  time curl -s -X GET http://localhost:8000/api/dashboard/overview/ \
    -H "Authorization: Bearer $TOKEN" > /dev/null
done
```

#### 8. ログ確認（必須実行）
```bash
echo "=== ログ確認 ==="
# エラーログがないことを確認
tail -n 50 backend/logs/django.log | grep -E "(ERROR|CRITICAL|Exception)" || echo "エラーログなし"

# アクセスログの確認
tail -n 10 backend/logs/django.log | grep -E "(GET|POST).*200"
```

### テスト完了の判定基準
以下を**すべて**満たすことを確認：

✅ **HTTPステータス**: 全APIで200レスポンス取得  
✅ **レスポンス形式**: JSONが正しく構造化されている  
✅ **データ整合性**: 組織/会員ごとの適切なデータフィルタリング  
✅ **必須フィールド**: フロントエンドが期待するフィールドが存在  
✅ **エラーハンドリング**: 不正リクエストで適切なエラーレスポンス  
✅ **パフォーマンス**: レスポンス時間が許容範囲内（通常2秒以内）  
✅ **ログ確認**: エラーログが出力されていない

### フロントエンド期待形式チェックリスト

**ダッシュボード API (`/api/dashboard/overview/`)**
```javascript
// フロントエンドが期待する形式
{
  "today": {
    "study_time": number,
    "problems_attempted": number,
    "problems_correct": number,
    "accuracy": number
  },
  "active_session": object | null,
  "study_streak": number,
  "weekly_summary": {
    "total_time": number,
    "total_problems": number,
    "total_correct": number,
    "accuracy": number
  },
  "recent_quizzes": array,
  "subject_progress": array,
  "upcoming_goals": array
}
```

**学習統計 API (`/api/studylogs/statistics/overview/`)**
```javascript
// フロントエンドが期待する形式
{
  "total_study_time": number,
  "total_study_time_display": string,
  "total_problems_attempted": number,
  "total_problems_correct": number,
  "overall_accuracy": number,
  "study_days": number,
  "current_streak": number,
  "longest_streak": number,
  // ... その他統計データ
}
```

### テスト失敗時の対処法

**パターン1: 500エラー**
```bash
# ログでエラー詳細確認
tail -f backend/logs/django.log
# モデル整合性チェックルールを適用
```

**パターン2: レスポンス形式不一致**
```bash
# APIレスポンスとフロントエンド期待形式を比較
# シリアライザーやビューの修正が必要
```

**パターン3: データが期待通りでない**
```bash
# Djangoシェルで同一条件でデータ取得テスト
# フィルタリングロジックの確認
```

### 自動化推奨
上記手順を`scripts/test_api_integration.sh`として保存し、修正後に実行：
```bash
chmod +x scripts/test_api_integration.sh
./scripts/test_api_integration.sh
```

## バックエンド修正時の要件適合性テスト必須ルール

### 修正ロジックの要件適合性検証手順
バックエンドの修正完了後、API統合テストに加えて、**ユーザーの指示・要望通りの挙動をするかを必ず検証**すること：

#### 1. 要件適合性テストの実行（必須）

**A. 指示内容の再確認**
```bash
# 修正指示の要件を明確化
echo "=== 修正要件の確認 ==="
echo "指示内容: [実際の修正指示を記載]"
echo "期待する挙動: [期待される動作を具体的に記載]"
echo "対象画面/API: [影響を受ける画面・API]"
```

**B. データフィルタリング検証（科目管理の場合）**
```bash
# 組織ごと・会員ごとのデータフィルタリングが要件通りか確認
echo "=== データフィルタリング検証 ==="

# 組織1のユーザーでテスト
echo "--- 組織1ユーザーテスト ---"
TOKEN_ORG1=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"org1_user@example.com", "password":"testpass"}' | jq -r '.token')

SUBJECTS_ORG1=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN_ORG1")
echo "組織1の科目数: $(echo "$SUBJECTS_ORG1" | jq 'length')"
echo "組織1の科目: $(echo "$SUBJECTS_ORG1" | jq '.[].name')"

# 組織2のユーザーでテスト
echo "--- 組織2ユーザーテスト ---"
TOKEN_ORG2=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"org2_user@example.com", "password":"testpass"}' | jq -r '.token')

SUBJECTS_ORG2=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN_ORG2")
echo "組織2の科目数: $(echo "$SUBJECTS_ORG2" | jq 'length')"
echo "組織2の科目: $(echo "$SUBJECTS_ORG2" | jq '.[].name')"

# データ分離確認
echo "--- データ分離確認 ---"
if [ "$(echo "$SUBJECTS_ORG1" | jq 'length')" != "$(echo "$SUBJECTS_ORG2" | jq 'length')" ] || \
   [ "$(echo "$SUBJECTS_ORG1" | jq -c 'sort')" != "$(echo "$SUBJECTS_ORG2" | jq -c 'sort')" ]; then
  echo "✅ 組織間でデータが適切に分離されています"
else
  echo "❌ 組織間でデータ分離が機能していません"
fi
```

**C. 画面別要件適合性確認**
```bash
# 画面ごとの要件適合性確認
echo "=== 画面別要件適合性確認 ==="

# ダッシュボード画面（要件に応じて科目表示を確認）
echo "--- ダッシュボード画面 ---"
DASHBOARD_RESP=$(curl -s -X GET http://localhost:8000/api/dashboard/overview/ -H "Authorization: Bearer $TOKEN_ORG1")

# subject_progress配列の存在確認
if echo "$DASHBOARD_RESP" | jq -e '.subject_progress' > /dev/null; then
  SUBJECT_COUNT=$(echo "$DASHBOARD_RESP" | jq '.subject_progress | length')
  echo "ダッシュボード表示科目数: $SUBJECT_COUNT"
  echo "表示科目: $(echo "$DASHBOARD_RESP" | jq '.subject_progress[].subject')"
  
  # 要件確認: 組織の科目のみ表示されているか（または会員選択科目のみか）
  echo "要件適合性: [組織単位/会員単位]の科目のみ表示されているかチェック"
else
  echo "❌ subject_progressが取得できません"
fi

# 学習統計画面（要件に応じて科目表示を確認）
echo "--- 学習統計画面 ---"
STATS_RESP=$(curl -s -X GET http://localhost:8000/api/studylogs/statistics/by_subject/ -H "Authorization: Bearer $TOKEN_ORG1")

if echo "$STATS_RESP" | jq -e '.' > /dev/null && [ "$(echo "$STATS_RESP" | jq 'length')" -gt 0 ]; then
  STATS_SUBJECT_COUNT=$(echo "$STATS_RESP" | jq 'length')
  echo "統計画面科目数: $STATS_SUBJECT_COUNT"
  echo "統計表示科目: $(echo "$STATS_RESP" | jq '.[].subject_name')"
  
  # 要件確認: ダッシュボードと同じ科目セットが表示されているか
  echo "要件適合性: ダッシュボードと統計で同じ科目セットかチェック"
else
  echo "❌ 統計データが取得できません"
fi

# 問題管理画面（組織の全科目表示の確認）
echo "--- 問題管理画面 ---"
PROBLEMS_RESP=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN_ORG1")
PROBLEMS_SUBJECT_COUNT=$(echo "$PROBLEMS_RESP" | jq 'length')
echo "問題管理画面科目数: $PROBLEMS_SUBJECT_COUNT"
echo "問題管理表示科目: $(echo "$PROBLEMS_RESP" | jq '.[].name')"
```

#### 2. 要件適合性の判定基準

**A. データ取得要件確認**
```bash
echo "=== 要件適合性判定 ==="

# 科目管理の要件例
case "$REQUIREMENT_TYPE" in
  "organization_only")
    echo "要件: 組織単位の科目表示"
    echo "確認項目: 同組織のユーザーが同じ科目セットを取得すること"
    ;;
  "user_specific")
    echo "要件: 会員ごとの科目表示"
    echo "確認項目: ユーザーが選択した科目のみが表示されること"
    ;;
  "mixed")
    echo "要件: 画面により組織単位/会員単位を使い分け"
    echo "確認項目: ダッシュボード・統計は会員単位、問題管理は組織単位"
    ;;
esac
```

**B. フロントエンド期待動作との照合**
```bash
# フロントエンドが期待する動作と実際の動作を照合
echo "=== フロントエンド期待動作との照合 ==="

# React コンポーネントの実装を確認
echo "--- React コンポーネント確認 ---"
grep -r "subject.*map\|subject.*filter\|subject.*find" frontend/src/ --include="*.tsx" --include="*.ts" -n

# APIレスポンスがReactの期待形式と一致するか確認
echo "--- レスポンス形式適合性確認 ---"
# ダッシュボードコンポーネントが期待するフィールド
REQUIRED_FIELDS=("subject" "progress" "total_problems" "completed_problems")
for field in "${REQUIRED_FIELDS[@]}"; do
  if echo "$DASHBOARD_RESP" | jq -e ".subject_progress[0].$field" > /dev/null; then
    echo "✅ $field フィールド存在"
  else
    echo "❌ $field フィールド不在"
  fi
done
```

#### 3. 挙動確認テスト（必須実行）

**A. 指示された要件の動作確認**
```python
# Djangoシェルでの動作確認
python manage.py shell -c "
from django.contrib.auth import get_user_model
from core.subject_service import SubjectService

User = get_user_model()

# 異なる組織のユーザーで科目取得テスト
user1 = User.objects.filter(organization_id=1).first()
user2 = User.objects.filter(organization_id=2).first()

print('=== 科目取得動作確認 ===')
subjects1 = list(SubjectService.get_user_subjects(user1))
subjects2 = list(SubjectService.get_user_subjects(user2))

print(f'組織1ユーザーの科目数: {len(subjects1)}')
print(f'組織1科目: {[s.name for s in subjects1]}')
print(f'組織2ユーザーの科目数: {len(subjects2)}')
print(f'組織2科目: {[s.name for s in subjects2]}')

# 要件確認
if len(subjects1) > 0 and len(subjects2) > 0:
    if set([s.name for s in subjects1]) == set([s.name for s in subjects2]):
        print('❌ 組織間で同じ科目が返されています（データ分離不備）')
    else:
        print('✅ 組織ごとに異なる科目が返されています')
else:
    print('⚠️ 科目データが不足しています')

# 会員ごとの科目選択要件の場合の追加確認
print('\\n=== 会員選択科目確認 ===')
# UserSubjectAccessテーブルの確認等
"
```

**B. エッジケースの確認**
```bash
echo "=== エッジケース確認 ==="

# 組織に所属しないユーザーの場合
echo "--- 組織未所属ユーザー ---"
NO_ORG_USER_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"no_org_user@example.com", "password":"testpass"}' | jq -r '.token')

NO_ORG_SUBJECTS=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $NO_ORG_USER_TOKEN")
echo "組織未所属ユーザーの科目数: $(echo "$NO_ORG_SUBJECTS" | jq 'length')"

# 科目選択していない会員の場合（会員ごと科目管理の場合）
echo "--- 科目未選択会員 ---"
# 未選択ユーザーでのテスト実装
```

#### 4. 要件適合性レポート生成（必須実行）

```bash
echo "=== 要件適合性レポート ==="
echo "修正日時: $(date)"
echo "修正内容: [実際の修正内容]"
echo ""
echo "## 要件適合性チェック結果"
echo "✅ API正常動作: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/dashboard/overview/ -H "Authorization: Bearer $TOKEN_ORG1" | grep -c "200")件"
echo "✅ データフィルタリング: [組織単位/会員単位]で正常動作"
echo "✅ フロントエンド形式適合: レスポンス形式が期待通り"
echo "✅ 指示要件適合: [具体的な指示内容]が実装済み"
echo ""
echo "## 検証したAPI"
echo "- /api/dashboard/overview/"
echo "- /api/studylogs/statistics/overview/"
echo "- /api/studylogs/statistics/by_subject/"
echo "- /api/problems/subjects/"
echo ""
echo "## 動作確認結果"
echo "[具体的な動作確認結果を記載]"
```

### 要件適合性テスト完了の判定基準
以下を**すべて**満たすことを確認：

✅ **指示要件適合**: ユーザーの指示通りの動作をする  
✅ **データ正確性**: 組織/会員ごとのデータが要件通り取得される  
✅ **画面間整合性**: 複数画面で一貫したデータ表示  
✅ **フロントエンド適合**: Reactコンポーネントが期待する形式  
✅ **エッジケース対応**: 特殊なケース（組織未所属等）で適切な動作  
✅ **既存機能非破綻**: 修正により他機能が影響を受けていない  
✅ **パフォーマンス維持**: 修正前と同等以上のパフォーマンス

### 修正完了時の必須報告項目
修正完了時は以下を**必ず**報告すること：

1. **要件適合性確認結果**
   - 指示内容の実装状況
   - 期待する挙動の動作確認結果
   - データフィルタリングの動作確認

2. **API統合テスト結果** 
   - 全関連APIの動作状況
   - レスポンス形式の適合性
   - エラーハンドリングの動作

3. **画面影響確認結果**
   - ダッシュボード画面への影響
   - 学習統計画面への影響  
   - 問題管理画面への影響

4. **検証時に発見した課題**
   - 期待と異なる動作があった場合の詳細
   - 修正が必要な追加の箇所

5. **今後の推奨事項**
   - さらなる改善提案
   - 関連する他機能への影響可能性

## 文書間の関係性記載ルール

### 計画書作成時の必須記載（初期作成）
計画書のヘッダーには、文書の因果関係を明確にするため以下を記載：

```markdown
## 基本情報
- **計画書ID**: plan_[タイプ]_[概要]_[連番]
- **関連イシュー**: #XXX
- **作成根拠資料**: reviewXXX_IXXX（問題分析と改善提案）
- **実装後評価**: （未作成）
- **作成日**: YYYY-MM-DD
```

- **作成根拠資料**: この計画書を作成するきっかけとなった分析・提案資料を明記
  - 例: `review001_I010（問題分析と改善提案）`
  - 「関連レビュー」という曖昧な表現は使用禁止
  
- **実装後評価**: この計画書の実装結果を評価する予定の文書
  - 未作成の場合: `（未作成）`
  - 作成済みの場合: `review002_I010_post（実装結果評価）`

### 計画書対応完了時の必須レビュー作成ルール

#### 基本原則
**計画書（plan_*.md）の実装対応が完了した場合は、必ず対応する実装結果評価レビューファイルを作成する**

#### 自動実行タイミング
1. **計画書の実装作業完了時**：TodoListの全タスクが完了した時点
2. **ユーザーから「完了」等の指示があった時**：明示的な完了宣言を受けた時点
3. **API統合テスト成功時**：テスト完了を確認した時点

#### 必須実行手順
計画書対応完了時は以下を**必ず**実行：

```bash
# 1. 対象計画書の情報を取得
PLAN_FILE="[実装対象の計画書パス]"
PLAN_ID=$(basename "$PLAN_FILE" .md)
ISSUE_NUM=$(echo "$PLAN_ID" | grep -o "I[0-9]\+" | sed 's/I//')

# 2. レビューファイル名を決定（通し番号管理）
# 既存レビューファイルから最大番号を取得
LAST_NUM=$(ls docs/reviews/*/review*.md 2>/dev/null | grep -v template | sed 's/.*review\([0-9]\{3\}\).*/\1/' | sort -n | tail -1)
if [ -z "$LAST_NUM" ]; then
  REVIEW_NUM="001"
else
  NEXT_NUM=$((10#$LAST_NUM + 1))
  REVIEW_NUM=$(printf "%03d" $NEXT_NUM)
fi
REVIEW_FILE="docs/reviews/open/review${REVIEW_NUM}_I${ISSUE_NUM}_post.md"

# 3. レビューファイル作成
cp docs/reviews/templates/review_template.md "$REVIEW_FILE"

# 4. ファイル内容の基本情報を更新（タイトルは具体的に、ファイル名規則は削除）
# タイトルとレビューIDを適切に設定

# 5. 計画書の更新
echo "- **実装後評価**: $(basename "$REVIEW_FILE" .md)（$(date '+%Y-%m-%d')作成）" >> "$PLAN_FILE"
echo "- **最終更新**: $(date '+%Y-%m-%d')" >> "$PLAN_FILE"
```

#### レビューファイル記載ルール（重要な変更）

**基本方針**: レビューファイル作成時は基本情報のみを記載し、レビュー内容部分はテンプレートのプレースホルダーのままにする

##### 必須記載項目（基本情報セクション）
以下の項目のみを具体的に記載：

```markdown
## 基本情報
- **レビューID**: reviewXXX_IXXX_post
- **レビュー目的**: 実装結果評価
- **対象計画書**: [実際の計画書ファイル名とパス]
- **実装完了日**: YYYY-MM-DD（実際の日付）
```

##### 記載禁止項目（テンプレートのまま残す）
以下の項目は**テンプレートのプレースホルダーや空白のまま**残すこと：

- 実装結果評価セクション
- 品質評価セクション
- 発見した問題・改善点セクション
- 今後の推奨事項セクション
- 最終判定セクション

##### 理由とメリット
- **文書間リンクの確保**: 基本情報により計画書とレビューファイルの相互参照が可能
- **ユーザー記入の余地**: 詳細評価内容はユーザーが後から記入可能
- **自動作業の軽減**: Claude Codeは基本情報のみを自動記載し、評価内容を推測しない
- **品質管理**: レビューファイル存在により対応完了が明確化

#### 実装完了宣言
レビューファイル作成後は以下を出力：

```
📋 実装結果評価レビュー作成完了: [レビューファイルパス]
🎉 計画書「[計画書名]」の実装対応が完了しました

✅ 実装内容:
- [主要な実装内容を箇条書き]

📊 テスト結果: 全て成功
📝 品質評価: [簡潔な総合評価]
```

#### TodoWrite連携ルール
計画書対応時のTodoListには必ず以下のタスクを含める：

```javascript
// 実装作業の最後に必ず追加
{
  "content": "実装結果評価レビューファイル作成",
  "status": "pending",
  "activeForm": "実装結果評価レビューファイルを作成中"
}
```

このタスクは実装作業の**最終段階**で実行し、完了時に自動的にレビューファイルを生成する。

#### 例外ルール
以下の場合はレビューファイル作成を省略可能：
1. **テスト・実験的な実装**: 「テスト」「実験」が計画書名に含まれる場合
2. **ユーザー明示的な省略指示**: ユーザーが「レビュー不要」等を明示した場合

ただし、省略する場合でも計画書の「実装後評価」欄に省略理由を記載すること。

### 実装後レビュー作成時の必須作業
1. **レビューファイル作成**: `reviewXXX_IXXX_post.md`を作成
2. **計画書の更新（必須）**: 元の計画書に戻って以下を更新
   ```markdown
   - **実装後評価**: reviewXXX_IXXX_post（YYYY-MM-DD作成）
   - **最終更新**: YYYY-MM-DD
   ```
3. **相互参照の確認**: 両文書が正しくリンクされていることを確認

### レビューファイル作成時の必須記載
レビューファイルには、その目的と位置づけを明確にするため以下を記載：

```markdown
## 基本情報
- **レビューID**: reviewXXX_IXXX
- **レビュー目的**: 問題分析 / 実装結果評価 / 定期品質確認
- **対象文書/コード**: [レビュー対象]
- **派生文書**: [このレビューから作成された計画書等]
```

### レビューファイルの自動記載ルール

#### 実装結果評価レビュー作成時の必須手順
レビューファイル作成時は、必ず以下の順序で実施すること：

1. **CLAUDE.mdの該当セクション確認（必須・最優先）**
   ```bash
   # レビューファイル作成ルールを確認
   grep -A 30 "レビューファイル作成時の必須" CLAUDE.md
   grep -A 20 "重複記載の回避" CLAUDE.md
   ```

2. **テンプレートファイル確認（必須）**
   ```bash
   # レビューテンプレートを確認
   cat docs/reviews/templates/review_template.md
   ```

3. **対象計画書の読み込み（必須）**
   ```bash
   # 対象となる計画書を必ず読み込む
   cat docs/plans/plan_[対象計画書].md
   ```

4. **レビューファイル作成（必須要件）**
   レビューファイルには必ず対象計画書へのパスを記載：
   - **対象計画書**: `plan_XXX_YYY.md`へのパス（実装結果評価の場合は必須）

   詳細な実装内容は計画書を参照することで確認可能なため、レビューファイルでの重複記載は不要

#### 重要な注意事項
- **CLAUDE.md最優先**: テンプレートより先にCLAUDE.mdの該当セクションを必ず確認
- **計画書へのリンク必須**: 実装結果評価では必ず対象計画書を明記
- **重複記載の回避**: 計画書に記載済みの内容をレビューに再記載しない
- **手順厳守**: 1→2→3→4の順序を必ず守る

### 文書更新を忘れないための確認コマンド
```bash
# 実装後評価が未記載の計画書を検出
grep -l "実装後評価.*未作成" docs/plans/*.md
```

これにより文書の時系列と因果関係が明確になり、「レビュー済み」という誤解を防げる。

## テンプレートファイル同期必須ルール

### 基本方針
**ルール変更時は必ず関連テンプレートファイルの存在をチェックし、存在する場合は同時更新する**

### ルール変更時の必須手順

#### ステップ1: ルール変更の実施
CLAUDE.mdまたは他のルールファイルを変更する

#### ステップ2: 関連テンプレートファイルの存在確認（必須）
変更したルールに関連するテンプレートファイルが存在するか確認：

```bash
# 変更したルールのキーワードに基づいてテンプレートを検索
echo "=== テンプレートファイル存在確認 ==="

# 計画書ルール変更の場合
if [変更内容が計画書に関連]; then
  ls -la docs/plans/templates/*.md 2>/dev/null || echo "計画書テンプレートなし"
fi

# レビューファイルルール変更の場合
if [変更内容がレビューに関連]; then
  ls -la docs/reviews/templates/*.md 2>/dev/null || echo "レビューテンプレートなし"
fi

# イシューファイルルール変更の場合
if [変更内容がイシューに関連]; then
  ls -la docs/issues/templates/*.md 2>/dev/null || echo "イシューテンプレートなし"
fi

# タスクファイルルール変更の場合
if [変更内容がタスクに関連]; then
  ls -la docs/tasks/templates/*.md 2>/dev/null || echo "タスクテンプレートなし"
fi
```

#### ステップ3: テンプレート更新要否の判定
- **テンプレートが存在する場合**: ステップ4へ進む（更新必須）
- **テンプレートが存在しない場合**: ステップ5へ進む（完了確認）

#### ステップ4: テンプレートファイルの更新（該当する場合は必須）
1. **変更内容の特定**
   - ルール変更箇所を明確化
   - テンプレートの対応箇所を特定

2. **テンプレート更新の実施**
   ```bash
   # 更新前にバックアップ（推奨）
   cp [テンプレートファイル] [テンプレートファイル].bak
   
   # テンプレート更新
   # - 必須項目の追加/変更
   # - 命名規則の更新
   # - 記載例の修正
   # - 説明文の更新
   ```

3. **更新内容の検証**
   - 新ルールとテンプレートの整合性確認
   - テンプレートを使用してサンプルファイル作成可能か確認

#### ステップ5: 完了確認チェックリスト
```markdown
## ルール変更完了チェックリスト
- [ ] CLAUDE.md（またはルールファイル）を更新した
- [ ] 関連テンプレートファイルの存在を確認した
- [ ] 存在するテンプレートファイルをすべて更新した
- [ ] テンプレートと新ルールの整合性を確認した
- [ ] 更新内容をコミットメッセージに記載した
```

### テンプレート更新が必要となる変更例
1. **ファイルヘッダー構造の変更**
   - 必須項目の追加・削除・名称変更
   - 項目の順序変更

2. **命名規則の変更**
   - ファイル名パターンの変更
   - IDフォーマットの変更

3. **文書間の関係性ルールの変更**
   - 相互参照ルールの追加
   - リンク方法の変更

### 重要な注意事項
- **テンプレート確認を省略しない**: ルール変更時は必ずステップ2を実行
- **部分的な更新を避ける**: ルールとテンプレートは必ずセットで更新
- **更新履歴を残す**: どのルール変更に伴うテンプレート更新かを明記

## 対応結果レビュー必須ルール

### 基本方針
**全ての対応完了後は必ずレビューファイルを作成し、品質向上と継続的改善を実現する**

### レビュー実施タイミング
- **イシュー対応完了後**: 必須でレビュー実施
- **アドホック修正完了後**: テキスト指示による修正等も必須
- **定期レビュー**: システム全体の品質確認時

### レビューファイル作成手順

#### 1. ファイル命名規則と通し番号管理（重要）
- **イシュー関連**: `reviewXXX_IYYY.md` または `reviewXXX_IYYY_post.md`
  - XXX: **全レビューファイル共通の通し番号**（3桁ゼロパディング）
  - YYY: 関連イシューID（3桁ゼロパディング）
  - 例: `review001_I010.md`, `review003_I009_post.md`

- **イシュー以外**: `reviewXXX_[カテゴリ]_YYYYMMDD.md`
  - AD (Ad-hoc): テキストでの修正依頼、一時的な対応
  - PR (Periodic Review): 定期的な品質レビュー
  - 例: `review004_AD_20250911.md`

**通し番号の決定方法（必須実行）**:
```bash
# 既存レビューファイルから最大番号を取得
LAST_NUM=$(ls docs/reviews/*/review*.md 2>/dev/null | grep -v template | sed 's/.*review\([0-9]\{3\}\).*/\1/' | sort -n | tail -1)
if [ -z "$LAST_NUM" ]; then
  REVIEW_NUM="001"
else
  NEXT_NUM=$((10#$LAST_NUM + 1))
  REVIEW_NUM=$(printf "%03d" $NEXT_NUM)
fi
echo "次のレビュー番号: review${REVIEW_NUM}"
```

#### 2. ファイル作成と内容記載ルール
```bash
# レビューテンプレートをコピー
cp docs/reviews/templates/review_template.md docs/reviews/open/review${REVIEW_NUM}_IYYY.md
```

**記載時の必須ルール**:
- **タイトル**: 具体的な内容を記載（例：「会員登録時の科目選択機能実装（組織別対応）実装結果評価」）
- **ファイル名規則の説明**: 個別ファイルには記載しない（テンプレートとCLAUDE.mdのみ）
- **レビュー番号**: ファイル名と一致する通し番号を使用（例：`# レビュー #003:`）

#### 3. 必須記載項目
- **問題点・改善点**: 発見された課題と改善が必要な部分
- **パターン分析**: 類似問題の予防策
- **アクションアイテム**: 具体的な改善タスク

#### 4. イシューとの相互参照
- **レビューファイル**: 「関連イシュー: #XXX」を記載
- **イシューファイル**: 対応履歴にレビューリンクを追加
  ```markdown
  ## 対応履歴
  - **YYYY-MM-DD**: [対応内容]
    - レビュー: [#XXX](../reviews/open/reviewXXX_IYYY.md)
  ```

### レビュー内容の必須要素

#### A. 対応品質評価
- 問題特定の正確性
- 修正内容の適切性
- 影響範囲の考慮
- テスト・検証の充実度

#### B. プロセス評価
- ワークフロー遵守状況
- 計画書・承認プロセス
- ドキュメント品質
- コミュニケーション

#### C. 技術的評価
- コード品質
- アーキテクチャ適合性
- パフォーマンス影響
- セキュリティ考慮

#### D. 改善提案
- **短期改善**: すぐに対応可能な改善点
- **中長期改善**: 構造的・システム的改善
- **予防策**: 同様問題の再発防止

### レビューファイルの管理

#### ステータス管理
1. **Open**: 初期作成、改善点あり
2. **In Progress**: 改善対応中
3. **Closed**: 全ての改善完了

#### ファイル移動
```bash
# 対応開始時
mv docs/reviews/open/reviewXXX_IYYY.md docs/reviews/in_progress/reviewXXX_IYYY.md

# 対応完了時
mv docs/reviews/in_progress/reviewXXX_IYYY.md docs/reviews/closed/reviewXXX_IYYY.md
```

### レビュー活用方法

#### 継続的改善
- 定期的なアクションアイテム確認
- パターン分析による予防策実装
- 品質指標の継続的モニタリング

#### 知識共有
- 類似問題の解決策参照
- ベストプラクティスの蓄積
- 技術的知見の共有

### 重要な注意事項
- **レビュー作成は対応者の責任**: 対応完了と同時にレビューファイル作成必須
- **客観的な評価**: 良い点・改善点を公正に記録
- **具体的なアクション**: 実行可能な改善提案を記載
- **継続的フォロー**: アクションアイテムの実施状況を追跡

詳細な運用方法は `docs/reviews/README.md` を参照すること。