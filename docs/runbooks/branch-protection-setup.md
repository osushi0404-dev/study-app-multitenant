# GitHub Branch Protection Rules 設定手順書

- **作成日**: 2026-04-10
- **関連イシュー**: I032 / GitHub Issue #73
- **改訂**: I178 / GitHub Issue #297（2026-10-17・承認者の限定）・I546（2026-11-17・E2E を必須チェックに足す）
- **対象ブランチ**: `develop`・`main`

---

## 概要

このドキュメントは GitHub リポジトリの Branch protection rules を設定するための手順書です。
設定後は以下が強制されます：

- `develop`・`main` への直接 push を GitHub 側でブロック
- §2 の必須チェックが全部通らないと PR のマージを GitHub がブロック
- 管理者も上記ルールを迂回不可
- develop は、bot や外部の人が作った PR を `oshui0404` が承認しない限りマージできない（Code Owners 必須・`.github/CODEOWNERS`）
- develop・main に push・マージできるのは `oshui0404` だけ（main は CODEOWNERS が届くまでこれで守る）

I430 から、develop・main への push と外部（fork）の PR のマージを止める守りは、Claude 側の見張りではなくこの設定が受け持つ（`docs/runbooks/danger-ops.md`）。設定を緩めると最後の守りが黙って消えるので、変えるときは danger-ops.md への影響を確かめる。

---

## 1. 設定値一覧

develop・main で共通（I178）。表の並びは GitHub の設定画面（classic branch protection）の並びに合わせている。

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **1** |
| Dismiss stale pull request approvals when new commits are pushed | **ON** |
| Require review from Code Owners | **ON** |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks | §2 の一覧 |
| Do not allow bypassing the above settings | **ON** |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Restrict pushes that create matching branches | **ON**（既定のまま） |
| Allow force pushes | OFF |
| Allow deletions | OFF |

---

## 1.5 承認者の限定（I178）

### 理由

このリポジトリは public で、外部（fork）の PR が届く（前例: PR #257）。
Claude の名義（`docs/runbooks/github-app-setup.md` の GitHub App）は書き込み権限を持つため、承認者を限定しないと、bot の承認や bot 自身の操作でマージ要件を満たせてしまう。
マージは GitHub の権限で止める（Claude 側の見張りは補助の層）。

### 3 つの設定の役割

1. **CODEOWNERS（`* @oshui0404`）＋ Require review from Code Owners**: 承認として数えられるのは `oshui0404` の承認だけになる。bot や外部の人が作った PR では、bot や外部の人が承認しても、マージ要件を満たさない。
2. **Restrict who can push to matching branches（`oshui0404` のみ）**: develop・main に push（PR のマージを含む）できる人を `oshui0404` だけにする。承認が付いた後でも、bot や外部の人はマージできない。
3. **Dismiss stale pull request approvals when new commits are pushed**: 承認の後に新しいコミットが入ったら承認を取り消す。「承認の後に bot が中身を差し替える」抜け道を塞ぐ。宛先ブランチを変えた PR（`gh pr edit --base`）は、承認の前に差分を確かめ直す。

### main の制約

**main には CODEOWNERS が無い**（main は初期コミットのみ）。GitHub は PR のベースブランチにある CODEOWNERS を使うため、main の「Require review from Code Owners」は、develop の内容が main に入るまで効かない。
それまでの間は、2 の Restrict who can push で守る（承認がどう付いても、`oshui0404` 以外は main にマージできない）。
main から作ったブランチには CI のワークフローが無く必須チェックが報告されないため、CODEOWNERS だけを main に先に入れる PR はマージできない。
main への反映は develop → main の PR で行う（bot が作成し、`oshui0404` が承認・マージする）。

### 運用

- **PR は bot（Claude）が作成する**（ユーザーは PR を作らない）。bot が作った PR では `oshui0404` に自動でレビュー依頼が出て、`oshui0404` の承認が必要になる。
- 承認の後に新しいコミットが入ると承認が取り消されるので、もう一度承認する。develop への追従（Update branch）のコミットでは、差分が変わらない場合に承認が残ることもある（取り消された場合だけ再承認すればよい）。
- Dependabot の PR も `oshui0404` の承認が必要。
- 自動マージ（auto-merge）はリポジトリ設定で許可していない（`allow_auto_merge=false`・2026-10-20 実測）。bot が `gh pr merge --auto` で承認と同時のマージを予約することはできない。許可に変える場合は、承認の後・マージの前に行う確認の順番が崩れないかを見直す。

---

## 2. 必須 CI チェック名

次のジョブをすべて Required status checks に登録する（この一覧が正。ほかの文書は件数を書かずにここを参照する）。

```
Backend Lint & Security
Backend Tests
Frontend Type Check
Frontend Lint & Security
Frontend Tests
API Types Up To Date
Harness Tests
E2E Tests (Playwright)
```

- 上の 7 つは `.github/workflows/ci.yml`、`E2E Tests (Playwright)` は `.github/workflows/e2e.yml` のジョブ
- `Harness Tests`（I193）は、ハーネス（スキル・スクリプト・見張り）の回帰テスト `scripts/claude/tests/run-all.sh` を流す
- `API Types Up To Date`（I493）は、画面の型（`frontend/src/types/api/schema.d.ts`）が API のスキーマ（`backend/openapi.yaml`）と同じかを見る
- `E2E Tests (Playwright)`（I546）は、画面の通しのテスト。Claude の review-gate はもともと E2E の結果を待つが、GitHub でも赤いままのマージを止めるために必須にする。E2E が不安定でマージが止まったときは、fix-loop で直す（必須から外さない）
- 登録はリポジトリ管理者（`oshui0404`）が設定画面で行う（bot には権限が無い）
- status checks の名前は `jobs.<job_id>.name` の値。候補が出ないときは §6 を見る

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

§1 の表に従って ON/OFF します。

**Require a pull request before merging**:
- チェックボックスをオン
- **Require approvals** をオンにし、数値を `1` に設定
- **Dismiss stale pull request approvals when new commits are pushed** をオン
- **Require review from Code Owners** をオン

**Require status checks to pass before merging**:
- チェックボックスをオン
- **Require branches to be up to date before merging** をオン
- **Status checks that are required** の検索ボックスに §2 の各ジョブ名を入力して追加

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

ステップ 1 に戻り、`main` ブランチに対して同じ操作を実施する（§1 の表は共通）。

---

## 4. 動作確認手順

設定後、以下の確認を実施してください。

### 確認 1・2: develop・main への直 push（行わない）

develop・main への直 push は試さない。理由:

- `oshui0404` が実行すると、Restrict の一覧に入っているため、「Do not allow bypassing」の設定を誤っていた場合に、確認の操作そのものが develop・main への直接 push として通ってしまう（main は初期コミットだけなので、レビューと CI を経ないコミットがすべて入る）。
- bot（Claude）からは GitHub の設定で拒否される。
- 人の端末で実行すると、どのアカウントの資格情報で push されるかを確かめにくい。

代わりに、PR 必須・bypass 不可・Restrict の設定は設定画面（§1 の表との突き合わせ）で確認し、効き目は確認 4・6（PR の承認状態と、bot によるマージ API の拒否）で確かめる。

### 確認 3: CI 失敗 PR がマージできないこと

1. CI が失敗する変更（意図的に Ruff のエラーを含むコミット等）で PR を作成する
2. GitHub の PR 画面でマージボタンが無効になっていること（またはエラーが表示されること）を確認する

### 確認 4: develop への PR で、`oshui0404` の承認なしにマージできないこと

1. bot が作成した PR（develop 宛て）について、承認前に次を実行する:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus
   ```
2. 期待結果: `reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED`
3. `oshui0404` が承認した後に同じコマンドを実行し、`reviewDecision=APPROVED` になることを確認する

main は CODEOWNERS が届くまで、bot の承認でも `reviewDecision=APPROVED` になり得る（§1.5「main の制約」）。main は設定画面（§1 の表との突き合わせ）で確認し、develop → main の PR を作ったときに確認 6（push 制限）を行う。

### 確認 6: bot がマージできないこと（push 制限）

1. bot が作成し `oshui0404` が承認した PR について、次を実行し、前提がすべて成り立つことを確かめる（push 制限以外の理由でマージに失敗する状態を除くため）:
   ```bash
   gh pr view <PR番号> --json reviewDecision,mergeStateStatus,headRefOid,reviews,statusCheckRollup
   ```
   - `reviewDecision=APPROVED`
   - `mergeStateStatus` が `BEHIND`・`DIRTY` でない
   - 最新の承認（`reviews` の最後の `APPROVED`）の `commit.oid` が `headRefOid` と同じ（承認後に新しいコミットが無い）
   - `statusCheckRollup` の §2 の必須チェックがすべて `SUCCESS`
2. **実行前に `oshui0404` の了承を得てから**、bot で GitHub のマージ API を直接呼ぶ（`gh pr merge` は API を呼ぶ前に手元で `BLOCKED` を判定し、push 制限と他の理由を区別できない汎用の文で止まるため使わない。`--auto` も付けない）。push 制限の設定を誤っていると、この操作で実際にマージされる点に注意する。`-i` で HTTP ステータスも表示させ、記録する:
   ```bash
   gh api -i -X PUT repos/osushi0404-dev/study-app-multitenant/pulls/<PR番号>/merge -f merge_method=merge
   ```
3. 期待結果: API が失敗し、`gh pr view <PR番号> --json state` は `OPEN` のまま。応答の `message` から URL（`http` で始まる部分）を除いたうえで、次の基準で判定する（大文字小文字は区別しない）。マージは、この確認の後に `oshui0404` が行う（手動テストの流れがある場合はそれに従う）
   - **合格（push 制限による拒否）**: `push` または `authorized` を含み、`review`・`approv`・`status check` を含まない
   - **前提崩れ（やり直し）**: `review`・`approv`・`status check` のいずれかを含む。1 の状態を整えてやり直す
   - **判断保留**: 上のどちらにも当たらない（例: `Resource not accessible by integration`）。文をそのまま記録し、`oshui0404` に確認する

（確認 5 は I178 の再オープンで廃止した。bot・外部の単独マージは確認 6 で止まることを確かめる）

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

CI が一度も実行されていないと候補に表示されない。PR を 1 件作成して CI を実行してから再度設定画面を開くか、検索ボックスにジョブ名（§2）を直接入力して登録する。

### 承認したのに BLOCKED に戻った

承認の後に新しいコミット（develop への追従など）が入ると、Dismiss stale approvals により承認が取り消される（追従のコミットで差分が変わらない場合は残ることもある）。取り消された場合は、もう一度承認する。

### 既存の Draft PR への影響

Draft PR はマージできないので影響しない。Ready にする前に CI を通す。
