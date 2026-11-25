# 敵対的レビュー [I619]（別プロセス・2026-11-24 02:46）

- 見た範囲: origin/develop...734f3258c7fd6865e62c360b14355e78cb387ff3
- 所要時間: 33 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（21 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I619.md の「## 必ず確かめる項目」（8 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 29 秒 | 0 | 0 | $0.2565 | ― | ― | ― |
| 2 | 報告あり | 21 秒 | 0 | 0 | $0.2296 | ― | ― | ― |
| 3 | 報告あり | 25 秒 | 0 | 0 | $0.2487 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I619] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。実験は 1 件も実行しておらず、すべて静的読解で確かめた。

探索した仮説:
- **challenge の使い回し・取り違え**
  - `consume_challenge` は `purpose` と `user` を条件に行を引く。ログイン用は `user=None` で `IS NULL` になるので、本人確認用や登録用の challenge は別の用途として弾かれる。
  - 消費は自前の `atomic` でコミットしてから検証する。そのため、検証に失敗した試行の challenge も 2 度使えない。
  - 期限切れの行は先に削除してから 400 を返す。
- **本人確認の印の偽造・使い回し**
  - 印は `uid` と `iat` を署名したもので、他人の印は `uid` の不一致で弾かれる。
  - 改ざんした印は署名エラーで弾かれる。
  - 期限は `0 <= age <= 300` で判定する。301 秒前の印は 403 になる。
  - 印が無い場合や未認証の場合は `False` になる。
- **他人・別の組織のパスキーへの操作**
  - `get_queryset` は `user=request.user` で絞る。他人のパスキーは 404 になる。
  - 詳細 URL の ID が不正でも、DRF の `get_object_or_404` が 404 に変換する。
  - 本人確認では、`passkey.user_id != user.id` の場合に `owner` で拒む。
- **パスワード総当たり**
  - ロックの判定が先にあり、ロック中は正しいパスワードでも印が出ない。
  - `ATOMIC_REQUESTS` は設定に無い。誤りの回数は例外を投げる前に自前の `atomic` でコミットされるので、ロールバックで消えることはない。
  - スロットル `passkey_reauth` は 5/min。
- **署名回数と無効化の抜け道**
  - 署名回数の巻き戻りは `py_webauthn` の検証に任せている。
  - `update()` で無効にした利用者・組織は、ログイン時の `_is_active` で拒まれる。

TC-30 は E2E ファイルの冒頭で、登録 → ログアウト → ログイン → 削除の流れを扱うと確認した。CI で実際に通ることは、読んだだけでは確かめられていない。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I619] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:

- **検証の差し替え**: `test_I619_passkeys.py` に `mock` や `patch` はありません。`passkeys.py` の `verify_registration_response` と `verify_authentication_response` は本物の py_webauthn が実行されます。ソフトの認証器 `webauthn_soft_authenticator.py` は、本物の ECDSA 署名・COSE 公開鍵・clientDataJSON・authData を組み立てます。そのため、応答が検証を通るのは実際に正しい場合だけです。
- **署名回数の巻き戻り（TC-08 d）**: DB の `sign_count` を 5 に更新し、`sign_count=5` を明示した応答を送ると 400 になります。続けて次の 3 点を確かめています。
  - `sign_count` が 5 のまま変わらないこと。
  - 消費済みの challenge で、正しい 6 を送っても 400 になること（m）。
  - 新しい challenge で 6 を送ると 200 になること。

  応答のうち違うのは回数だけで、origin・user_handle・uv は成功する場合と同じです。そのため、400 になった原因は回数のチェックだけで、他の要因による偶然の拒否ではありません。
- **0/0 の許可（TC-08 e）**: 登録時の回数を 0 にし、`sign_count=0` を明示して 200 を確かめています。`assertion_response` は `if sign_count is None` で判定するので、0 は上書きされません。DB の値が 0 であることも先に assert しています。
- **弱い点（Low）**: `assert_login_rejected` は 400 と固定の文言しか見ません。理由は `reason=` のログにしか残らず、拒否の理由が回数のチェックであることはテストが直接は確かめていません。ただし、上で述べた対照の成功ケースがあるので、実害のある false-green ではありません。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I619] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 設定の強制 | `http://` の origin や合わない RP ID を止めるのはシステムチェックだけだ。`backend/Dockerfile:46` の gunicorn の CMD はチェックを走らせない。`manage.py migrate` や `check` を走らせる手順を通らない本番の起動では、止まらない恐れがある。本番環境はまだ無く、`docker-compose.yml:74` の migrate はチェックを通るので、重大度は Low とする。 | `backend/accounts/checks.py`、`backend/Dockerfile:46` | 静的読解。実機では確かめていない。 |

そのほかの確認結果は次のとおり。
- 無効化の入口は、`post_save` のシグナルで `toggle_active`・`AdminUserViewSet.update`・`save()` を覆っている。`update_fields` に `is_active` を含まない保存だけを飛ばす。
- 組織の無効化も、組織の `post_save` で覆っている。
- queryset の `update()` はシグナルを通らない。しかし `authenticate_passkey` が `_is_active` で拒む（TC-08）。
- ログインの応答は `complete_login` に一本化している。パスワードのログインも同じ関数を使う。
- パスワードの誤りは、`select_for_update` の `atomic` の中で `record_failed_login` を呼ぶ。`PasskeyError` は `atomic` を出てから送出するので、誤りの回数は巻き戻らない。
- ロック中は、正しいパスワードでも印を出さない。
- 本人確認は 5/min のスロットルもある。

探した仮説は 3 つ。
1. 無効化の入口に漏れがないか。
2. 本人確認のパスワード総当たりの競合とロールバック。
3. 本番の設定を止める仕組みの強制力。

> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=read
> ITEM: V8 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 734f3258c7fd6865e62c360b14355e78cb387ff3
ROUNDS: 1
VERDICT: OK
