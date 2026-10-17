# GitHub Branch Protection Rules 設定手順書

- **作成日**: 2026-04-10
- **関連イシュー**: I032 / GitHub Issue #73
- **改訂**: I178 / GitHub Issue #297（2026-10-17・承認者の限定）
- **対象ブランチ**: `develop`・`main`

---

## 概要

このドキュメントは GitHub リポジトリの Branch protection rules を設定するための手順書です。
設定後は以下が強制されます：

- `develop`・`main` への直接 push を GitHub 側でもブロック（二重ガード）
- CI（5ジョブ）が全通過しないと PR のマージを GitHub がブロック
- 管理者も上記ルールを迂回不可
- develop は `oshui0404` が承認しない限りマージできない（Code Owners 必須・`.github/CODEOWNERS`）
- develop・main に push・マージできるのは `oshui0404` だけ（main は CODEOWNERS が届くまでこれで守る）

---

## 1. 設定値一覧

### develop ブランチ

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **1** |
| Dismiss stale pull request approvals when new commits are pushed | **ON** |
| Require review from Code Owners | **ON** |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks（5件） | 後述 |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Do not allow bypassing the above settings | **ON** |
| Allow force pushes | OFF |
| Allow deletions | OFF |

### main ブランチ

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **1**（本番ゲート） |
| Dismiss stale pull request approvals when new commits are pushed | **ON** |
| Require review from Code Owners | **ON** |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks（5件） | 後述 |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Do not allow bypassing the above settings | **ON** |
| Allow force pushes | OFF |
| Allow deletions | OFF |

develop と main は同じ設定にする（I178）。

---

## 1.5 承認者の限定（I178）

### 理由

このリポジトリは public で、外部（fork）の PR が届く（前例: PR #257）。
bot アカウント `osushi0404-bot` は書き込み権限を持つため、承認者を限定しないと、bot の承認や bot 自身の操作でマージ要件を満たせてしまう。
以前の develop は承認の要件が無く、main は承認 1 件が必要でも承認者が限定されていなかった。
Claude 側のガード（I146・`scripts/claude/hooks/pretooluse_guard.py`）は補助の層で、マージは GitHub の権限で止める。

### 3 つの設定の役割

1. **CODEOWNERS（`* @oshui0404`）＋ Require review from Code Owners**: 承認として数えられるのは `oshui0404` の承認だけになる。bot や外部の人が承認しても、マージ要件を満たさない。
2. **Restrict who can push to matching branches（`oshui0404` のみ）**: develop・main に push（PR のマージを含む）できる人を `oshui0404` だけにする。承認が付いた後でも、bot や外部の人はマージできない。
3. **Dismiss stale pull request approvals when new commits are pushed**: 承認の後に新しいコミットが入ったら承認を取り消す。「承認の後に bot が中身を差し替える」抜け道を塞ぐ。

### main の制約

**main には CODEOWNERS が無い**（main は初期コミットのみ）。GitHub は PR のベースブランチにある CODEOWNERS を使うため、main の「Require review from Code Owners」は、develop の内容が main に入るまで効かない。
それまでの間は、2 の Restrict who can push で守る（承認がどう付いても、`oshui0404` 以外は main にマージできない）。
main から作ったブランチには CI のワークフローが無く必須チェックが報告されないため、CODEOWNERS だけを main に先に入れる PR はマージできない。

### 運用

- **PR は必ず bot（Claude）が作成する**。ユーザー自身が作った PR は自分で承認できず、bypass も許していないためマージできない。
- 承認の後に develop への追従（Update branch）などでコミットが入ると承認が取り消されるので、もう一度承認する。
- Dependabot の PR も `oshui0404` の承認が必要。

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
4. **「Add classic branch rule」** ボタンをクリック

> **注意**: GitHub の UI では「Add rule」「Add branch ruleset」「Add classic branch rule」の3種類が表示される場合があります。
> 従来の Branch protection rules を設定するには **「Add classic branch rule」** を選んでください。
> 「Add branch ruleset」は新しい Rulesets 機能で、設定項目が異なります。

### ステップ 2: ブランチ名パターンを入力

- **Branch name pattern** フィールドに `develop`（または `main`）を入力

### ステップ 3: 各項目を設定

以下のチェックボックスを設定値一覧に従って ON/OFF します（develop と main で同じ手順）。

**Require a pull request before merging**:
- チェックボックスをオン
- **Require approvals** をオンにし、数値を `1` に設定
- **Dismiss stale pull request approvals when new commits are pushed** をオン
- **Require review from Code Owners** をオン

**Require status checks to pass before merging**:
- チェックボックスをオン
- **Require branches to be up to date before merging** をオン
- **Status checks that are required** の検索ボックスに各ジョブ名を入力して追加（5件）:
  - `Backend Lint & Security`
  - `Backend Tests`
  - `Frontend Type Check`
  - `Frontend Lint & Security`
  - `Frontend Tests`

**Restrict who can push to matching branches**:
- チェックボックスをオン
- 検索ボックスに `oshui0404` を入力して追加する（一覧に `oshui0404` だけが表示されていること）

**Do not allow bypassing the above settings**:
- チェックボックスをオン（管理者も対象）

**Allow force pushes**: オフのまま（デフォルト）

**Allow deletions**: オフのまま（デフォルト）

### ステップ 4: 保存

- **Create** ボタン（または **Save changes**）をクリック

### ステップ 5: main ブランチも同様に設定

ステップ 1 に戻り、`main` ブランチに対して同じ操作を実施（設定値は main の表を参照）。

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

### 確認 4: develop・main への PR で、`oshui0404` の承認なしにマージできないこと

1. bot が作成した PR（develop 宛て）について、承認前に次を実行する:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus
   ```
2. 期待結果: `reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED`
3. `oshui0404` が承認した後に同じコマンドを実行し、`reviewDecision=APPROVED` になることを確認する

### 確認 5: bot が承認してもマージ要件を満たさないこと

1. `oshui0404` が develop 宛ての中身のない確認用 PR を作成する（bot は自分の PR を承認できないため）
2. bot で承認する:
   ```bash
   gh pr review <PR番号> --approve
   ```
3. 次を実行し、`reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` のままであることを確認する:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus
   ```
4. 確認後、マージせずに閉じる:
   ```bash
   gh pr close <PR番号>
   ```

---

## 5. ロールバック手順

Branch protection rules を削除・緩和する場合:

1. GitHub Settings > Branches を開く
2. 対象ブランチのルール右側の **Edit** ボタンをクリック
3. 設定を変更して **Save changes** / または **Delete rule** ボタンをクリック

I178 の変更を元に戻す場合:

1. develop・main の各ルールで「Require review from Code Owners」「Restrict who can push to matching branches」を OFF にする
2. develop は「Require approvals」と「Dismiss stale pull request approvals when new commits are pushed」も OFF に戻す（main は承認 1・Dismiss stale ON のまま＝元の値）
3. `.github/CODEOWNERS` は revert の PR で削除する

コード・データへの影響はなく、即時復元可能です。

---

## 6. トラブルシューティング

### status checks の候補が表示されない

CI が一度も実行されていないと候補に表示されません。
PR を 1 件作成して CI を実行してから再度設定画面を開いてください。
または、検索ボックスにジョブ名を直接入力することでも登録できます。

### 自分が作った PR を承認・マージできない

GitHub では PR の作成者は自分の PR を承認できない。このリポジトリでは bypass も許していないため、ユーザーが作った PR はマージできない。
PR は bot（Claude）に作らせる。急ぎで必要な場合は、ブランチ保護を一時的に緩め、作業後すぐ戻す（§5）。

### 承認したのに BLOCKED に戻った

承認の後に新しいコミット（develop への追従など）が入ると、Dismiss stale approvals により承認が取り消される。もう一度承認する。

### 既存の Draft PR への影響

Branch protection rules は Draft PR には影響しません（Draft PR はマージ不可のため）。
既存の Draft PR を Ready にする前に CI を通過させてください。
