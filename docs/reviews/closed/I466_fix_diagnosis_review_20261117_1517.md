# 診断レビュー [I466]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 原因は成立しています。e2e/ 内の overview 固定応答は `dashboard-layout.spec.ts` の 1 か所だけで、`recommendations: []` の行はあるのに `weak_difficulties`・`rushed_mistakes` は無いと grep で確認しました。画面側は欠けたキーをエラーにする決まりなので、4 件が落ちる筋は通っています。 | dashboard-layout.spec.ts:28 |
| Info | 対応方針 | 案 A の推奨は妥当です。案 B は I473 の決まりに反するため、棄却理由に納得できます。案 C は範囲外として retro に回す判断も適切です。 | 対応方針 |
| Info | 影響調査 | 推奨案を実装するときは、390px の横はみ出しの確認を同じ TC に入れてください。TC-23 の高さ（900px に収まるか）は、E2E の実行後に CI で確かめてください。 | TC-21〜23・26 |

## 影響調査の網羅性評価
- 同型の箇所は調べられています。e2e/ 内の overview 固定は 1 か所だけです。frontend の単体テストは修正済みです。
- 私の grep でも、`dashboard/overview` を参照するテストは `dashboard-layout.spec.ts` と `Dashboard.test.tsx` の 2 つ、バックエンドのテスト、OpenAPI でした。診断メモの内容と矛盾はありません。
- 統計画面（`/api/dashboard/analytics/`）は契約を変えていないので影響なしで、この判断は妥当です。
- 再発防止は「契約のキーを足すときは e2e/ も grep する」を記録し、型で縛る案 C は retro に回す方針です。これで足ります。

VERDICT: OK
