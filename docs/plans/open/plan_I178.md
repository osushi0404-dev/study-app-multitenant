# I178 計画書: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

## 基本情報
- **計画書ID**: plan_I178
- **関連イシュー**: #297
- **Draft PR**: #298
- **作成根拠資料**: docs/issues/open/I178.md（起点イシュー・設計確認メモ確定済み）
- **実装後評価**: docs/reviews/open/I178_review.md
- **作成日**: 2026-10-17

---

## 1. 背景/目的

**背景**: I146 では、外部（fork）PR への危険な操作を Claude 側のフック（`scripts/claude/hooks/pretooluse_guard.py`）で止める仕組みを入れた。ただし、コマンド文字列で判定する方式には原理的な限界がある（`bash -c`・`eval`・エイリアス等）。調べたところ、GitHub 側でマージを止める仕組みはほとんど無かった。develop は承認が不要で、main は承認 1 件が必要なものの、承認者が限定されていなかった。

**目的**: 外部 PR も bot（Claude）単独の操作も、**リポジトリ管理者 `oshui0404` が承認し、かつ `oshui0404` がマージしない限り、GitHub が develop・main へのマージを拒否する**状態にする。あわせて、ハーネスの文書（runbook・close スキル）を実際の設定にそろえる。

---

## 2. 受け入れ条件

イシュー I178「受け入れ条件」と同一。番号はテスト文書・レビュー文書から参照する。

| AC | 内容 | 検証 |
|---|---|---|
| AC-1 | `.github/CODEOWNERS` が存在し、コメント以外の行が `* @oshui0404` の 1 行のみ | TC-01・TC-02・TC-03・TC-04 |
| AC-2 | develop と main の両方で「Require review from Code Owners」が有効。bot の PR が `reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` になる | 手動 No.1・No.2・No.3・No.4・No.7（develop で Code Owners の効き目を区別できるのは、CODEOWNERS が develop に入った後の No.7。No.3・No.4 は承認要件が付いたことの確認） |
| AC-3 | ユーザーが承認すると、同じ PR が `reviewDecision=APPROVED` になりマージ可能になる | 手動 No.5 |
| AC-4 | bot が他人の PR を承認しても、マージ要件を満たさない | 手動 No.7（マージ後） |
| AC-5 | develop・main で「Dismiss stale approvals」「Restrict who can push（`oshui0404` のみ）」「Do not allow bypassing」が有効 | 手動 No.1・No.2・No.6・No.8 |
| AC-6 | `branch-protection-setup.md` に新しい設定・変更の理由・運用（PR は bot が作る）が書かれ、「自己 approve 可」の誤記が無い | TC-05〜TC-12・TC-18・TC-19 |
| AC-7 | close スキルと pr-base-sync の前提（承認前の正常な状態は BLOCKED）が実際の設定と一致している | TC-13〜TC-16・TC-19 |

---

## 3. 調査結果

### 3-1. 原因の概要（平易な説明）

「誰がマージしてよいか」を最後に決めているのが、GitHub の設定ではなく「いつもユーザーがマージしている」という運用と Claude 側のガードだった。bot には書き込み権限があるため、GitHub の設定上は、bot が自分でマージすることも、外部 PR を承認して要件を満たすこともできる。

### 3-2. 詳細な原因分析（2026-10-17 実測）

| # | 確認内容 | コマンド | 結果 |
|---|---|---|---|
| 1 | 共同作業者と権限 | `gh api repos/osushi0404-dev/study-app-multitenant/collaborators --jq ".[] \| {login, role_name}"` | `oshui0404`=admin・`osushi0404-bot`=write の 2 名のみ |
| 2 | リポジトリ所有者の種別 | `gh api repos/osushi0404-dev/study-app-multitenant --jq "{owner: .owner.login, type: .owner.type, visibility}"` | `osushi0404-dev`・**Organization**・public。組織のリポジトリなので、classic branch protection の「Restrict who can push to matching branches」が使える |
| 3 | 承認者アカウントの権限 | `gh api .../collaborators/oshui0404/permission --jq .permission` | `admin` |
| 4 | bot の権限（対照） | `gh api .../collaborators/osushi0404-bot/permission --jq .permission` | `write` |
| 5 | develop の承認要件（現状） | `gh pr view 298 --json reviewDecision,mergeStateStatus,isDraft` | `reviewDecision=""`（承認要件なし） |
| 6 | main の中身 | `git ls-tree -r --name-only origin/main` | **`README.md` のみ**（初期コミットだけ） |
| 7 | main の必須チェック | `gh api .../branches/main --jq ".protection.required_status_checks"` | 5 件・`enforcement_level=everyone` |
| 8 | CODEOWNERS の構文検査 API | `gh api "repos/.../codeowners/errors?ref=develop"` | **404**（CODEOWNERS が無いブランチでは 404）。bot 権限で呼べることは確認できた |
| 9 | GitHub Actions による develop/main への push・マージ | `grep -rln -E "git push\|gh pr merge\|contents: write" .github/` | 0 件。push 制限で止まる自動処理は無い |
| 10 | main 宛て PR の実績 | `gh pr list --state all --base main` | #75 の 1 件のみ（close・未マージ） |
| 11 | ユーザー作成 PR の実績 | `gh pr list --state all --author oshui0404` | #93 の 1 件のみ |

**根本原因（設定・文書レベル）**

| # | 箇所 | 問題 |
|---|---|---|
| 1 | develop のブランチ保護 | 承認要件が無い（`reviewDecision=""`）。書き込み権限があれば誰でもマージできる |
| 2 | main のブランチ保護 | 承認 1 件は必要だが、承認者が限定されていない。bot の承認で要件を満たせる |
| 3 | リポジトリ | CODEOWNERS が無い |
| 4 | `docs/runbooks/branch-protection-setup.md` L27・L37-38・L106 | develop を「承認不要」と定めている |
| 5 | `docs/runbooks/branch-protection-setup.md` L45・L194-197 | 「自己 approve 可」と書いているが、GitHub では PR の作成者は自分の PR を承認できない（誤記） |
| 6 | `.claude/skills/close/SKILL.md` L151-152・L156 | 「ユーザーの Approve がマージ条件」と書いているが、develop では設定で強制されていなかった |

### 3-3. 調査で判明した制約: main には CODEOWNERS が届かない

GitHub は、PR のベースブランチにある CODEOWNERS を使う。main には `README.md` しか無いため、このイシューで develop に CODEOWNERS を入れても、**main 宛ての PR では「Require review from Code Owners」が実質的に効かない**（所有者が定義されていない状態になり、承認 1 件の要件だけが残る）。

- 代わりの案「main 宛てに CODEOWNERS だけの PR を出す」は**実現できない**。main から作ったブランチには CI のワークフローが無いため、必須チェック 5 件が永久に報告されず、bypass 不可の設定ではマージできない。
- そのため main は「**Restrict who can push（`oshui0404` のみ）**」で守る。マージは push の一種なので、承認がどう付いても、`oshui0404` 以外は main にマージできない。bot の承認で承認 1 件の要件が満たされても、bot も外部の人もマージボタンを押せない。
- 「Require review from Code Owners」は main でも ON にしておく。develop の内容が将来 main に入った時点で、自動的に効き始める。
- この制約と守り方を runbook に明記する（TC-10）。

### 3-4. 消費箇所の全件列挙（承認前提を書いている箇所）

`grep -rn -i -E "approve|承認不要|Require approvals|CODEOWNERS|self.?approve|セルフ" docs/runbooks .claude/skills CONTRIBUTING.md SECURITY.md .github scripts/claude/pr-base-sync.sh` の結果、このイシューで扱う「マージに承認が要るか」の記述は次の箇所だけだった。

| ファイル | 行 | 扱い |
|---|---|---|
| `docs/runbooks/branch-protection-setup.md` | L27・L37-38・L45・L59・L106-108・L167-170・L194-197 | 変更（ステップ 2） |
| `.claude/skills/close/SKILL.md` | L151-152・L156 | 変更（ステップ 3） |
| `scripts/claude/pr-base-sync.sh` | L6・L114 | **変更しない**。「Approve 待ちの BLOCKED は正常」は新しい設定とそのまま一致する（TC-15・TC-16） |
| `docs/runbooks/workflow.md` | L263-264 | 変更しない。I146 の Claude 側ガードが `review --approve` を ask にするという記述で、承認要件の前提ではない |
| `docs/runbooks/danger-ops.md` L3・`workflow.md` L42・`implement/SKILL.md` L19 | — | 対象外。`danger-approved` ラベルの話で、ブランチ保護とは関係ない |

### 3-5. 環境前提確認

| 確認項目 | コマンド | 実測結果 |
|---|---|---|
| 実行環境 | ワークツリー `/mnt/c/app/wt-harness`（track:harness） | ホスト。コンテナ・DB・フロントエンドのビルドは使わない |
| GitHub CLI | `gh --version` | gh 2.88.1 |
| bot の権限 | 3-2 #4 | write（ブランチ保護の変更・閲覧は不可。設定はユーザーが UI で行う） |
| 既存テスト | `bash scripts/claude/tests/test_pr_base_sync.sh` | `RESULT: OK (21/21 cases, 30 assertions)` |

### 3-6. スパイク実証

| # | 前提 | 区分 | 結果 |
|---|---|---|---|
| S1 | CODEOWNERS に書く名前が、書き込み権限以上を持つ実在のアカウントである | (1) 稼働中セッションで実証可能 | `oshui0404` = admin ✅（3-2 #3） |
| S2 | CODEOWNERS の構文と所有者の有効性を GitHub に検査させられる | (1) ただし CODEOWNERS を含むブランチが必要 | bot 権限で API を呼べることは確認済み（3-2 #8）。実際の検査は**ステップ 1 で CODEOWNERS を push した直後**に TC-04 で行う。不成立（errors が 1 件以上）なら後続ステップに進まない |
| S3 | 設定後に bot の承認が要件を満たさない | (2) 稼働中セッションでは実証不能（リポジトリ設定の変更と CODEOWNERS の develop 反映が必要） | 未実証。マージ後の手動 No.7 で実証する |

---

## 4. 影響範囲

| 区分 | 内容 |
|---|---|
| Backend | なし |
| Frontend | なし |
| DB | なし |
| Config/Infra | `.github/CODEOWNERS`（新規）・GitHub リポジトリ設定（develop・main のブランチ保護。ユーザーが UI で変更） |
| ハーネス文書 | `docs/runbooks/branch-protection-setup.md`・`.claude/skills/close/SKILL.md` |
| ハーネステスト | `scripts/claude/tests/test_i178_branch_protection_doc.sh`（新規・adversarial 第1周 High 対応） |
| 運用 | 設定後は、すべての PR でマージ前に `oshui0404` の承認が必要。承認後に新しいコミットが入ると承認は取り消される。ユーザー自身が作った PR はマージできない（PR は bot が作る） |
| 進行中の PR | 設定を変えた時点で、#293（I174）などの作業中 PR にも承認が必要になる |

---

## 5. 変更点一覧

### 修正アプローチ

GitHub 側の 3 つの設定を組み合わせて、マージの最後の砦を GitHub の権限にする。

1. **CODEOWNERS**: 全ファイルの所有者を `oshui0404` だけにする → 承認として数えられるのは `oshui0404` の承認だけになる（develop）。
2. **Restrict who can push**: develop・main に push（マージを含む）できる人を `oshui0404` だけにする → 承認が付いた後でも、bot や外部の人はマージできない。main に CODEOWNERS が届いていない間も、これで守れる。
3. **Dismiss stale approvals**: 承認の後に新しいコミットが入ったら承認を取り消す → 「承認の後に bot が中身を差し替える」抜け道を塞ぐ。

文書（runbook・close スキル）は、この設定に合わせて書き換える。

### 5-1. `.github/CODEOWNERS`（新規）

**修正方針**: すべてのパスの所有者を `oshui0404` だけにする。CODEOWNERS 自体も `*` に含まれるので、CODEOWNERS の変更にも `oshui0404` の承認が必要になる。

```
# 全ファイルの所有者をリポジトリ管理者に限定する（I178）。
# develop・main のブランチ保護「Require review from Code Owners」と組み合わせ、
# 管理者以外（bot・外部の人）の承認ではマージ要件を満たさないようにする。
# 設定と理由: docs/runbooks/branch-protection-setup.md
* @oshui0404
```

### 5-2. `docs/runbooks/branch-protection-setup.md`（変更）

**修正方針**: develop・main の設定値を新しい設定に書き換え、理由・運用・確認手順を追記する。誤記を直す。

| 箇所 | 変更内容 |
|---|---|
| 冒頭メタ情報 | `- **関連イシュー**: I032 / GitHub Issue #73` の下に `- **改訂**: I178 / GitHub Issue #297（2026-10-17・承認者の限定）` を追加 |
| §概要 の箇条書き | 「develop は `oshui0404` が承認しない限りマージできない（Code Owners 必須）」「develop・main に push・マージできるのは `oshui0404` だけ（main は CODEOWNERS が届くまでこれで守る）」を追加 |
| §1 develop の表 | `Require approvals` を **ON・1**、`Require review from Code Owners` 行を追加し **ON**、`Dismiss stale pull request approvals when new commits are pushed` を **ON**、`Restrict who can push to matching branches` 行を追加し **ON（`oshui0404` のみ）** |
| §1 develop 下の補足（L36-38） | 「承認不要にするには…」の補足を削除する |
| §1 main の表 | L45 の「（本番ゲート。自己 approve 可）」を「（本番ゲート）」に直し、`Require review from Code Owners` **ON**・`Restrict who can push to matching branches` **ON（`oshui0404` のみ）** の行を追加 |
| §1「develop と main の差異」表 | 差異が無くなるため、表を「develop と main は同じ設定にする（I178）。」の 1 文に置き換える |
| 新設 §1.5「承認者の限定（I178）」 | 次の 4 点を書く。(a) 理由: このリポジトリは public で、外部（fork）の PR が届く（前例 #257）。bot `osushi0404-bot` は書き込み権限を持つため、承認者を限定しないと、bot の承認や bot 自身の操作でマージ要件を満たせてしまう。Claude 側のガード（I146）は補助の層で、マージは GitHub の権限で止める。(b) 3 つの設定の役割（5 章「修正アプローチ」の 1〜3 と同じ内容）。(c) 「**main には CODEOWNERS が無い**（main は初期コミットのみ）ため、main の Code Owners 要件は develop の内容が main に入るまで効かない。それまでの間は Restrict who can push で守る」。(d) 運用: 「**PR は必ず bot（Claude）が作成する**。ユーザー自身が作った PR は自分で承認できず、bypass も許していないためマージできない」「承認の後に develop への追従（Update branch）などでコミットが入ると承認が取り消されるので、もう一度承認する」「Dependabot の PR も `oshui0404` の承認が必要」。**注意**: §1.5 を含む runbook 全体で「承認不要」という文字列は使わない（以前の状態を説明するときは「承認の要件が無かった」と書く）。TC-08 が旧記述の残存を検知するため、歴史的な説明に同じ文字列があると誤って不合格になる（plan-review 20261017_1916 Info 対応） |
| §3 ステップ 1 | 既存ルール（develop・main）を変更する場合は **Edit** を開く旨を追記し、ステップ 4 の保存ボタンを「既存ルールを Edit した場合は Save changes」と書き分ける（adversarial 第1周 Low 対応） |
| §3 ステップ 3 | develop・main ともに「Require approvals: 1」「Require review from Code Owners」「Dismiss stale pull request approvals」「Restrict who can push to matching branches → `oshui0404` を追加」をオンにする手順に書き換える（develop と main で同じ手順）。並びは GitHub の画面（classic branch protection）に合わせ、「Do not allow bypassing」→「Restrict who can push」の順にする。下位項目「Restrict pushes that create matching branches」は **ON（既定のまま）** と明記する（§1 の表も同じ並び・同じ値。adversarial 第1周 Low 対応） |
| §1.5 追記 | 「main への反映は develop → main の PR（bot が作成・`oshui0404` が承認・マージ）で行う」と、「設定変更直後の develop」（CODEOWNERS を追加した PR #298 が develop に入るまでは develop でも Code Owners 要件が効かず、Restrict who can push で守る）を追記する（adversarial 第1周 Medium・Low 対応） |
| §4 確認 4 | 「main への PR で approval なしに…」を「develop への PR で、`oshui0404` の承認なしにマージできないこと」に変え、確認コマンド `gh pr view <PR番号> --json reviewDecision,mergeStateStatus` と期待値（`REVIEW_REQUIRED`・`BLOCKED`）を書く。main は CODEOWNERS が届くまで bot の承認で `APPROVED` になり得るため、確認 6（push 制限）と設定画面で確認する旨を書く（adversarial 第1周 Medium 対応） |
| §4 確認 5（新規） | bot が承認してもマージ要件を満たさないこと。develop に CODEOWNERS が入った後に行う。手順: ユーザーが develop 宛てに **1 行のファイル変更を含む**確認用 PR を作る（Code Owners の要件はファイル変更を含む PR にだけ働くため、空コミットは不可）→ bot で `gh pr review <PR番号> --approve` → `gh pr view <PR番号> --json reviewDecision,mergeStateStatus` が `REVIEW_REQUIRED`・`BLOCKED` のまま → マージせずに `gh pr close <PR番号> --delete-branch`（adversarial 第1周 Medium 対応・fix-loop 20261018 L1 で `--delete-branch` を追加） |
| §4 確認 6（新規） | bot がマージできないこと（push 制限）。前提（`APPROVED`・BEHIND/DIRTY でない・承認後のコミットなし・必須チェック 5 件 SUCCESS）を `gh pr view <PR番号> --json reviewDecision,mergeStateStatus,headRefOid,reviews,statusCheckRollup` で確かめてから、GitHub のマージ API（`gh api -X PUT repos/osushi0404-dev/study-app-multitenant/pulls/<PR番号>/merge -f merge_method=merge`）を呼び、応答の `message` が push 権限の不足を示すこと。`gh pr merge` は手元で `BLOCKED` を判定して汎用の文で止まり区別できないため使わない（adversarial 第1周・第2周 Medium 対応）。fix-loop 20261018 で次を追加: 実行前に `oshui0404` の了承を得る（設定ミス時は実際にマージされるため）・`gh api -i` で HTTP ステータスも記録する・`message` から URL を除いてから判定する・マージは確認の後に行う（手動テストの流れがある場合はそれに従う） |
| §1.5 Dismiss stale の補足 | 「PR の宛先ブランチの変更（`gh pr edit --base`）では承認が取り消されない可能性がある（未確認・/retro で確認）。宛先が変わった PR は承認の前に差分を確かめ直す」を追記する（fix-loop 20261018 L5・/retro 送り） |
| §4 確認 1・2 | 期待結果を「push が拒否される」に変える（adversarial 第2周 Low 対応）。**bot だけが実行し、`oshui0404` は実行しない**と明記する。`oshui0404` は Restrict の一覧に入っているため、「Do not allow bypassing」の設定を誤っていると確認の操作そのものが develop・main への直接 push として通ってしまう（main は初期コミットだけなので、レビューと CI を経ないコミットがすべて入る）。PR 必須と bypass 不可は設定画面で確認する（adversarial 再ステージ第1周 Medium 対応） |
| §1.5 運用・§6「承認したのに BLOCKED に戻った」 | develop への追従のコミットでは、差分が変わらない場合に承認が残ることもある旨を書き、「取り消された場合だけ再承認」とする（adversarial 再ステージ第1周 Low 対応） |
| §6 緊急手順の追記 | 「Do not allow bypassing」をオンに戻した後、設定画面で §1 の表と突き合わせて戻っていることを確かめる一文を追加する（adversarial 第2周 Low 対応） |
| §5 ロールバック | develop・main の「Require review from Code Owners」「Restrict who can push」を OFF にし、develop だけ「Require approvals」「Dismiss stale approvals」も OFF に戻す（main は承認 1・Dismiss stale ON のまま＝元の値）。CODEOWNERS は revert の PR で削除する（8 章と同じ内容。adversarial 第1周 Low 対応で 8 章に合わせた） |
| §6「main への PR で自分が approve できない」（L194-197） | 見出しを「自分が作った PR を承認・マージできない」に変え、本文を「GitHub では PR の作成者は自分の PR を承認できない。このリポジトリでは bypass も許していないため、ユーザーが作った PR はマージできない。PR は bot（Claude）に作らせる。どうしても必要な場合は、対象ブランチのルールを Edit して『Do not allow bypassing the above settings』を一時的にオフにし、管理者として要件を迂回してマージした後、すぐにオンに戻す（§5 の I178 全体の戻し手順ではマージできない）」に書き換える（adversarial 第1周 Low 対応） |
| §6（新規）「承認したのに BLOCKED に戻った」 | 「承認の後に新しいコミット（develop への追従など）が入ると、Dismiss stale approvals により承認が取り消される。もう一度承認する」 |

### 5-3. `.claude/skills/close/SKILL.md`（変更）

**修正方針**: step 5.5・6 の前提を、実際の設定（Code Owners の承認が必須・承認後のコミットで承認が取り消される）に合わせる。判定ロジック（pr-base-sync の合格条件）は変えない。

L151-152 を次に置き換える:

```
   合格条件は「**BEHIND / DIRTY でない ＋ CI 全グリーン**」（CLEAN は要求しない。develop は
   Code Owners（`oshui0404`）の承認が必須、main は承認 1 件が必須で push・マージできるのは
   `oshui0404` だけの設定のため（main には CODEOWNERS が無い・`docs/runbooks/branch-protection-setup.md`）、
   承認前の正常な最終状態は BLOCKED＝CI 全緑・承認待ちのみ）。
```

（plan-review 20261017_1916 Warning 対応: develop と main で守り方が違うこと（3-3）を区別して書く。）

L156 を次に置き換える:

```
6) ユーザーへ GitHub 上で Approve & Merge を依頼（承認とマージはユーザー `oshui0404` だけが行える。
   承認の後に develop への追従などでコミットが入ると承認は取り消されるため、その場合は再承認を依頼する）
   手動テスト文書に、承認の後・マージの前に行う確認がある場合は、まず承認だけを依頼し、その確認を終えてからマージを依頼する。そのような確認がない場合は、承認とマージを一度に依頼する。
```

（3 行目は fix-loop 20261018 H2 対応で追加。I178 の手動テストでは、承認の後・マージの前に No.6・No.8 を行うため、承認と同時にマージされると確認できなくなる。）

### 5-3b. `scripts/claude/tests/test_i178_branch_protection_doc.sh`（新規・adversarial 第1周 High 対応・第2周 High で方式変更）

**修正方針**: TC-05〜TC-12 は文言がファイルのどこかにあるかしか見ず、§1 の表や §3 の手順を消す・古い設定に戻しても合格してしまう（false-green）。第1周では行ごとの存在確認にしたが、第2周で親スイッチ（Require a pull request before merging）のオフ・矛盾行の併記・空白の違い・コメントで隠す等の後退を取りこぼすと分かった。そのため、runbook と close スキルを見出し行（完全一致）で節ごと（`### develop ブランチ`〜`### main ブランチ`・`### main ブランチ`〜`## 1.5 承認者の限定（I178）`・`### ステップ 3: 各項目を設定`〜`### ステップ 4: 保存`・close の step 5.5〜step 6）に切り出し、スクリプト内の期待値と**全文の完全一致**で比較する。開始・終了の見出しのどちらかが無ければ節は空になり NG。設定を変えるときは、このスクリプトの期待値と 5-5 の表を同時に更新する。対象は環境変数 `RUNBOOK`・`SKILL` で差し替え可能にし、失敗注入に使う（`test_pr_base_sync.sh` の `TARGET_SCRIPT` と同じ方式）。決定論ゲートから `bash scripts/claude/tests/test_i178_branch_protection_doc.sh` で実走する（TC-19）。

**fix-loop 20261018（adversarial 第3周 High・案 A）での追加**: 節の列挙方式では、列挙から漏れた部分（§3 のステップ 2・5、概要、§1.5、§4〜§6、同じ見出しの重複）の後退を検知できなかった。そのため、(1) runbook はファイル全体の SHA-256 をスクリプト内の `RUNBOOK_SHA256` と比較し、一致しなければ NG にする（runbook を正当に直すときは、内容をレビューし、5-5 の表と節の期待値を確かめてから値を更新する）。(2) 節の開始・終了に使う見出し行がファイル内にちょうど 1 回だけであることを確かめる。(3) close step 6 は 3 行（追加した一文を含む）を固定する。close スキルは他のイシューでも変わるため、ファイル全体は固定しない（step 5.5〜6 の外に矛盾する文を足す後退は残余として記録する）。

### 5-4. `scripts/claude/pr-base-sync.sh`（変更しない）

L6「CLEAN は要求しない＝Approve 待ちの BLOCKED は正常」・L114「BLOCKED|UNSTABLE ＝Approve 待ち等」は、新しい設定とそのまま一致する。文言を変える必要が無いため、変更しない（TC-15 で無改変、TC-16 で既存テストの合格を確認）。

### 5-5. GitHub リポジトリ設定（ユーザーが UI で変更・Danger Ops）

Settings → Branches → develop・main それぞれのルールの **Edit** で、次の状態にして **Save changes**。

| 設定項目 | develop | main |
|---|---|---|
| Require a pull request before merging | ON（変更なし） | ON（変更なし） |
| Require approvals | **ON・1**（変更） | ON・1（変更なし） |
| Dismiss stale pull request approvals when new commits are pushed | **ON**（変更） | ON（変更なし） |
| Require review from Code Owners | **ON**（新規） | **ON**（新規） |
| Require status checks to pass before merging（5 件）・up to date | ON（変更なし） | ON（変更なし） |
| Do not allow bypassing the above settings | ON（変更なし） | ON（変更なし） |
| Restrict who can push to matching branches | **ON・`oshui0404` のみ**（新規） | **ON・`oshui0404` のみ**（新規） |
| Restrict pushes that create matching branches（Restrict の下位項目） | ON（既定のまま） | ON（既定のまま） |
| Allow force pushes / Allow deletions | OFF（変更なし） | OFF（変更なし） |

---

## 6. 実装手順

依存関係: ステップ 1 → 2 → 3 は順番に行う（ステップ 1 の TC-04 が不成立なら止める）。ステップ 2 と 3 は互いに独立だが、同じコミット系列で行う。ステップ 4（ユーザー操作）はステップ 1〜3 の push と自動テストの合格が前提。ステップ 5 はマージ後。

### ステップ 1: CODEOWNERS を追加して push し、GitHub に検査させる（未知リスク先行）
- `.github/CODEOWNERS` を 5-1 の内容で新規作成し、コミット・push する。
- → TC-01・TC-02・TC-03・TC-04 参照。TC-04（GitHub の構文検査で errors 0 件）が不成立なら、後続ステップに進まず計画を見直す。

### ステップ 2: runbook を書き換える
- `docs/runbooks/branch-protection-setup.md` を 5-2 のとおり変更する。
- → TC-05〜TC-12・TC-18・TC-19 参照。

### ステップ 3: close スキルを書き換える
- `.claude/skills/close/SKILL.md` L151-152・L156 を 5-3 のとおり変更する。`scripts/claude/pr-base-sync.sh` は変更しない。
- → TC-13〜TC-16 参照。

### ステップ 4: ブランチ保護の変更（ユーザー操作・Danger Ops）
- 事前に、設定を変えると #293 などの作業中 PR にも承認が必要になることをユーザーに伝える。
- ユーザーが 5-5 の表のとおり develop・main を設定し、設定画面で確認する。
- → 手動 No.1〜No.6・No.8 参照（PR #298 を使った確認）。確認が期待どおりにならない場合の分岐は手動テスト文書の「確認が失敗した場合」に従う（No.4・No.5・No.6・No.8・マージ後の No.7・TC-17 のそれぞれ）。

### ステップ 5: マージ後の確認と記録
- PR #298 のマージ後（CODEOWNERS が develop に入った後）に行う。
- 結果は、bot が作る記録用 PR（`docs(I178): マージ後確認の記録`・develop 宛て）で closed のテスト文書に記入し、ユーザーが承認・マージする（adversarial 第2周 Medium 対応）。記録用 PR の対象は No.7・TC-17・No.8 の結果と、レビュー文書の AC 判定表のうち未記入のもの（AC-1 は TC-17 で確定、AC-2〜AC-5 は手動確認の結果。AC-6・AC-7 は /test で記入）（fix-loop 20261018 M3・M4 対応・adversarial 再ステージ第1周 Medium 対応）。
- No.7 または TC-17 が NG の場合は Issue #297 を開き直し、原因を調べて直す（設定の誤りはユーザーが設定画面で、文書・CODEOWNERS の誤りは bot が作る新しい PR で直す）。直した後にやり直し、結果を記録用 PR で記入する（fix-loop 20261018 M4 対応）。
- /close step 6 では承認だけを依頼し、ユーザーは No.5 で Approve だけを押す。マージは No.8 の再承認の後（fix-loop 20261018 H2 対応）。
- → TC-17・手動 No.7 参照。

（マージ前の No.4〜No.6 の結果は /close 中に記入してコミットし、そのコミットで承認が取り消されることを手動 No.8 で確かめた後、ユーザーが再承認してマージする。順番は手動テスト文書の「実施の順番と記録の残し方」を参照）

---

## 7. テスト計画

テストレベル: アプリのコード変更が無いため、ユニット/結合/E2E のアプリテストは非該当。検証は (1) ファイル内容とリポジトリ API への決定論チェック（自動テスト文書）、(2) GitHub 上の PR 状態の実地確認（手動テスト文書）で行う。

- 自動: `docs/tests/open/I178_auto_test.md`（TC-01〜TC-19）
- 手動: `docs/tests/open/I178_manual_test.md`（No.1〜No.8）
- 認可テスト: 本イシューは「誰がマージできるか」という認可の変更にあたる。手動 No.3〜No.7 で、bot の PR は承認待ちになること（No.3・No.4）、管理者の承認で APPROVED になること（No.5）、bot がマージできないこと（No.6）、bot の承認は数えられないこと（No.7）を確認する。
- 再発防止: close スキルの step 5.5 の前提（BLOCKED＝承認待ち）に設定の参照先を書き、文書と設定の対応を明示する。ただし、bot は保護設定を読めず、pr-base-sync は CLEAN も合格として扱うため、設定が緩められたことを close の手順で検知する仕組みは**無い**。機械的な検知は本イシューの範囲外（R7）。

---

## 8. ロールバック

1. GitHub Settings → Branches → develop・main の各ルールの **Edit** で、「Require review from Code Owners」「Restrict who can push to matching branches」を OFF にする。develop は「Require approvals」と「Dismiss stale pull request approvals」も OFF に戻す（main は承認 1・Dismiss stale ON のまま＝元の値）。
2. CODEOWNERS は revert の PR で削除する。
3. runbook と close スキルは同じ revert の PR で元に戻す。

コード・データへの影響は無く、すぐに元に戻せる。

---

## 9. Risk & 回避策

| # | リスク | 回避策 |
|---|---|---|
| R1 | CODEOWNERS の名前が間違っていて、承認できる人がいなくなる | ステップ 1 で TC-03（`oshui0404` が admin）と TC-04（GitHub の構文検査で errors 0 件）を通してから設定を変える |
| R2 | 「Restrict who can push」の対象を入れ忘れて、誰もマージできなくなる | 手動 No.1・No.2 で、ユーザーが設定画面で `oshui0404` が入っていることを確認する。万一の場合も、管理者が設定画面から直せる |
| R3 | main には CODEOWNERS が無く、Code Owners の要件が効かない | Restrict who can push で守る（3-3）。runbook に明記する（TC-10） |
| R4 | ユーザー自身が作った PR がマージできない | PR は bot が作る運用を runbook に明記する（TC-11）。急ぎの場合の手順も書く（5-2 §6） |
| R5 | 設定を変えた時点で、作業中の PR（#293 など）に承認が必要になる | ステップ 4 の前にユーザーへ伝える。増える手間は承認ボタン 1 回 |
| R6 | 承認の後に develop が進むと、追従のコミットで承認が取り消され、再承認が必要になる | grill-me で了承済み。close スキル step 6 と runbook §6 に書く（TC-14・TC-12） |
| R7 | 将来、設定が誰かの操作で緩められても、bot は保護設定を読めないので気づけない | 本イシューの範囲外。現状は検知の仕組みが無い（pr-base-sync は CLEAN も合格として扱い、push 制限のため bot から見た状態が CLEAN になるとも限らない。adversarial 第1周 Medium 対応で、以前の「CLEAN が兆候になる」という記述を取り消した）。機械的な検知は /retro で別イシュー化を判断する |
| R8 | 「Restrict who can push」は classic branch protection の組織リポジトリ専用の設定 | 所有者が Organization であることを確認済み（3-2 #2） |

---

## 10〜15. 条件付きセクション

- 10 データ整合性設計: DB 変更なし（該当なし）
- 11 運用設計: 外部 API・非同期処理・バッチの追加なし（該当なし）
- 12 コスト・保守見積もり: 新しいインフラ・外部サービスなし。運用者の手作業は「PR ごとの承認 1 回（＋追従時の再承認）」だけ増える（4 章）
- 13 性能・UX: フロントエンド変更なし（該当なし）
- 14 学習効果: 該当なし
- 15 プライバシー: 個人情報・テナントデータを扱わない（該当なし）

---

## 16. 承認ポイント

- [ ] CODEOWNERS は `* @oshui0404` の 1 行（＋説明コメント）にする
- [ ] develop・main とも 5-5 の表の設定にする（ユーザーが UI で操作）
- [ ] main には CODEOWNERS が届かないため、main は「Restrict who can push」で守る（3-3。代わりの案は実現できない）
- [ ] `scripts/claude/pr-base-sync.sh` は文言が新しい設定と一致しているため、変更しない
- [ ] `docs/runbooks/workflow.md` は承認要件の前提を書いていないため、変更しない
- [ ] AC-4 の確認（bot が承認しても数えられないこと）はマージ後に行う（CODEOWNERS が develop に入っている必要があるため）
- [ ] 設定変更（ステップ 4）は、ステップ 1〜3 の自動テストが通った後、PR #298 のマージ前に行う
- [ ] 手動 No.6 で、ユーザーの承認後に bot が GitHub のマージ API（`gh api -X PUT .../pulls/298/merge`）を呼び、push 制限で拒否されることを確かめる（実行直前に改めて了承を取る。adversarial 第2周で `gh pr merge` から変更）

## レビュー結果
- [20261018_1409 判定: ✅ 完了](../../reviews/I178_plan_review_20261018_1409.md)
- [20261018_1145 判定: ✅ 完了](../../reviews/I178_plan_review_20261018_1145.md)
- [20261018_1126 判定: ✅ 完了](../../reviews/I178_plan_review_20261018_1126.md)
- [20261017_1926 判定: ✅ 完了](../../reviews/I178_plan_review_20261017_1926.md)
- [20261017_1921 判定: ✅ 完了](../../reviews/I178_plan_review_20261017_1921.md)
- [20261017_1916 判定: ✅ 完了](../../reviews/I178_plan_review_20261017_1916.md)

## セキュリティレビュー結果

**実施日**: 2026-10-17

アプリのコード変更なし（Backend・Frontend・DB の変更なし）。ただし本イシューは GitHub リポジトリの認可（誰が承認・マージできるか）の変更であるため、その設定を対象にレビューした。前提の確認: `.github/workflows/` に `pull_request_target`・`workflow_run` は無く、`push`/`pull_request`（ci・e2e）と `schedule`（dependency-audit・`contents: read`）のみ。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | 認証・認可 | main では CODEOWNERS が届かないため（3-3）、main 宛ての PR は bot（write）の承認 1 件で「承認」の要件を満たせる。その状態をユーザーが見て、外部 PR を誤って main にマージする余地が残る | 必須防御条件: main の「Restrict who can push」を `oshui0404` のみにする（bot・外部はマージ不可）。外部 PR は I146 の手順で close し、bot による fork PR への `review --approve` は I146 のガードが確認を求める。runbook に main の制約を明記する（TC-10） |
| Low | 認証・認可 | bot が PR の中で `.github/CODEOWNERS` を書き換えて自分を所有者に加える | GitHub はベースブランチの CODEOWNERS を使うため、PR の中の書き換えはマージまで効かない。CODEOWNERS 自体が `*` に含まれ、変更には `oshui0404` の承認が要る。残るのは「ユーザーが差分を見ずに承認する」ことだけ（残余リスク） |
| Low | セキュリティ設定ミス | 「Restrict who can push」の対象を空にする・名前を間違える等の設定ミスで、誰もマージできなくなる（可用性）、または制限が効かない | 手動 No.1・No.2 でユーザーが設定画面を確認する。手動 No.6 で bot のマージが失敗することを実地で確かめる |
| なし | マルチテナント | 該当なし（アプリのデータに触れない） | — |
| なし | 入力検証 | 該当なし | — |
| なし | 機密情報 | CODEOWNERS・runbook にはアカウント名のみ。アカウント名は PR・コミット履歴で既に公開されている | — |
| なし | ファイル操作 | 該当なし | — |
| なし | 外部通信 | 該当なし（GitHub の設定のみ） | — |
| なし | 依存ライブラリ | 追加なし | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | develop/main へのマージ | bot（write） | bot が自分の PR、または承認済みの PR を自分でマージする | push 制限（`oshui0404` のみ）でマージが拒否される | No（bot は保護設定を読めない） | Yes: 手動 No.6 | なし | Low |
| 2 | PR の承認 | bot（write） | bot が外部 PR・ユーザーの PR を承認し、develop の承認要件を満たす | Code Owners 必須で、bot の承認は数えられない | No | Yes: 手動 No.7（マージ後） | main は CODEOWNERS が届くまで承認 1 件で満たせる（設計レビュー 1 行目・push 制限で補完） | Low |
| 3 | 承認後の追加 push | bot（write） | ユーザーの承認後に bot が別の変更を push し、承認済みのままマージさせる | Dismiss stale approvals で承認が取り消される | No | Yes: 手動 No.8（No.4〜No.6 の結果を記録するコミットを承認後に push し、`reviewDecision` が `REVIEW_REQUIRED` に戻ることを確かめる。adversarial 第2周で観測任せから専用の確認に変更） | なし | Low |
| 4 | 外部（fork）PR | 外部（権限なし） | fork から PR を出し、マージされるのを待つ | 外部は書き込み権限が無くマージ不可。承認も Code Owners ではないので数えられない | No | No（権限上不可能・I146 で close 手順を定義済み） | ユーザーが中身を確認せずに承認・マージする（運用上のリスク） | Low |
| 5 | CODEOWNERS の改ざん | bot（write） | PR で CODEOWNERS に bot を加える | ベースの CODEOWNERS が使われ、変更自体に `oshui0404` の承認が要る | Yes: TC-02（CODEOWNERS が `* @oshui0404` の 1 行のみ） | No | ユーザーが差分を見ずに承認する | Low |
| 6 | ワークフローの悪用 | bot（write） | PR にワークフローを追加し、Actions のトークンで develop に push・マージさせる | Actions（`github-actions`）は push 制限の許可対象に入っていない | No | No | 秘密情報の持ち出し等、マージ以外の悪用は本イシューの範囲外（既存のリスク） | Low |
| 7 | ブランチ保護の変更 | bot（write） | bot が保護設定を緩める | 設定の変更には admin 権限が必要（bot は 404） | No | No | なし | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 0件 | 0件 |
| Low     | 3件 | 7件 |

### 残余リスク処遇
（/retro で決定する）
