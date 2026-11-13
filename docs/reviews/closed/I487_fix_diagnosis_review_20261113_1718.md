# 診断レビュー [I487]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 根本原因は妥当です。`_current_streak` は今日に答えがあれば今日、無ければ昨日を終点にします（selectors.py:106）。一方、画面は終点を常に今日として `daysBefore(today, days-1)` を呼びます（dashboardAchievements.ts:131）。コードで裏付けが取れています。 | selectors.py:106 / dashboardAchievements.ts:131 |
| Info | 対応方針 | 案 A は裏側と整合します。`today` は `last_days[-1]` から作られ（:192）、`streak` と同じ `scoped` の答えを使います。`today.answered_count>0` は「今日が days に含まれる」と同値です。 | selectors.py:192,199 |
| Info | 影響調査 | `streakRuns` に保存済みの値は、旧計算（終点＝今日）で作られています。今日未解答の日に開いて保存された記録は、案 A の計算結果と食い違います。ただし、これが起きるのは修正前に保存した端末だけです。そのため、1 回だけ再表示される可能性があるという注記で足ります。 | streakRuns |
| Info | 影響調査 | `overview.today` が使えない状況（応答が欠けているなど）の扱いは、サービス側の型検査（dashboard.service.ts:30）で担保されているはずです。実装時にこの点を確認してください。 | dashboard.service.ts |
| Info | 影響調査 | TC-14 の既存ケースは、`today.answered_count` を明示して終点を今日にそろえる必要があります。これは診断メモに記載済みです。加えて、旧挙動で通っていたケースが修正後も正しいことを確認してください。 | dashboardAchievements.test.ts:24 |

## 影響調査の網羅性評価
- 同型バグ: `daysBefore` の呼び出しは `decideAchievements` の 1 か所だけです。grep で確認できました。他の開始日計算はありません。
- 呼び出し箇所: `useDashboardAchievements` だけで、渡す値は変わりません。
- 関連機能: 解答数、正答率、目標達成の判定は開始日を使いません。影響はありません。
- 代替案: B（幅を持たせる方式）は取り違えのリスク、C（API 拡張）は契約変更の範囲拡大という理由で却下されています。トレードオフの根拠は妥当です。
- 日付ずれ（#481）を別範囲とする切り分けも妥当です。

VERDICT: OK
