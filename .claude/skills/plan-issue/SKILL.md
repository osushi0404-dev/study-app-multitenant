---
name: plan-issue
description: Create branch, push, draft PR, then plan + tests + review docs for an issue.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /plan-issue

必読:
- docs/issues/open/$ARGUMENTS.md
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

**前提（invariant）**: イシューファイルは **plan-issue が feature ブランチで初コミットする**のが原則。`/issue-bootstrap` はローカル作成（未コミット）に留め、develop 等のベースブランチへ事前コミットしない（retro/close のハンドオフでも同様）。同一ファイルシステム上の untracked ファイルは context clear をまたいでも残り、別コンテキストの plan-issue が拾える（develop 事前コミットもハンドオフ PR も不要）。

イシューが既にベースへコミット済みかを自動判定する（既コミットだと `docs: create issue` が no-op 化し `gh pr create` が「No commits between develop and feature/…」で失敗するため）。パスはバージョン非依存になるよう open/closed を明示列挙する（`**` glob は git バージョン/設定依存のため使わない）:
```bash
if git log origin/develop --oneline -- \
     "docs/issues/open/I${ISSUE_NUM}.md" "docs/issues/closed/I${ISSUE_NUM}.md" \
     "docs/issues/open/${ISSUE_NUM}.md"  "docs/issues/closed/${ISSUE_NUM}.md" | grep -q .; then
  echo "ISSUE_ALREADY_ON_BASE"   # → 既コミット経路（issue commit をスキップ）
fi
```

- **未コミット（通常）**:
  ```bash
  git add docs/issues/open/I${ISSUE_NUM}.md
  git commit -m "docs: create issue I${ISSUE_NUM}"
  git push -u origin feature/I${ISSUE_NUM}-[概要]
  ```
  → step 3 でそのまま draft PR を作成する。
- **既コミット（`ISSUE_ALREADY_ON_BASE`）**: `docs: create issue` コミットを **スキップ**する。本スキルで生成する計画書 docs（plan/tests/review）を最初のコミットとする:
  ```bash
  git add docs/plans/open/plan_I${ISSUE_NUM}.md docs/tests/open/I${ISSUE_NUM}_*.md docs/reviews/open/I${ISSUE_NUM}_review.md
  git commit -m "docs(I${ISSUE_NUM}): plan/tests/review 作成"
  git push -u origin feature/I${ISSUE_NUM}-[概要]
  ```
  → step 3 で draft PR を作成する（docs コミットが差分になるため PR 作成は成功する）。

#### 3. Draft PR 作成
（既コミット経路の場合は、上記の計画書 docs を commit・push した後に本コマンドを実行する。）
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
- docs/plans/open/plan_$ARGUMENTS.md
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/reviews/open/$ARGUMENTS_review.md

テスト文書（`$ARGUMENTS_manual_test.md`）の「実施者」欄は以下の基準で判定する:
- **Claude で実施可**: ファイルの内容確認（Read ツール）・コマンド実行・ログ確認（Bash ツール）・ファイル間の比較・差分確認
- **Human のみ可**: ブラウザ操作・画面の目視確認・外部ツール（Figma・Slack 等）の操作・操作感・UX の感覚的な確認

禁止:
- コード変更（承認前のEdit/Write開始は禁止）

承認ポイント提示前に必ず以下を実施する:

**要件適合性・業務ロジックチェック（必須）**
計画書の変更点について以下を確認する:
- 計画書が受け入れ条件の範囲を超えた仕様追加・仕様変更を含んでいないか
- マルチテナント・組織スコープの閲覧範囲・操作範囲の制約が計画書に明示されているか（該当する場合）
- ステータス遷移・承認条件・更新可否条件が計画書で正しく定義されているか（該当する場合）
- エッジケース・境界値での業務ルールが計画書で考慮されているか

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

**テスト計画チェック（必須）**
計画書のテスト計画について以下を確認する:
- バグ修正の場合、再発防止テストがテスト計画に含まれているか
- テストレベルの選択（ユニット/結合/E2E の使い分け）が計画書に明示されているか
- 認証・認可・テナント境界を検証するテストケースが計画に含まれているか（認可変更がある場合）

**データ整合性・運用性・コスト設計チェック（該当する場合）**
計画書の変更点について以下を確認し、該当する場合は計画書への記載を確認する:
- DB変更がある場合: データ整合性設計（セクション10）が計画書に含まれているか
- 外部API・非同期処理・バッチがある場合: 運用設計（セクション11）が計画書に含まれているか
- 新規インフラリソース・外部サービス追加・大規模設計変更がある場合: コスト・保守見積もり（セクション12）が計画書に含まれているか
- 依存関係ファイル（requirements*.txt / package*.json）を変更する場合: Dockerfile のインストール対象・docker-compose.yml のビルドターゲットへの波及を確認し、計画書の影響範囲テーブルに記載する
該当なし（コード変更なし・既存パターンの踏襲のみ等）の場合は「P3/P5/P8 影響なし」と明記する。

**性能・UX設計チェック（該当する場合）**
計画書の変更点について以下を確認する:
- フロントエンド変更がある場合: ローディング・空状態・エラー状態の表示方針が計画書に含まれているか
- フロントエンド変更がある場合: 破壊的操作（削除等）の確認導線の設計があるか
- パフォーマンス懸念（N+1・キャッシュ・ページネーション等）が計画書で考慮されているか（大量データ・外部API連携がある場合）
- 上記のいずれかに該当する場合: セクション13（性能・UX設計）が計画書に含まれているか
該当なし（コード変更なし・UIなし・データ量や外部API懸念なし等）の場合は「P6 影響なし」と明記する。

**プライバシー・コンプライアンスチェック（該当する場合）**
計画書の変更点について以下を確認する:
- 個人情報・未成年データ・テナントデータを扱う変更がある場合: プライバシー・コンプライアンス設計（セクション15）が計画書に含まれているか（同意取得・保持期間・削除権・未成年配慮・データ所有権・目的外利用禁止・ポリシー面のテナント分離）
- 未成年データ・個人情報のテナント越境・目的外利用がある場合: 高リスク判定（I043）に該当し `/security-review`（I044）対象になるため、その旨が計画書で考慮されているか
該当なし（コード変更なし・個人情報や未成年データ・テナントデータを扱わない等）の場合は「P9 影響なし」と明記する。

**設計品質チェック（必須）**
計画書の設計判断について以下を確認する:
- 旧来のアンチパターン（Django: Fat View・Raw SQL 乱用、React: Props drilling・巨大コンポーネント等）を踏襲しない設計か
- null / undefined / 空値の扱い方針が設計で統一されているか（複雑なデータ処理がある場合）
- 例外処理・エラーハンドリングの方針が計画書に含まれているか（外部API・複雑な処理がある場合）
- 設定値・定数がハードコードされない方針になっているか

**設計判断の明示チェック（必須）**
計画書に書いた設計判断（権限範囲・エラー時の挙動・ディレクトリ構成・使用ライブラリ等）を列挙し、
それぞれについて「イシューに明記されている / 仮定で決めた」を区別して承認ポイントに記載する。
「仮定で決めた」項目が1つでもある場合は、承認ポイントより先にユーザーへ確認する。

**文書品質ゲート（承認ポイント提示前に必ず自己チェック）**
以下を 1 つでも満たせない場合は、承認ポイントを提示する前に計画書・テスト文書を修正する:
- [ ] 全 API エンドポイントに URL・HTTP メソッド・レスポンス型が明記されているか
- [ ] 全 permission_classes が具体的なクラス名で記載されているか
- [ ] エラーレスポンスの HTTP ステータスコードと body 形式が明記されているか
- [ ] DB フィールドの型・制約（null/blank/on_delete）が明記されているか（DB 変更がある場合）
- [ ] 自動テストの期待値（status_code・body の具体的な値）が記載されているか
- [ ] 手動テストの期待結果が「〜できる」ではなく、具体的な画面表示・動作で記載されているか
- [ ] 計画書の各実装ステップ本文内に検証コマンドが残っていないか（ある場合は自動テスト文書のTCに昇格する）
- [ ] lint / 静的解析ツールの異常系テストがある場合、インプットコードを対象ツールで実際に実行し非ゼロ終了することを確認済みか
- [ ] 新しいテストケース（auto_test.md の TC）を追加したステップがある場合、そのTCをすべて実行・記録してから承認ポイントを提示しているか

完了したら「承認ポイント」を提示して停止する。

承認後の次のステップ: `/plan-issue-review $ARGUMENTS` を実行して計画書・テスト文書をレビューしてください。
