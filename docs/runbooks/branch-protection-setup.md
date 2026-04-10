# GitHub Branch Protection Rules 設定手順書

- **作成日**: 2026-04-10
- **関連イシュー**: I032 / GitHub Issue #73
- **対象ブランチ**: `develop`・`main`

---

## 概要

このドキュメントは GitHub リポジトリの Branch protection rules を設定するための手順書です。
設定後は以下が強制されます：

- `develop`・`main` への直接 push を GitHub 側でもブロック（二重ガード）
- CI（5ジョブ）が全通過しないと PR のマージを GitHub がブロック
- 管理者も上記ルールを迂回不可

---

## 1. 設定値一覧

### develop ブランチ

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **0** |
| Dismiss stale pull request approvals when new commits are pushed | OFF |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks（5件） | 後述 |
| Do not allow bypassing the above settings | **ON** |
| Allow force pushes | OFF |
| Allow deletions | OFF |

### main ブランチ

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **1**（本番ゲート。自己 approve 可） |
| Dismiss stale pull request approvals when new commits are pushed | **ON** |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks（5件） | 後述 |
| Do not allow bypassing the above settings | **ON** |
| Allow force pushes | OFF |
| Allow deletions | OFF |

### develop と main の差異

| 項目 | develop | main | 理由 |
|-----|---------|------|------|
| Required approvals | 0 | **1** | main は本番相当のため意図的リリースゲートを設ける |
| Dismiss stale reviews | OFF | **ON** | main は最新コードでの approve を保証するため |

---

## 2. 必須 CI チェック名

`.github/workflows/ci.yml` で定義されている以下の 5 ジョブをすべて Required status checks に登録します。

```
Backend Lint & Security
Backend Tests
Frontend Type Check
Frontend Lint & Security
Frontend Tests
```

> **注意**: status checks の名前は `jobs.<job_id>.name` の値です。
> GitHub の UI に候補が表示されない場合は、先に PR を 1 件作成・CI を実行してから登録してください。
> 候補が出ない場合は手動でジョブ名を入力することも可能です。

---

## 3. GitHub Settings 操作手順

以下の手順を `develop`・`main` それぞれに対して実施します。

### ステップ 1: Branch protection rules 画面を開く

1. GitHub リポジトリのトップページを開く
2. **Settings** タブをクリック
3. 左サイドバーの **Code and automation** > **Branches** をクリック
4. **Branch protection rules** セクションの **Add rule** ボタンをクリック

### ステップ 2: ブランチ名パターンを入力

- **Branch name pattern** フィールドに `develop`（または `main`）を入力

### ステップ 3: 各項目を設定

以下のチェックボックスを設定値一覧に従って ON/OFF します。

**Require a pull request before merging**:
- チェックボックスをオン
- **Required approvals**: develop は `0`、main は `1` に設定
- main のみ: **Dismiss stale pull request approvals when new commits are pushed** をオン

**Require status checks to pass before merging**:
- チェックボックスをオン
- **Require branches to be up to date before merging** をオン
- **Status checks that are required** の検索ボックスに各ジョブ名を入力して追加（5件）:
  - `Backend Lint & Security`
  - `Backend Tests`
  - `Frontend Type Check`
  - `Frontend Lint & Security`
  - `Frontend Tests`

**Do not allow bypassing the above settings**:
- チェックボックスをオン（管理者も対象）

**Allow force pushes**: オフのまま（デフォルト）

**Allow deletions**: オフのまま（デフォルト）

### ステップ 4: 保存

- **Create** ボタン（または **Save changes**）をクリック

### ステップ 5: main ブランチも同様に設定

ステップ 1 に戻り、`main` ブランチに対して同じ操作を実施（設定値は main 列を参照）。

---

## 4. 動作確認手順

設定後、以下の確認を実施してください。

### 確認 1: develop への直 push がブロックされること

```bash
# 現在のブランチから develop に直 push を試みる
git push origin HEAD:develop
```

期待結果:
```
remote: error: GH006: Protected branch update failed for refs/heads/develop.
remote: error: Changes must be made through a pull request.
```

### 確認 2: main への直 push がブロックされること

```bash
git push origin HEAD:main
```

期待結果: develop と同様のエラーメッセージ

### 確認 3: CI 失敗 PR がマージできないこと

1. CI が失敗する変更（意図的に flake8 エラーを含むコミット等）で PR を作成する
2. GitHub の PR 画面でマージボタンが無効になっていること（またはエラーが表示されること）を確認する

### 確認 4: main への PR で approval なしにマージできないこと

1. `main` を target にした PR を作成する
2. approve なしの状態でマージボタンが無効になっていること（`1 approval required` のメッセージ）を確認する

---

## 5. ロールバック手順

Branch protection rules を削除・緩和する場合:

1. GitHub Settings > Branches を開く
2. 対象ブランチのルール右側の **Edit** ボタンをクリック
3. 設定を変更して **Save changes** / または **Delete rule** ボタンをクリック

コード・データへの影響はなく、即時復元可能です。

---

## 6. トラブルシューティング

### status checks の候補が表示されない

CI が一度も実行されていないと候補に表示されません。
PR を 1 件作成して CI を実行してから再度設定画面を開いてください。
または、検索ボックスにジョブ名を直接入力することでも登録できます。

### main への PR で自分が approve できない

GitHub はデフォルトでセルフ approve（自分の PR を自分で approve）が可能です。
PR 画面の **Files changed** タブから **Review changes > Approve** を選択してください。

### 既存の Draft PR への影響

Branch protection rules は Draft PR には影響しません（Draft PR はマージ不可のため）。
既存の Draft PR を Ready にする前に CI を通過させてください。
