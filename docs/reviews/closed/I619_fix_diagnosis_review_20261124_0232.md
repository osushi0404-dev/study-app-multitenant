# 診断レビュー [I619]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | F2 は `models.py:187-192` を読んで確認できた。`record_failed_login()` は期限切れの判定をせずに `failed_login_attempts` を加算する。成功時か `unlock_account()` の呼び出し時にしか 0 に戻らない。診断メモの説明と一致する。 | `backend/accounts/models.py:187-192` |
| Info | 対応方針 | F2 案 A では、期限切れの判定を「`account_locked_until` があり、かつ `is_account_locked()` が偽」とする。これなら、ロックされたことのない（`account_locked_until` が None の）利用者の回数は戻らず、1〜4 回の誤りは累積する。テストにもこの境界を入れておくとよい。入れる内容は、ロックなしで 3 回間違えた後は 4 回になること、期限切れの後は 1 になることの 2 点。 | F2 案 A |
| Info | 影響調査 | `passkeys.py:282-289` の本人確認と `serializers.py:156-183` のログインが `record_failed_login` と `is_account_locked` を呼ぶことは、grep で確認できた。どちらも直しで同じ規則になる。ただし `serializers.py:176` の `failed_user` が最新の行かは、メモで触れていない。古いインスタンスを使っていると、期限切れの判定にずれが出うる。実装時に確認するとよい。 | `serializers.py:176` |
| Info | 対応方針 | F1 案 A は妥当。`validate()` で `name` の有無を見る方法は、一覧の出力に影響しない。`partial=True` でも `validate()` は走るため、直しが効く。 | `views.py:153` |

## 影響調査の網羅性評価
- **同型バグ**: F1 は、`validated_data[...]` を直接読む箇所を ViewSet 内で調べてある。`register` と `AdminUserViewSet` も除外理由つきで確認している。F2 は、回数とロック期限を書く箇所を `record_failed_login`・`unlock_account`・管理画面に絞り込んである。grep の結果とも一致した。
- **呼び出し元**: `is_account_locked` の呼び出し元（ログイン・本人確認・管理画面）を挙げている。パスキーのログインがロックを見ないことも明記してある。
- **案の比較**: 各項目で 3 案を比べ、推奨の理由とセキュリティ面の評価を書いてある。
- **AC11 との関係**: ロックの欠陥の修正であり、ログインの成否の判定は変わらないと説明してある。
- **テスト計画**: 失敗注入つきで、F1 は `PATCH {}`、F2 は本人確認とパスワードのログインの両方を対象にしている。
- 重大な欠落はない。

VERDICT: OK
