# 敵対的レビュー [I636]（別プロセス・2026-11-27 03:42）

- 見た範囲: origin/develop...a233e69f50fa912ae0295b8032c94bdec1bf109c
- 所要時間: 29 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（18 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I636.md の「## 必ず確かめる項目」（4 項目）

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
| 1 | 報告あり | 22 秒 | 0 | 0 | $0.2522 | ― | ― | ― |
| 2 | 報告あり | 27 秒 | 0 | 0 | $0.2616 | ― | ― | ― |
| 3 | 報告あり | 19 秒 | 0 | 0 | $0.2340 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I636] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **形の違う `passkey_id`（V3）**: `views.py` の `delete_member_passkey` は、先に `_credential_target()` を通る。ここで `get_object()` が走り、他の組織のメンバーの ID は 404 になる。続く `uuid.UUID(passkey_id)` は、`-` が 36 個の ID や `0` が 36 個の ID で `ValueError` を出し、`Http404` に変わる。32 桁の 16 進に `-` を混ぜた ID は UUID として読める。そのときは `delete_passkey_of` の `filter(...).first()` が `None` を返し、404 になる。運営の `AdminUserViewSet` も同じミックスインを使うので、同じ直しが効く。
- **メンバー管理の入口が同じ条件か（V1）**: `User.can_manage_members` は `role == 'admin'`、組織あり、`Organization.objects.invitable()` の 3 条件だけで決まる。これは前の `IsOrgMemberManager` と同じ条件だ。`is_staff` は条件に入っていないので、運営の管理者の扱いは前と変わらない。TC-05 は次の 8 通りで `/api/auth/me/` の `can_manage_members` と `/api/members/` の 200/403 の一致を確かめている。
  - 管理者: 有効な招待用の組織・無効な組織・本人ひとりの組織・共有の personal・slug が共有でない personal
  - 一般の利用者
  - 運営の管理者
  - 組織なしの管理者
  - 軽微な懸念（Low）: `UserSerializer` を使う場所では、`can_manage_members` が利用者ごとに組織の問い合わせを 1 回増やす。`organization_name` と同じ外部キーなので、`select_related` 済みなら増えない。重大ではない。

どちらの項目も、実験なしで読んで確かめられた。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I636] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。
- **TC-02 が引き直しの有無を見分けられないのではないか。**
  - `complete_link_registration`（`registration_links.py:140-144`）は、1 回目の確かめ、`consume_challenge`、鍵つきの引き直しの順に進む。
  - `_unusable_after_consume` は本物の `consume_challenge` を呼んだ直後にリンクを使えなくする。そのため 1 回目の確かめは通り、止められるのは鍵つきの引き直しだけになる。
  - 注入版の `_skip_locked_recheck` は `lock=True` のときだけ確かめずに行を返す。1 回目の `lock=False` は本物を通す。
  - よって注入版では期限切れのまま `verify_and_create_passkey` と `used_at` の確定まで進み、200 になる。本来のテストは 400 を期待するので落ちる形になっている。
  - `revoked` を注入の種類にしない理由は、DB の制約が確定を止めるためと計画変更記録に書かれている。これは妥当。
- **TC-03 の待ち合わせが偽の緑になるのではないか。**
  - 包みは本物の `verify_and_create_passkey` を、待ち合わせの後で呼んでいる。
  - 鍵がある場合、2 本目は `select_for_update` で待たされ、待ち合わせに届かない。1 本目だけが 2 秒で時間切れになって先へ進み、`broken` が記録される。結果は `[200, 400]` になる。
  - 鍵を外した注入版では、両方が待ち合わせを通って `broken` が空になり、`[200, 200]` と Passkey 2 件になる。本来のテストの `assert broken` と `== [200, 400]` が落ちる。
  - 実行順に頼らない作りになっている。
- **モックが別のモジュール参照に効かず、空振りしていないか。**
  - `registration_links` は `from . import passkeys` で `passkeys.consume_challenge` を呼ぶ。`mock.patch.object(passkeys, ...)` はこの参照に効く。
  - `_usable_link` も同じモジュールの属性として呼ばれるので、`patch.object(registration_links, "_usable_link")` が効く。

指摘は Low 以下にも挙げるものがない。AC3 の「10 回流して記録」は手動テスト側の作業なので、読んだだけでは確認できない。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I636] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。

探索した仮説（差分とテストの読解のみ。実験は実行していない）:
- **例外の中身とユーザー ID がログと応答に漏れる**
  - `create_member` のログは `organization_id` だけで、`user_id` も例外の文字列も出さない。
  - 応答は固定文 `DUPLICATE_USER_ID` の `ValidationError` だけ。`IntegrityError` の内容は応答に載らない。
  - `ValidationError` は `except` 節で raise している。そのため `__context__` に `IntegrityError` が残るが、DRF の例外ハンドラは `ValidationError` をログに出さないので外へ出ない。
  - `test_i636_create_member_race_is_400` が `racer` の文字列がログに無いことを確かめている。
- **`transaction.atomic()` の中で受けて、外側のトランザクションを壊さないか**
  - `with transaction.atomic()` の内側（セーブポイント）で `create_user` を呼び、`IntegrityError` は `with` の外で受けている。違反でセーブポイントだけがロールバックされ、外側は有効なまま残る。
  - 同じテストが、競合の後に `User.objects.filter(...)` を発行して通っている。`pytest.mark.django_db` は外側を `atomic` で包むので、壊れていれば `TransactionManagementError` で落ちる。
- **`IntegrityError` が別の制約の違反を「重複」と誤報する**
  - `create_user` に渡すのは `user_id`・組織・役割だけ。`email` は `None` で、一意の制約は `user_id` だけと読める。この想定は `create_user` と `User` モデルを開いて確かめていない。
  - 組織は `request.user.organization` で、存在する行を渡している。そのため外部キー違反は現実には起きない。誤報の余地は実質ない。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: a233e69f50fa912ae0295b8032c94bdec1bf109c
ROUNDS: 1
VERDICT: OK
