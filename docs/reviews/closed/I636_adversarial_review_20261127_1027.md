# 敵対的レビュー [I636]（別プロセス・2026-11-27 10:27）

- 見た範囲: c9eec7df7d479af927462f316bd563658ffc94bb...c57931a73f83236366b70273fe1b4b8d3398452d
- 所要時間: 33 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（5 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I636.md の「## 必ず確かめる項目」（4 項目）
- 引き継ぎ: 引き継がない（I636_adversarial_review_20261127_0408.md の REVIEWED_COMMIT c9eec7df7d479af927462f316bd563658ffc94bb から HEAD までに記録の場所の外が変わった: .claude/agents/code-reviewer.md .claude/agents/plan-reviewer.md .claude/hooks/reviewed-hook.sh .claude/hooks/unreviewed.py docs/runbooks/danger-ops.md docs/runbooks/review-rules.md docs/runbooks/workflow.md e2e/tests/registration-link.spec.ts frontend/src/App.tsx frontend/src/components/AccessibilityProvider.tsx frontend/src/components/AppToaster.tsx frontend/src/constants/layout.ts scripts/claude/adversarial-review.sh scripts/claude/code-review.sh scripts/claude/fix-diagnosis-review.sh scripts/claude/fix-review-lib.sh scripts/claude/gate-check.sh scripts/claude/issue-review.sh scripts/claude/plan-issue-review.sh scripts/claude/reviewer-agents-lib.sh scripts/claude/tests/fixtures/i185/workflow_stop_conditions.txt scripts/claude/tests/i599_cases.py scripts/claude/tests/lib_test_snapshot.sh scripts/claude/tests/test_fix_review.sh scripts/claude/tests/test_i193_official_flow.sh scripts/claude/tests/test_i197_adversarial_process.sh scripts/claude/tests/test_i197_review_ledger.sh scripts/claude/tests/test_i202_ledger_cleanup.sh scripts/claude/tests/test_i205_stop_criteria.sh scripts/claude/tests/test_i212_review_base.sh scripts/claude/tests/test_i593_review_from_base.sh scripts/claude/tests/test_review_gates.sh）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 29 秒 | 0 | 0 | $0.3303 | ― | ― | ― |
| 2 | 報告あり | 19 秒 | 0 | 0 | $0.2802 | ― | ― | ― |
| 3 | 報告あり | 15 秒 | 0 | 0 | $0.2563 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I636] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説と結果は次のとおり。実験は出していない（すべて読んで確認）。

- **V1: メンバー管理の入口が同じ条件か。**
  - `User.can_manage_members`（`models.py:178-186`）は、`role=='admin'`・組織あり・`Organization.objects.invitable()` に当たること、の 3 つだけを見る。
  - `IsOrgMemberManager`（`permissions.py:20-22`）と `UserSerializer` の `can_manage_members` は、どちらもこの property を読む。条件が 1 か所にあるので、画面と API が食い違う道は見当たらない。
  - TC-05（`test_I636_member_access.py:50-77`）は、組織の種類 5 つ（有効な招待用・無効・本人ひとり・共有の personal・slug が共有でない personal）を網羅している。役割は、管理者・一般・組織なし・運営の管理者を試している。各ケースで `/api/auth/me/` の真偽と `/api/members/` の 200/403 を照らしている。
  - 運営（`is_staff`）の管理者が招待用の組織にいるケースは、200 側（`staff_admin`）で固定されている。`MemberViewSet` の絞り込みは `is_staff=False, is_superuser=False`（`views.py:296`）のままで、運営のアカウントを相手に見せない。この絞り込みは今回の差分の外で、変わっていない。
  - Low: 運営かつ管理者で、本人ひとり・共有の personal など招待できない組織にいるケースは TC-05 に無い。ただ、判定は `is_staff` を見ない 1 本の式なので、抜け道にはならない。
- **V3: 形の違う ID で 500 にならないか。**
  - `delete_member_passkey`（`views.py:255-263`）は、URL の正規表現が通した 36 文字の値を `uuid.UUID` で読み、`ValueError` なら `Http404` にする。`'-'*36` は空になって `ValueError`、`'0'*36` は桁数の誤りで `ValueError` になり、どちらも 404 になる。
  - `'g'*36` は URL の解決の時点で 404 になる。TC-01 の 3 通りで固定されている。
  - メンバーの ID の形の誤りは、`get_object()` が `ValidationError` を 404 に直す。`test_i636_malformed_member_id_is_404` が確かめている。
  - 別の組織のメンバーの ID は、`_credential_target()` が先に呼ばれて 404 になる。`test_i636_delete_passkey_other_org_member_is_404` が確かめていて、パスキーも残ることを見ている。運営の経路も、形の違う ID で 404 になる（`test_i636_staff_delete_passkey_malformed_id_is_404`）。
  - 残る標準外の形（ハイフンの位置が違う 36 文字）は、既知（F2・#643）として扱う。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I636] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つです。どれも静的読解のみで、実験は実行していません。

- **TC-02 の注入版が、鍵つきの引き直しの有無を見分けられないのではないか。**
  - `_unusable_after_consume` は、本物の `consume_challenge` を呼んだ直後にリンクを使えなくします（test_I620_registration_links.py:443-451）。そのため、1 回目の確かめは通り、リンクを止められるのは鍵つきの引き直し（lock=True）だけです。
  - `_skip_locked_recheck` は `lock=True` のときだけ、確かめずに行を返します。`lock=False` は本物を通します（同 454-463）。
  - 注入版の `test_i636_complete_without_locked_recheck_would_pass` は、期限切れのまま確定まで進んで 200 になります（同 489-497）。
  - 本来の `test_i636_complete_unusable_after_first_check` は 400 と「使用済みの印・Passkey が無いこと」を確かめます。鍵つきの引き直しを外すと、このテストは落ちます。
  - 注入に `revoked` を使わない理由は、「使用済みかつ失効」を禁じる DB の制約が別に止めてしまい、引き直しの有無を見分けられないからです。この理由は妥当です。

- **TC-03（TC-07 と注入版）の待ち合わせの包みが、本物の検証を呼ばずに偽の緑になるのではないか。**
  - `wait_then_create` は、待ち合わせの後に本物の `verify_and_create_passkey` を呼びます（同 567-573）。
  - 鍵がある場合は、2 本目が鍵で待たされて待ち合わせに届きません。そのため、1 本目が 2 秒の時間切れで先へ進み、`broken` に記録されます。2 本目は鍵の後の引き直しで 400 になり、結果は `[200, 400]` になります。
  - 鍵を外した注入版 `_without_row_lock` は、引き直しを `lock=False` にします。2 本とも待ち合わせを通るので `broken` は空になり、結果は `[200, 200]`、Passkey は 2 件になります（同 621-630）。
  - 本来の TC-07 の `results == [200, 400]` と `assert broken` は、この版で落ちます。結果は実行の順に頼らず、鍵の有無で決まります。

- **モックが実装の参照に効かず、空振りしていないか。**
  - `mock.patch.object` の対象は `passkeys` と `registration_links` のモジュール属性です。実装側がモジュール属性として呼ぶ参照を差し替えるので、空振りの根拠は見当たりません。
  - 注入版は 200 や `[200, 200]` という、本来の版と食い違う結果を実際に確かめています。このため、モックが効いていない場合は注入版が落ち、空振りに気づけます。

Low として残す点が 1 つあります。`Barrier(timeout=2)` は CI が極端に遅いと、時間切れ前に 2 本が揃う余地があります。ただし計画書 R3 で受け入れ済みで、手動テスト No.1 の 10 回の記録でも担保されているため、新規の指摘にはしません。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I636] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。`registration_links.py` を Read で確かめた。実験は実行していない。

- **ログと応答に例外の中身・ユーザー ID が出る。**
  - ログは `organization_id` だけを出す（`registration_links.py:166`）。
  - 応答は固定文 `DUPLICATE_USER_ID` の `ValidationError` だけで、`IntegrityError` の中身は載らない（:167）。
  - `raise` は `except` の中にあるので、例外の連鎖が `__context__` に残る。DRF の応答には出ない。
- **外側のトランザクションが壊れる。**
  - `transaction.atomic()` は `create_user` だけを囲む（:163-164）。
  - `IntegrityError` は `with` の外で受ける。ロールバックされるのはセーブポイントだけで、外側のトランザクションは有効なまま残る。
- **別の制約の違反を「重複」と誤報する。**
  - 渡す値は `user_id`・組織・役割だけで、`email` は `None`。docstring のとおり、実質 `user_id` の重複に限られる。
  - 組織は既存の行なので、外部キー違反は起きない。

この範囲の差分のうち、V4 に関わる backend の変更は無い。差分は `Settings.tsx` 周りとハーネス・記録の文書が中心で、V4 の挙動は前の周から変わらない。

> 補足（Low・新規ではなく数えない）: 5 本の入口のうち `plan-issue-review.sh` の `force_plan_highrisk` は、VERDICT の無い出力にも「判定: Yes」の節を足す。出力が壊れていても UNKNOWN にならず HIGHRISK 扱いになる。ただし倒れる側は高リスク（厳しい側）で、通らない側ではない。code-review の組み込みレビューも同じ点を指摘している。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: c57931a73f83236366b70273fe1b4b8d3398452d
ROUNDS: 1
VERDICT: OK
