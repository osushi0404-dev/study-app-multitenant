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
| Do not allow bypassing the above settings | **ON** |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Restrict pushes that create matching branches | **ON**（既定のまま） |
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
| Do not allow bypassing the above settings | **ON** |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Restrict pushes that create matching branches | **ON**（既定のまま） |
| Allow force pushes | OFF |
| Allow deletions | OFF |

develop と main は同じ設定にする（I178）。表の並びは GitHub の設定画面（classic branch protection）の並びに合わせている。

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
3. **Dismiss stale pull request approvals when new commits are pushed**: 承認の後に新しいコミットが入ったら承認を取り消す。「承認の後に bot が中身を差し替える」抜け道を塞ぐ。ただし、PR の宛先ブランチの変更（`gh pr edit --base`）では承認が取り消されない可能性がある（未確認・I178 の /retro で確認する）。宛先が変わった PR は、承認の前に差分を確かめ直す。

### main の制約

**main には CODEOWNERS が無い**（main は初期コミットのみ）。GitHub は PR のベースブランチにある CODEOWNERS を使うため、main の「Require review from Code Owners」は、develop の内容が main に入るまで効かない。
それまでの間は、2 の Restrict who can push で守る（承認がどう付いても、`oshui0404` 以外は main にマージできない）。
main から作ったブランチには CI のワークフローが無く必須チェックが報告されないため、CODEOWNERS だけを main に先に入れる PR はマージできない。
main への反映は develop → main の PR で行う（bot が作成し、`oshui0404` が承認・マージする）。

### 設定変更直後の develop

develop も同じ理由で、CODEOWNERS を追加した PR（I178・#298）が develop にマージされるまでは「Require review from Code Owners」が効かない（承認 1 件の要件だけが働く）。その間も Restrict who can push により、`oshui0404` 以外はマージできない。

### 運用

- **PR は必ず bot（Claude）が作成する**。ユーザー自身が作った PR は自分で承認できず、bypass も許していないためマージできない（どうしても必要な場合は §6 を参照）。
- 承認の後に新しいコミットが入ると承認が取り消されるので、もう一度承認する。develop への追従（Update branch）のコミットでは、差分が変わらない場合に承認が残ることもある（取り消された場合だけ再承認すればよい）。
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
4. **「Add classic branch rule」** ボタンをクリック（既にルールがある `develop`・`main` を変更する場合は、対象ルール右側の **Edit** をクリックし、ステップ 3 へ進む）

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

**Do not allow bypassing the above settings**:
- チェックボックスをオン（管理者も対象）

**Restrict who can push to matching branches**:
- チェックボックスをオン
- 検索ボックスに `oshui0404` を入力して追加する（一覧に `oshui0404` だけが表示されていること）
- **Restrict pushes that create matching branches** はオンのまま（既定）

**Allow force pushes**: オフのまま（デフォルト）

**Allow deletions**: オフのまま（デフォルト）

### ステップ 4: 保存

- **Create** ボタン（既存ルールを Edit した場合は **Save changes**）をクリック

### ステップ 5: main ブランチも同様に設定

ステップ 1 に戻り、`main` ブランチに対して同じ操作を実施（設定値は main の表を参照）。

---

## 4. 動作確認手順

設定後、以下の確認を実施してください。

### 確認 1: develop への直 push がブロックされること

**bot（Restrict の一覧に無いアカウント）だけが実行する。`oshui0404` は実行しない**。`oshui0404` は Restrict の一覧に入っているため、「Do not allow bypassing」の設定を誤っていると、この確認の操作そのものが develop・main への直接 push として通ってしまう（main は初期コミットだけなので、レビューと CI を経ないコミットがすべて入る）。PR 必須と bypass 不可の設定は、設定画面（§1 の表との突き合わせ）で確認する。

```bash
# 現在のブランチから develop に直 push を試みる（bot で実行）
git push origin HEAD:develop
```

期待結果: push が拒否される（`remote: error: GH006: Protected branch update failed for refs/heads/develop.` に続けて、拒否の理由が表示される）。理由の文は push 権限の不足（`You're not authorized to push to this branch` 等）または PR 必須（`Changes must be made through a pull request.`）のどちらか。どちらでも拒否されていれば合格

### 確認 2: main への直 push がブロックされること

```bash
# bot で実行（oshui0404 は実行しない）
git push origin HEAD:main
```

期待結果: develop と同様に拒否される

### 確認 3: CI 失敗 PR がマージできないこと

1. CI が失敗する変更（意図的に flake8 エラーを含むコミット等）で PR を作成する
2. GitHub の PR 画面でマージボタンが無効になっていること（またはエラーが表示されること）を確認する

### 確認 4: develop への PR で、`oshui0404` の承認なしにマージできないこと

1. bot が作成した PR（develop 宛て）について、承認前に次を実行する:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus
   ```
2. 期待結果: `reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED`
3. `oshui0404` が承認した後に同じコマンドを実行し、`reviewDecision=APPROVED` になることを確認する

main は CODEOWNERS が届くまで、bot の承認でも `reviewDecision=APPROVED` になり得る（§1.5「main の制約」）。main は設定画面（§1 の main の表との突き合わせ）で確認し、develop → main の PR を作ったときに確認 6（push 制限）を行う。

### 確認 5: bot が承認してもマージ要件を満たさないこと

develop に CODEOWNERS が入った後に行う（§1.5「設定変更直後の develop」）。

1. `oshui0404` が develop 宛ての確認用 PR を作成する（bot は自分の PR を承認できないため）。Code Owners の要件はファイルの変更を含む PR にだけ働くので、空コミットではなく 1 行のファイル変更（例: `check_codeowners.txt` の追加）を含める
2. bot で承認する:
   ```bash
   gh pr review <PR番号> --approve
   ```
3. 次を実行し、`reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` のままであることを確認する:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus
   ```
4. 確認後、マージせずに閉じ、確認用ブランチも削除する:
   ```bash
   gh pr close <PR番号> --delete-branch
   ```

### 確認 6: bot がマージできないこと（push 制限）

1. bot が作成し `oshui0404` が承認した PR について、次を実行し、前提がすべて成り立つことを確かめる（push 制限以外の理由でマージに失敗する状態を除くため）:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus,headRefOid,reviews,statusCheckRollup
   ```
   - `reviewDecision=APPROVED`
   - `mergeStateStatus` が `BEHIND`・`DIRTY` でない
   - 最新の承認（`reviews` の最後の `APPROVED`）の `commit.oid` が `headRefOid` と同じ（承認後に新しいコミットが無い）
   - `statusCheckRollup` の必須チェック 5 件がすべて `SUCCESS`
2. **実行前に `oshui0404` の了承を得てから**、bot で GitHub のマージ API を直接呼ぶ（`gh pr merge` は API を呼ぶ前に手元で `BLOCKED` を判定し、push 制限と他の理由を区別できない汎用の文で止まるため使わない。`--auto` も付けない）。push 制限の設定を誤っていると、この操作で実際にマージされる点に注意する。`-i` で HTTP ステータスも表示させ、記録する:
   ```bash
   gh api -i -X PUT repos/osushi0404-dev/study-app-multitenant/pulls/<PR番号>/merge -f merge_method=merge
   ```
3. 期待結果: API が失敗し、`gh pr view <PR番号> --json state` は `OPEN` のまま。応答の `message` から URL（`http` で始まる部分）を除いたうえで、次の基準で判定する（大文字小文字は区別しない）。マージは、この確認の後に `oshui0404` が行う（手動テストの流れがある場合はそれに従う）
   - **合格（push 制限による拒否）**: `push` または `authorized` を含み、`review`・`approv`・`status check` を含まない
   - **前提崩れ（やり直し）**: `review`・`approv`・`status check` のいずれかを含む。1 の状態を整えてやり直す
   - **判断保留**: 上のどちらにも当たらない（例: `Resource not accessible by integration`）。文をそのまま記録し、`oshui0404` に確認する

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
PR は bot（Claude）に作らせる。どうしてもユーザーが作った PR をマージする必要がある場合は、対象ブランチのルールを **Edit** して「Do not allow bypassing the above settings」を一時的にオフにし、PR 画面で管理者として要件を迂回してマージした後、すぐにオンに戻す（§5 の I178 全体の戻し手順ではマージできない）。戻した後は、設定画面で対象ブランチのルールを開き、§1 の表と突き合わせて「Do not allow bypassing the above settings」がオンに戻っていることを確かめる（bot は保護設定を読めないため、戻し忘れは画面でしか分からない）。

### 承認したのに BLOCKED に戻った

承認の後に新しいコミット（develop への追従など）が入ると、Dismiss stale approvals により承認が取り消される（追従のコミットで差分が変わらない場合は残ることもある）。取り消された場合は、もう一度承認する。

### 既存の Draft PR への影響

Branch protection rules は Draft PR には影響しません（Draft PR はマージ不可のため）。
既存の Draft PR を Ready にする前に CI を通過させてください。
