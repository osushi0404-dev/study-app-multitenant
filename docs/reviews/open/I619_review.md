# I619 レビュー: パスキーでログイン

## 変更概要
- パスキー（WebAuthn）の登録・一覧・名前の変更・削除（登録・削除は 5 分の本人確認つき）と、パスキーだけでのログインを足す。移行期間はパスワードのログインも残す（計画: docs/plans/open/plan_I619.md）

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: （実装後に書く。計画の 3 を参照）

## テスト結果
- 自動: （実装後に書く）
- 手動: （test-gate で書く）

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert し、`python manage.py migrate accounts 0023` で表 2 つを消す。backend・frontend のイメージを作り直す

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 画面の配置・流れ・文言はユーザーに案を見せて確定し、それ以外（ライブラリ・challenge を DB に置く・本人確認の印・スロットル・無効化をシグナルで消す・パスキーのログインはロックを見ない・上限 20）は Claude が決めた — 理由は計画書 9
- [plan] e2e コンテナでの RP ID `frontend` は未実証のまま実装ステップ 1 で確かめる — 作業場所の中で chromium が起動せず、Playwright MCP のブラウザは安全なコンテキストの起動オプションを持たない。CI の E2E は localhost で影響しない

STAGE_DONE: plan NEXT: plan-review
