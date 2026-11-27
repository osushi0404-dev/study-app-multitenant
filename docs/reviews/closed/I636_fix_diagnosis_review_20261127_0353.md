# 診断レビュー [I636]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 原因は成立しています。`Settings.tsx:159-176` を確認しました。効果に後片付けがなく、`getUserSettings` の応答で無条件に `resetSettingsForm` を呼びます。StrictMode の二重実行と、遅れて届く 2 回目の応答という機序が、「並行時だけ 50 に戻る」症状を説明できます。ただし、2 回目の応答が入力より後に届いた順序はログで直接確認していません。Jest で再現する計画なので、これで補えます。 | 根本原因 |
| Info | 対応方針 | 案 A では、`ignore` のガードを `finally` の `setLoading(false)` にも付けるかどうかが曖昧です。メモには `setLoading` をしないと書いてあります。ただし 1 回目を捨てて 2 回目だけが `loading` を解除する形になり、これで問題はありません。実装時にこの点を取り違えないでください。 | 案 A |
| Info | 影響調査 | `getUserSettings` の呼び出し元に `NotificationContext.tsx:59` と `useDailyStudyGoal.ts:22` があります。どちらもフォームを `reset` しないため同型ではありません。メモには明記がないので、補記すると確実です。 | 影響調査 1 |
| Info | 影響調査 | TC-30 の原因として挙げた `api.ts:142` の `/api/auth/token/refresh/` と、`backend/accounts/urls.py:31` の `auth/refresh/` の食い違いは、コードで確認できました。`auth.service.ts:56` にも同じ `token/refresh/` があり、同じ食い違いの別箇所です。retro でイシュー化するときは、この箇所も含めてください。この fix-loop で直さない判断は妥当です。 | 影響調査 3 |

## 影響調査の網羅性評価
- **同型バグ**: 調査済みです。取得した応答でフォームを `reset` する箇所は `Settings.tsx` だけでした。`QuizManagement`、`SubjectManagement`、`AddMemberDialog`、`PasskeyRenameDialog` は、私の grep の結果とも一致します。
- **関連機能**: 保存後のキャッシュ処理、通知、テーマとの切り分けができています。
- **計画との関係**: `Settings.tsx` が計画の実装対象に無いことを認識しています。計画変更と plan-review を通し直す手順も書かれています。
- **別の落ち方**: TC-30 は別原因として切り分けられています。
- **対応方針**: 4 案を比較し、推奨理由も示されています。

重大な欠落はありません。

VERDICT: OK
