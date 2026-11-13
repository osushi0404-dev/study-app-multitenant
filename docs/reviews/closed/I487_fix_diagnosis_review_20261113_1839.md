# 診断レビュー [I487]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 対応方針 | `cancelQueries` は、取得がキャンセルされるときにキャッシュを取得前の状態に戻す。`setQueryData` は取得の中断より先に走らないよう、`await` した後に呼ぶこと。案 A はその順序で書かれていて問題ない。 | Settings.tsx:195 |
| Info | 影響調査 | `cancelQueries` は取得を中断するが、`useDailyStudyGoal` の `queryFn` が `signal` を使っていなくても、React Query は古い結果を破棄する。サーバー側のリクエストは走り続けるが、キャッシュには影響しない。 | useDailyStudyGoal.ts:30 |
| Info | 影響調査 | `setQueryData` を呼ぶ箇所は `Settings.tsx` の 1 か所だけで、Grep で確認できた。同型バグはない。 | frontend/src |
| Info | 影響調査 | 保存の前に始まった取得を、保存の後に返すテストの設計は妥当。`cancelQueries` を入れる前はこのテストが落ち、入れた後は通ることを確認すること。 | TC-10d |

## 影響調査の網羅性評価
- 同型のバグは調査済み。`setQueryData` の呼び出しは Settings.tsx:195 の 1 か所だけで、それ以外はテストの初期値設定にしか使われていない。
- `userSettingsKey` を使う箇所は、読み取り側の `useDailyStudyGoal` と書き込み側の `Settings.tsx` で、キーの接頭辞は `USER_SETTINGS_KEY_ROOT` で共通化されている。波及先は十分に確認されている。
- 根本原因は、進行中の取得が保存の後にキャッシュを上書きする競合として成立している。案 A（公式の手順）と案 B（取り直しの短い窓が残る）の比較も妥当で、推奨の理由も示されている。

VERDICT: OK
