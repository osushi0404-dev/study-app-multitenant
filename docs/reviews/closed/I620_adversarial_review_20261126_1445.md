# 敵対的レビュー [I620]（別プロセス・2026-11-26 14:45）

- 見た範囲: origin/develop...7039746791ae53467caf2600ae7ada1c1ec65744
- 所要時間: 54 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 1 件は下の表）
- コンテナ: backend を起こして確かめた（19 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I620.md の「## 必ず確かめる項目」（7 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 50 秒 | 1 | 1 | $0.5255 | ― | ― | ― |
| 2 | 報告あり | 24 秒 | 0 | 0 | $0.2411 | ― | ― | ― |
| 3 | 報告あり | 20 秒 | 0 | 0 | $0.2398 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 拒否された
~~~
docker compose exec -T backend bash -c 'ulimit -v 2097152; timeout 60 python manage.py shell -c "
from django.test import Client
from rest_framework.test import APIClient
from accounts.models import User, Organization, OrganizationCategory
from accounts import passkeys
from django.db import transaction
import uuid
transaction.set_autocommit(False)
try:
    cat=OrganizationCategory.objects.create(name=\"x620\",slug=\"x620\")
    org=Organization.objects.create(name=\"x620\",slug=\"x620\",category=cat)
    a=User.objects.create_user(user_id=\"x620a\",password=\"Xx620pass!!\",organization=org,role=\"admin\")
    b=User.objects.create_user(user_id=\"x620b\",password=\"Xx620pass!!\",organization=org)
    c=APIClient(raise_request_exception=False); c.force_authenticate(a)
    t=passkeys.issue_reauth_token(user=a)
    r=c.delete(f\"/api/members/{b.id}/passkeys/{chr(45)*36}/\",HTTP_X_REAUTH_TOKEN=t)
    print(\"STATUS\",r.status_code)
finally:
    transaction.rollback()
" 2>&1 | tail -5'
~~~
出力の先頭:
~~~

~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I620] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | 分岐の抜け道 | パスキー削除の URL の `passkey_id` は正規表現 `[0-9a-f-]{36}` を通れば UUID でなくてもよい。たとえば `-` を 36 個並べた値が通る。`Passkey.objects.filter(pk=passkey_id)` は、UUIDField が不正な値に `ValidationError` を投げるため、404 ではなく 500 になるおそれがある。`pk` 側は `get_object` が `ValidationError` を捕まえて 404 にするが、`delete_passkey_of` には同じ処理が無い。権限の抜け道ではなく、エラーの種類が違うだけ。 | `backend/accounts/registration_links.py` の `delete_passkey_of`、`backend/accounts/views.py` の `delete_member_passkey` | 静的読解のみ。実験 P1-E1 は拒否されたので、実測できていない。 |
| Low | セッション失効 | `revoke_sessions` は `OutstandingToken` の行だけを失効にする。`token_blacklist` を入れる前に発行された refresh トークンは `OutstandingToken` に行が無い。そのため発行後も `/api/auth/refresh/` が通る。access トークンも期限まで有効。デプロイ時点の既存セッションだけに効く過渡期の問題。 | `backend/accounts/registration_links.py` の `revoke_sessions`、`backend/core/settings.py` | 静的読解のみ。 |

V1・V2・V3・V7 の本筋は、読んだ範囲では破れなかった。
- **V1**: `get_queryset` が自組織かつ非運営に絞るので、ほかの組織は 404 になる。`IsOrgMemberManager` が本人ひとりの組織を拒む。
- **V2**: 使用の確定を `select_for_update` の中で再検証している。
- **V3**: 発行時に、パスキーの削除と refresh トークンの失効を同じトランザクションで行っている。
- **V7**: `get_permissions` が書き込みの action に `HasRecentReauth` を足している。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I620] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | テストの網羅 | 期限切れ・失効・無効の利用者・無効の組織のリンクは、`options` の側でしか確かめていない。`complete` の側で確かめているのは「使用済み」だけ（`test_tc06_complete_logs_in` の 2 回目）。今の実装は `complete` でも `options` と同じ `_usable_link` を最初に呼ぶので、挙動は正しい。ただし、`complete_link_registration` の先頭の `_usable_link(lock=False)` と、トランザクション内の `lock=True` の再確認の片方だけを外したり変えたりしても、`expired`・`revoked`・`inactive` では落ちるテストが無い。 | test_I620_registration_links.py:`test_tc05_options_unusable` と `test_tc06_*` | 静的読解。`complete` 側の parametrize が無いことを確かめた。 |
| Low | 競合テストの安定性 | `test_tc07` はバリアで 2 本を同時に出すが、実行の順は決まらない。`select_for_update` を外しても、順番しだいでテストが通る（false-green になる）可能性がある。外したときに必ず落ちる保証は無い。 | `test_tc07_concurrent_complete_only_once` | 静的読解 |

V5 の各項目の確かめ方は次のとおり。
- 次の理由は、`options` で別々の `reason=` のログと同じ文 `LINK_UNUSABLE` を確かめている。各分岐を外すと落ちる。
  - 期限切れ
  - 使用済み
  - 失効
  - 無効の利用者
  - 無効の組織
- 別の用途（`register`）の challenge と、別の利用者の challenge は、`test_tc06_complete_rejects_other_challenges` で確かめている。`consume_challenge` の用途と利用者の確認を外すと、400 にならず 200 になって落ちる。
- 状態は DB を直接 `update` して作っている。実装の分岐をなぞるだけの tautology にはなっていない。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I620] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **V4（リンクの値の平文）**:
  - DB の `RegistrationLink` は `token_hash` だけを持つ。値は URL の `#token=` の後ろに付くので、サーバーのアクセスログにも出ない。
  - `_unusable` と各 `logger.info` が出すのは UUID と reason だけで、値もハッシュも出さない。形が合わないときのログにも値は無い。
  - `WebAuthnChallenge` と `OutstandingToken` にも値は入らない。
  - TC-03 は `RegistrationLink` の全列を見て、TC-11 は caplog で値・ハッシュ・ユーザー ID が無いことを見る。
- **V6（運営の API の境界）**:
  - 運営のアカウントあては `STAFF_TARGET`、本人ひとりの組織は `INDIVIDUAL_TARGET`、自分は `CANNOT_TARGET_SELF` で、どれも 400 になる。
  - 組織の管理者は、`AdminUserViewSet` の `IsAdminUser` で 403 になる。
  - `get_permissions` は `HasRecentReauth` を書き込みの action だけに足す。パスキーの一覧は本人確認なしで読めるが、削除・発行・失効は 403 になる。
  - 運営の範囲で、`member_passkeys` は `_credential_target` を通るので、運営のアカウント・本人ひとりの組織・自分の一覧も 400 になる。
  - 管理コマンドだけが運営のアカウントに発行できる。
- **残るリスク（受け入れ済み）**:
  - 組織の管理者が、同じ組織のほかの管理者あてに発行できる。
  - これは計画で決めた仕様で、発行の前に本人確認があり、ログにも残る。
  - 欠陥には数えない。

> ITEM: V4 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 7039746791ae53467caf2600ae7ada1c1ec65744
ROUNDS: 1
VERDICT: OK
