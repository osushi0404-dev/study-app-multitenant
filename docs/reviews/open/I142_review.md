# I142 実装後レビュー

- 関連イシュー: #253
- 計画書: docs/plans/open/plan_I142.md
- Draft PR: #256
- レビュー日時: （実装後に記入）
- レビュー結果: （OK / NG）

## レビュー対象
| ファイル | 変更内容 | 確認結果 |
|----------|----------|----------|
| `backend/core/exceptions.py` | 非 APIException 分岐（ログ+統一 JSON 500）・`EnvironmentMisconfiguredError` 追加 | |
| `backend/core/settings.py` | INSTALLED_APPS に `rest_framework_simplejwt.token_blacklist` 追加 | |
| `backend/accounts/views.py` | 登録 / validate-slug / logout の例外設計再構成 | |
| `backend/accounts/tests/test_I142_error_handling.py` | 新規回帰テスト（TC-AUTO-01〜10） | |
| `backend/accounts/tests/test_I140_personal_org_fallback.py` | personal 不在時の期待値 400→500（TC-AUTO-11/12） | |
| `rules/ultimate_django_coding_standards.md` | エラーハンドリング方針の明文化・既存コード例の整合 | |

## 受け入れ条件の充足確認
| AC | 内容 | 検証手段 | 結果 |
|----|------|----------|------|
| 1 | 広域 `except Exception` が意図的な 1 箇所のみ | TC-DET-01 | |
| 2 | 想定内 4xx の既存契約が不変 | TC-AUTO-05/07〜10・TC-AUTO-13 | |
| 3 | personal 不在は統一 JSON 500 | TC-AUTO-11/12 | |
| 4 | 想定外例外が 500 + スタックトレース記録 | TC-AUTO-01/02/04 | |
| 5 | DEBUG 時のみ例外詳細を露出 | TC-AUTO-03 | |
| 6 | logout が 200 + トークン失効 | TC-AUTO-06 | |
| 7 | 既存テスト全 PASS（baseline 94） | TC-AUTO-14 | |
| 8 | 規約の明文化と既存コード例の整合 | TC-DET-02 | |
| 9 | FE 導線の実動作退行なし | 手動テスト No.5〜10 | |

## レビュー観点（本イシュー固有）
- [ ] 想定内エラーの分岐が「例外任せ」でなく明示的な条件分岐で書かれているか（logout・登録の非 dict body）
- [ ] 新設した広域でない `except` が捕捉する例外型が、実際に発生し得る型と一致しているか（`TokenError` の import 元が `rest_framework_simplejwt.exceptions` か）
- [ ] `custom_exception_handler` の非 APIException 分岐が、`Http404` / `PermissionDenied` / `Ratelimited`（429/403 経路）を巻き込んでいないか
- [ ] `DEBUG=False` で例外メッセージ・スタックトレースが応答 body に漏れていないか
- [ ] 意図的に残す広域 except（メール送信）に理由コメントがあるか
- [ ] `token_blacklist` 追加に伴うマイグレーションが自作されていないか（simplejwt 同梱のみを使用しているか）
- [ ] テストが本番コードに注入点を作っていないか（`mock.patch` が ORM 境界に限定されているか）
- [ ] 計画書に記載のないファイル変更が含まれていないか（特に `accounts/views.py:90` の平文パスワードログは I144 送りで**変更しない**）

## セキュリティレビュー観点
- [ ] エラー応答から内部情報（例外文字列・SQL・パス）が本番設定で漏れないか
- [ ] logout のトークン失効が実際に機能しているか（再利用で 400）
- [ ] bandit MEDIUM 以上の新規指摘がないか（pre-commit）

## 指摘事項
（実装後に記入）

## 総評
（実装後に記入）
