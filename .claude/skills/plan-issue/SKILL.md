---
name: plan-issue
description: Create branch, push, draft PR, then plan + tests + review docs for an issue.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /plan-issue

必読:
- docs/issues/open/$ARGUMENTS_*.md
- docs/runbooks/plan-writing-rules.md
- rules/ultimate_django_coding_standards.md
- rules/react-coding-standards-integrated.md

### ブランチ作成・プッシュ・Draft PR（必須）
イシューファイルを読んで GitHub Issue 番号を確認した後、以下を実行する。

#### 1. ブランチ作成
developブランチをベースにfeatureブランチを作成：
```bash
git checkout develop
git pull origin develop
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

**ブランチ命名規則**:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例: `feature/I030-media-asset-models`

**概要の英語化ルール**:
- 日本語の概要をシンプルな英語に変換
- スペースは`-`（ハイフン）に変換
- 最大5単語程度に要約

#### 2. イシューファイルのコミット・プッシュ
```bash
git add docs/issues/open/I${ISSUE_NUM}.md
git commit -m "docs: create issue I${ISSUE_NUM}"
git push -u origin feature/I${ISSUE_NUM}-[概要]
```

#### 3. Draft PR 作成
```bash
gh pr create \
  --title "feat: I${ISSUE_NUM} [イシュータイトル]" \
  --body "$(cat <<'EOF'
## 概要
I${ISSUE_NUM}: [概要]

## 関連イシュー
Closes #[GitHubイシュー番号]
EOF
)" \
  --draft \
  --base develop
```

Draft PR 番号をイシューファイルの「## 関連資料」セクションに追記する:
```
- Draft PR: #XX
```

生成物:
- docs/plans/open/plan_$ARGUMENTS_{概要}.md（plan-writing-rules.md の命名規則に準拠）
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/reviews/open/$ARGUMENTS_review.md

禁止:
- コード変更（承認前のEdit/Write開始は禁止）

承認ポイント提示前に必ず以下を実施する:

**セキュリティ・ベストプラクティスチェック（必須）**
計画書の変更点について以下を確認し、該当する項目を承認ポイントに記載する:
- 入力バリデーション・サニタイズの考慮が含まれているか
- 認証・認可の変更が適切に設計されているか（最小権限の原則）
- 機密データ（パスワード・トークン・個人情報）の扱いが適切か
- OWASP Top 10 関連リスク（XSS・SQLインジェクション・CSRF 等）への対策が含まれるか
- フレームワーク推奨パターン（Django セキュリティ設定・React のセキュアコーディング）に準拠しているか
- 追加・更新する依存ライブラリに既知脆弱性がないか（必要に応じて pip-audit / npm audit）
- セキュリティスキャンツールの重大度基準を計画書に明記しているか（bandit: MEDIUM以上を修正対象・LOW は # nosec で抑制、npm audit: high/critical を修正対象）
該当なし（バックエンド・フロントエンドのコード変更がない等）の場合は「セキュリティ影響なし」と明記する。

**設計判断の明示チェック（必須）**
計画書に書いた設計判断（権限範囲・エラー時の挙動・ディレクトリ構成・使用ライブラリ等）を列挙し、
それぞれについて「イシューに明記されている / 仮定で決めた」を区別して承認ポイントに記載する。
「仮定で決めた」項目が1つでもある場合は、承認ポイントより先にユーザーへ確認する。

完了したら「承認ポイント」を提示して停止する。

承認後の次のステップ: `/plan-issue-review $ARGUMENTS` を実行して計画書・テスト文書をレビューしてください。
